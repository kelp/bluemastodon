# Managing GitHub Actions Cache

Social-Sync uses GitHub's cache to store state between workflow runs. This state
file (`sync_state.json`) contains records of which posts have already been
synced to prevent duplicate posts.

## Clearing the Cache

There may be times when you need to clear the cache, such as:

- If you've deleted a post on Mastodon and want to re-sync it
- When testing the workflow functionality
- If the sync state becomes corrupted
- When troubleshooting sync issues

### Method 1: Using GitHub CLI Extension

The simplest way to manage the cache is with the GitHub CLI `actions-cache`
extension:

1. Install the extension (if not already installed):
   ```bash
   gh extension install actions/gh-actions-cache
   ```

2. List all caches to identify the sync-state cache:
   ```bash
   gh actions-cache list -R username/social-sync
   ```

3. Delete the sync-state cache:
   ```bash
   gh actions-cache delete sync-state -R username/social-sync --confirm
   ```

4. Run the workflow again to create a fresh state:
   ```bash
   gh workflow run "Sync Social Media Posts" -R username/social-sync
   ```

### Method 2: Using GitHub REST API

If you prefer using the API directly:

1. List caches:
   ```bash
   curl -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token YOUR_GITHUB_TOKEN" \
        https://api.github.com/repos/username/social-sync/actions/caches
   ```

2. Delete cache by key:
   ```bash
   curl -X DELETE \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Authorization: token YOUR_GITHUB_TOKEN" \
        https://api.github.com/repos/username/social-sync/actions/caches?key=sync-state
   ```

## How the Cache Works

- The cache stores a JSON file with IDs of previously synced posts
- It is persisted between workflow runs using GitHub's caching system
- The workflow checks this file to determine which posts to skip
- If a cache is lost/cleared, all posts within the lookback window may be re-synced

## Troubleshooting

If you experience duplicate posts or missing syncs:

1. Enable debug mode on your next workflow run:
   ```bash
   gh workflow run "Sync Social Media Posts" -R username/social-sync --field debug=true
   ```

2. Check the workflow run logs for cache-related messages:
   - "Restored cache from key: sync-state" indicates the cache was found
   - "Cache not found for key: sync-state" indicates a fresh start
   - Look for the content of the sync state file to verify what IDs are tracked

3. Clear the cache and run with dry-run mode to safely test:
   ```bash
   gh actions-cache delete sync-state -R username/social-sync --confirm
   gh workflow run "Sync Social Media Posts" -R username/social-sync --field dry_run=true
   ```
