"""Tests for the mastodon module."""

from unittest.mock import MagicMock, patch

import pytest

from social_sync.config import MastodonConfig
from social_sync.mastodon import MastodonClient
from social_sync.models import (BlueskyPost, Link, MastodonPost,
                                MediaAttachment, MediaType)


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

    @patch("social_sync.mastodon.MastodonAPI")
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

    @patch("social_sync.mastodon.MastodonAPI")
    def test_verify_credentials_failure(self, mock_mastodon_api):
        """Test credential verification failure."""
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

    def test_ensure_authenticated_already_authed(self):
        """Test ensure_authenticated when already authenticated."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._authenticated = True

        with patch.object(client, "verify_credentials") as mock_verify:
            result = client.ensure_authenticated()

            assert result is True
            mock_verify.assert_not_called()

    def test_ensure_authenticated_not_authed(self):
        """Test ensure_authenticated when not authenticated."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client._authenticated = False

        with patch.object(client, "verify_credentials") as mock_verify:
            mock_verify.return_value = True
            result = client.ensure_authenticated()

            assert result is True
            mock_verify.assert_called_once()

    def test_format_post_content_basic(self):
        """Test _format_post_content with basic content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a simple post
        post = BlueskyPost(
            id="test123",
            uri="at://test/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post",
            created_at=MagicMock(),
            author_id="did:plc:test",
            author_handle="test.bsky.social",
            links=[],
        )

        # Call the method
        result = client._format_post_content(post)

        # Expected format: just the content (no attribution footer)
        expected = "This is a test post"
        assert result == expected

    def test_format_post_content_with_links(self):
        """Test _format_post_content with external links."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a post with links
        post = BlueskyPost(
            id="test123",
            uri="at://test/app.bsky.feed.post/test123",
            cid="cid123",
            content="Check out this link",
            created_at=MagicMock(),
            author_id="did:plc:test",
            author_handle="test.bsky.social",
            links=[
                Link(url="https://example.com", title="Example Website"),
                Link(url="https://already-in.com"),
            ],
        )

        # Simulate link already in content
        post.content = "Check out this link https://already-in.com"

        # Call the method
        result = client._format_post_content(post)

        # Should add only the missing link (no attribution footer)
        expected = "Check out this link https://already-in.com\n\nhttps://example.com"
        assert result == expected

    def test_format_post_content_character_limit(self):
        """Test _format_post_content with content exceeding character limit."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a post with very long content
        long_content = "A" * 600  # Well over the 500 character limit
        post = BlueskyPost(
            id="test123",
            uri="at://test/app.bsky.feed.post/test123",
            cid="cid123",
            content=long_content,
            created_at=MagicMock(),
            author_id="did:plc:test",
            author_handle="test.bsky.social",
            links=[],
        )

        # Call the method
        result = client._format_post_content(post)

        # Should truncate to 497 characters + ellipsis
        expected = "A" * 497 + "..."
        assert result == expected
        assert len(result) == 500  # Exactly at the limit

    @patch("social_sync.mastodon.urlretrieve")
    @patch("social_sync.mastodon.tempfile.NamedTemporaryFile")
    @patch("social_sync.mastodon.os.unlink")
    def test_upload_media_success(self, mock_unlink, mock_temp_file, mock_urlretrieve):
        """Test _upload_media success case."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Mock the client and temp file
        client.client = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_file"
        mock_temp_file.return_value.__enter__.return_value = mock_temp

        # Mock the media_post response
        mock_media = MagicMock()
        mock_media.id = "media123"
        client.client.media_post.return_value = mock_media

        # Create test attachments
        attachments = [
            MediaAttachment(
                url="https://example.com/image1.jpg",
                alt_text="Image 1",
                mime_type="image/jpeg",
                media_type=MediaType.IMAGE,
            ),
            MediaAttachment(
                url="https://example.com/image2.jpg",
                alt_text=None,
                mime_type="image/jpeg",
                media_type=MediaType.IMAGE,
            ),
        ]

        # Call the method
        result = client._upload_media(attachments)

        # Check results
        assert result == ["media123", "media123"]

        # Verify mock calls
        assert mock_urlretrieve.call_count == 2
        mock_urlretrieve.assert_any_call(
            "https://example.com/image1.jpg", "/tmp/test_file"
        )
        mock_urlretrieve.assert_any_call(
            "https://example.com/image2.jpg", "/tmp/test_file"
        )

        assert client.client.media_post.call_count == 2
        client.client.media_post.assert_any_call(
            "/tmp/test_file", mime_type="image/jpeg", description="Image 1"
        )
        client.client.media_post.assert_any_call(
            "/tmp/test_file", mime_type="image/jpeg", description=""
        )

        assert mock_unlink.call_count == 2
        mock_unlink.assert_called_with("/tmp/test_file")

    @patch("social_sync.mastodon.urlretrieve")
    @patch("social_sync.mastodon.tempfile.NamedTemporaryFile")
    @patch("social_sync.mastodon.os.unlink")
    def test_upload_media_error(self, mock_unlink, mock_temp_file, mock_urlretrieve):
        """Test _upload_media with error."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Mock the client and temp file
        client.client = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_file"
        mock_temp_file.return_value.__enter__.return_value = mock_temp

        # Mock media_post to raise an exception
        client.client.media_post.side_effect = Exception("Upload failed")

        # Create test attachment
        attachments = [
            MediaAttachment(
                url="https://example.com/image.jpg",
                alt_text="Image",
                mime_type="image/jpeg",
                media_type=MediaType.IMAGE,
            )
        ]

        # Call the method
        result = client._upload_media(attachments)

        # Check result is empty list (error handled)
        assert result == []

        # Verify mock calls
        mock_urlretrieve.assert_called_once_with(
            "https://example.com/image.jpg", "/tmp/test_file"
        )
        client.client.media_post.assert_called_once_with(
            "/tmp/test_file", mime_type="image/jpeg", description="Image"
        )
        # We don't assert unlink because in the error case it's not called (exception happens during upload)

    def test_determine_media_type(self):
        """Test _determine_media_type method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Test all known types
        assert client._determine_media_type("image") == "image"
        assert client._determine_media_type("video") == "video"
        assert client._determine_media_type("gifv") == "video"
        assert client._determine_media_type("audio") == "audio"
        assert client._determine_media_type("unknown") == "other"

        # Test unknown type
        assert client._determine_media_type("something_else") == "other"

    def test_convert_to_mastodon_post(self):
        """Test _convert_to_mastodon_post method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a mock toot response
        toot = MagicMock()
        toot.id = 12345
        toot.content = "Test post content"
        toot.created_at = "2023-01-01T12:00:00Z"
        toot.url = "https://mastodon.test/@user/12345"
        toot.visibility = "public"

        # Mock account
        toot.account.id = 67890
        toot.account.acct = "user@mastodon.test"
        toot.account.display_name = "User Name"

        # Mock application
        toot.application.name = "TestApp"

        # Mock media_attachments
        media = MagicMock()
        media.url = "https://mastodon.test/media/image.jpg"
        media.description = "Test image"
        media.type = "image"
        media.mime_type = "image/jpeg"
        toot.media_attachments = [media]

        # Additional properties
        toot.sensitive = True
        toot.spoiler_text = "Content warning"
        toot.favourites_count = 5
        toot.reblogs_count = 2

        # Mock determine_media_type
        with patch.object(
            client, "_determine_media_type", return_value=MediaType.IMAGE
        ):
            # Call the method
            result = client._convert_to_mastodon_post(toot)

            # Check the result
            assert isinstance(result, MastodonPost)
            assert result.id == "12345"
            assert result.content == "Test post content"
            assert result.created_at.isoformat() == "2023-01-01T12:00:00+00:00"
            assert result.url == "https://mastodon.test/@user/12345"
            assert result.author_id == "67890"
            assert result.author_handle == "user@mastodon.test"
            assert result.author_display_name == "User Name"
            assert result.application == "TestApp"
            assert result.sensitive is True
            assert result.spoiler_text == "Content warning"
            assert result.visibility == "public"
            assert result.favourites_count == 5
            assert result.reblogs_count == 2
            assert result.platform == "mastodon"

            # Check media attachment
            assert len(result.media_attachments) == 1
            assert (
                result.media_attachments[0].url
                == "https://mastodon.test/media/image.jpg"
            )
            assert result.media_attachments[0].alt_text == "Test image"
            assert result.media_attachments[0].media_type == MediaType.IMAGE
            assert result.media_attachments[0].mime_type == "image/jpeg"

    def test_is_duplicate_post(self):
        """Test the _is_duplicate_post method for detecting duplicate content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Mock Mastodon client
        client.client = MagicMock()
        client._account = MagicMock()
        client._account.id = "user123"

        # Mock recent posts
        post1 = MagicMock()
        post1.content = "<p>This is a unique post about cats</p>"

        post2 = MagicMock()
        post2.content = "<p>This is an exact match for testing</p>"

        post3 = MagicMock()
        post3.content = "<p>This post has lots of similar words to our test content with some matching terms</p>"

        client.client.account_statuses.return_value = [post1, post2, post3]

        # Test exact match
        is_duplicate, matched_post = client._is_duplicate_post(
            "This is an exact match for testing"
        )
        assert is_duplicate is True
        assert matched_post == post2

        # Test similar content (above threshold)
        test_content = "This post has lots of similar words to our test content with matching terms"
        is_duplicate, matched_post = client._is_duplicate_post(test_content)
        assert is_duplicate is True
        assert matched_post == post3

        # Test non-duplicate content
        is_duplicate, matched_post = client._is_duplicate_post(
            "This is completely different content"
        )
        assert is_duplicate is False
        assert matched_post is None

    def test_is_duplicate_post_error_handling(self):
        """Test error handling in the _is_duplicate_post method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Mock client to raise exception
        client.client = MagicMock()
        client.client.account_statuses.side_effect = Exception("API error")

        # Function should return False (fail open) on error
        is_duplicate, matched_post = client._is_duplicate_post("Test content")
        assert is_duplicate is False
        assert matched_post is None

    @patch("social_sync.mastodon.MastodonClient.ensure_authenticated")
    @patch("social_sync.mastodon.MastodonClient._format_post_content")
    @patch("social_sync.mastodon.MastodonClient._is_duplicate_post")
    @patch("social_sync.mastodon.MastodonClient._upload_media")
    @patch("social_sync.mastodon.MastodonClient._convert_to_mastodon_post")
    def test_cross_post_success(
        self,
        mock_convert,
        mock_upload_media,
        mock_is_duplicate,
        mock_format_content,
        mock_auth,
    ):
        """Test cross_post success case."""
        # Setup configuration and client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Setup mocks
        mock_auth.return_value = True
        mock_format_content.return_value = "Formatted content"
        mock_is_duplicate.return_value = (False, None)  # Not a duplicate
        mock_upload_media.return_value = ["media1", "media2"]

        mock_toot = MagicMock()
        client.client.status_post.return_value = mock_toot

        mock_mastodon_post = MagicMock()
        mock_convert.return_value = mock_mastodon_post

        # Create test Bluesky post
        bluesky_post = MagicMock()
        bluesky_post.media_attachments = ["attachment1", "attachment2"]
        bluesky_post.id = "test123"

        # Call the method
        result = client.cross_post(bluesky_post)

        # Check the result
        assert result == mock_mastodon_post

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_format_content.assert_called_once_with(bluesky_post)
        mock_is_duplicate.assert_called_once_with("Formatted content")
        mock_upload_media.assert_called_once_with(bluesky_post.media_attachments)
        client.client.status_post.assert_called_once_with(
            status="Formatted content",
            media_ids=["media1", "media2"],
            visibility="public",
            sensitive=False,
        )
        mock_convert.assert_called_once_with(mock_toot)

    @patch("social_sync.mastodon.MastodonClient.ensure_authenticated")
    def test_cross_post_not_authenticated(self, mock_auth):
        """Test cross_post when not authenticated."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Setup mock to return False for authentication
        mock_auth.return_value = False

        # Call the method and check exception
        with pytest.raises(ValueError, match="Not authenticated with Mastodon"):
            client.cross_post(MagicMock())

        # Verify mock call
        mock_auth.assert_called_once()

    @patch("social_sync.mastodon.MastodonClient.ensure_authenticated")
    @patch("social_sync.mastodon.MastodonClient._format_post_content")
    @patch("social_sync.mastodon.MastodonClient._is_duplicate_post")
    @patch("social_sync.mastodon.MastodonClient._convert_to_mastodon_post")
    def test_cross_post_duplicate_with_existing_post(
        self, mock_convert, mock_is_duplicate, mock_format_content, mock_auth
    ):
        """Test cross_post when a duplicate post is detected with the existing post available."""
        # Setup configuration and client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Setup mocks
        mock_auth.return_value = True
        mock_format_content.return_value = "Formatted content"

        # Create a mock existing post and return it with is_duplicate=True
        mock_existing_post = MagicMock()
        mock_is_duplicate.return_value = (True, mock_existing_post)

        mock_mastodon_post = MagicMock()
        mock_convert.return_value = mock_mastodon_post

        # Create test Bluesky post
        bluesky_post = MagicMock()
        bluesky_post.id = "test123"

        # Call the method
        result = client.cross_post(bluesky_post)

        # Check the result is the converted existing post
        assert result == mock_mastodon_post

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_format_content.assert_called_once_with(bluesky_post)
        mock_is_duplicate.assert_called_once_with("Formatted content")
        mock_convert.assert_called_once_with(mock_existing_post)

        # Ensure posting was not attempted
        assert not client.client.status_post.called

    @patch("social_sync.mastodon.MastodonClient.ensure_authenticated")
    @patch("social_sync.mastodon.MastodonClient._format_post_content")
    @patch("social_sync.mastodon.MastodonClient._is_duplicate_post")
    def test_cross_post_duplicate_without_existing_post(
        self, mock_is_duplicate, mock_format_content, mock_auth
    ):
        """Test cross_post when a duplicate post is detected but the existing post is not available."""
        # Setup configuration and client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Setup mocks
        mock_auth.return_value = True
        mock_format_content.return_value = "Formatted content"

        # Return is_duplicate=True but no existing post
        mock_is_duplicate.return_value = (True, None)

        # Create test Bluesky post
        bluesky_post = MagicMock()
        bluesky_post.id = "test123"

        # Call the method
        result = client.cross_post(bluesky_post)

        # Check the result is None (since we can't return the existing post)
        assert result is None

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_format_content.assert_called_once_with(bluesky_post)
        mock_is_duplicate.assert_called_once_with("Formatted content")

        # Ensure posting was not attempted
        assert not client.client.status_post.called

    @patch("social_sync.mastodon.MastodonClient.ensure_authenticated")
    @patch("social_sync.mastodon.MastodonClient._format_post_content")
    @patch("social_sync.mastodon.MastodonClient._is_duplicate_post")
    @patch("social_sync.mastodon.MastodonClient._upload_media")
    def test_cross_post_error(
        self, mock_upload_media, mock_is_duplicate, mock_format_content, mock_auth
    ):
        """Test cross_post when posting fails."""
        # Setup configuration and client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        client.client = MagicMock()

        # Setup mocks
        mock_auth.return_value = True
        mock_format_content.return_value = "Formatted content"
        mock_is_duplicate.return_value = (False, None)  # Not a duplicate
        mock_upload_media.return_value = ["media1", "media2"]

        # Mock status_post to raise an exception
        client.client.status_post.side_effect = Exception("Posting failed")

        # Create test Bluesky post
        bluesky_post = MagicMock()
        bluesky_post.media_attachments = ["attachment1", "attachment2"]

        # Call the method
        result = client.cross_post(bluesky_post)

        # Check the result is None
        assert result is None

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_is_duplicate.assert_called_once_with("Formatted content")
        mock_format_content.assert_called_once_with(bluesky_post)
        mock_upload_media.assert_called_once_with(bluesky_post.media_attachments)
        client.client.status_post.assert_called_once_with(
            status="Formatted content",
            media_ids=["media1", "media2"],
            visibility="public",
            sensitive=False,
        )
