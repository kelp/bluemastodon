"""Bluesky API client for bluemastodon.

This module handles interactions with the Bluesky API, including authentication,
fetching posts, and parsing post content.
"""

from datetime import datetime, timedelta
from typing import Any

from atproto import Client as AtProtoClient
from atproto.exceptions import AtProtocolError
from loguru import logger

from bluemastodon.config import BlueskyConfig
from bluemastodon.models import BlueskyPost, Link, MediaAttachment, MediaType


class BlueskyClient:
    """Client for interacting with the Bluesky API."""

    def __init__(self, config: BlueskyConfig):
        """Initialize the Bluesky client.

        Args:
            config: Bluesky configuration with credentials
        """
        self.config = config
        self.client = AtProtoClient()
        self._authenticated = False

    def authenticate(self) -> bool:
        """Authenticate with the Bluesky API.

        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            self.client.login(
                self.config.username,
                self.config.password,
            )
            self._authenticated = True
            logger.info(f"Authenticated as {self.config.username}")
            return True
        except AtProtocolError as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def ensure_authenticated(self) -> bool:
        """Check authentication and re-authenticate if needed.

        Returns:
            True if authenticated, False otherwise
        """
        if not self._authenticated:
            return self.authenticate()
        return True

    def get_recent_posts(
        self, hours_back: int = 24, limit: int = 20, include_threads: bool = True
    ) -> list[BlueskyPost]:
        """Get recent posts from the authenticated user.

        Args:
            hours_back: How many hours to look back
            limit: Maximum number of posts to return
            include_threads: Whether to include self-replies (threads)

        Returns:
            List of BlueskyPost objects

        Raises:
            ValueError: If not authenticated
        """
        if not self.ensure_authenticated():
            raise ValueError("Not authenticated with Bluesky")

        # Get user profile and DID
        profile = self._get_user_profile()
        if profile is None:
            logger.error("Failed to get user profile")
            return []

        # Fetch the user's posts
        feed_response = self._fetch_author_feed(profile.did, limit)
        if not feed_response or not hasattr(feed_response, "feed"):
            return []

        # Filter and convert posts
        since_time = datetime.now() - timedelta(hours=hours_back)
        posts = []

        for feed_view in feed_response.feed:
            if self._should_include_post(
                feed_view, since_time, profile.did, include_threads
            ):
                posts.append(self._convert_to_bluesky_post(feed_view, profile))

        return posts

    def _get_user_profile(self) -> Any:
        """Get the authenticated user's profile."""
        try:
            return self.client.app.bsky.actor.get_profile(
                {"actor": self.config.username}
            )
        except AtProtocolError as e:
            logger.error(f"Error fetching user profile: {e}")
            return None

    def _fetch_author_feed(self, author_did: str, limit: int) -> Any:
        """Fetch posts from the specified author."""
        try:
            return self.client.app.bsky.feed.get_author_feed(
                {
                    "actor": author_did,
                    "limit": limit,
                }
            )
        except AtProtocolError as e:
            logger.error(f"Error fetching posts: {e}")
            return None

    def _should_include_post(
        self,
        feed_view: Any,
        since_time: datetime,
        user_did: str,
        include_threads: bool = True,
    ) -> bool:
        """Determine if a post should be included based on filters.

        Args:
            feed_view: The feed view containing the post
            since_time: The cutoff time for posts
            user_did: The DID of the authenticated user
            include_threads: Whether to include self-replies (threads)

        Returns:
            True if the post should be included, False otherwise
        """
        post = feed_view.post

        # Skip reposts
        if feed_view.reason:
            return False

        # Handle replies:
        # - Skip replies to others
        # - Include self-replies (threads) if enabled
        if hasattr(post.record, "reply") and post.record.reply:
            # If include_threads is False, skip all replies
            if not include_threads:
                return False

            # If include_threads is True, check if it's a self-reply (thread)
            if hasattr(post.record.reply, "parent") and hasattr(
                post.record.reply.parent, "author"
            ):
                # If the parent author is not the same as the current user, skip it
                parent_author_did = getattr(
                    post.record.reply.parent.author, "did", None
                )
                if parent_author_did != user_did:
                    return False
            else:
                # If we can't determine the parent author, skip it to be safe
                return False

            # Log that we're including a thread post
            logger.info(f"Including thread post (self-reply): {post.uri}")

        # Skip older posts
        created_at = datetime.fromisoformat(
            post.record.created_at.replace("Z", "+00:00")
        )
        # Make sure we're comparing offset-aware datetimes
        if since_time.tzinfo is None:
            since_time = since_time.replace(tzinfo=created_at.tzinfo)
        if created_at < since_time:
            return False

        return True

    def _convert_to_bluesky_post(self, feed_view: Any, profile: Any) -> BlueskyPost:
        """Convert Bluesky API post to BlueskyPost model."""
        post = feed_view.post
        created_at = datetime.fromisoformat(
            post.record.created_at.replace("Z", "+00:00")
        )

        media_attachments = self._extract_media_attachments(post)
        links = self._extract_links(post)

        # Check if this is a reply
        is_reply = hasattr(post.record, "reply") and post.record.reply is not None
        reply_parent_id = None
        reply_root_id = None

        # Extract parent and root IDs if this is a reply
        if is_reply:
            # Get parent post
            if hasattr(post.record.reply, "parent") and hasattr(
                post.record.reply.parent, "uri"
            ):
                parent_uri = post.record.reply.parent.uri
                reply_parent_id = parent_uri.split("/")[-1] if parent_uri else None
                logger.info(
                    f"Found that post {post.uri} is a reply to parent: {parent_uri}"
                )

                # Check if it's a self-reply (thread)
                parent_author_did = None
                if hasattr(post.record.reply.parent, "author") and hasattr(
                    post.record.reply.parent.author, "did"
                ):
                    parent_author_did = post.record.reply.parent.author.did
                    if parent_author_did == profile.did:
                        logger.info("Detected a thread (self-reply) to user's own post")

            # Get root post (if different from parent)
            if hasattr(post.record.reply, "root") and hasattr(
                post.record.reply.root, "uri"
            ):
                root_uri = post.record.reply.root.uri
                reply_root_id = root_uri.split("/")[-1] if root_uri else None
                if root_uri != parent_uri:
                    logger.info(f"Thread has different root: {root_uri}")

        return BlueskyPost(
            id=post.uri.split("/")[-1],
            uri=post.uri,
            cid=post.cid,
            content=post.record.text,
            created_at=created_at,
            author_id=profile.did,
            author_handle=self.config.username,
            author_display_name=(
                profile.display_name if hasattr(profile, "display_name") else None
            ),
            media_attachments=media_attachments,
            links=links,
            is_reply=is_reply,
            is_repost=False,
            in_reply_to_id=reply_parent_id,
            reply_parent=reply_parent_id,  # For Bluesky, direct parent
            reply_root=reply_root_id,  # For Bluesky, root of the thread if different
            visibility="public",
            like_count=post.like_count if hasattr(post, "like_count") else None,
            repost_count=post.repost_count if hasattr(post, "repost_count") else None,
        )

    def _extract_media_attachments(self, post: Any) -> list[MediaAttachment]:
        """Extract media attachments from a post."""
        attachments: list[MediaAttachment] = []

        if not (hasattr(post.record, "embed") and post.record.embed):
            return attachments

        if hasattr(post.record.embed, "images"):
            for img in post.record.embed.images:
                blob = img.image
                attachments.append(
                    MediaAttachment(
                        url=self._get_blob_url(post, blob.ref.link),
                        alt_text=img.alt if hasattr(img, "alt") else None,
                        media_type=MediaType.IMAGE,
                        mime_type=(
                            blob.mime_type if hasattr(blob, "mime_type") else None
                        ),
                        width=blob.size.width if hasattr(blob, "size") else None,
                        height=blob.size.height if hasattr(blob, "size") else None,
                    )
                )

        return attachments

    def _extract_links(self, post: Any) -> list[Link]:
        """Extract links from a post."""
        links: list[Link] = []

        if not (hasattr(post.record, "embed") and post.record.embed):
            return links

        if hasattr(post.record.embed, "external"):
            ext = post.record.embed.external
            links.append(
                Link(
                    url=ext.uri,
                    title=ext.title,
                    description=(
                        ext.description if hasattr(ext, "description") else None
                    ),
                    image_url=(
                        self._get_blob_url(post, ext.thumb.ref.link)
                        if hasattr(ext, "thumb")
                        else None
                    ),
                )
            )

        return links

    def _get_blob_url(self, post: Any, ref: str) -> str:
        """Convert a blob reference to a URL.

        Args:
            post: The post containing the blob
            ref: The blob reference

        Returns:
            URL to the blob
        """
        # For simplicity, we're using a basic approach
        # In a production app, you might want to download and re-upload the media
        return (
            f"https://bsky.social/xrpc/com.atproto.sync.get_blob"
            f"?did={post.author.did}&cid={ref}"
        )
