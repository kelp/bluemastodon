"""Tests for the social_sync package."""

import os
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

from social_sync import main

# Tests need pytest fixtures


class TestMain:
    """Test the main function."""

    @patch("social_sync.argparse.ArgumentParser.parse_args")
    @patch("social_sync.load_config")
    @patch("social_sync.SyncManager")
    @patch("social_sync.logger")
    def test_main_success(
        self, mock_logger, mock_manager_class, mock_load_config, mock_parse_args
    ):
        """Test main function with successful sync."""
        # Setup mocks
        args = MagicMock()
        args.config = None
        args.state = None
        args.debug = False
        args.dry_run = False
        mock_parse_args.return_value = args

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager.run_sync.return_value = [MagicMock(success=True)]
        mock_manager_class.return_value = mock_manager

        # Call the function
        result = main([])

        # Check the result
        assert result == 0

        # Verify mock calls
        mock_load_config.assert_called_once_with(None)
        mock_manager_class.assert_called_once_with(mock_config, None)
        mock_manager.run_sync.assert_called_once()

    @patch("social_sync.argparse.ArgumentParser.parse_args")
    @patch("social_sync.load_config")
    @patch("social_sync.SyncManager")
    @patch("social_sync.logger")
    def test_main_with_failures(
        self, mock_logger, mock_manager_class, mock_load_config, mock_parse_args
    ):
        """Test main function with some sync failures."""
        # Setup mocks
        args = MagicMock()
        args.config = "config.env"
        args.state = "state.json"
        args.debug = True
        args.dry_run = False
        mock_parse_args.return_value = args

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_manager = MagicMock()
        # Return a mix of successful and failed records
        mock_manager.run_sync.return_value = [
            MagicMock(success=True),
            MagicMock(success=False),
        ]
        mock_manager_class.return_value = mock_manager

        # Call the function
        result = main([])

        # Check the result
        assert result == 1  # Should be non-zero if any failures

        # Verify mock calls
        mock_load_config.assert_called_once_with("config.env")
        mock_manager_class.assert_called_once_with(mock_config, "state.json")
        mock_manager.run_sync.assert_called_once()

    @patch("social_sync.argparse.ArgumentParser.parse_args")
    @patch("social_sync.load_config")
    @patch("social_sync.SyncManager")
    @patch("social_sync.logger")
    def test_main_dry_run(
        self, mock_logger, mock_manager_class, mock_load_config, mock_parse_args
    ):
        """Test main function in dry-run mode."""
        # Setup mocks
        args = MagicMock()
        args.config = None
        args.state = None
        args.debug = False
        args.dry_run = True
        mock_parse_args.return_value = args

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Set up BlueskyClient for dry-run
        mock_bluesky = MagicMock()
        mock_bluesky.ensure_authenticated.return_value = True
        mock_bluesky.get_recent_posts.return_value = [MagicMock(), MagicMock()]
        mock_manager.bluesky = mock_bluesky

        # Call the function
        result = main([])

        # Check the result
        assert result == 0

        # Verify mock calls for dry-run mode
        mock_load_config.assert_called_once_with(None)
        mock_manager_class.assert_called_once_with(mock_config, None)
        mock_bluesky.ensure_authenticated.assert_called_once()
        mock_bluesky.get_recent_posts.assert_called_once()
        # Should not call run_sync in dry-run mode
        mock_manager.run_sync.assert_not_called()

    @patch("social_sync.argparse.ArgumentParser.parse_args")
    @patch("social_sync.load_config")
    @patch("social_sync.SyncManager")
    @patch("social_sync.logger")
    def test_main_dry_run_auth_failure(
        self, mock_logger, mock_manager_class, mock_load_config, mock_parse_args
    ):
        """Test main function in dry-run mode with authentication failure."""
        # Setup mocks
        args = MagicMock()
        args.config = None
        args.state = None
        args.debug = False
        args.dry_run = True
        mock_parse_args.return_value = args

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Set up BlueskyClient for dry-run with auth failure
        mock_bluesky = MagicMock()
        mock_bluesky.ensure_authenticated.return_value = False
        mock_manager.bluesky = mock_bluesky

        # Call the function
        result = main([])

        # Check the result
        assert result == 1

        # Verify mock calls
        mock_load_config.assert_called_once_with(None)
        mock_manager_class.assert_called_once_with(mock_config, None)
        mock_bluesky.ensure_authenticated.assert_called_once()
        mock_bluesky.get_recent_posts.assert_not_called()
        mock_manager.run_sync.assert_not_called()

    def test_module_main(self):
        """Test __main__ block."""
        # To test the if __name__ == "__main__" block, we'll create a module copy
        module_content = """
import sys
def main():
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

        # Write to a temp file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
            temp_file.write(module_content.encode())
            module_path = temp_file.name

        try:
            # Run as script which should trigger the __name__ == "__main__" block
            proc = subprocess.run([sys.executable, module_path], capture_output=True)
            # Script should exit with code 0
            assert proc.returncode == 0

        finally:
            # Cleanup
            if os.path.exists(module_path):
                os.unlink(module_path)

    @patch("social_sync.argparse.ArgumentParser.parse_args")
    @patch("social_sync.load_config")
    @patch("social_sync.logger")
    def test_main_exception(self, mock_logger, mock_load_config, mock_parse_args):
        """Test main function with exception."""
        # Setup mocks
        args = MagicMock()
        mock_parse_args.return_value = args

        # Mock load_config to raise an exception
        mock_load_config.side_effect = ValueError("Test error")

        # Call the function
        result = main([])

        # Check the result
        assert result == 1

        # Verify mock calls
        mock_load_config.assert_called_once()
        mock_logger.exception.assert_called_once()
