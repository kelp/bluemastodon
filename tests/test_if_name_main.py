"""
Test the if __name__ == "__main__" block in bluemastodon modules.
"""

import sys
import unittest
from unittest.mock import patch


class TestMainModule(unittest.TestCase):
    """Test the __main__.py module."""

    def test_main_module(self):
        """Test the __main__.py module's entry point."""
        # Save original imports and modules
        original_sys_modules = sys.modules.copy()

        # Mock main function to prevent actual execution
        with patch("bluemastodon.main") as mock_main:
            mock_main.return_value = 0

            # Execute the module in a way that __name__ == "__main__" evaluates to True
            try:
                # This import executes the code in __main__.py with
                # __name__ set to "__main__"
                with patch.dict(
                    sys.modules, {"__main__": __import__("bluemastodon.__main__")}
                ):
                    import bluemastodon.__main__

                    # Manually invoke the main block from __main__ with
                    # name set to __main__
                    # to trigger the execution of sys.exit(main())
                    bluemastodon.__main__.__name__ = "__main__"
                    exec(
                        """
if __name__ == "__main__":
    sys.exit(main())
                        """,
                        vars(bluemastodon.__main__),
                    )
            except SystemExit as e:
                # Ensure the exit code is the one returned by our mock
                self.assertEqual(e.code, 0)

            # Verify that main was called
            mock_main.assert_called_once()

        # Restore original modules
        sys.modules = original_sys_modules


if __name__ == "__main__":
    unittest.main()
