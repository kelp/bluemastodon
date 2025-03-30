"""Mastodon API client for social-sync.

This module handles interactions with the Mastodon API, including authentication,
creating posts, and handling media uploads.
"""

import os
import tempfile
from datetime import datetime
from typing import Any, List, Optional
from urllib.request import urlretrieve

from loguru import logger
from mastodon import Mastodon as MastodonAPI

from social_sync.config import MastodonConfig
from social_sync.models import BlueskyPost, MastodonPost, MediaAttachment


class MastodonClient:
    """Client for interacting with the Mastodon API."""

    def __init__(self, config: MastodonConfig):
        """Initialize the Mastodon client.

        Args:
            config: Mastodon configuration with credentials
        """
        self.config = config
        self.client = MastodonAPI(
            access_token=config.access_token, api_base_url=config.instance_url
        )
        self._authenticated = False
        self._account = None

    def verify_credentials(self) -> bool:
        """Verify the provided credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            self._account = self.client.account_verify_credentials()
            self._authenticated = True
            logger.info(f"Authenticated with Mastodon as {self._account.username}")
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

    def cross_post(self, bluesky_post: BlueskyPost) -> Optional[MastodonPost]:
        """Create a Mastodon post from a Bluesky post.

        Args:
            bluesky_post: The Bluesky post to cross-post

        Returns:
            The created Mastodon post or None if posting failed

        Raises:
            ValueError: If not authenticated
        """
        if not self.ensure_authenticated():
            raise ValueError("Not authenticated with Mastodon")

        # Process content
        content = self._format_post_content(bluesky_post)
        visibility = "public"  # Default visibility

        # Upload media if any
        media_ids = self._upload_media(bluesky_post.media_attachments)

        try:
            # Create post
            toot = self.client.status_post(
                status=content,
                media_ids=media_ids,
                visibility=visibility,
                sensitive=False,  # Could be a configurable option
            )

            return self._convert_to_mastodon_post(toot)
        except Exception as e:
            logger.error(f"Error posting to Mastodon: {e}")
            return None

    def _format_post_content(self, bluesky_post: BlueskyPost) -> str:
        """Format Bluesky post content for Mastodon.

        Args:
            bluesky_post: The Bluesky post to format

        Returns:
            Formatted content string
        """
        content = bluesky_post.content

        # Add links if any and not already in content
        for link in bluesky_post.links:
            if link.url not in content:
                content += f"\n\n{link.url}"

        # Add footer with source attribution
        content += (f"\n\n📱 Originally posted on Bluesky: "
                  f"https://bsky.app/profile/{bluesky_post.author_handle}/"
                  f"post/{bluesky_post.id}")

        return content

    def _upload_media(self, attachments: List[MediaAttachment]) -> List[str]:
        """Upload media attachments to Mastodon.

        Args:
            attachments: List of media attachments

        Returns:
            List of media IDs from Mastodon
        """
        media_ids = []

        for attachment in attachments:
            try:
                # Download the media to a temp file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    urlretrieve(attachment.url, temp_file.name)

                    # Upload to Mastodon
                    media = self.client.media_post(
                        temp_file.name,
                        mime_type=attachment.mime_type,
                        description=attachment.alt_text or "",
                    )
                    media_ids.append(media.id)

                # Clean up the temp file
                os.unlink(temp_file.name)
            except Exception as e:
                logger.error(f"Error uploading media: {e}")

        return media_ids

    def _convert_to_mastodon_post(self, toot: Any) -> MastodonPost:
        """Convert Mastodon API post to MastodonPost model.

        Args:
            toot: The Mastodon API post object

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
                        media_type=media_type,
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
