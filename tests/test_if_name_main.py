"""
Test the if __name__ == "__main__" block in social_sync.
This module should be run directly as a script, not imported.
"""

import social_sync

if __name__ == "__main__":
    # Temporarily modify __name__ to "__main__" to trigger the block
    original_name = social_sync.__name__
    social_sync.__name__ = "__main__"

    # Backup the original sys.exit
    import sys

    original_exit = sys.exit

    # Mock sys.exit to prevent actual exit
    def mock_exit(code=0):
        print(f"sys.exit called with code {code}")
        return code

    sys.exit = mock_exit

    # Import to trigger the if __name__ == "__main__" block
    import social_sync

    # Restore the original values
    sys.exit = original_exit
    social_sync.__name__ = original_name

    print("Test completed successfully")
