"""Tests for the sync module."""

import os
import json
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

import pytest

from social_sync.sync import SyncManager
from social_sync.models import BlueskyPost, MastodonPost, SyncRecord


class TestSyncManager:
    """Test the SyncManager class."""

    def test_init(self, sample_config):
        """Test initialization of SyncManager."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky, \
             patch('social_sync.sync.MastodonClient') as mock_masto:
            
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
        with patch('social_sync.sync.os.path.exists', return_value=False), \
             patch('social_sync.sync.BlueskyClient'), \
             patch('social_sync.sync.MastodonClient'):
            
            manager = SyncManager(sample_config)
            
            # Check that state is empty
            assert manager.synced_posts == set()
            assert manager.sync_records == []

    def test_load_state_with_file(self, sample_config, sample_sync_state_file):
        """Test _load_state with existing state file."""
        with patch('social_sync.sync.BlueskyClient'), \
             patch('social_sync.sync.MastodonClient'):
            
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

    def test_load_state_with_invalid_file(self, sample_config):
        """Test _load_state with invalid state file."""
        # Create an invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("this is not valid json")
            invalid_state_file = temp_file.name
        
        try:
            with patch('social_sync.sync.BlueskyClient'), \
                 patch('social_sync.sync.MastodonClient'):
                
                # Create manager with invalid state file
                manager = SyncManager(sample_config, invalid_state_file)
                
                # Check that state is empty
                assert manager.synced_posts == set()
                assert manager.sync_records == []
        
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
                        "synced_at": datetime.now().isoformat()
                    }
                ]
            }
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                json.dump(state_content, temp_file)
                invalid_record_file = temp_file.name
            
            with patch('social_sync.sync.BlueskyClient'), \
                 patch('social_sync.sync.MastodonClient'), \
                 patch('social_sync.sync.logger') as mock_logger:
                
                # Create manager with invalid record file
                manager = SyncManager(sample_config, invalid_record_file)
                
                # Check that synced_posts were loaded but invalid record was skipped
                assert manager.synced_posts == {"post1"}
                assert manager.sync_records == []
                
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                assert "Could not parse sync record" in mock_logger.warning.call_args[0][0]
        
        finally:
            # Clean up
            if invalid_record_file and os.path.exists(invalid_record_file):
                os.unlink(invalid_record_file)

    def test_save_state(self, sample_config):
        """Test _save_state method."""
        # Setup mock for open and json.dump
        mock_file = MagicMock()
        m_open = mock_open(mock=mock_file)
        
        with patch('social_sync.sync.BlueskyClient'), \
             patch('social_sync.sync.MastodonClient'), \
             patch('social_sync.sync.open', m_open), \
             patch('social_sync.sync.json.dump') as mock_dump, \
             patch('social_sync.sync.os.makedirs') as mock_makedirs:
            
            # Create manager
            manager = SyncManager(sample_config, "/tmp/state.json")
            
            # Add some state
            manager.synced_posts = {"post1", "post2"}
            
            now = datetime.now()
            record = SyncRecord(
                source_id="post1",
                source_platform="bluesky",
                target_id="toot1",
                target_platform="mastodon",
                synced_at=now,
                success=True
            )
            manager.sync_records = [record]
            
            # Call _save_state
            manager._save_state()
            
            # Verify directory was created
            mock_makedirs.assert_called_once_with(os.path.dirname("/tmp/state.json"), exist_ok=True)
            
            # Verify file was opened
            m_open.assert_called_once_with("/tmp/state.json", 'w')
            
            # Verify json.dump was called with correct data
            # Extract the data argument from the call
            call_args = mock_dump.call_args[0]
            data = call_args[0]
            
            # Check state content
            assert isinstance(data, dict)
            assert set(data["synced_posts"]) == {"post1", "post2"}
            assert len(data["sync_records"]) == 1
            assert data["sync_records"][0]["source_id"] == "post1"
            assert data["sync_records"][0]["target_id"] == "toot1"
            
    def test_save_state_error(self, sample_config):
        """Test _save_state error handling."""
        with patch('social_sync.sync.BlueskyClient'), \
             patch('social_sync.sync.MastodonClient'), \
             patch('social_sync.sync.open', side_effect=OSError("Failed to open file")), \
             patch('social_sync.sync.logger') as mock_logger, \
             patch('social_sync.sync.os.makedirs'):
            
            # Create manager
            manager = SyncManager(sample_config, "/tmp/state.json")
            
            # Call _save_state
            manager._save_state()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Failed to save sync state" in mock_logger.error.call_args[0][0]

    @patch('social_sync.sync.SyncManager._save_state')
    def test_sync_post_success(self, mock_save_state, sample_config, sample_bluesky_post):
        """Test _sync_post success case."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto
            
            # Mock mastodon post response
            mock_mastodon_post = MagicMock()
            mock_mastodon_post.id = "toot123"
            mock_masto.cross_post.return_value = mock_mastodon_post
            
            # Create manager
            manager = SyncManager(sample_config)
            
            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)
            
            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == "toot123"
            assert result.target_platform == "mastodon"
            assert result.success is True
            assert result.error_message is None
            
            # Check state was updated
            assert sample_bluesky_post.id in manager.synced_posts
            assert result in manager.sync_records
            
            # Verify mock calls
            mock_masto.cross_post.assert_called_once_with(sample_bluesky_post)
            mock_save_state.assert_not_called()  # _save_state is called after run_sync, not after each post

    @patch('social_sync.sync.SyncManager._save_state')
    def test_sync_post_failure(self, mock_save_state, sample_config, sample_bluesky_post):
        """Test _sync_post when cross-posting fails."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto
            
            # Mock cross_post to return None (failure)
            mock_masto.cross_post.return_value = None
            
            # Create manager
            manager = SyncManager(sample_config)
            
            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)
            
            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == ""
            assert result.target_platform == "mastodon"
            assert result.success is False
            assert result.error_message is not None
            
            # Check state was updated (record added, but synced_posts not updated)
            assert sample_bluesky_post.id not in manager.synced_posts
            assert result in manager.sync_records
            
            # Verify mock calls
            mock_masto.cross_post.assert_called_once_with(sample_bluesky_post)
            mock_save_state.assert_not_called()

    @patch('social_sync.sync.SyncManager._sync_post')
    @patch('social_sync.sync.SyncManager._save_state')
    def test_run_sync_success(self, mock_save_state, mock_sync_post, sample_config):
        """Test run_sync success case."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto
            
            # Mock authentication
            mock_bsky.ensure_authenticated.return_value = True
            mock_masto.ensure_authenticated.return_value = True
            
            # Mock recent posts
            post1 = MagicMock()
            post1.id = "post1"
            post2 = MagicMock()
            post2.id = "post2"
            post3 = MagicMock()
            post3.id = "already_synced"
            mock_bsky.get_recent_posts.return_value = [post1, post2, post3]
            
            # Mock sync_post results
            record1 = MagicMock()
            record2 = MagicMock()
            mock_sync_post.side_effect = [record1, record2]
            
            # Create manager with one post already synced
            manager = SyncManager(sample_config)
            manager.synced_posts = {"already_synced"}
            
            # Call run_sync
            result = manager.run_sync()
            
            # Check the result
            assert result == [record1, record2]
            
            # Verify mock calls
            mock_bsky.ensure_authenticated.assert_called_once()
            mock_masto.ensure_authenticated.assert_called_once()
            mock_bsky.get_recent_posts.assert_called_once_with(
                hours_back=sample_config.lookback_hours,
                limit=sample_config.max_posts_per_run
            )
            
            # Should only sync new posts, not the already synced one
            assert mock_sync_post.call_count == 2
            mock_sync_post.assert_any_call(post1)
            mock_sync_post.assert_any_call(post2)
            
            # Should save state after syncing
            mock_save_state.assert_called_once()

    def test_run_sync_bluesky_auth_failure(self, sample_config):
        """Test run_sync when Bluesky authentication fails."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
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
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
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

    @patch('social_sync.sync.SyncManager._save_state')
    def test_run_sync_no_new_posts(self, mock_save_state, sample_config):
        """Test run_sync when there are no new posts to sync."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class:
            
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
            mock_save_state.assert_called_once()
            
    def test_sync_post_exception(self, sample_config, sample_bluesky_post):
        """Test _sync_post with an exception during cross-posting."""
        with patch('social_sync.sync.BlueskyClient') as mock_bsky_class, \
             patch('social_sync.sync.MastodonClient') as mock_masto_class, \
             patch('social_sync.sync.logger') as mock_logger:
            
            # Setup mocks
            mock_bsky = MagicMock()
            mock_masto = MagicMock()
            mock_bsky_class.return_value = mock_bsky
            mock_masto_class.return_value = mock_masto
            
            # Mock cross_post to raise an exception
            mock_masto.cross_post.side_effect = Exception("Unexpected error during cross-posting")
            
            # Create manager
            manager = SyncManager(sample_config)
            
            # Call _sync_post
            result = manager._sync_post(sample_bluesky_post)
            
            # Check the result
            assert isinstance(result, SyncRecord)
            assert result.source_id == sample_bluesky_post.id
            assert result.source_platform == "bluesky"
            assert result.target_id == ""
            assert result.target_platform == "mastodon"
            assert result.success is False
            assert "Unexpected error during cross-posting" in result.error_message
            
            # Verify the error was logged
            mock_logger.error.assert_called_once()
            assert f"Error syncing post {sample_bluesky_post.id}" in mock_logger.error.call_args[0][0]
            
            # Verify the record was added to sync_records
            assert result in manager.sync_records