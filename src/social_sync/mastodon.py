"""Mastodon API client for social-sync.

This module handles interactions with the Mastodon API, including authentication,
posting content, and checking for duplicates.
"""

import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

from loguru import logger
from mastodon import Mastodon

from social_sync.config import MastodonConfig
from social_sync.models import MastodonPost, MediaAttachment, MediaType, SocialPost


class MastodonClient:
    """Client for interacting with the Mastodon API."""

    def __init__(self, config: MastodonConfig):
        """Initialize the Mastodon client.

        Args:
            config: Configuration for the Mastodon API
        """
        self.config = config
        self.client = Mastodon(
            access_token=config.access_token,
            api_base_url=config.instance_url,
        )
        self._authenticated = False
        self._account = None

    def verify_credentials(self) -> bool:
        """Verify the credentials for the Mastodon client.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            self._account = self.client.account_verify_credentials()
            self._authenticated = True
            username = self._account.username if self._account else "unknown"
            logger.info(f"Authenticated with Mastodon as {username}")
            return True
        except Exception as e:
            logger.error(f"Mastodon authentication failed: {e}")
            return False

    def ensure_authenticated(self) -> bool:
        """Check authentication and re-verify if needed.

        Returns:
            True if authenticated, False otherwise
        """
        if not self._authenticated:
            return self.verify_credentials()
        return True

    def post(self, post: SocialPost) -> Optional[MastodonPost]:
        """Post content to Mastodon.

        Args:
            post: The post to create on Mastodon

        Returns:
            MastodonPost object if successful, None if failed
        """
        if not self.ensure_authenticated():
            logger.error("Cannot post to Mastodon: Not authenticated")
            return None

        try:
            # Check for duplicate content
            is_duplicate, existing_post = self._is_duplicate_post(post.content)
            if is_duplicate:
                # Handle both cases: when we have the existing post info or not
                if existing_post:
                    logger.info(
                        f"Skipping duplicate post on Mastodon: {post.content[:50]}..."
                    )
                    try:
                        return self._convert_to_mastodon_post(existing_post)
                    except Exception as e:
                        logger.warning(f"Error converting existing post: {e}")
                        # Fall back to a minimal post if conversion fails
                        minimal_post = MastodonPost(
                            id=(
                                str(existing_post.id)
                                if hasattr(existing_post, "id")
                                else "duplicate"
                            ),
                            content=post.content,
                            created_at=datetime.now(),
                            author_id="",
                            author_handle="",
                            author_display_name="",
                            media_attachments=[],
                            url=(
                                existing_post.url
                                if hasattr(existing_post, "url")
                                else ""
                            ),
                        )
                        return minimal_post
                else:
                    logger.info(
                        f"Duplicate detected but post info not available: "
                        f"{post.content[:40]}..."
                    )
                    # Create a minimal post object to indicate success without posting
                    minimal_post = MastodonPost(
                        id="duplicate",
                        content=post.content,
                        created_at=datetime.now(),
                        author_id="",
                        author_handle="",
                        author_display_name="",
                        media_attachments=[],
                        url="",
                    )
                    return minimal_post

            # Apply character limits
            content = self._apply_character_limits(post.content)

            # Upload media if present
            media_ids: List[str] = []
            if post.media_attachments and len(post.media_attachments) > 0:
                for attachment in post.media_attachments:
                    # Skip if no URL is provided
                    if not attachment.url:
                        continue

                    try:
                        # Download and upload the media
                        # For now, we'll stub this - real implementation would download
                        # and then upload to Mastodon
                        logger.info(f"Would upload media: {attachment.url}")
                        # media_id = self._upload_media(attachment)
                        # media_ids.append(media_id)
                    except Exception as e:
                        logger.error(f"Error uploading media to Mastodon: {e}")

            # Create the post
            toot = self.client.status_post(
                status=content,
                media_ids=media_ids if media_ids else None,
                sensitive=post.sensitive if hasattr(post, "sensitive") else False,
                visibility=(
                    post.visibility
                    if hasattr(post, "visibility") and post.visibility
                    else "public"
                ),
                spoiler_text=(
                    post.spoiler_text
                    if hasattr(post, "spoiler_text") and post.spoiler_text
                    else None
                ),
            )

            logger.info(
                f"Posted to Mastodon: {toot.url if hasattr(toot, 'url') else 'No URL'}"
            )
            return self._convert_to_mastodon_post(toot)

        except Exception as e:
            logger.error(f"Error posting to Mastodon: {e}")
            return None

    def _is_duplicate_post(self, content: str) -> Tuple[bool, Optional[Any]]:
        """Check if a similar post already exists on Mastodon.

        Args:
            content: The content to check for duplication

        Returns:
            Tuple of (is_duplicate, matching_post)
            - is_duplicate: True if similar post exists, False otherwise
            - matching_post: The matching post object if found, None otherwise
        """
        if not self._account:
            logger.warning("No Mastodon account available for duplicate checking")
            return False, None

        try:
            # Get recent posts from the user's timeline
            recent_posts = self.client.account_statuses(self._account.id, limit=20)

            # Normalize the content for comparison
            normalized_content = " ".join(content.split()).lower()

            for post in recent_posts:
                # Strip HTML and normalize existing post content
                post_text = post.content
                # Remove HTML tags
                post_text = re.sub(r"<[^>]+>", "", post_text)
                # Normalize whitespace and case
                post_text = " ".join(post_text.split()).lower()

                # Check for high similarity (80% of words match)
                post_words = set(post_text.split())
                content_words = set(normalized_content.split())
                if len(post_words) > 0 and len(content_words) > 0:
                    common_words = post_words.intersection(content_words)
                    similarity = len(common_words) / max(
                        len(post_words), len(content_words)
                    )
                    if similarity > 0.8:
                        logger.info(
                            f"Found similar post (similarity: {similarity:.2f})"
                        )
                        return True, post

            return False, None
        except Exception as e:
            logger.warning(f"Error checking for duplicate posts: {e}")
            # On error, proceed with posting (fail open)
            return False, None

    def _apply_character_limits(self, content: str) -> str:
        """Apply Mastodon's character limits to content.

        Args:
            content: The original content

        Returns:
            Content that respects Mastodon's character limits
        """
        # Mastodon has a 500 character limit
        max_length = 500

        # Make sure URLs are properly formatted
        # This converts shortened URLs like "github.com/..." to full URLs
        content = re.sub(
            r"(?<!\w)((?:github|twitter|mastodon|bsky)\.com/[^\s]+)",
            r"https://\1",
            content,
        )

        # Make sure domains like example.com are linked
        content = re.sub(
            r"(?<!\w|\.)([a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}\b(?:/\S*)?)",
            r"https://\1",
            content,
        )

        if len(content) <= max_length:
            return content

        # Truncate while preserving word boundaries and add ellipsis
        truncated = content[: max_length - 3].rsplit(" ", 1)[0]
        return f"{truncated}..."

    def _convert_to_mastodon_post(self, toot: Any) -> MastodonPost:
        """Convert a Mastodon API post to our MastodonPost model.

        Args:
            toot: The post object from the Mastodon API

        Returns:
            MastodonPost model
        """
        # Extract media attachments
        media_attachments = []
        if hasattr(toot, "media_attachments") and toot.media_attachments:
            for media in toot.media_attachments:
                media_type = self._determine_media_type(media.type)
                media_attachments.append(
                    MediaAttachment(
                        url=media.url,
                        alt_text=media.description,
                        media_type=self._convert_to_media_type(media_type),
                        mime_type=(
                            media.mime_type if hasattr(media, "mime_type") else None
                        ),
                    )
                )

        # Create the post object
        return MastodonPost(
            id=str(toot.id),
            content=toot.content,
            created_at=datetime.fromisoformat(toot.created_at.replace("Z", "+00:00")),
            author_id=str(toot.account.id),
            author_handle=toot.account.acct,
            author_display_name=toot.account.display_name,
            media_attachments=media_attachments,
            url=toot.url,
            application=(
                toot.application.name
                if hasattr(toot, "application") and toot.application
                else None
            ),
            sensitive=toot.sensitive if hasattr(toot, "sensitive") else False,
            spoiler_text=toot.spoiler_text if hasattr(toot, "spoiler_text") else None,
            visibility=toot.visibility,
            favourites_count=(
                toot.favourites_count if hasattr(toot, "favourites_count") else None
            ),
            reblogs_count=(
                toot.reblogs_count if hasattr(toot, "reblogs_count") else None
            ),
        )

    def _determine_media_type(self, mastodon_type: str) -> str:
        """Convert Mastodon media type to our MediaType enum.

        Args:
            mastodon_type: The media type string from Mastodon

        Returns:
            MediaType enum value
        """
        type_mapping = {
            "image": "image",
            "video": "video",
            "gifv": "video",
            "audio": "audio",
            "unknown": "other",
        }

        return type_mapping.get(mastodon_type, "other")

    def _convert_to_media_type(self, type_str: str) -> MediaType:
        """Convert a string media type to the MediaType enum.

        Args:
            type_str: The string media type

        Returns:
            The corresponding MediaType enum value
        """
        type_mapping = {
            "image": MediaType.IMAGE,
            "video": MediaType.VIDEO,
            "audio": MediaType.AUDIO,
            "gif": MediaType.VIDEO,  # Use VIDEO for GIFs
            "other": MediaType.OTHER,
        }

        result = type_mapping.get(type_str)
        if result is None:
            return MediaType.OTHER
        return result
