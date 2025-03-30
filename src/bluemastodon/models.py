"""Data models for social-sync.

This module defines the data structures used throughout the application,
particularly for representing posts from different platforms.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Types of media attachments."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class MediaAttachment(BaseModel):
    """Represents a media attachment in a post."""

    url: str
    alt_text: Optional[str] = None
    mime_type: Optional[str] = None
    media_type: MediaType
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None


class Link(BaseModel):
    """Represents an external link in a post."""

    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class SocialPost(BaseModel):
    """Base model for social media posts."""

    id: str
    content: str
    created_at: datetime
    platform: str
    author_id: str
    author_handle: str
    author_display_name: Optional[str] = None
    media_attachments: List[MediaAttachment] = Field(default_factory=list)
    links: List[Link] = Field(default_factory=list)
    is_reply: bool = False
    is_repost: bool = False
    in_reply_to_id: Optional[str] = None
    repost_of_id: Optional[str] = None
    language: Optional[str] = None
    visibility: Optional[str] = None


class BlueskyPost(SocialPost):
    """Bluesky-specific post model."""

    platform: str = "bluesky"
    # Bluesky-specific fields
    uri: str  # The AT URI
    cid: str  # The CID
    reply_root: Optional[str] = None
    reply_parent: Optional[str] = None
    like_count: Optional[int] = None
    repost_count: Optional[int] = None


class MastodonPost(SocialPost):
    """Mastodon-specific post model."""

    platform: str = "mastodon"
    # Mastodon-specific fields
    url: str
    application: Optional[str] = None
    sensitive: bool = False
    spoiler_text: Optional[str] = None
    favourites_count: Optional[int] = None
    reblogs_count: Optional[int] = None


class SyncRecord(BaseModel):
    """Record of a cross-posted item."""

    source_id: str
    source_platform: str
    target_id: str
    target_platform: str
    synced_at: datetime = Field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None
