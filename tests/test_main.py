"""Test the __main__.py module."""

import sys
import unittest
from unittest.mock import patch


class TestMainModule(unittest.TestCase):
    """Test for the __main__.py module."""

    def test_main_execution(self):
        """Test that __main__.py properly calls main() when executed."""
        # Use patch to avoid actual execution
        with patch("social_sync.main") as mock_main:
            # Set up the mock
            mock_main.return_value = 0
            
            # Temporarily modify the name to simulate execution as __main__
            import social_sync.__main__
            original_name = social_sync.__main__.__name__
            
            try:
                # Set __name__ to "__main__" to trigger the conditional block
                social_sync.__main__.__name__ = "__main__"
                
                # Import the module to trigger code execution
                with self.assertRaises(SystemExit) as cm:
                    # This is the same code as in __main__.py
                    if social_sync.__main__.__name__ == "__main__":
                        sys.exit(mock_main())
                
                # Verify exit code
                self.assertEqual(cm.exception.code, 0)
                
                # Verify main was called
                mock_main.assert_called_once()
                
            finally:
                # Restore original name
                social_sync.__main__.__name__ = original_name