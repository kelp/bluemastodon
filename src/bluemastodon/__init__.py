"""BlueMastodon: A tool to automatically cross-post from Bluesky to Mastodon.

This package provides tools for syncing posts from Bluesky to Mastodon.
"""

import argparse
import os
import sys

from loguru import logger

from bluemastodon.bluesky import BlueskyClient
from bluemastodon.config import Config, load_config
from bluemastodon.mastodon import MastodonClient
from bluemastodon.models import (
    BlueskyPost,
    Link,
    MastodonPost,
    MediaAttachment,
    MediaType,
    SocialPost,
    SyncRecord,
)
from bluemastodon.sync import SyncManager

# No typing imports needed here due to Python 3.10+ syntax


__version__ = "0.9.7"

# Export public classes
__all__ = [
    "Config",
    "load_config",
    "BlueskyClient",
    "MastodonClient",
    "SyncManager",
    "SocialPost",
    "BlueskyPost",
    "MastodonPost",
    "MediaAttachment",
    "Link",
    "MediaType",
    "SyncRecord",
    "main",
]


def main(args: list[str] | None = None) -> int:
    """Run the bluemastodon tool from the command line.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser(description="Sync posts from Bluesky to Mastodon")
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file (.env format)",
        default=os.environ.get("BLUEMASTODON_CONFIG"),
    )
    parser.add_argument(
        "--state",
        "-s",
        help="Path to state file (JSON format)",
        default=os.environ.get("BLUEMASTODON_STATE"),
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate syncing without posting",
    )

    parsed_args = parser.parse_args(args)

    # Configure logging
    log_level = "DEBUG" if parsed_args.debug else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    try:
        # Load configuration
        config = load_config(parsed_args.config)

        # Initialize sync manager
        sync_manager = SyncManager(config, parsed_args.state)

        if parsed_args.dry_run:
            # Just authenticate and get posts
            logger.info("Dry run mode - no posts will be created")
            if not sync_manager.bluesky.ensure_authenticated():
                logger.error("Failed to authenticate with Bluesky")
                return 1

            posts = sync_manager.bluesky.get_recent_posts(
                hours_back=config.lookback_hours, limit=config.max_posts_per_run
            )

            logger.info(f"Found {len(posts)} recent posts on Bluesky")
            for post in posts:
                logger.info(f"Post {post.id}: {post.content[:50]}...")

            return 0
        else:
            # Run the actual sync
            new_records = sync_manager.run_sync()
            logger.info(f"Synced {len(new_records)} posts")

            # Print sync summary
            success_count = sum(1 for r in new_records if r.success)
            error_count = len(new_records) - success_count

            logger.info(
                f"Sync completed: {success_count} succeeded, {error_count} failed"
            )

            return 0 if error_count == 0 else 1

    except Exception as e:
        logger.exception(f"Error running sync: {e}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
