"""Data models for bluemastodon.

This module defines the data structures used throughout the application,
particularly for representing posts from different platforms.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# No typing imports needed here due to Python 3.10+ syntax


class MediaType(str, Enum):
    """Types of media attachments."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class MediaAttachment(BaseModel):
    """Represents a media attachment in a post."""

    url: str
    alt_text: str | None = None
    mime_type: str | None = None
    media_type: MediaType
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None


class Link(BaseModel):
    """Represents an external link in a post."""

    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None


class SocialPost(BaseModel):
    """Base model for social media posts."""

    id: str
    content: str
    created_at: datetime
    platform: str
    author_id: str
    author_handle: str
    author_display_name: str | None = None
    media_attachments: list[MediaAttachment] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    is_reply: bool = False
    is_repost: bool = False
    in_reply_to_id: str | None = None
    repost_of_id: str | None = None
    language: str | None = None
    visibility: str | None = None


class BlueskyPost(SocialPost):
    """Bluesky-specific post model."""

    platform: str = "bluesky"
    # Bluesky-specific fields
    uri: str  # The AT URI
    cid: str  # The CID
    reply_root: str | None = None
    reply_parent: str | None = None
    like_count: int | None = None
    repost_count: int | None = None


class MastodonPost(SocialPost):
    """Mastodon-specific post model."""

    platform: str = "mastodon"
    # Mastodon-specific fields
    url: str
    application: str | None = None
    sensitive: bool = False
    spoiler_text: str | None = None
    favourites_count: int | None = None
    reblogs_count: int | None = None


class SyncRecord(BaseModel):
    """Record of a cross-posted item."""

    source_id: str
    source_platform: str
    target_id: str
    target_platform: str
    synced_at: datetime = Field(default_factory=datetime.now)
    success: bool = True
    error_message: str | None = None
