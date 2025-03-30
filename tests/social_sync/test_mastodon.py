"""Tests for the mastodon module."""

import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from social_sync.config import MastodonConfig
from social_sync.mastodon import MastodonClient
from social_sync.models import (
    BlueskyPost,
    Link,
    MastodonPost,
    MediaAttachment,
    MediaType,
)


class TestMastodonClient:
    """Test the MastodonClient class."""

    def test_init(self):
        """Test initialization of MastodonClient."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        assert client.config == config
        assert client._authenticated is False
        assert client._account is None
        assert client.client is not None

    @patch("social_sync.mastodon.Mastodon")
    def test_verify_credentials_success(self, mock_mastodon_api):
        """Test successful credential verification."""
        # Setup mock
        mock_client = MagicMock()
        mock_account = MagicMock()
        mock_account.username = "test_user"
        mock_client.account_verify_credentials.return_value = mock_account
        mock_mastodon_api.return_value = mock_client

        # Create client and verify credentials
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        result = client.verify_credentials()

        # Check results
        assert result is True
        assert client._authenticated is True
        assert client._account == mock_account
        mock_client.account_verify_credentials.assert_called_once()

    @patch("social_sync.mastodon.Mastodon")
    def test_verify_credentials_failure(self, mock_mastodon_api):
        """Test failed credential verification."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.account_verify_credentials.side_effect = Exception("Auth failed")
        mock_mastodon_api.return_value = mock_client

        # Create client and verify credentials
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        result = client.verify_credentials()

        # Check results
        assert result is False
        assert client._authenticated is False
        assert client._account is None
        mock_client.account_verify_credentials.assert_called_once()

    def test_ensure_authenticated_already_authenticated(self):
        """Test ensure_authenticated when already authenticated."""
        # Create client and set as already authenticated
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._authenticated = True

        # Call ensure_authenticated
        with patch.object(client, "verify_credentials") as mock_verify:
            result = client.ensure_authenticated()

        # Check results
        assert result is True
        mock_verify.assert_not_called()

    def test_ensure_authenticated_not_authenticated(self):
        """Test ensure_authenticated when not authenticated."""
        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._authenticated = False

        # Call ensure_authenticated
        with patch.object(client, "verify_credentials") as mock_verify:
            mock_verify.return_value = True
            result = client.ensure_authenticated()

        # Check results
        assert result is True
        mock_verify.assert_called_once()

    def test_apply_character_limits_short_content(self):
        """Test applying character limits to short content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        content = "This is a short post under the limit."
        result = client._apply_character_limits(content)

        assert result == content

    def test_apply_character_limits_long_content(self):
        """Test applying character limits to long content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a post that's longer than the 500 character limit
        content = "x" * 600
        result = client._apply_character_limits(content)

        assert len(result) <= 500
        assert result.endswith("...")

    def test_apply_character_limits_word_boundary(self):
        """Test that character limits respect word boundaries."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a post that exceeds the 500 character limit
        words = ["word"] * 150  # This will be over 500 characters
        content = " ".join(words)
        result = client._apply_character_limits(content)

        assert len(result) <= 500
        assert result.endswith("...")

        # The last part before "..." should be a complete word
        before_ellipsis = result[:-3]
        assert " " in before_ellipsis
        assert not before_ellipsis.endswith(" ")

    @patch("social_sync.mastodon.re")
    def test_is_duplicate_post_no_account(self, mock_re):
        """Test _is_duplicate_post when no account is available."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._account = None

        is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None
        mock_re.sub.assert_not_called()

    def test_is_duplicate_post_high_similarity(self):
        """Test _is_duplicate_post with high similarity content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._account = MagicMock()
        client._account.id = "12345"

        # Setup mock posts
        mock_post = MagicMock()
        mock_post.content = "<p>This is a test post about Python programming</p>"
        client.client = MagicMock()
        client.client.account_statuses.return_value = [mock_post]

        # Test with similar content
        is_duplicate, post = client._is_duplicate_post(
            "This is a test post about Python programming."
        )

        assert is_duplicate is True
        assert post == mock_post

    def test_is_duplicate_post_low_similarity(self):
        """Test _is_duplicate_post with low similarity content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._account = MagicMock()
        client._account.id = "12345"

        # Setup mock posts
        mock_post = MagicMock()
        mock_post.content = "<p>This is a post about Python programming</p>"
        client.client = MagicMock()
        client.client.account_statuses.return_value = [mock_post]

        # Test with different content
        is_duplicate, post = client._is_duplicate_post(
            "This is a completely different topic about JavaScript."
        )

        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_error(self):
        """Test _is_duplicate_post handling errors."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._account = MagicMock()
        client._account.id = "12345"

        # Setup mock to raise exception
        client.client = MagicMock()
        client.client.account_statuses.side_effect = Exception("API error")

        # Should fail open (not duplicate)
        is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None

    def test_determine_media_type(self):
        """Test _determine_media_type conversion."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        assert client._determine_media_type("image") == "image"
        assert client._determine_media_type("video") == "video"
        assert client._determine_media_type("gifv") == "video"
        assert client._determine_media_type("audio") == "audio"
        assert client._determine_media_type("unknown") == "other"
        assert client._determine_media_type("something_else") == "other"

    def test_convert_to_media_type(self):
        """Test _convert_to_media_type conversion."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        assert client._convert_to_media_type("image") == MediaType.IMAGE
        assert client._convert_to_media_type("video") == MediaType.VIDEO
        assert client._convert_to_media_type("audio") == MediaType.AUDIO
        assert client._convert_to_media_type("gif") == MediaType.VIDEO
        assert client._convert_to_media_type("other") == MediaType.OTHER
        assert client._convert_to_media_type("something_else") == MediaType.OTHER

    def test_convert_to_mastodon_post(self):
        """Test converting Mastodon API response to our model."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create mock toot
        mock_toot = MagicMock()
        mock_toot.id = "12345"
        mock_toot.content = "<p>Test content</p>"
        mock_toot.created_at = "2023-06-15T12:34:56Z"
        mock_toot.account.id = "67890"
        mock_toot.account.acct = "test_user@mastodon.test"
        mock_toot.account.display_name = "Test User"
        mock_toot.url = "https://mastodon.test/@test_user/12345"
        mock_toot.application.name = "social-sync"
        mock_toot.sensitive = False
        mock_toot.spoiler_text = ""
        mock_toot.visibility = "public"
        mock_toot.favourites_count = 5
        mock_toot.reblogs_count = 2

        # Add mock media attachment
        mock_media = MagicMock()
        mock_media.url = "https://mastodon.test/media/image.jpg"
        mock_media.description = "Test image"
        mock_media.type = "image"
        mock_media.mime_type = "image/jpeg"
        mock_toot.media_attachments = [mock_media]

        # Convert to our model
        result = client._convert_to_mastodon_post(mock_toot)

        # Check result
        assert isinstance(result, MastodonPost)
        assert result.id == "12345"
        assert result.content == "<p>Test content</p>"
        assert result.author_id == "67890"
        assert result.author_handle == "test_user@mastodon.test"
        assert result.author_display_name == "Test User"
        assert result.url == "https://mastodon.test/@test_user/12345"
        assert result.application == "social-sync"
        assert result.sensitive is False
        assert result.spoiler_text == ""
        assert result.visibility == "public"
        assert result.favourites_count == 5
        assert result.reblogs_count == 2

        # Check media attachments
        assert len(result.media_attachments) == 1
        assert (
            result.media_attachments[0].url == "https://mastodon.test/media/image.jpg"
        )
        assert result.media_attachments[0].alt_text == "Test image"
        assert result.media_attachments[0].media_type == MediaType.IMAGE
        assert result.media_attachments[0].mime_type == "image/jpeg"

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_success(self, mock_auth, mock_convert, mock_is_duplicate):
        """Test post success case."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        mock_toot = MagicMock()
        mock_mastodon_post = MastodonPost(
            id="12345",
            content="Test content",
            created_at=datetime.now(),
            author_id="67890",
            author_handle="test_user@mastodon.test",
            author_display_name="Test User",
            url="https://mastodon.test/@test_user/12345",
            media_attachments=[],
        )
        mock_convert.return_value = mock_mastodon_post

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()
        client.client.status_post.return_value = mock_toot

        # Create test post
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            media_attachments=[],
            links=[],
        )

        # Post
        result = client.post(bluesky_post)

        # Assert
        assert result == mock_mastodon_post
        client.client.status_post.assert_called_once()
        mock_convert.assert_called_once_with(mock_toot)

    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_not_authenticated(self, mock_auth):
        """Test post when not authenticated."""
        # Setup
        mock_auth.return_value = False

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Post
        result = client.post(MagicMock())

        # Assert
        assert result is None

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_duplicate_with_existing_post(
        self, mock_auth, mock_convert, mock_is_duplicate
    ):
        """Test post when a duplicate post is detected with the existing post available."""
        # Setup
        mock_auth.return_value = True

        mock_existing_post = MagicMock()
        mock_mastodon_post = MastodonPost(
            id="12345",
            content="Test content",
            created_at=datetime.now(),
            author_id="67890",
            author_handle="test_user@mastodon.test",
            author_display_name="Test User",
            url="https://mastodon.test/@test_user/12345",
            media_attachments=[],
        )
        mock_is_duplicate.return_value = (True, mock_existing_post)
        mock_convert.return_value = mock_mastodon_post

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Create test post
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            media_attachments=[],
            links=[],
        )

        # Post
        result = client.post(bluesky_post)

        # Assert
        assert result == mock_mastodon_post
        client.client.status_post.assert_not_called()
        mock_convert.assert_called_once_with(mock_existing_post)

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_duplicate_without_existing_post(self, mock_auth, mock_is_duplicate):
        """Test post when a duplicate post is detected but the existing post is not available."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (True, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Create test post
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            media_attachments=[],
            links=[],
        )

        # Post
        result = client.post(bluesky_post)

        # Assert
        assert result is None
        client.client.status_post.assert_not_called()

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_error(self, mock_auth, mock_is_duplicate):
        """Test post when posting fails."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()
        client.client.status_post.side_effect = Exception("API error")

        # Create test post
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            media_attachments=[],
            links=[],
        )

        # Post
        result = client.post(bluesky_post)

        # Assert
        assert result is None
        client.client.status_post.assert_called_once()
