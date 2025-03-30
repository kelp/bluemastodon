"""Synchronization orchestration for social-sync.

This module handles the core logic for syncing posts from Bluesky to Mastodon,
including post mapping, cross-posting workflow, and state tracking.
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Set

from loguru import logger

from social_sync.bluesky import BlueskyClient
from social_sync.config import Config
from social_sync.mastodon import MastodonClient
from social_sync.models import BlueskyPost, SyncRecord


class SyncManager:
    """Manager for syncing posts between platforms."""

    def __init__(self, config: Config, state_file: Optional[str] = None):
        """Initialize the sync manager.

        Args:
            config: Application configuration
            state_file: Path to the state file for tracking synced posts
        """
        self.config = config
        self.bluesky = BlueskyClient(config.bluesky)
        self.mastodon = MastodonClient(config.mastodon)

        self.state_file = state_file or os.path.expanduser("~/.social-sync/state.json")
        self.synced_posts: Set[str] = set()
        self.sync_records: List[SyncRecord] = []

        # Load previous state if it exists
        self._load_state()

    def _load_state(self) -> None:
        """Load the sync state from the state file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.synced_posts = set(data.get("synced_posts", []))

                    # Convert record dicts to SyncRecord objects
                    records = []
                    for record_dict in data.get("sync_records", []):
                        try:
                            # Convert string timestamp to datetime
                            if isinstance(record_dict.get("synced_at"), str):
                                record_dict["synced_at"] = datetime.fromisoformat(
                                    record_dict["synced_at"].replace("Z", "+00:00")
                                )
                            records.append(SyncRecord(**record_dict))
                        except Exception as e:
                            logger.warning(f"Could not parse sync record: {e}")

                    self.sync_records = records

                logger.info(f"Loaded sync state: {len(self.synced_posts)} synced posts")
        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")
            # Initialize empty state
            self.synced_posts = set()
            self.sync_records = []

    def _save_state(self) -> None:
        """Save the current sync state to the state file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            # Convert SyncRecord objects to dictionaries with string timestamps
            record_dicts = []
            for record in self.sync_records:
                record_dict = record.model_dump()
                if isinstance(record_dict.get("synced_at"), datetime):
                    record_dict["synced_at"] = record_dict["synced_at"].isoformat()
                record_dicts.append(record_dict)

            # Save state to file
            with open(self.state_file, "w") as f:
                json.dump(
                    {
                        "synced_posts": list(self.synced_posts),
                        "sync_records": record_dicts,
                    },
                    f,
                )

            logger.info(f"Saved sync state: {len(self.synced_posts)} synced posts")
        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def run_sync(self) -> List[SyncRecord]:
        """Run the synchronization process.

        Returns:
            List of SyncRecord objects for newly synced posts
        """
        # Authenticate with both platforms
        if not self.bluesky.ensure_authenticated():
            logger.error("Failed to authenticate with Bluesky")
            return []

        if not self.mastodon.ensure_authenticated():
            logger.error("Failed to authenticate with Mastodon")
            return []

        # Get recent posts from Bluesky
        recent_posts = self.bluesky.get_recent_posts(
            hours_back=self.config.lookback_hours, limit=self.config.max_posts_per_run
        )

        logger.info(f"Found {len(recent_posts)} recent posts on Bluesky")

        # Filter out already synced posts
        new_posts = [post for post in recent_posts if post.id not in self.synced_posts]
        logger.info(f"Found {len(new_posts)} posts not yet synced")

        # Sync each post
        new_records = []
        for post in new_posts:
            record = self._sync_post(post)
            if record:
                new_records.append(record)

        # Update and save state
        self._save_state()

        return new_records

    def _sync_post(self, post: BlueskyPost) -> SyncRecord:
        """Sync a single post from Bluesky to Mastodon.

        Args:
            post: The BlueskyPost to sync

        Returns:
            SyncRecord with success or failure information
        """
        try:
            logger.info(f"Syncing post {post.id} from Bluesky to Mastodon")

            # Cross-post to Mastodon
            mastodon_post = self.mastodon.cross_post(post)

            if not mastodon_post:
                logger.error(f"Failed to cross-post {post.id}")
                # Create error record
                record = SyncRecord(
                    source_id=post.id,
                    source_platform="bluesky",
                    target_id="",
                    target_platform="mastodon",
                    synced_at=datetime.now(),
                    success=False,
                    error_message="Failed to cross-post",
                )
                self.sync_records.append(record)
                return record

            # Create sync record
            record = SyncRecord(
                source_id=post.id,
                source_platform="bluesky",
                target_id=mastodon_post.id,
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=True,
            )

            # Update state
            self.synced_posts.add(post.id)
            self.sync_records.append(record)

            logger.info(
                f"Successfully synced post {post.id} to Mastodon as "
                f"{mastodon_post.id}"
            )

            return record
        except Exception as e:
            logger.error(f"Error syncing post {post.id}: {e}")

            # Create error record
            record = SyncRecord(
                source_id=post.id,
                source_platform="bluesky",
                target_id="",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=False,
                error_message=str(e),
            )

            self.sync_records.append(record)
            return record
