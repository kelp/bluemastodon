# Social-Sync

A Python application to automatically cross-post manual Bluesky posts to Mastodon.

## Overview

Social-Sync monitors your Bluesky account for new posts and automatically cross-posts them to your Mastodon account. It's designed to be run as a scheduled job via GitHub Actions or any other scheduler.

## Features

- Fetches recent Bluesky posts
- Cross-posts to Mastodon
- Maintains post formatting
- Supports media attachments
- Handles external links
- Keeps track of synced posts to avoid duplicates
- Extensive error handling and logging

## Setup

### Prerequisites

- Python 3.9 - 3.12
- A Bluesky account
- A Mastodon account with API access

### Installation

1. Clone the repository:

```bash
git clone https://github.com/kelp/social-sync.git
cd social-sync
```

2. Install with Poetry:

```bash
poetry install
```

3. Create a `.env` file with your credentials:

```
BLUESKY_USERNAME=your_bluesky_username
BLUESKY_PASSWORD=your_bluesky_password
MASTODON_INSTANCE_URL=https://your.mastodon.instance
MASTODON_ACCESS_TOKEN=your_mastodon_access_token
LOOKBACK_HOURS=24
SYNC_INTERVAL_MINUTES=60
MAX_POSTS_PER_RUN=5
INCLUDE_MEDIA=true
INCLUDE_LINKS=true
```

## Usage

### Command Line

Run the sync manually:

```bash
poetry run python -m social_sync
```

Options:

- `-c, --config`: Path to custom config file (.env format)
- `-s, --state`: Path to custom state file (JSON format)
- `-d, --debug`: Enable debug logging
- `--dry-run`: Simulate syncing without posting

### Scheduled Sync with GitHub Actions

1. Add your configuration as GitHub repository secrets
2. Set up a workflow file in `.github/workflows/sync.yml`:

```yaml
name: Social Sync

on:
  schedule:
    - cron: '0 * * * *'  # Hourly
  workflow_dispatch:     # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install Poetry
        uses: snok/install-poetry@v1
      - name: Install dependencies
        run: poetry install
      - name: Run sync
        env:
          BLUESKY_USERNAME: ${{ secrets.BLUESKY_USERNAME }}
          BLUESKY_PASSWORD: ${{ secrets.BLUESKY_PASSWORD }}
          MASTODON_INSTANCE_URL: ${{ secrets.MASTODON_INSTANCE_URL }}
          MASTODON_ACCESS_TOKEN: ${{ secrets.MASTODON_ACCESS_TOKEN }}
        run: poetry run python -m social_sync
```

## Development

### Testing

Run tests with coverage:

```bash
poetry run pytest
```

### Linting and Formatting

```bash
poetry run black .
poetry run isort .
poetry run flake8
poetry run mypy .
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.