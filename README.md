# BlueMastodon

A Python tool to automatically cross-post manual Bluesky posts to Mastodon.

*Formerly known as bluemastodon*

![Version](https://img.shields.io/badge/version-0.9.7-blue)
![Status](https://img.shields.io/badge/status-beta-orange)
![Test Status](https://github.com/kelp/bluemastodon/actions/workflows/test.yml/badge.svg)
![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/github/license/kelp/bluemastodon)

## Overview

BlueMastodon monitors your Bluesky account for new posts and automatically
cross-posts them to your Mastodon account. It's designed to be run as a
scheduled job via GitHub Actions or any other scheduler.

This tool specifically handles synchronizing manual posts from Bluesky to
Mastodon. Blog post publishing to social platforms can be managed by a
separate tool.

## Features

- 🔄 **Automatic Synchronization**: Fetches recent Bluesky posts and
  cross-posts to Mastodon
- 🖼️ **Media Support**: Transfers images and attachments between platforms
- 🔗 **Link Handling**: Preserves external links in your posts
- 🧠 **Smart Synchronization**: Keeps track of synced posts to avoid duplicates
- 📝 **Format Preservation**: Maintains post formatting during cross-posting
- 🚨 **Error Handling**: Robust error handling and logging
- 🔒 **Secure**: Handles API credentials securely
- 🤖 **GitHub Action Ready**: Easily deployable as a GitHub Actions workflow

## Setup

### Prerequisites

- Python 3.10 or higher (tested on 3.10, 3.11, 3.12, 3.13)
- A Bluesky account
- A Mastodon account with API access

### Installation

#### Using pip

Install directly from PyPI:

```bash
pip install bluemastodon
```

#### Using Homebrew

Install using Homebrew on macOS or Linux:

```bash
# Add the tap first (only needed once)
brew tap kelp/tools

# Install bluemastodon
brew install kelp/tools/bluemastodon
```

After installation, you can run the tool from the command line:

```bash
# Basic usage
bluemastodon --config /path/to/your/.env

# Dry run (won't post to Mastodon, just shows what would be posted)
bluemastodon --config /path/to/your/.env --dry-run

# With debug logging enabled
bluemastodon --config /path/to/your/.env --debug

# Specify state file location (default is sync_state.json in current directory)
bluemastodon --config /path/to/your/.env --state /path/to/state.json
```

You can also use it as a library in your Python code:

```python
from bluemastodon import Config, SyncManager

# Create configuration
config = Config(
    bluesky_username="your_username.bsky.social",
    bluesky_password="your_app_password",
    mastodon_instance_url="https://your.mastodon.instance",
    mastodon_access_token="your_access_token",
    lookback_hours=6,
)

# Initialize sync manager
sync_manager = SyncManager(config, state_file="sync_state.json")

# Run the sync
new_records = sync_manager.run_sync()
print(f"Synced {len(new_records)} posts")
```

#### Using Poetry

1. Clone the repository:

```bash
git clone https://github.com/kelp/bluemastodon.git
cd bluemastodon
```

2. Install with Poetry:

```bash
poetry install
```

### Configuration

Create a `.env` file with your credentials:

```env
# Required credentials
BLUESKY_USERNAME=your_bluesky_username
BLUESKY_PASSWORD=your_bluesky_password
MASTODON_INSTANCE_URL=https://your.mastodon.instance
MASTODON_ACCESS_TOKEN=your_mastodon_access_token

# Optional settings with defaults
LOOKBACK_HOURS=24                # How far back to look for posts
SYNC_INTERVAL_MINUTES=60         # Frequency of synchronization
MAX_POSTS_PER_RUN=5              # Maximum posts to sync in one run
INCLUDE_MEDIA=true               # Include media attachments
INCLUDE_LINKS=true               # Include post links
```

#### Obtaining API Credentials

##### Bluesky

For Bluesky, you'll need your username and application password.

##### Mastodon

1. Log in to your Mastodon instance
2. Go to Preferences > Development > New Application
3. Give your app a name and select the following permissions:
   - `read:accounts`
   - `read:statuses`
   - `write:media`
   - `write:statuses`
4. Save and copy the "Access token"

## Usage

### Command Line

Run the sync manually:

```bash
# If installed with pip
bluemastodon

# If using Poetry
poetry run python -m social_sync
```

#### Options

```
-c, --config    Path to custom config file (.env format)
-s, --state     Path to custom state file (JSON format)
-d, --debug     Enable debug logging
--dry-run       Simulate syncing without posting
```

#### Example Commands

```bash
# Run with debug logging
bluemastodon --debug

# Dry run (no actual posts)
bluemastodon --dry-run

# Use custom config file
bluemastodon --config /path/to/custom.env

# Specify state file location
bluemastodon --state /path/to/state.json
```

### Scheduled Sync with GitHub Actions

#### Setting Up Securely with GitHub Secrets

BlueMastodon is designed to work with GitHub Actions in a secure way, using
GitHub's encrypted secrets feature to store sensitive credentials:

1. Fork this repository or copy the workflow files to your own repository
2. In your GitHub repository, go to "Settings" > "Secrets and variables" >
   "Actions"
3. Add the following repository secrets (these are encrypted and secure):
   - `BLUESKY_USERNAME`: Your Bluesky username
   - `BLUESKY_PASSWORD`: Your Bluesky application password
   - `MASTODON_INSTANCE_URL`: Your Mastodon instance URL
   - `MASTODON_ACCESS_TOKEN`: Your Mastodon API access token

For detailed instructions on obtaining and setting up these secrets, see the
[GitHub Secrets Setup Guide](docs/setup-github-secrets.md).

> **SECURITY WARNING**: Never commit your actual credentials to the repository!
> Always use GitHub Secrets for sensitive information.

#### Optional Configuration Variables

You can also add these as repository variables (not secrets, as they're not
sensitive):

1. Go to "Settings" > "Secrets and variables" > "Actions" > "Variables" tab
2. Configure any of the following:
   - `LOOKBACK_HOURS`: How far back to look for posts (default: 24)
   - `SYNC_INTERVAL_MINUTES`: How often to sync (default: 60)
   - `MAX_POSTS_PER_RUN`: Maximum posts to sync (default: 5)
   - `INCLUDE_MEDIA`: Whether to include media (default: true)
   - `INCLUDE_LINKS`: Whether to include links (default: true)

#### Running the Workflow

1. Enable the workflow in your GitHub repository (go to "Actions" tab)
2. The sync will run automatically according to the schedule (hourly by default)
3. You can also trigger it manually from the Actions tab by clicking "Run
   workflow"
4. For manual runs, you can enable debug mode or dry-run mode using the provided
   options

#### How Duplicate Posts Are Prevented

BlueMastodon uses a robust state tracking system to prevent duplicate posts:

1. **State File**: Each run maintains a JSON file with IDs of previously synced
   posts
2. **GitHub Actions Cache**: The state file is persisted between runs using
   GitHub's cache
3. **Lookback Window**: The tool only examines posts from the last 6 hours
   (configurable)
4. **Deduplication Logic**: Posts with IDs already in the state file are
   automatically skipped

This system ensures:
- Each post is only synced once, even across multiple workflow runs
- If a workflow run is missed, posts are still captured in the next run
- Even if the cache is lost, only posts within the lookback window might be
  duplicated

For advanced cache management options (including how to clear the cache), see
[Managing GitHub Actions Cache](docs/managing-cache.md).

## Development

### Version Information

BlueMastodon follows [Semantic Versioning](https://semver.org/) and is currently
at version 0.9.7 (beta). For more information about our versioning system
and release process, see [Versioning Guidelines](docs/versioning.md).

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/kelp/bluemastodon.git
cd bluemastodon

# Run the setup script (installs dependencies and pre-commit hooks)
./scripts/setup-dev.sh

# Or manually:
# Install dependencies
poetry install

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type pre-push
```

#### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks run:

- Code formatting (Black, isort)
- Linting (Flake8, pylint)
- Type checking (Mypy)
- Security analysis (Bandit)
- Tests with minimum coverage requirements (pytest)

Pre-commit hooks run automatically on commit. Pre-push hooks run more
comprehensive checks before pushing to the remote repository.

### Testing

Run tests with coverage:

```bash
# Run all tests
make test

# Run with coverage report
make test-cov
```

### Linting and Formatting

```bash
# Format code
make format

# Run linting
make lint

# Run type checking
make type-check
```

### Building and Publishing

```bash
# Build package
make build

# Create a release
make release

# Publish to PyPI (requires credentials)
make publish
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify your credentials in the `.env` file
   - Ensure your Mastodon token has the correct permissions

2. **No Posts Being Synced**:
   - Check the `LOOKBACK_HOURS` setting
   - Verify that you have recent posts on Bluesky
   - Run with `--debug` for detailed logging

3. **Media Not Transferring**:
   - Ensure `INCLUDE_MEDIA=true` in your configuration
   - Some media types might not be supported by both platforms

4. **GitHub Actions Not Running**:
   - Check if the workflow is enabled
   - Verify all required secrets are set
   - Check the workflow logs for errors

5. **Security Concerns**:
   - Never commit `.env` files with real credentials to your repository
   - Always use GitHub Secrets for sensitive information
   - Regularly rotate your API tokens for better security
   - If you suspect your tokens were compromised, regenerate them immediately

6. **Cache Issues**:
   - If you experience duplicate posts, the GitHub Actions cache may have been
     lost
   - Cache can expire after 7 days of non-use or during GitHub maintenance
   - To debug cache issues, check workflow logs for "Cache restored from key:
     sync-state"
   - For instructions on how to view, clear, or reset the cache, see
     [Managing GitHub Actions Cache](docs/managing-cache.md)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## Acknowledgements

- [atproto](https://atproto.blue/en/latest/) for Bluesky API access
- [Mastodon.py](https://mastodonpy.readthedocs.io/) for Mastodon API access
