"""Tests for the sync module."""

import json
import os
import tempfile

# uuid is used in tests via mocks
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from bluemastodon.models import BlueskyPost, MastodonPost, SyncRecord
from bluemastodon.sync import SyncManager

# Tests need pytest fixtures


@pytest.fixture
def mock_mastodon_success_post():
    """Fixture for a successful Mastodon post object."""
    return MastodonPost(
        id="toot123",
        content="Test content",
        created_at=datetime.now(),
        author_id="masto_author",
        author_handle="masto_author@test.social",
        author_display_name="Masto Author",
        url="https://test.social/@masto_author/toot123",
    )


class TestSyncManager:
    """Test the SyncManager class."""

    def test_init(self, sample_config):
        """Test initialization of SyncManager."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky,
            patch("bluemastodon.sync.MastodonClient") as mock_masto,
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Create manager with default state file
            manager = SyncManager(sample_config)

            # Check initialization
            assert manager.config == sample_config
            assert manager.synced_posts == set()
            assert manager.sync_records == []
            mock_bsky.assert_called_once_with(sample_config.bluesky)
            mock_masto.assert_called_once_with(sample_config.mastodon)

            # Create manager with custom state file
            custom_state_file = "/tmp/custom_state.json"
            manager = SyncManager(sample_config, custom_state_file)
            assert manager.state_file == custom_state_file

    def test_load_state_no_file(self, sample_config):
        """Test _load_state when file doesn't exist."""
        with (
            patch("bluemastodon.sync.os.path.exists", return_value=False),
            patch("bluemastodon.sync.BlueskyClient"),
            patch("bluemastodon.sync.MastodonClient"),
        ):

            manager = SyncManager(sample_config)

            # Check that state is empty
            assert manager.synced_posts == set()
            assert manager.sync_records == []

    def test_load_state_with_file(self, sample_config, sample_sync_state_file):
        """Test _load_state with existing state file."""
        with (
            patch("bluemastodon.sync.BlueskyClient"),
            patch("bluemastodon.sync.MastodonClient"),
        ):

            # Create manager with sample state file
            manager = SyncManager(sample_config, sample_sync_state_file)

            # Check that state was loaded correctly
            assert manager.synced_posts == {"existing1", "existing2"}
            assert len(manager.sync_records) == 2

            # Check record properties
            record1 = manager.sync_records[0]
            assert record1.source_id == "existing1"
            assert record1.source_platform == "bluesky"
            assert record1.target_id == "target1"
            assert record1.target_platform == "mastodon"
            assert record1.success is True
            assert record1.error_message is None

            # Check parent map is built (should contain both valid records)
            assert manager.mastodon_parent_map == {
                "existing1": "target1",
                "existing2": "target2",
            }

    def test_load_state_with_invalid_file(self, sample_config):
        """Test _load_state with invalid state file."""
        # Create an invalid JSON file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("this is not valid json")
            invalid_state_file = temp_file.name

        try:
            with (
                patch("bluemastodon.sync.BlueskyClient"),
                patch("bluemastodon.sync.MastodonClient"),
                patch("bluemastodon.sync.logger") as mock_logger,
            ):

                # Create manager with invalid state file
                manager = SyncManager(sample_config, invalid_state_file)

                # Check that state is empty
                assert manager.synced_posts == set()
                assert manager.sync_records == []
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Failed to load sync state" in mock_logger.error.call_args[0][0]

        finally:
            # Clean up
            if os.path.exists(invalid_state_file):
                os.unlink(invalid_state_file)

    def test_load_state_with_invalid_record(self, sample_config):
        """Test _load_state with invalid record in state file."""
        # Create a file with an invalid record
        invalid_record_file = None
        try:
            # Create a state file with invalid record format
            state_content = {
                "synced_posts": ["post1"],
                "sync_records": [
                    {
                        "source_id": "post1",
                        # Missing required fields
                        "synced_at": datetime.now().isoformat(),
                    }
                ],
            }

            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
                json.dump(state_content, temp_file)
                invalid_record_file = temp_file.name

            with (
                patch("bluemastodon.sync.BlueskyClient"),
                patch("bluemastodon.sync.MastodonClient"),
                patch("bluemastodon.sync.logger") as mock_logger,
            ):

                # Create manager with invalid record file
                manager = SyncManager(sample_config, invalid_record_file)

                # Check that synced_posts were loaded but invalid record was skipped
                assert manager.synced_posts == {"post1"}
                assert manager.sync_records == []

                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                assert (
                    "Could not parse sync record" in mock_logger.warning.call_args[0][0]
                )

        finally:
            # Clean up
            if invalid_record_file and os.path.exists(invalid_record_file):
                os.unlink(invalid_record_file)

    def test_save_state(self, sample_config):
        """Test _save_state method with atomic write and pruning."""
        # Setup mock for open and json.dump
        mock_file = MagicMock()
        m_open = mock_open(mock=mock_file)
        mock_uuid = "test-uuid-1234"
        state_file_path = "/tmp/state.json"
        temp_file_path = f"{state_file_path}.{mock_uuid}.tmp"

        with (
            patch("bluemastodon.sync.BlueskyClient"),
            patch("bluemastodon.sync.MastodonClient"),
            patch("bluemastodon.sync.open", m_open),
            patch("bluemastodon.sync.json.dump") as mock_dump,
            patch("bluemastodon.sync.os.makedirs") as mock_makedirs,
            patch("bluemastodon.sync.os.replace") as mock_replace,
            patch("bluemastodon.sync.uuid.uuid4", return_value=mock_uuid),
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Create manager
            manager = SyncManager(sample_config, state_file_path)

            # Add some state
            manager.synced_posts = {"post1", "post2", "old_post"}

            now = datetime.now()
            recent_record = SyncRecord(
                source_id="post1",
                source_platform="bluesky",
                target_id="toot1",
                target_platform="mastodon",
                synced_at=now,
                success=True,
            )
            # Create a record older than the retention period (7 days)
            old_record = SyncRecord(
                source_id="old_post",
                source_platform="bluesky",
                target_id="old_toot",
                target_platform="mastodon",
                synced_at=now - timedelta(days=10),
                success=True,
            )
            manager.sync_records = [recent_record, old_record]

            # Reset the mock to clear any calls from initialization
            m_open.reset_mock()

            # Call _save_state
            manager._save_state()

            # Verify directory was created (once before atomic write)
            mock_makedirs.assert_called_once_with(
                os.path.dirname(state_file_path), exist_ok=True
            )

            # Verify temp file was opened with write mode
            m_open.assert_called_once_with(temp_file_path, "w")

            # Verify json.dump was called with correct data
            call_args = mock_dump.call_args[0]
            data = call_args[0]

            # Check state content
            assert isinstance(data, dict)
            # The old post should still be in synced_posts, but the record pruned
            assert set(data["synced_posts"]) == {"post1", "post2", "old_post"}
            # Only the recent record should remain after pruning
            assert len(data["sync_records"]) == 1
            assert data["sync_records"][0]["source_id"] == "post1"
            assert data["sync_records"][0]["target_id"] == "toot1"

            # Verify atomic replace was called
            mock_replace.assert_called_once_with(temp_file_path, state_file_path)

    def test_save_state_error(self, sample_config):
        """Test _save_state error handling during atomic write."""
        state_file_path = "/tmp/state.json"
        mock_uuid = "test-uuid-error"
        temp_file_path = f"{state_file_path}.{mock_uuid}.tmp"

        with (
            patch("bluemastodon.sync.BlueskyClient"),
            patch("bluemastodon.sync.MastodonClient"),
            patch(
                "bluemastodon.sync.open", mock_open()
            ),  # Mock open to succeed initially
            patch("bluemastodon.sync.json.dump"),  # Mock dump to succeed
            patch("bluemastodon.sync.os.makedirs"),
            patch(
                "bluemastodon.sync.os.replace", side_effect=OSError("Replace failed")
            ),
            patch("bluemastodon.sync.uuid.uuid4", return_value=mock_uuid),
            patch(
                "bluemastodon.sync.os.remove", side_effect=OSError("Remove failed")
            ) as mock_remove,  # Add side effect
            patch("bluemastodon.sync.logger") as mock_logger,
            # Single patch for os.path.exists with a side effect
            patch("bluemastodon.sync.os.path.exists") as mock_exists,
        ):
            # Define side effect for os.path.exists
            # It should return False for the main state file during init (_load_state)
            # and True for the temp file during cleanup check in _save_state
            def exists_side_effect(path):
                if path == state_file_path:
                    # Return False to simulate no existing state file for load
                    return False
                elif path == temp_file_path:
                    return True  # Simulate temp file exists for cleanup
                return False  # Default for any other path

            mock_exists.side_effect = exists_side_effect

            # Create manager - this will call _load_state which calls os.path.exists
            manager = SyncManager(sample_config, state_file_path)

            # Reset the mock logger to clear any calls from initialization
            mock_logger.reset_mock()

            # Call _save_state - it should catch the OSError and log errors
            manager._save_state()

            # Verify error was logged during atomic write attempt
            mock_logger.error.assert_any_call(
                "Failed during atomic write to state file: Replace failed"
            )
            # Verify temp file removal was attempted and failed
            mock_exists.assert_any_call(temp_file_path)
            mock_remove.assert_called_once_with(temp_file_path)
            # Check that the error during removal was logged
            mock_logger.error.assert_any_call(
                f"Failed to remove temporary state file {temp_file_path}: Remove failed"
            )
            # Verify the final "Failed to save sync state" error was logged
            mock_logger.error.assert_any_call(
                "Failed to save sync state: Replace failed"
            )
            # Ensure exactly three error logs occurred
            assert mock_logger.error.call_count == 3

    def test_find_mastodon_id_for_bluesky_post(self, sample_config):
        """Test find_mastodon_id_for_bluesky_post method."""
        with (
            patch("bluemastodon.sync.BlueskyClient"),
            patch("bluemastodon.sync.MastodonClient"),
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Create manager
            manager = SyncManager(sample_config)

            # Setup test sync records
            record1 = SyncRecord(
                source_id="bluesky1",
                source_platform="bluesky",
                target_id="mastodon1",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=True,
            )
            record2 = SyncRecord(
                source_id="bluesky2",
                source_platform="bluesky",
                target_id="mastodon2",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=True,
            )
            record3 = SyncRecord(  # Failed record
                source_id="bluesky3",
                source_platform="bluesky",
                target_id="",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=False,
            )
            record4 = SyncRecord(  # Different platform
                source_id="other1",
                source_platform="other",
                target_id="mastodon3",
                target_platform="mastodon",
                synced_at=datetime.now(),
                success=True,
            )
            manager.sync_records = [record1, record2, record3, record4]

            # Rebuild the parent map
            manager._rebuild_parent_map()

            # Test finding existing records
            assert manager.find_mastodon_id_for_bluesky_post("bluesky1") == "mastodon1"
            assert manager.find_mastodon_id_for_bluesky_post("bluesky2") == "mastodon2"

            # Test failed record (should not be in map)
            assert manager.find_mastodon_id_for_bluesky_post("bluesky3") is None

            # Test record from different platform
            assert manager.find_mastodon_id_for_bluesky_post("other1") is None

            # Test non-existent record
            assert manager.find_mastodon_id_for_bluesky_post("nonexistent") is None

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_success(
        self,
        mock_save_state,
        sample_config,
        sample_bluesky_post,
        mock_mastodon_success_post,
    ):
        """Test _sync_post success case."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon post response
            mock_masto.post.return_value = ("success", mock_mastodon_success_post, None)

            # Create manager
            manager = SyncManager(sample_config)
            # Patch rebuild map to check it's called
            manager._rebuild_parent_map = MagicMock()

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == mock_mastodon_success_post.id
            assert result.target_platform == "mastodon"
            assert result.success is True
            assert result.error_message is None

            # Check state was updated
            assert sample_bluesky_post.id in manager.synced_posts
            assert result in manager.sync_records

            # Verify mock calls
            mock_masto.post.assert_called_once()
            args, kwargs = mock_masto.post.call_args
            assert args[0] == sample_bluesky_post
            assert "in_reply_to_id" in kwargs and kwargs["in_reply_to_id"] is None
            # _save_state is now called immediately after successful posting
            mock_save_state.assert_called_once()
            # _rebuild_parent_map should be called after adding the record
            manager._rebuild_parent_map.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_duplicate(
        self,
        mock_save_state,
        sample_config,
        sample_bluesky_post,
        mock_mastodon_success_post,
    ):
        """Test _sync_post when a duplicate is detected."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon post response for duplicate
            mock_masto.post.return_value = (
                "duplicate",
                mock_mastodon_success_post,
                None,
            )

            # Create manager
            manager = SyncManager(sample_config)
            manager._rebuild_parent_map = MagicMock()  # Patch rebuild map

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result (should be treated as success)
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.target_id == mock_mastodon_success_post.id
            assert result.success is True
            assert result.error_message == "Duplicate post detected"

            # Check state was updated (marked as synced)
            assert sample_bluesky_post.id in manager.synced_posts
            assert result in manager.sync_records

            # Verify mock calls
            mock_masto.post.assert_called_once()
            # _save_state is called immediately for duplicates too
            mock_save_state.assert_called_once()
            # _rebuild_parent_map should be called
            manager._rebuild_parent_map.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_failure(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test _sync_post when posting fails."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock post to return failure status
            error_message = "API rate limit exceeded"
            mock_masto.post.return_value = ("failed", None, error_message)

            # Create manager
            manager = SyncManager(sample_config)
            manager._rebuild_parent_map = MagicMock()  # Patch rebuild map

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == ""
            assert result.target_platform == "mastodon"
            assert result.success is False
            assert result.error_message == error_message

            # Check state was updated (record added, but synced_posts not updated)
            assert sample_bluesky_post.id not in manager.synced_posts
            assert result in manager.sync_records

            # Verify mock calls
            mock_masto.post.assert_called_once()
            args, kwargs = mock_masto.post.call_args
            assert args[0] == sample_bluesky_post
            assert "in_reply_to_id" in kwargs
            # _save_state IS called on failure now
            mock_save_state.assert_called_once()
            # _rebuild_parent_map should NOT be called on failure
            manager._rebuild_parent_map.assert_not_called()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_exception_outside_mastodon_call(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test _sync_post with an exception outside the mastodon.post call."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon.post to succeed
            mock_masto.post.return_value = ("success", MagicMock(id="toot123"), None)

            # Create manager
            manager = SyncManager(sample_config)

            # Mock something *after* the mastodon.post call to raise an exception
            # e.g., _rebuild_parent_map
            error_msg = "Error during parent map rebuild"
            manager._rebuild_parent_map = MagicMock(side_effect=Exception(error_msg))

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result - should be a failure record due to the exception
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.success is False
            assert f"Sync process error: {error_msg}" in result.error_message

            # Verify the error was logged by the outer exception handler
            mock_logger.error.assert_called_once()
            assert (
                "Unexpected error during sync process"
                in mock_logger.error.call_args[0][0]
            )

            # Verify save_state is called twice
            assert mock_save_state.call_count == 2

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_exception_before_mastodon_call(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test _sync_post with an exception before the mastodon.post call."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Create manager
            manager = SyncManager(sample_config)

            # Mock find_mastodon_id_for_bluesky_post to raise an exception
            error_msg = "Error during parent lookup"
            manager.find_mastodon_id_for_bluesky_post = MagicMock(
                side_effect=Exception(error_msg)
            )

            # Make the post a reply to trigger the lookup
            sample_bluesky_post.is_reply = True
            sample_bluesky_post.reply_parent = "some_parent_id"

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result - should be a failure record due to the exception
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.success is False
            assert f"Sync process error: {error_msg}" in result.error_message

            # Verify the error was logged by the outer exception handler
            mock_logger.error.assert_called_once()
            assert (
                "Unexpected error during sync process"
                in mock_logger.error.call_args[0][0]
            )
            # Verify mastodon.post was NOT called
            mock_masto.post.assert_not_called()
            # Verify save_state is called once for the error
            mock_save_state.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_unknown_status(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test _sync_post handling an unexpected status from mastodon.post."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon.post to return an invalid status
            mock_masto.post.return_value = (
                "weird_status",
                None,
                "Something odd happened",
            )

            # Create manager
            manager = SyncManager(sample_config)

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result - should be a failure record
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.success is False
            assert "Unknown status: weird_status" in result.error_message

            # Verify the error was logged
            mock_logger.error.assert_called_once()
            assert "Unknown status 'weird_status'" in mock_logger.error.call_args[0][0]
            # Verify save_state is called once for the error
            mock_save_state.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_thread_with_parent(
        self,
        mock_save_state,
        sample_config,
        sample_bluesky_reply_post,
        mock_mastodon_success_post,
    ):
        """Test _sync_post with a self-reply post where the parent ID IS found."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon post response
            mock_masto.post.return_value = ("success", mock_mastodon_success_post, None)

            # Create manager
            manager = SyncManager(sample_config)
            manager._rebuild_parent_map = MagicMock()  # Patch rebuild map

            # Mock find_mastodon_id_for_bluesky_post to return a valid parent ID
            parent_mastodon_id = "parent_toot_123"
            manager.find_mastodon_id_for_bluesky_post = MagicMock(
                return_value=parent_mastodon_id
            )

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_reply_post)

            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_reply_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == mock_mastodon_success_post.id
            assert result.target_platform == "mastodon"
            assert result.success is True
            assert result.error_message is None

            # Check state was updated
            assert sample_bluesky_reply_post.id in manager.synced_posts
            assert result in manager.sync_records

            # Verify mock calls
            mock_masto.post.assert_called_once()
            args, kwargs = mock_masto.post.call_args
            assert args[0] == sample_bluesky_reply_post
            assert (
                kwargs["in_reply_to_id"] == parent_mastodon_id
            )  # Should use the parent ID

            # Verify info log message about finding parent
            mock_logger.info.assert_any_call(
                f"Found Mastodon parent ID: {parent_mastodon_id} "
                f"for Bluesky parent: {sample_bluesky_reply_post.reply_parent}"
            )

            # _save_state is called immediately after successful posting
            mock_save_state.assert_called_once()
            # _rebuild_parent_map should be called
            manager._rebuild_parent_map.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_success_without_post_object(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test _sync_post when status is success but no post object returned."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon post response with success but no post object
            mock_masto.post.return_value = ("success", None, None)

            # Create manager
            manager = SyncManager(sample_config)
            manager._rebuild_parent_map = MagicMock()  # Patch rebuild map

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)

            # Check the result - looking at the implementation, we see that
            # a missing post object causes a wrapped Exception, which leads to
            # a "failed" status in the record
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == ""  # Should be empty since no post object
            assert result.target_platform == "mastodon"
            assert result.success is False  # Marked as failed due to error handling
            # The warning message gets wrapped in a sync process error
            assert "Sync process error" in result.error_message

            # Verify warning was logged about missing post object
            mock_logger.warning.assert_called_with(
                f"Post {sample_bluesky_post.id} reported as success but no post object."
            )

            # _save_state is called twice
            assert mock_save_state.call_count == 2
            # _rebuild_parent_map should NOT be called on failure
            manager._rebuild_parent_map.assert_not_called()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_sync_post_thread_without_parent(
        self,
        mock_save_state,
        sample_config,
        sample_bluesky_reply_post,
        mock_mastodon_success_post,
    ):
        """Test _sync_post with a self-reply post where the parent ID can't be found."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            patch("bluemastodon.sync.logger") as mock_logger,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock mastodon post response
            mock_masto.post.return_value = ("success", mock_mastodon_success_post, None)

            # Create manager
            manager = SyncManager(sample_config)
            manager._rebuild_parent_map = MagicMock()  # Patch rebuild map

            # Ensure find_mastodon_id_for_bluesky_post returns None (parent not found)
            manager.find_mastodon_id_for_bluesky_post = MagicMock(return_value=None)

            # Call _sync_post
            result = manager._sync_post(sample_bluesky_reply_post)

            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_reply_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == mock_mastodon_success_post.id
            assert result.target_platform == "mastodon"
            assert result.success is True
            assert result.error_message is None

            # Check state was updated
            assert sample_bluesky_reply_post.id in manager.synced_posts
            assert result in manager.sync_records

            # Verify mock calls
            mock_masto.post.assert_called_once()
            args, kwargs = mock_masto.post.call_args
            assert args[0] == sample_bluesky_reply_post
            assert (
                kwargs["in_reply_to_id"] is None
            )  # Should be None when parent not found

            # Verify warning was logged about not finding parent
            mock_logger.warning.assert_called_with(
                f"Could not find Mastodon parent ID for Bluesky parent: "
                f"{sample_bluesky_reply_post.reply_parent}"
            )

            # _save_state is called immediately after successful posting
            mock_save_state.assert_called_once()
            # _rebuild_parent_map should be called
            manager._rebuild_parent_map.assert_called_once()

    @patch("bluemastodon.sync.SyncManager._sync_post")
    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_run_sync_success(self, mock_save_state, mock_sync_post, sample_config):
        """Test run_sync success case."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock authentication
            mock_bsky.ensure_authenticated.return_value = True
            mock_masto.ensure_authenticated.return_value = True

            # Mock recent posts with comparable created_at times
            now = datetime.now()
            post1 = MagicMock(spec=BlueskyPost)  # Use spec for attribute access
            post1.id = "post1"
            post1.created_at = now - timedelta(minutes=10)  # Older
            post2 = MagicMock(spec=BlueskyPost)
            post2.id = "post2"
            post2.created_at = now - timedelta(minutes=5)  # Newer
            post3 = MagicMock(spec=BlueskyPost)
            post3.id = "already_synced"
            # post3 doesn't need created_at as it's filtered out before sorting
            # Return in reverse chrono order to test sorting
            mock_bsky.get_recent_posts.return_value = [post2, post1, post3]

            # Mock sync_post results
            record1 = MagicMock(spec=SyncRecord)  # Corresponds to post1 (older)
            record2 = MagicMock(spec=SyncRecord)  # Corresponds to post2 (newer)
            # side_effect order should match the sorted order (post1, then post2)
            mock_sync_post.side_effect = [record1, record2]

            # Create manager with one post already synced
            manager = SyncManager(sample_config)
            manager.synced_posts = {"already_synced"}

            # Mock find_mastodon_id_for_bluesky_post to always return None
            manager.find_mastodon_id_for_bluesky_post = MagicMock(return_value=None)

            # Call run_sync
            result = manager.run_sync()

            # Check the result
            assert result == [record1, record2]

            # Verify mock calls
            mock_bsky.ensure_authenticated.assert_called_once()
            mock_masto.ensure_authenticated.assert_called_once()
            mock_bsky.get_recent_posts.assert_called_once_with(
                hours_back=sample_config.lookback_hours,
                limit=sample_config.max_posts_per_run,
                include_threads=sample_config.include_threads,
            )

            # Should only sync new posts, not the already synced one
            assert mock_sync_post.call_count == 2
            # Check calls were made in sorted order (post1 then post2)
            assert mock_sync_post.call_args_list == [call(post1), call(post2)]

            # Should save state at the end if new records were processed
            mock_save_state.assert_called_once()

    def test_run_sync_bluesky_auth_failure(self, sample_config):
        """Test run_sync when Bluesky authentication fails."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock authentication failure
            mock_bsky.ensure_authenticated.return_value = False

            # Create manager
            manager = SyncManager(sample_config)

            # Call run_sync
            result = manager.run_sync()

            # Check the result
            assert result == []

            # Verify mock calls
            mock_bsky.ensure_authenticated.assert_called_once()
            mock_masto.ensure_authenticated.assert_not_called()
            mock_bsky.get_recent_posts.assert_not_called()

    def test_run_sync_mastodon_auth_failure(self, sample_config):
        """Test run_sync when Mastodon authentication fails."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock authentication
            mock_bsky.ensure_authenticated.return_value = True
            mock_masto.ensure_authenticated.return_value = False

            # Create manager
            manager = SyncManager(sample_config)

            # Call run_sync
            result = manager.run_sync()

            # Check the result
            assert result == []

            # Verify mock calls
            mock_bsky.ensure_authenticated.assert_called_once()
            mock_masto.ensure_authenticated.assert_called_once()
            mock_bsky.get_recent_posts.assert_not_called()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_run_sync_no_new_posts(self, mock_save_state, sample_config):
        """Test run_sync when there are no new posts to sync."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):

            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock authentication
            mock_bsky.ensure_authenticated.return_value = True
            mock_masto.ensure_authenticated.return_value = True

            # Return empty list of recent posts
            mock_bsky.get_recent_posts.return_value = []

            # Create manager
            manager = SyncManager(sample_config)

            # Call run_sync
            result = manager.run_sync()

            # Check the result
            assert result == []

            # Verify mock calls
            mock_bsky.ensure_authenticated.assert_called_once()
            mock_masto.ensure_authenticated.assert_called_once()
            mock_bsky.get_recent_posts.assert_called_once()
            # State is only saved if there are new records
            mock_save_state.assert_not_called()

    @patch("bluemastodon.sync.SyncManager._save_state")
    def test_run_sync_with_new_posts(
        self, mock_save_state, sample_config, sample_bluesky_post
    ):
        """Test run_sync with new posts to sync."""
        with (
            patch("bluemastodon.sync.BlueskyClient") as mock_bsky_class,
            patch("bluemastodon.sync.MastodonClient") as mock_masto_class,
            # Prevent _load_state from trying to read the file
            patch("bluemastodon.sync.os.path.exists", return_value=False),
        ):
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto

            # Mock authentication
            mock_bsky.ensure_authenticated.return_value = True
            mock_masto.ensure_authenticated.return_value = True

            # Return list with one post
            mock_bsky.get_recent_posts.return_value = [sample_bluesky_post]

            # Create manager and patch _sync_post to return a success record
            manager = SyncManager(sample_config)

            with patch.object(manager, "_sync_post") as mock_sync_post:
                # Create a mock record
                mock_record = SyncRecord(
                    source_id=sample_bluesky_post.id,
                    source_platform="bluesky",
                    target_id="toot123",
                    target_platform="mastodon",
                    synced_at=datetime.now(),
                    success=True,
                )
                mock_sync_post.return_value = mock_record

                # Call run_sync
                result = manager.run_sync()

                # Check the result
                assert len(result) == 1
                assert result[0] == mock_record

                # Verify mock calls
                mock_bsky.ensure_authenticated.assert_called_once()
                mock_masto.ensure_authenticated.assert_called_once()
                mock_bsky.get_recent_posts.assert_called_once()
                mock_sync_post.assert_called_once_with(sample_bluesky_post)

                # Verify final state save
                mock_save_state.assert_called_once()
