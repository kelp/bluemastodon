"""Synchronization orchestration for bluemastodon.

This module handles the core logic for syncing posts from Bluesky to Mastodon,
including post mapping, cross-posting workflow, and state tracking.
"""

import json
import os

# tempfile no longer needed
import uuid  # Import uuid for unique temporary file names
from datetime import datetime, timedelta

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
        self.mastodon_parent_map: dict[str, str] = {}  # For fast parent lookups

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

                # Build the lookup map after loading records
                self._rebuild_parent_map()
                logger.info(
                    f"Loaded sync state: {len(self.synced_posts)} posts, "
                    f"{len(self.sync_records)} records, "
                    f"{len(self.mastodon_parent_map)} parent entries"
                )
        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")
            # Initialize empty state
            self.synced_posts = set()
            self.sync_records = []
            self.mastodon_parent_map = {}

    def _rebuild_parent_map(self) -> None:
        """Rebuild the mastodon_parent_map from sync_records."""
        self.mastodon_parent_map = {
            record.source_id: record.target_id
            for record in self.sync_records
            if record.success
            and record.target_id
            and record.source_platform == "bluesky"
        }

    def _save_state(self) -> None:
        """Save the current sync state atomically, pruning old records."""
        try:
            # --- Pruning Logic ---
            # Define retention period (e.g., 7 days, adjust as needed)
            retention_period = timedelta(days=7)
            cutoff_time = datetime.now() - retention_period

            original_record_count = len(self.sync_records)
            # Filter records based on timestamp (ensure synced_at is datetime)
            self.sync_records = [
                record
                for record in self.sync_records
                if isinstance(record.synced_at, datetime)
                and record.synced_at >= cutoff_time
            ]
            pruned_count = original_record_count - len(self.sync_records)
            if pruned_count > 0:
                logger.info(f"Pruned {pruned_count} old sync records.")

            # Rebuild the parent map after pruning
            self._rebuild_parent_map()

            # --- Prepare data for JSON serialization ---
            record_dicts = []
            for record in self.sync_records:
                record_dict = record.model_dump()
                if isinstance(record_dict.get("synced_at"), datetime):
                    record_dict["synced_at"] = record_dict["synced_at"].isoformat()
                record_dicts.append(record_dict)

            state_data = {
                "synced_posts": list(self.synced_posts),
                "sync_records": record_dicts,
            }

            # Get directory and ensure it exists
            dirname = os.path.dirname(self.state_file)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

            # --- Atomic Write ---
            # Create a unique temporary file in the same directory
            temp_file_path = f"{self.state_file}.{uuid.uuid4()}.tmp"
            try:
                # Directory existence is already checked and created above

                with open(temp_file_path, "w") as f:
                    json.dump(state_data, f, indent=2)  # Add indent for readability

                # Atomically replace the old state file with the new one
                os.replace(temp_file_path, self.state_file)

                logger.info(
                    f"Saved sync state atomically: {len(self.synced_posts)} posts, "
                )
            except Exception as write_err:
                logger.error(f"Failed during atomic write to state file: {write_err}")
                # Clean up the temporary file if it exists
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError as remove_err:
                        logger.error(
                            f"Failed to remove temp file {temp_file_path}: {remove_err}"
                        )
                # Re-raise the original error to signal failure
                raise write_err
            # --- End Atomic Write ---

            logger.info(
                f"Saved sync state successfully: {len(self.synced_posts)} posts, "
                f"{len(self.sync_records)} records"
            )

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
            hours_back=self.config.lookback_hours,
            limit=self.config.max_posts_per_run,
            include_threads=self.config.include_threads,
        )

        logger.info(f"Found {len(recent_posts)} recent posts on Bluesky")

        # Filter out already synced posts
        new_posts = [post for post in recent_posts if post.id not in self.synced_posts]
        logger.info(f"Found {len(new_posts)} posts not yet synced")

        # Sort posts chronologically (oldest first) to improve reply threading
        new_posts.sort(key=lambda p: p.created_at)
        if new_posts:
            logger.info(
                f"Sorted {len(new_posts)} posts chronologically before syncing."
            )

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

    def find_mastodon_id_for_bluesky_post(self, bluesky_post_id: str) -> str | None:
        """Find the corresponding Mastodon post ID for a Bluesky post ID.

        Args:
            bluesky_post_id: The Bluesky post ID to find

        Returns:
            The Mastodon post ID if found, None otherwise
        """
        # Use the pre-built dictionary for efficient lookup
        return self.mastodon_parent_map.get(bluesky_post_id)

    def _sync_post(self, post: BlueskyPost) -> SyncRecord:
        """Sync a single post from Bluesky to Mastodon.

        Args:
            post: The BlueskyPost to sync

        Returns:
            SyncRecord with success or failure information
        """
        try:
            logger.info(f"Syncing post {post.id} from Bluesky to Mastodon")

            # Check if this is a reply to a post we've previously synced
            mastodon_parent_id = None
            if post.is_reply and post.reply_parent:
                # Look up the Mastodon ID for the parent post
                mastodon_parent_id = self.find_mastodon_id_for_bluesky_post(
                    post.reply_parent
                )
                if mastodon_parent_id:
                    logger.info(
                        f"Found Mastodon parent ID: {mastodon_parent_id} "
                        f"for Bluesky parent: {post.reply_parent}"
                    )
                else:
                    logger.warning(
                        f"Could not find Mastodon parent ID for Bluesky parent: "
                        f"{post.reply_parent}"
                    )

            # Cross-post to Mastodon, passing thread information
            # MastodonClient.post returns tuple: (status, post_object, error_message)
            result = self.mastodon.post(post, in_reply_to_id=mastodon_parent_id)
            # Type-safe unpacking with proper error handling
            if isinstance(result, tuple) and len(result) == 3:
                status, mastodon_post_obj, error_msg = result
            else:
                # For backward compatibility, treat non-tuple return as success
                mastodon_post_obj = result
                status = "success" if mastodon_post_obj else "failed"
                error_msg = None if mastodon_post_obj else "Unknown error"

            # --- Handle Posting Result ---
            if status == "success" or status == "duplicate":
                # Mark as synced in our state for both success and duplicate
                self.synced_posts.add(post.id)
                # Save state immediately to prevent re-posting on crash
                self._save_state()

                # Ensure we have a post object (even minimal fallback/duplicate)
                if mastodon_post_obj:
                    target_id = (
                        str(mastodon_post_obj.id) if mastodon_post_obj.id else ""
                    )
                    log_msg = (
                        f"Successfully synced post {post.id} as {target_id}"
                        if status == "success"
                        else f"Post {post.id} exists as {target_id} (duplicate)"
                    )
                    logger.info(log_msg)

                    record = SyncRecord(
                        source_id=post.id,
                        source_platform="bluesky",
                        target_id=target_id,
                        target_platform="mastodon",
                        synced_at=datetime.now(),
                        success=True,  # Treat duplicate as success for record keeping
                        error_message=(
                            "Duplicate post detected" if status == "duplicate" else None
                        ),
                    )
                else:
                    # Handle missing post object defensively
                    logger.warning(
                        f"Post {post.id} reported as {status} but no post object."
                    )
                    record = SyncRecord(
                        source_id=post.id,
                        source_platform="bluesky",
                        target_id="",
                        target_platform="mastodon",
                        synced_at=datetime.now(),
                        success=True,  # Still mark success to avoid retry
                        error_message=f"Post {status}, missing Mastodon object",
                    )

                self.sync_records.append(record)
                # Update parent map only if target_id is valid
                if target_id and target_id != "duplicate" and target_id != "unknown":
                    self._rebuild_parent_map()  # Rebuild map after adding record

                return record

            elif status == "failed":
                logger.error(f"Failed to cross-post {post.id}: {error_msg}")
                record = SyncRecord(
                    source_id=post.id,
                    source_platform="bluesky",
                    target_id="",
                    target_platform="mastodon",
                    synced_at=datetime.now(),
                    success=False,
                    error_message=str(error_msg) if error_msg else "Unknown error",
                )
                self.sync_records.append(record)
                # Save state to record the failure
                self._save_state()
                return record

            else:  # pragma: no cover
                # Should not happen with Literal type hint, but handle defensively
                logger.error(
                    f"Unknown status '{status}' from MastodonClient.post: {post.id}"
                )
                record = SyncRecord(
                    source_id=post.id,
                    source_platform="bluesky",
                    target_id="",
                    target_platform="mastodon",
                    synced_at=datetime.now(),
                    success=False,
                    error_message=f"Unknown status: {status}",
                )
                self.sync_records.append(record)
                self._save_state()
                return record

        except Exception as e:
            # Catches unexpected errors outside the self.mastodon.post call
            # Errors within self.mastodon.post are handled by its return value
            logger.error(f"Unexpected sync error for post {post.id}: {e}")
            record = SyncRecord(
                source_id=post.id,
                source_platform="bluesky",
                target_id="",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=False,
                error_message=f"Sync process error: {e}",
            )
            self.sync_records.append(record)
            # Save state to record the failure
            self._save_state()
            return record
