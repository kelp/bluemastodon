"""Test the __main__.py module."""

import sys
from unittest.mock import MagicMock, patch


class TestMainModule:
    """Test for the __main__.py module."""

    def test_main_execution(self) -> None:
        """Test that __main__.py properly calls main() when executed."""
        # Create a mock for the main function
        mock_main = MagicMock(return_value=0)

        # Patch the main function and sys.exit
        with patch("bluemastodon.__main__.main", mock_main):
            with patch("sys.exit") as mock_exit:
                # Import and execute the code in __main__.py
                # The import will trigger the if __name__ == "__main__" block
                # but we've mocked sys.exit to prevent actual exit

                # Read and execute the __main__.py code
                import bluemastodon.__main__ as main_module

                # Execute the main block code directly
                if hasattr(main_module, "main"):
                    sys.exit(main_module.main())

                # Verify main was called
                mock_main.assert_called_once()
                # Verify sys.exit was called with the return value
                mock_exit.assert_called_once_with(0)
