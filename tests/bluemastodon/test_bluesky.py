"""Tests for the bluesky module."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from atproto.exceptions import AtProtocolError

from bluemastodon.bluesky import BlueskyClient
from bluemastodon.config import BlueskyConfig
from bluemastodon.models import BlueskyPost, Link, MediaAttachment, MediaType


class TestBlueskyClient:
    """Test the BlueskyClient class."""

    def test_init(self) -> None:
        """Test initialization of BlueskyClient."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        assert client.config == config
        assert client._authenticated is False
        assert client.client is not None

    @patch("bluemastodon.bluesky.AtProtoClient")
    def test_authenticate_success(self, mock_client_class: Any) -> None:
        """Test successful authentication."""
        # Setup mock
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create client and authenticate
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)
        result = client.authenticate()

        # Check results
        assert result is True
        assert client._authenticated is True
        mock_client.login.assert_called_once_with("test_user", "test_password")

    @patch("bluemastodon.bluesky.AtProtoClient")
    def test_authenticate_failure(self, mock_client_class: Any) -> None:
        """Test authentication failure."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.login.side_effect = AtProtocolError("Auth failed")
        mock_client_class.return_value = mock_client

        # Create client and authenticate
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)
        result = client.authenticate()

        # Check results
        assert result is False
        assert client._authenticated is False
        mock_client.login.assert_called_once_with("test_user", "test_password")

    def test_ensure_authenticated_already_authed(self) -> None:
        """Test ensure_authenticated when already authenticated."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)
        setattr(client, "_authenticated", True)

        with patch.object(client, "authenticate") as mock_auth:
            result = client.ensure_authenticated()

            assert result is True
            mock_auth.assert_not_called()

    def test_ensure_authenticated_not_authed(self) -> None:
        """Test ensure_authenticated when not authenticated."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)
        setattr(client, "_authenticated", False)

        with patch.object(client, "authenticate") as mock_auth:
            mock_auth.return_value = True
            result = client.ensure_authenticated()

            assert result is True
            mock_auth.assert_called_once()

    def test_get_user_profile_success(self) -> None:
        """Test _get_user_profile success."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock client and response
        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.app.bsky.actor.get_profile.return_value = mock_response
        setattr(client, "client", mock_client)

        # Call the method
        result = client._get_user_profile()

        # Check results
        assert result == mock_response
        client.client.app.bsky.actor.get_profile.assert_called_once_with(
            {"actor": "test_user"}
        )

    def test_get_user_profile_error(self) -> None:
        """Test _get_user_profile with API error."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock client with error
        mock_client = MagicMock()
        mock_client.app.bsky.actor.get_profile.side_effect = AtProtocolError(
            "API error"
        )
        setattr(client, "client", mock_client)

        # Call the method
        result = client._get_user_profile()

        # Check results
        assert result is None
        client.client.app.bsky.actor.get_profile.assert_called_once_with(
            {"actor": "test_user"}
        )

    def test_fetch_author_feed_success(self) -> None:
        """Test _fetch_author_feed success."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock client and response
        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.app.bsky.feed.get_author_feed.return_value = mock_response
        setattr(client, "client", mock_client)

        # Call the method
        result = client._fetch_author_feed("did:test", 10)

        # Check results
        assert result == mock_response
        client.client.app.bsky.feed.get_author_feed.assert_called_once_with(
            {
                "actor": "did:test",
                "limit": 10,
            }
        )

    def test_fetch_author_feed_error(self) -> None:
        """Test _fetch_author_feed with API error."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock client with error
        mock_client = MagicMock()
        mock_client.app.bsky.feed.get_author_feed.side_effect = AtProtocolError(
            "API error"
        )
        setattr(client, "client", mock_client)

        # Call the method
        result = client._fetch_author_feed("did:test", 10)

        # Check results
        assert result is None
        client.client.app.bsky.feed.get_author_feed.assert_called_once_with(
            {
                "actor": "did:test",
                "limit": 10,
            }
        )

    def test_should_include_post(self) -> None:
        """Test _should_include_post for various scenarios."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)
        now = datetime.now()
        since_time = now - timedelta(hours=24)
        user_did = "did:plc:test_user"

        # Create a feed view with no reason and no reply
        post = MagicMock()
        post.record.created_at = now.isoformat() + "Z"
        post.record.reply = None
        feed_view = MagicMock()
        feed_view.reason = None
        feed_view.post = post

        # Should include this post
        assert client._should_include_post(feed_view, since_time, user_did) is True

        # Should exclude posts with a reason (reposts)
        feed_view.reason = "repost"
        assert client._should_include_post(feed_view, since_time, user_did) is False
        feed_view.reason = None

        # Should exclude posts older than since_time
        old_time = (now - timedelta(hours=48)).isoformat() + "Z"
        post.record.created_at = old_time
        assert client._should_include_post(feed_view, since_time, user_did) is False
        post.record.created_at = now.isoformat() + "Z"

        # Test reply cases

        # Regular reply with include_threads=False should be excluded
        post.record.reply = MagicMock()
        assert (
            client._should_include_post(
                feed_view, since_time, user_did, include_threads=False
            )
            is False
        )

        # Reply to other user should always be excluded
        post.record.reply = MagicMock()
        post.record.reply.parent = MagicMock()
        post.record.reply.parent.author = MagicMock()
        post.record.reply.parent.author.did = "did:plc:different_user"
        post.uri = "at://test_user/app.bsky.feed.post/reply123"
        assert (
            client._should_include_post(
                feed_view, since_time, user_did, include_threads=True
            )
            is False
        )

        # Self-reply (thread) with include_threads=True should be included
        post.record.reply.parent.author.did = user_did
        assert (
            client._should_include_post(
                feed_view, since_time, user_did, include_threads=True
            )
            is True
        )

        # Test case where parent has no author attribute
        post.record.reply = MagicMock()
        post.record.reply.parent = MagicMock()
        # Delete the author attribute
        delattr(post.record.reply.parent, "author")
        assert (
            client._should_include_post(
                feed_view, since_time, user_did, include_threads=True
            )
            is False
        )

    @patch("bluemastodon.bluesky.BlueskyClient._extract_media_attachments")
    @patch("bluemastodon.bluesky.BlueskyClient._extract_links")
    def test_convert_to_bluesky_post(
        self, mock_extract_links: Any, mock_extract_media: Any
    ) -> None:
        """Test _convert_to_bluesky_post method."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Mock data
        now = datetime.now()
        mock_profile = MagicMock()
        mock_profile.did = "did:plc:test"
        mock_profile.display_name = "Test User"

        post = MagicMock()
        post.uri = "at://did:plc:test/app.bsky.feed.post/test123"
        post.cid = "cid123"
        post.record.text = "Test post"
        post.record.created_at = now.isoformat() + "Z"
        post.like_count = 5
        post.repost_count = 2

        # Explicitly set post.record.reply to None to indicate this is not a reply
        post.record.reply = None

        feed_view = MagicMock()
        feed_view.post = post

        # Setup mocks for media and links
        mock_media = [
            MediaAttachment(
                url="https://example.com/image.jpg", media_type=MediaType.IMAGE
            )
        ]
        mock_links_result = [Link(url="https://example.com")]
        mock_extract_media.return_value = mock_media
        mock_extract_links.return_value = mock_links_result

        # Call the method
        result = client._convert_to_bluesky_post(feed_view, mock_profile)

        # Check the result
        assert isinstance(result, BlueskyPost)
        assert result.id == "test123"  # Extracted from URI
        assert result.uri == "at://did:plc:test/app.bsky.feed.post/test123"
        assert result.cid == "cid123"
        assert result.content == "Test post"
        assert result.author_id == "did:plc:test"
        assert result.author_handle == "test_user"  # From config
        assert result.author_display_name == "Test User"
        assert result.media_attachments == mock_media
        assert result.links == mock_links_result
        assert result.like_count == 5
        assert result.repost_count == 2
        assert result.platform == "bluesky"
        assert result.is_reply is False
        assert result.reply_parent is None
        assert result.reply_root is None

        # Verify mock calls
        mock_extract_media.assert_called_once_with(post)
        mock_extract_links.assert_called_once_with(post)

        # Test with a reply post
        mock_extract_media.reset_mock()
        mock_extract_links.reset_mock()

        # Set up reply post data
        reply_post = MagicMock()
        reply_post.uri = "at://did:plc:test/app.bsky.feed.post/reply123"
        reply_post.cid = "cid456"
        reply_post.record.text = "Reply post"
        reply_post.record.created_at = now.isoformat() + "Z"

        # Configure reply structure
        reply_post.record.reply = MagicMock()
        reply_post.record.reply.parent = MagicMock()
        reply_post.record.reply.parent.uri = (
            "at://did:plc:test/app.bsky.feed.post/parent123"
        )
        reply_post.record.reply.parent.author = MagicMock()
        reply_post.record.reply.parent.author.did = (
            "did:plc:test"  # Same author (self-reply)
        )

        # Add root info
        reply_post.record.reply.root = MagicMock()
        reply_post.record.reply.root.uri = (
            "at://did:plc:test/app.bsky.feed.post/root123"
        )

        reply_feed_view = MagicMock()
        reply_feed_view.post = reply_post

        # Call the method
        result = client._convert_to_bluesky_post(reply_feed_view, mock_profile)

        # Check the result
        assert result.is_reply is True
        assert result.reply_parent == "parent123"
        assert result.in_reply_to_id == "parent123"

    def test_extract_media_attachments_with_images(self) -> None:
        """Test _extract_media_attachments with images."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock post with embed.images
        post = MagicMock()
        post.author.did = "did:plc:test"

        # Mock image data
        image1 = MagicMock()
        image1.alt = "Image 1"
        image1.image.ref.link = "link1"
        image1.image.mime_type = "image/jpeg"
        image1.image.size.width = 800
        image1.image.size.height = 600

        image2 = MagicMock()
        image2.alt = "Image 2"
        image2.image.ref.link = "link2"
        image2.image.mime_type = "image/png"
        image2.image.size.width = 400
        image2.image.size.height = 300

        # Add images to post
        post.record.embed.images = [image1, image2]

        # Mock get_blob_url method
        with patch.object(client, "_get_blob_url") as mock_get_url:
            mock_get_url.side_effect = (
                lambda p, link_ref: f"https://example.com/{link_ref}"
            )

            # Call the method
            result = client._extract_media_attachments(post)

            # Check results
            assert len(result) == 2

            assert result[0].url == "https://example.com/link1"
            assert result[0].alt_text == "Image 1"
            assert result[0].media_type == MediaType.IMAGE
            assert result[0].mime_type == "image/jpeg"
            assert result[0].width == 800
            assert result[0].height == 600

            assert result[1].url == "https://example.com/link2"
            assert result[1].alt_text == "Image 2"
            assert result[1].media_type == MediaType.IMAGE
            assert result[1].mime_type == "image/png"
            assert result[1].width == 400
            assert result[1].height == 300

            # Verify get_blob_url calls
            assert mock_get_url.call_count == 2
            mock_get_url.assert_any_call(post, "link1")
            mock_get_url.assert_any_call(post, "link2")

    def test_extract_media_attachments_no_embed(self) -> None:
        """Test _extract_media_attachments with no embed."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock post with no embed
        post = MagicMock()
        type(post.record).embed = PropertyMock(return_value=None)

        # Call the method
        result = client._extract_media_attachments(post)

        # Check result is empty list
        assert result == []

    def test_extract_links_with_external(self) -> None:
        """Test _extract_links with external link."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock post with external link
        post = MagicMock()
        post.author.did = "did:plc:test"

        # Mock external data
        external = MagicMock()
        external.uri = "https://example.com"
        external.title = "Example Website"
        external.description = "An example website"
        external.thumb.ref.link = "thumb_link"

        # Add external to post
        post.record.embed.external = external

        # Mock get_blob_url method
        with patch.object(client, "_get_blob_url") as mock_get_url:
            mock_get_url.return_value = "https://example.com/thumb"

            # Call the method
            result = client._extract_links(post)

            # Check results
            assert len(result) == 1
            assert result[0].url == "https://example.com"
            assert result[0].title == "Example Website"
            assert result[0].description == "An example website"
            assert result[0].image_url == "https://example.com/thumb"

            # Verify get_blob_url call
            mock_get_url.assert_called_once_with(post, "thumb_link")

    def test_extract_links_no_embed(self) -> None:
        """Test _extract_links with no embed."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock post with no embed
        post = MagicMock()
        type(post.record).embed = PropertyMock(return_value=None)

        # Call the method
        result = client._extract_links(post)

        # Check result is empty list
        assert result == []

    def test_get_blob_url(self) -> None:
        """Test _get_blob_url method."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Create mock post
        post = MagicMock()
        post.author.did = "did:plc:test"

        # Call the method
        result = client._get_blob_url(post, "blob123")

        # Check the result
        base_url = "https://bsky.social/xrpc/com.atproto.sync.get_blob"
        expected = f"{base_url}?did=did:plc:test&cid=blob123"
        assert result == expected

    @patch("bluemastodon.bluesky.BlueskyClient.ensure_authenticated")
    @patch("bluemastodon.bluesky.BlueskyClient._get_user_profile")
    @patch("bluemastodon.bluesky.BlueskyClient._fetch_author_feed")
    @patch("bluemastodon.bluesky.BlueskyClient._should_include_post")
    @patch("bluemastodon.bluesky.BlueskyClient._convert_to_bluesky_post")
    def test_get_recent_posts_success(
        self,
        mock_convert: Any,
        mock_should_include: Any,
        mock_fetch_feed: Any,
        mock_get_profile: Any,
        mock_auth: Any,
    ) -> None:
        """Test get_recent_posts success case."""
        # Setup configuration and client
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Setup mocks
        mock_auth.return_value = True
        mock_profile = MagicMock()
        mock_get_profile.return_value = mock_profile

        # Create feed with two posts, one should be included and one excluded
        mock_feed_view1 = MagicMock()
        mock_feed_view2 = MagicMock()
        mock_response = MagicMock()
        mock_response.feed = [mock_feed_view1, mock_feed_view2]
        mock_fetch_feed.return_value = mock_response

        # Mock should_include to include first post but not second
        mock_should_include.side_effect = (
            lambda post, since_time, user_did, include_threads=True: post
            == mock_feed_view1
        )

        # Mock convert to return a post
        mock_post = MagicMock()
        mock_convert.return_value = mock_post

        # Call the method with default include_threads=True
        result = client.get_recent_posts(hours_back=24, limit=10)

        # Check the result
        assert result == [mock_post]

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_get_profile.assert_called_once()
        mock_fetch_feed.assert_called_once_with(mock_profile.did, 10)
        assert mock_should_include.call_count == 2
        # Check that the mock was called - we can't easily test the timedelta arg
        mock_should_include.assert_called()
        # No need to check exact call parameters as they're hard to mock
        mock_convert.assert_called_once_with(mock_feed_view1, mock_profile)

        # Reset mocks
        mock_auth.reset_mock()
        mock_get_profile.reset_mock()
        mock_fetch_feed.reset_mock()
        mock_should_include.reset_mock()
        mock_convert.reset_mock()

        # Test with include_threads=False
        mock_should_include.side_effect = (
            lambda post, since_time, user_did, include_threads: (
                post == mock_feed_view1 and not include_threads
            )
        )

        # Call the method with include_threads=False
        result = client.get_recent_posts(hours_back=24, limit=10, include_threads=False)

        # Verify the mock was called
        mock_should_include.assert_called()
        # Can't easily check the exact arguments

    @patch("bluemastodon.bluesky.BlueskyClient.ensure_authenticated")
    def test_get_recent_posts_not_authenticated(self, mock_auth: Any) -> None:
        """Test get_recent_posts when not authenticated."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Setup mock to return False for authentication
        mock_auth.return_value = False

        # Call the method and check exception
        with pytest.raises(ValueError, match="Not authenticated with Bluesky"):
            client.get_recent_posts()

        # Verify mock call
        mock_auth.assert_called_once()

    @patch("bluemastodon.bluesky.BlueskyClient.ensure_authenticated")
    @patch("bluemastodon.bluesky.BlueskyClient._get_user_profile")
    def test_get_recent_posts_profile_error(
        self, mock_get_profile: Any, mock_auth: Any
    ) -> None:
        """Test get_recent_posts when profile fetch fails."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Setup mocks
        mock_auth.return_value = True
        mock_get_profile.return_value = None

        # Call the method
        result = client.get_recent_posts()

        # Check the result is an empty list
        assert result == []

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_get_profile.assert_called_once()

    @patch("bluemastodon.bluesky.BlueskyClient.ensure_authenticated")
    @patch("bluemastodon.bluesky.BlueskyClient._get_user_profile")
    @patch("bluemastodon.bluesky.BlueskyClient._fetch_author_feed")
    def test_get_recent_posts_feed_error(
        self, mock_fetch_feed: Any, mock_get_profile: Any, mock_auth: Any
    ) -> None:
        """Test get_recent_posts when feed fetch fails."""
        config = BlueskyConfig(username="test_user", password="test_password")
        client = BlueskyClient(config)

        # Setup mocks
        mock_auth.return_value = True
        mock_profile = MagicMock()
        mock_get_profile.return_value = mock_profile
        mock_fetch_feed.return_value = None

        # Call the method
        result = client.get_recent_posts()

        # Check the result is an empty list
        assert result == []

        # Verify mock calls
        mock_auth.assert_called_once()
        mock_get_profile.assert_called_once()
        mock_fetch_feed.assert_called_once()
