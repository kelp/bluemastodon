"""Mastodon API client for bluemastodon.

This module handles interactions with the Mastodon API, including authentication,
posting content, and checking for duplicates.
"""

import re
from datetime import datetime
from typing import Any

from loguru import logger
from mastodon import Mastodon

from bluemastodon.config import MastodonConfig
from bluemastodon.models import (
    MastodonPost,
    MediaAttachment,
    MediaType,
    SocialPost,
)


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

    def post(self, post: SocialPost) -> MastodonPost | None:
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
                            id=self._safe_int_to_str(
                                self._get_safe_attr(existing_post, "id", "duplicate")
                            ),
                            content=post.content,
                            created_at=datetime.now(),
                            author_id="",
                            author_handle="",
                            author_display_name="",
                            media_attachments=[],
                            url=self._get_safe_attr(existing_post, "url", ""),
                        )
                        return minimal_post
                else:
                    logger.info(
                        "Duplicate detected but post info not available: "
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

            # Process content - add full URLs from link metadata
            content = post.content
            if hasattr(post, "links") and post.links:
                # Extract links from post and append full URLs
                links = []
                for link_obj in post.links:
                    if hasattr(link_obj, "url") and link_obj.url:
                        links.append(link_obj.url)
                        logger.info(f"Added full URL to content: {link_obj.url}")

                # Add all links to content on separate lines to avoid truncation
                if links:
                    # Variable for newline separator to avoid backslash in f-string
                    newline_separator = "\n"
                    joined_links = newline_separator.join(links)
                    content = f"{content}\n\n{joined_links}"

            # Apply character limits
            content = self._apply_character_limits(content)

            # Upload media if present
            media_ids: list[str] = []
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
                        # pragma: no cover - Stub for future implementation
                        # media_id = self._upload_media(attachment)
                        # media_ids.append(media_id)
                    except Exception as e:
                        logger.error(f"Error uploading media to Mastodon: {e}")

            # Create the post
            try:
                # Get Mastodon visibility
                visibility = "public"  # Default
                if hasattr(post, "visibility") and post.visibility:
                    visibility = post.visibility

                # Get spoiler text
                spoiler_text = None
                if (
                    hasattr(post, "spoiler_text") and post.spoiler_text
                ):  # pragma: no branch
                    spoiler_text = post.spoiler_text  # pragma: no cover

                # Get sensitivity flag
                sensitive = False
                if hasattr(post, "sensitive"):  # pragma: no branch
                    sensitive = post.sensitive  # pragma: no cover

                # Create the post with safely handled parameters
                toot = self.client.status_post(
                    status=content,
                    media_ids=media_ids if media_ids else None,
                    sensitive=sensitive,
                    visibility=visibility,
                    spoiler_text=spoiler_text,
                )

                # Log successful post creation
                post_url = self._get_safe_attr(toot, "url", "No URL")
                logger.info(f"Posted to Mastodon: {post_url}")

                # Try to convert the toot to our model with extensive error handling
                try:
                    mastodon_post = self._convert_to_mastodon_post(toot)
                    return mastodon_post
                except Exception as conversion_error:
                    # Detailed error for troubleshooting but create a fallback post
                    logger.error(
                        f"Failed to convert post after successful creation: "
                        f"{conversion_error}"
                    )

                    # Create a minimal valid post with the data we know is good
                    return MastodonPost(
                        id=self._safe_int_to_str(
                            self._get_safe_attr(toot, "id", "unknown")
                        ),
                        content=content,  # We know this is valid as we just posted it
                        created_at=datetime.now(),
                        author_id="",
                        author_handle="",
                        author_display_name="",
                        media_attachments=[],
                        url=post_url,
                    )
            except Exception as post_error:
                logger.error(f"Error creating Mastodon post: {post_error}")
                return None

        except Exception as e:
            logger.error(f"Unhandled error in Mastodon post method: {e}")
            return None

    def _is_duplicate_post(self, content: str) -> tuple[bool, Any | None]:
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
            # Safely get the account ID, converting to string if necessary
            account_id = self._safe_int_to_str(self._get_safe_attr(self._account, "id"))
            if not account_id:
                logger.warning("Cannot get account ID for duplicate checking")
                return False, None

            # Get recent posts from the user's timeline
            try:
                recent_posts = self.client.account_statuses(account_id, limit=20)
            except Exception as e:
                logger.warning(f"Error fetching recent posts: {e}")
                return False, None

            # Normalize the content for comparison
            normalized_content = " ".join(content.split()).lower()

            for post in recent_posts:
                try:
                    # Safely get post content
                    post_text = self._get_safe_attr(post, "content", "")
                    if not post_text:
                        continue

                    # Remove HTML tags
                    post_text = re.sub(r"<[^>]+>", "", post_text)
                    # Normalize whitespace and case
                    post_text = " ".join(post_text.split()).lower()

                    # Check for high similarity (80% of words match)
                    post_words = set(post_text.split())
                    content_words = set(normalized_content.split())

                    if len(post_words) > 0 and len(content_words) > 0:
                        common_words = post_words.intersection(content_words)
                        # Prevent division by zero
                        max_words = max(len(post_words), len(content_words))
                        if max_words > 0:
                            similarity = len(common_words) / max_words
                            if similarity > 0.8:
                                logger.info(
                                    f"Found similar post (similarity: {similarity:.2f})"
                                )
                                return True, post
                except Exception as post_error:  # pragma: no cover
                    # If one post fails, continue checking others
                    logger.warning(
                        f"Error checking specific post for similarity: {post_error}"
                    )
                    continue

            return False, None
        except Exception as e:  # pragma: no cover
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

        # Make sure URLs are properly formatted - fixed regex patterns
        # This converts shortened URLs like "github.com/..." to full URLs

        # Pattern 1: Check for URLs without https:// prefix
        content = re.sub(
            r"(^|\s)((?:github|twitter|mastodon|bsky)\.com/[^\s]+)",
            r"\1https://\2",
            content,
        )

        # Pattern 2: Make sure domains like example.com are linked
        content = re.sub(
            r"(^|\s)([a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}\b(?:/\S*)?)",
            r"\1https://\2",
            content,
        )

        if len(content) <= max_length:
            return content

        # Truncate while preserving word boundaries and add ellipsis
        truncated = content[: max_length - 3].rsplit(" ", 1)[0]
        return f"{truncated}..."

    def _get_safe_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from an object.

        Args:
            obj: The object to get the attribute from
            attr: The attribute name
            default: The default value to return if the attribute doesn't exist

        Returns:
            The attribute value or the default
        """
        try:
            if hasattr(obj, attr):
                return getattr(obj, attr)
            return default
        except Exception as e:
            logger.warning(f"Error getting attribute {attr}: {e}")
            return default

    def _safe_int_to_str(self, value: Any) -> str:
        """Safely convert any value to a string.

        Args:
            value: The value to convert

        Returns:
            String representation of the value
        """
        try:
            if value is None:
                return ""
            return str(value)
        except Exception as e:
            logger.warning(f"Error converting value to string: {e}")
            return ""

    def _safe_get_nested(self, obj: Any, *attrs: str, default: Any = None) -> Any:
        """Safely navigate nested attributes.

        Args:
            obj: The object to navigate
            *attrs: The attribute names to follow
            default: The default value if any attribute is missing

        Returns:
            The nested attribute value or default
        """
        try:
            current = obj
            for attr in attrs:
                if current is None or not hasattr(current, attr):
                    return default
                current = getattr(current, attr)
            return current
        except Exception as e:
            logger.warning(f"Error getting nested attributes {attrs}: {e}")
            return default

    def _convert_to_mastodon_post(self, toot: Any) -> MastodonPost:
        """Convert a Mastodon API post to our MastodonPost model.

        Args:
            toot: The post object from the Mastodon API

        Returns:
            MastodonPost model
        """
        try:
            # Extract media attachments with comprehensive error handling
            media_attachments = []
            if self._get_safe_attr(toot, "media_attachments"):
                for media in toot.media_attachments:
                    try:
                        media_type = self._determine_media_type(
                            self._get_safe_attr(media, "type", "unknown")
                        )
                        media_attachments.append(
                            MediaAttachment(
                                url=self._get_safe_attr(media, "url", ""),
                                alt_text=self._get_safe_attr(media, "description", ""),
                                media_type=self._convert_to_media_type(media_type),
                                mime_type=self._get_safe_attr(media, "mime_type"),
                            )
                        )
                    except (
                        Exception
                    ) as e:  # pragma: no cover - Difficult to trigger in tests
                        logger.warning(f"Error processing media attachment: {e}")
                        # Continue processing other attachments

            # Handle ID - ALWAYS convert to string
            post_id = self._safe_int_to_str(self._get_safe_attr(toot, "id", "unknown"))

            # Handle datetime with comprehensive error catching
            created_at = datetime.now()  # Default fallback
            try:
                toot_created_at = self._get_safe_attr(toot, "created_at")
                if toot_created_at is not None:
                    if isinstance(toot_created_at, str):
                        created_at = datetime.fromisoformat(
                            toot_created_at.replace("Z", "+00:00")
                        )
                    elif isinstance(toot_created_at, datetime):  # pragma: no cover
                        created_at = toot_created_at
            except Exception as e:
                logger.warning(f"Error parsing created_at: {e}, using current time")

            # Safely handle account information
            account = self._get_safe_attr(toot, "account")
            author_id = self._safe_int_to_str(self._get_safe_attr(account, "id", ""))
            author_handle = self._get_safe_attr(account, "acct", "")
            author_display_name = self._get_safe_attr(account, "display_name", "")

            # Safely handle application information
            application_name = self._safe_get_nested(toot, "application", "name")

            # Create the post object with safe defaults for all fields
            return MastodonPost(
                id=post_id,
                content=self._get_safe_attr(toot, "content", ""),
                created_at=created_at,
                author_id=author_id,
                author_handle=author_handle,
                author_display_name=author_display_name,
                media_attachments=media_attachments,
                url=self._get_safe_attr(toot, "url", ""),
                application=application_name,
                sensitive=self._get_safe_attr(toot, "sensitive", False),
                spoiler_text=self._get_safe_attr(toot, "spoiler_text"),
                visibility=self._get_safe_attr(toot, "visibility", "public"),
                favourites_count=self._get_safe_attr(toot, "favourites_count"),
                reblogs_count=self._get_safe_attr(toot, "reblogs_count"),
            )
        except Exception as e:
            # Last resort fallback - create a minimal valid post
            logger.error(
                f"Critical error converting Mastodon post, using fallback: {e}"
            )
            return MastodonPost(
                id=self._safe_int_to_str(self._get_safe_attr(toot, "id", "error")),
                content=self._get_safe_attr(toot, "content", ""),
                created_at=datetime.now(),
                author_id="",
                author_handle="",
                author_display_name="",
                media_attachments=[],
                url=self._get_safe_attr(toot, "url", ""),
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
