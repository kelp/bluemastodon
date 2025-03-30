"""Tests for the config module."""

import os
from unittest.mock import patch

import pytest

from social_sync.config import BlueskyConfig, Config, MastodonConfig, load_config


class TestConfig:
    """Test the config module."""

    def test_config_dataclass(self):
        """Test that Config dataclass works correctly."""
        # Create config with minimal required fields
        bluesky = BlueskyConfig(username="user", password="pass")
        mastodon = MastodonConfig(
            instance_url="https://example.com", access_token="token"
        )
        config = Config(bluesky=bluesky, mastodon=mastodon)

        # Check default values
        assert config.lookback_hours == 24
        assert config.sync_interval_minutes == 60
        assert config.max_posts_per_run == 5
        assert config.include_media is True
        assert config.include_links is True

        # Check passed values
        assert config.bluesky.username == "user"
        assert config.bluesky.password == "pass"
        assert config.mastodon.instance_url == "https://example.com"
        assert config.mastodon.access_token == "token"

        # Create config with all fields
        config = Config(
            bluesky=bluesky,
            mastodon=mastodon,
            lookback_hours=12,
            sync_interval_minutes=30,
            max_posts_per_run=10,
            include_media=False,
            include_links=False,
        )

        # Check custom values
        assert config.lookback_hours == 12
        assert config.sync_interval_minutes == 30
        assert config.max_posts_per_run == 10
        assert config.include_media is False
        assert config.include_links is False

    def test_load_config_from_env_file(self, sample_env_file):
        """Test loading config from an environment file."""
        config = load_config(sample_env_file)

        # Check that config was loaded correctly
        assert config.bluesky.username == "test_user"
        assert config.bluesky.password == "test_password"
        assert config.mastodon.instance_url == "https://mastodon.test"
        assert config.mastodon.access_token == "test_token"
        assert config.lookback_hours == 12
        assert config.sync_interval_minutes == 30
        assert config.max_posts_per_run == 10
        assert config.include_media is True
        assert config.include_links is True

    @patch.dict(
        os.environ,
        {
            "BLUESKY_USERNAME": "env_user",
            "BLUESKY_PASSWORD": "env_pass",
            "MASTODON_INSTANCE_URL": "https://env.test",
            "MASTODON_ACCESS_TOKEN": "env_token",
            "LOOKBACK_HOURS": "6",
            "SYNC_INTERVAL_MINUTES": "15",
            "MAX_POSTS_PER_RUN": "3",
            "INCLUDE_MEDIA": "false",
            "INCLUDE_LINKS": "false",
        },
    )
    def test_load_config_from_env_vars(self):
        """Test loading config from environment variables."""
        config = load_config()

        # Check that config was loaded correctly from env vars
        assert config.bluesky.username == "env_user"
        assert config.bluesky.password == "env_pass"
        assert config.mastodon.instance_url == "https://env.test"
        assert config.mastodon.access_token == "env_token"
        assert config.lookback_hours == 6
        assert config.sync_interval_minutes == 15
        assert config.max_posts_per_run == 3
        assert config.include_media is False
        assert config.include_links is False

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_missing_required_vars(self):
        """Test that load_config raises ValueError when required vars are missing."""
        with pytest.raises(ValueError) as excinfo:
            load_config()

        # Check that error message lists all missing variables
        error_message = str(excinfo.value)
        assert "Missing required environment variables" in error_message
        assert "BLUESKY_USERNAME" in error_message
        assert "BLUESKY_PASSWORD" in error_message
        assert "MASTODON_INSTANCE_URL" in error_message
        assert "MASTODON_ACCESS_TOKEN" in error_message

    @patch.dict(
        os.environ,
        {
            "BLUESKY_USERNAME": "env_user",
            "BLUESKY_PASSWORD": "env_pass",
            "MASTODON_INSTANCE_URL": "https://env.test",
            "MASTODON_ACCESS_TOKEN": "env_token",
            "LOOKBACK_HOURS": "not_a_number",  # Invalid value
        },
        clear=True,
    )
    def test_load_config_invalid_number_values(self):
        """Test handling of invalid numeric environment variables."""
        with pytest.raises(ValueError):
            load_config()

    @patch.dict(
        os.environ,
        {
            "BLUESKY_USERNAME": "env_user",
            "BLUESKY_PASSWORD": "env_pass",
            "MASTODON_INSTANCE_URL": "https://env.test",
            "MASTODON_ACCESS_TOKEN": "env_token",
            "INCLUDE_MEDIA": "not_a_boolean",  # Invalid value
        },
        clear=True,
    )
    def test_load_config_invalid_boolean_values(self):
        """Test handling of non-boolean values for boolean settings."""
        # Should not be true for most invalid boolean values
        config = load_config()
        assert config.include_media is False
