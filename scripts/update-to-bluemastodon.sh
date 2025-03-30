#!/bin/bash
# Script to help with the repository rename from social-sync to bluemastodon

# Step 1: Ensure we're in the right directory
if [ ! -d "src/social_sync" ]; then
    echo "Error: This script must be run from the repository root directory."
    exit 1
fi

# Step 2: Confirm remaining references to be updated
echo "Checking for remaining references to 'social_sync' and 'social-sync'..."
grep -r "social[_-]sync" --include="*.py" --include="*.md" --include="*.yml" .

# Step 3: Rename the directory
echo "Repository rename steps:"
echo "1. First, commit all your current changes."
echo "2. Create a new repository on GitHub named 'bluemastodon'."
echo "3. Update the remote origin with the following command:"
echo "   git remote set-url origin https://github.com/kelp/bluemastodon.git"
echo "4. Push your changes to the new repository:"
echo "   git push -u origin main"
echo ""
echo "IMPORTANT: After completing these steps, you should further update tests and any remaining references."
