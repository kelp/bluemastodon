#!/bin/bash
set -e

# Navigate to the project root (assuming this script is in the scripts directory)
cd "$(dirname "$0")/.."

# Print current directory for confirmation
echo "Setting up development environment in: $(pwd)"

# Ensure poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install poetry first."
    echo "See https://python-poetry.org/docs/#installation for instructions."
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
poetry run pre-commit install

# Install pre-push hook
echo "Installing pre-push hook..."
mkdir -p .git/hooks
cp .pre-commit-hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# Update pre-commit hooks
echo "Updating pre-commit hooks..."
poetry run pre-commit autoupdate

# Run pre-commit hooks on all files
echo "Running pre-commit hooks on all files..."
poetry run pre-commit run --all-files || {
    echo "Some pre-commit hooks failed. This is expected on first run as they may modify files."
    echo "The modified files have been fixed according to our code standards."
    echo "Please review the changes and commit them."
}

echo ""
echo "Development environment setup complete!"
echo ""
echo "You can now commit changes and the pre-commit hooks will automatically run."
echo "To manually run the hooks on all files: poetry run pre-commit run --all-files"
echo ""