"""Configuration management for bluemastodon.

This module handles loading configuration from environment variables and
providing access to API credentials and settings.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# No typing imports needed here due to Python 3.10+ syntax


@dataclass
class BlueskyConfig:
    """Configuration for Bluesky API."""

    username: str
    password: str


@dataclass
class MastodonConfig:
    """Configuration for Mastodon API."""

    instance_url: str
    access_token: str


@dataclass
class Config:
    """Main configuration container."""

    bluesky: BlueskyConfig
    mastodon: MastodonConfig
    # How far back to look for posts (in hours)
    lookback_hours: int = 24
    # Frequency of synchronization (in minutes)
    sync_interval_minutes: int = 60
    # Maximum posts to sync in one run
    max_posts_per_run: int = 5
    # Whether to include media attachments
    include_media: bool = True
    # Whether to include post links
    include_links: bool = True


def load_config(env_file: str | None = None) -> Config:
    """Load configuration from environment variables.

    Args:
        env_file: Optional path to .env file

    Returns:
        Config object with loaded settings

    Raises:
        ValueError: If required environment variables are missing
    """
    if env_file:
        load_dotenv(env_file)
    else:
        # Try to load from default locations
        load_dotenv()

    # Required environment variables
    required_vars = [
        "BLUESKY_USERNAME",
        "BLUESKY_PASSWORD",
        "MASTODON_INSTANCE_URL",
        "MASTODON_ACCESS_TOKEN",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # Load optional settings with defaults
    lookback_hours = int(os.getenv("LOOKBACK_HOURS", "24"))
    sync_interval = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    max_posts = int(os.getenv("MAX_POSTS_PER_RUN", "5"))
    # Handle invalid boolean values by defaulting to True
    include_media_str = os.getenv("INCLUDE_MEDIA", "true").lower()
    include_media = include_media_str in ["true", "1", "yes", "y"]

    include_links_str = os.getenv("INCLUDE_LINKS", "true").lower()
    include_links = include_links_str in ["true", "1", "yes", "y"]

    return Config(
        bluesky=BlueskyConfig(
            username=os.getenv("BLUESKY_USERNAME", ""),
            password=os.getenv("BLUESKY_PASSWORD", ""),
        ),
        mastodon=MastodonConfig(
            instance_url=os.getenv("MASTODON_INSTANCE_URL", ""),
            access_token=os.getenv("MASTODON_ACCESS_TOKEN", ""),
        ),
        lookback_hours=lookback_hours,
        sync_interval_minutes=sync_interval,
        max_posts_per_run=max_posts,
        include_media=include_media,
        include_links=include_links,
    )
