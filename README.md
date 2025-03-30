# Social-Sync

A Python application to automatically cross-post manual Bluesky posts to Mastodon.

![Test Status](https://github.com/kelp/social-sync/actions/workflows/test.yml/badge.svg)
![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
![License](https://img.shields.io/github/license/kelp/social-sync)

## Overview

Social-Sync monitors your Bluesky account for new posts and automatically cross-posts them to your Mastodon account. It's designed to be run as a scheduled job via GitHub Actions or any other scheduler.

This tool specifically handles synchronizing manual posts from Bluesky to Mastodon. Blog post publishing to social platforms can be managed by a separate tool.

## Features

- 🔄 **Automatic Synchronization**: Fetches recent Bluesky posts and cross-posts to Mastodon
- 🖼️ **Media Support**: Transfers images and attachments between platforms
- 🔗 **Link Handling**: Preserves external links in your posts
- 🧠 **Smart Synchronization**: Keeps track of synced posts to avoid duplicates
- 📝 **Format Preservation**: Maintains post formatting during cross-posting
- 🚨 **Error Handling**: Robust error handling and logging
- 🔒 **Secure**: Handles API credentials securely
- 🤖 **GitHub Action Ready**: Easily deployable as a GitHub Actions workflow

## Setup

### Prerequisites

- Python 3.9 or higher (tested on 3.9, 3.10, 3.11, 3.12)
- A Bluesky account
- A Mastodon account with API access

### Installation

#### Using pip

```bash
pip install social-sync
```

#### Using Poetry

1. Clone the repository:

```bash
git clone https://github.com/kelp/social-sync.git
cd social-sync
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
social-sync

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
social-sync --debug

# Dry run (no actual posts)
social-sync --dry-run

# Use custom config file
social-sync --config /path/to/custom.env

# Specify state file location
social-sync --state /path/to/state.json
```

### Scheduled Sync with GitHub Actions

1. Fork this repository or copy the workflow files to your own repository
2. Add your configuration as GitHub repository secrets:
   - `BLUESKY_USERNAME`
   - `BLUESKY_PASSWORD`
   - `MASTODON_INSTANCE_URL`
   - `MASTODON_ACCESS_TOKEN`
3. (Optional) Configure the following variables in your repository:
   - `LOOKBACK_HOURS`
   - `SYNC_INTERVAL_MINUTES`
   - `MAX_POSTS_PER_RUN`
   - `INCLUDE_MEDIA`
   - `INCLUDE_LINKS`
4. Enable the workflow in your GitHub repository
5. The sync will run automatically according to the schedule (hourly by default)
6. You can also trigger it manually from the Actions tab

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/kelp/social-sync.git
cd social-sync

# Install dependencies
poetry install

# Install pre-commit hooks
pre-commit install
```

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