"""Synchronization orchestration for bluemastodon.

This module handles the core logic for syncing posts from Bluesky to Mastodon,
including post mapping, cross-posting workflow, and state tracking.
"""

import json
import os
from datetime import datetime

from loguru import logger

from bluemastodon.bluesky import BlueskyClient
from bluemastodon.config import Config
from bluemastodon.mastodon import MastodonClient
from bluemastodon.models import BlueskyPost, SyncRecord

# No typing imports needed here due to Python 3.10+ syntax


class SyncManager:
    """Manager for syncing posts between platforms."""

    def __init__(self, config: Config, state_file: str | None = None):
        """Initialize the sync manager.

        Args:
            config: Application configuration
            state_file: Path to the state file for tracking synced posts
        """
        self.config = config
        self.bluesky = BlueskyClient(config.bluesky)
        self.mastodon = MastodonClient(config.mastodon)

        self.state_file = state_file or "sync_state.json"
        self.synced_posts: set[str] = set()
        self.sync_records: list[SyncRecord] = []

        # Load previous state if it exists
        self._load_state()

    def _load_state(self) -> None:
        """Load the sync state from the state file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
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
            # Only create directories if path contains directories
            dirname = os.path.dirname(self.state_file)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

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

    def run_sync(self) -> list[SyncRecord]:
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

        # State is saved after each successful post,
        # but we'll save once more to record any failed attempts
        if new_records:
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
            mastodon_post = self.mastodon.post(post)

            # IMPORTANT: Mark the post as synced immediately if we got any response
            # This prevents double posting even if later processing fails
            if mastodon_post:
                # Add to synced_posts immediately
                self.synced_posts.add(post.id)
                # Save state file immediately after successful posting
                self._save_state()

                # Create sync record - ensure target_id is always a string
                target_id = str(mastodon_post.id) if mastodon_post.id else ""
                record = SyncRecord(
                    source_id=post.id,
                    source_platform="bluesky",
                    target_id=target_id,
                    target_platform="mastodon",
                    synced_at=datetime.now(),
                    success=True,
                )

                self.sync_records.append(record)

                logger.info(
                    f"Successfully synced post {post.id} to Mastodon as "
                    f"{mastodon_post.id}"
                )

                return record
            else:
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
        except Exception as e:
            logger.error(f"Error syncing post {post.id}: {e}")

            # If the error includes "Posted to Mastodon", it means we likely succeeded
            # but had a post-processing error. Mark as synced to prevent double posting.
            log_msg = str(e).lower()
            if "posted to mastodon" in log_msg:
                logger.warning(
                    "Post may have succeeded despite error. "
                    "Marking as synced to prevent duplication."
                )
                self.synced_posts.add(post.id)
                self._save_state()

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
            # Save state to record the failure
            self._save_state()
            return record
