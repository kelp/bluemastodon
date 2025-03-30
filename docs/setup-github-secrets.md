# Setting Up GitHub Repository Secrets for Social-Sync

To enable the Social-Sync application to access your Bluesky and Mastodon
accounts when running in GitHub Actions, you need to set up repository
secrets. This guide explains how to create these secrets.

## Required Secrets

You need to set up four repository secrets:

1. `BLUESKY_USERNAME`: Your Bluesky handle (example: `username.bsky.social`)
2. `BLUESKY_PASSWORD`: Your Bluesky app password (not your account password)
3. `MASTODON_INSTANCE_URL`: Your Mastodon instance URL (example:
   `https://mastodon.social`)
4. `MASTODON_ACCESS_TOKEN`: Your Mastodon access token

## Step-by-Step Instructions

### Setting Up Repository Secrets

1. Go to your GitHub repository
2. Click on "Settings" in the top navigation bar
3. In the left sidebar, click on "Secrets and variables" then "Actions"
4. Click on "New repository secret" to add each secret
5. Add each of the required secrets mentioned above

### Obtaining Bluesky Credentials

1. **Bluesky Username**: Use your full handle including `.bsky.social`
   (e.g., `username.bsky.social`)

2. **Bluesky App Password**:
   - Log in to your Bluesky account in a web browser
   - Go to Settings → App Passwords
   - Click "Add app password"
   - Give it a name like "Social-Sync"
   - Copy the generated password and store it securely
   - Use this as your `BLUESKY_PASSWORD` secret

### Obtaining Mastodon Credentials

1. **Mastodon Instance URL**: This is the base URL of your Mastodon instance
   (e.g., `https://mastodon.social`)

2. **Mastodon Access Token**:
   - Log in to your Mastodon account in a web browser
   - Go to Preferences → Development → New Application
   - Give it a name like "Social-Sync"
   - Set the required permissions (scopes):
     - `read:accounts`
     - `read:statuses`
     - `write:media`
     - `write:statuses`
   - Submit the form
   - On the next page, copy the "Access token" field
   - Use this as your `MASTODON_ACCESS_TOKEN` secret

## Optional Environment Variables

Besides secrets, you can configure additional settings through repository
variables:

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Click on the "Variables" tab
3. Click "New repository variable" to add each variable

Available variables:

- `LOOKBACK_HOURS`: Number of hours to look back for posts (default: 6)
- `SYNC_INTERVAL_MINUTES`: Minutes between sync runs (default: 60)
- `MAX_POSTS_PER_RUN`: Maximum posts to sync per run (default: 5)
- `INCLUDE_MEDIA`: Whether to include media files (default: "true")
- `INCLUDE_LINKS`: Whether to include links (default: "true")

## Testing the Workflow

After setting up all secrets and variables:

1. Go to the "Actions" tab in your repository
2. Select the "Sync Social Media Posts" workflow
3. Click "Run workflow"
4. Select "Run workflow" from the dropdown

You can enable debug mode or dry run mode when manually triggering the
workflow.

## Troubleshooting

If you encounter issues:

1. Check the workflow logs for detailed error messages
2. Verify that all secrets and variables are correctly set
3. Confirm that your Bluesky and Mastodon credentials have the necessary
   permissions
4. Check that your accounts are active and not rate-limited

For more help, refer to the [README.md](../README.md) or open an issue on
GitHub.
