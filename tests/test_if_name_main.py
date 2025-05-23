"""Test the if __name__ == "__main__" block in bluemastodon modules."""

from unittest.mock import MagicMock, patch


class TestMainModule:
    """Test the __main__.py module."""

    def test_main_module(self) -> None:
        """Test the __main__.py module's entry point."""
        # Mock the main function to prevent actual execution
        mock_main = MagicMock(return_value=0)

        with patch("bluemastodon.main", mock_main):
            with patch("sys.exit") as mock_exit:
                # Import the __main__ module
                # This should trigger the if __name__ == "__main__" block
                # since __main__.py has that check
                exec(
                    open("src/bluemastodon/__main__.py").read(),
                    {"__name__": "__main__"},
                )

                # Verify main was called
                mock_main.assert_called_once()
                # Verify sys.exit was called
                mock_exit.assert_called_once_with(0)
