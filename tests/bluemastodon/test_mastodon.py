"""Tests for the mastodon module."""

import re  # Import re
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from bluemastodon.config import MastodonConfig
from bluemastodon.mastodon import MastodonClient
from bluemastodon.models import (
    BlueskyPost,
    Link,
    MastodonPost,
    MediaAttachment,
    MediaType,
)


class TestMastodonClient:
    """Test the MastodonClient class."""

    def test_init(self) -> None:
        """Test initialization of MastodonClient."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        assert client.config == config
        assert client._authenticated is False
        assert client._account is None
        assert client.client is not None

    @patch("bluemastodon.mastodon.Mastodon")
    def test_verify_credentials_success(self, mock_mastodon_api: Any) -> None:
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

    @patch("bluemastodon.mastodon.Mastodon")
    def test_verify_credentials_failure(self, mock_mastodon_api: Any) -> None:
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

    def test_ensure_authenticated_already_authenticated(self) -> None:
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

    def test_ensure_authenticated_not_authenticated(self) -> None:
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

    def test_apply_character_limits_short_content(self) -> None:
        """Test applying character limits to short content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        content = "This is a short post under the limit."
        result = client._apply_character_limits(content)

        assert result == content

    def test_apply_character_limits_long_content(self) -> None:
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

    def test_apply_character_limits_word_boundary(self) -> None:
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

    def test_apply_character_limits_url_conversion(self) -> None:
        """Test that character limits handle URL conversion."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Test case 1: GitHub URL conversion (without https://)
        content = "Check out github.com/kelp/bluemastodon for a cool project!"
        result = client._apply_character_limits(content)

        # Should replace github.com with https://github.com
        assert "https://github.com/kelp/bluemastodon" in result

        # Test case 2: Regular domain conversion
        content = "Visit example.com for more information."
        result = client._apply_character_limits(content)

        # Should replace example.com with https://example.com
        assert "https://example.com" in result

        # Test case 3: Multiple URL conversions
        content = "Check github.com/kelp/bluemastodon and mastodon.com/web"
        result = client._apply_character_limits(content)

        # Should replace both URLs
        assert "https://github.com/kelp/bluemastodon" in result
        assert "https://mastodon.com/web" in result

        # Test case 4: Twitter URL conversion
        content = "Check twitter.com/username and bsky.com/profile"
        result = client._apply_character_limits(content)

        # Should replace both URLs
        assert "https://twitter.com/username" in result
        assert "https://bsky.com/profile" in result

        # Test case 5: Already prefixed URLs - prevent double https://
        content = "Check https://github.com/kelp/bluemastodon for a cool project!"
        result = client._apply_character_limits(content)

        # Should NOT create a double https://
        assert "https://github.com/kelp/bluemastodon" in result
        assert "https://https://github.com" not in result

        # Test case 6: Mixed prefixed and non-prefixed URLs
        content = (
            "Compare https://github.com/kelp/bluemastodon and github.com/kelp/webdown"
        )
        result = client._apply_character_limits(content)

        # Should handle both cases correctly
        assert "https://github.com/kelp/bluemastodon" in result
        assert "https://github.com/kelp/webdown" in result
        assert "https://https://" not in result

    @patch("bluemastodon.mastodon.re")
    def test_is_duplicate_post_no_account(self, mock_re: Any) -> None:
        """Test _is_duplicate_post when no account is available."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "_account", None)

        is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None
        mock_re.sub.assert_not_called()

    def test_is_duplicate_post_invalid_account_id(self) -> None:
        """Test _is_duplicate_post with invalid account ID."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "_account", MagicMock())

        # Make the ID property unavailable
        setattr(
            type(client._account),
            "id",
            property(lambda _: (_ for _ in ()).throw(ValueError("ID error"))),
        )

        with patch.object(client, "_safe_int_to_str", return_value=""):
            is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_api_error(self) -> None:
        """Test _is_duplicate_post with API error."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Make account_statuses raise an exception
        mock_client = MagicMock()
        mock_client.account_statuses.side_effect = Exception("API error")
        setattr(client, "client", mock_client)

        is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_high_similarity(self) -> None:
        """Test _is_duplicate_post with high similarity content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock posts
        mock_post = MagicMock()
        mock_post.content = "<p>This is a test post about Python programming</p>"
        mock_client = MagicMock()
        mock_client.account_statuses.return_value = [mock_post]
        setattr(client, "client", mock_client)

        # Test with similar content
        is_duplicate, post = client._is_duplicate_post(
            "This is a test post about Python programming."
        )

        assert is_duplicate is True
        assert post == mock_post

    def test_is_duplicate_post_low_similarity(self) -> None:
        """Test _is_duplicate_post with low similarity content."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock posts
        mock_post = MagicMock()
        mock_post.content = "<p>This is a post about Python programming</p>"
        mock_client = MagicMock()
        mock_client.account_statuses.return_value = [mock_post]
        setattr(client, "client", mock_client)

        # Test with different content
        is_duplicate, post = client._is_duplicate_post(
            "This is a completely different topic about JavaScript."
        )

        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_error_in_post_processing(self) -> None:
        """Test _is_duplicate_post handling post processing errors."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock posts with one that will cause an error
        mock_post = MagicMock()
        # Make post content access raise an exception
        type(mock_post).content = property(
            lambda _: (_ for _ in ()).throw(ValueError("Content error"))
        )

        # Add a second valid post
        valid_post = MagicMock()
        valid_post.content = "<p>This is a test post about Python programming</p>"

        mock_client = MagicMock()
        mock_client.account_statuses.return_value = [mock_post, valid_post]
        setattr(client, "client", mock_client)

        # Test should still check the second post even if first fails
        is_duplicate, post = client._is_duplicate_post(
            "This is a test post about Python programming."
        )

        # Should still find the match in the second post
        assert is_duplicate is True
        assert post == valid_post

    def test_is_duplicate_post_division_by_zero_protection(self) -> None:
        """Test _is_duplicate_post division by zero protection."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock post with empty content
        mock_post = MagicMock()
        mock_post.content = ""
        mock_client = MagicMock()
        mock_client.account_statuses.return_value = [mock_post]
        setattr(client, "client", mock_client)

        # Test with non-empty content (should avoid division by zero)
        is_duplicate, post = client._is_duplicate_post("Non-empty content")

        # Should not match and should not crash
        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_error(self) -> None:
        """Test _is_duplicate_post handling errors."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_client.account_statuses.side_effect = Exception("API error")
        setattr(client, "client", mock_client)

        # Should fail open (not duplicate)
        is_duplicate, post = client._is_duplicate_post("Test content")

        assert is_duplicate is False
        assert post is None

    def test_is_duplicate_post_inner_exception(self) -> None:
        """Test _is_duplicate_post handling exceptions during post check."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(client, "_account", mock_account)

        # Setup mock posts
        mock_post_error_trigger = MagicMock()
        mock_post_error_trigger.content = "<p>This post will cause regex error</p>"
        mock_post_valid = MagicMock()
        mock_post_valid.content = (
            "<p>Valid post</p>"  # This is the one we expect to match
        )

        mock_client = MagicMock()
        mock_client.account_statuses.return_value = [
            mock_post_error_trigger,
            mock_post_valid,
        ]
        setattr(client, "client", mock_client)

        # Patch re.sub to raise an error only when processing the first post's content
        original_re_sub = re.sub

        def mock_re_sub(pattern, repl, string, count=0):
            if "regex error" in string:
                raise ValueError("Regex error")
            return original_re_sub(pattern, repl, string, count=count)

        with patch("bluemastodon.mastodon.re.sub", side_effect=mock_re_sub):
            with patch("bluemastodon.mastodon.logger") as mock_logger:
                is_duplicate, post = client._is_duplicate_post("Valid post")

                # Should skip the error post and find the valid one
                assert is_duplicate is True
                assert post == mock_post_valid
                # Verify the correct warning was logged for the error during post check
                mock_logger.warning.assert_any_call(
                    "Error checking specific post for similarity: Regex error"
                )

    def test_is_duplicate_post_outer_exception(self) -> None:
        """Test _is_duplicate_post handling exceptions during initial fetch or setup."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_account = MagicMock()
        mock_account.id = "12345"
        setattr(
            client, "_account", mock_account
        )  # Need a valid ID to get past the first check

        # Mock account_statuses to raise an exception
        mock_client = MagicMock()
        mock_client.account_statuses.side_effect = RuntimeError("Fetch error")
        setattr(client, "client", mock_client)

        with patch("bluemastodon.mastodon.logger") as mock_logger:
            is_duplicate, post = client._is_duplicate_post("Some content")
            # Should fail open
            assert is_duplicate is False
            assert post is None
            # Verify warning was logged (from inner try/except around account_statuses)
            mock_logger.warning.assert_called_once()
            assert (
                "Error fetching recent posts: Fetch error"
                in mock_logger.warning.call_args[0][0]
            )

    def test_determine_media_type(self) -> None:
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

    def test_convert_to_media_type(self) -> None:
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

    def test_get_safe_attr(self) -> None:
        """Test the _get_safe_attr method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Use a regular object instead of MagicMock for better testing
        class TestObject:
            def __init__(self):
                self.existing_attr = "test_value"

            @property
            def error_property(self):
                raise ValueError("Test error")

        obj = TestObject()

        # Test case: Attribute exists
        assert client._get_safe_attr(obj, "existing_attr") == "test_value"

        # Test case: Attribute doesn't exist
        assert client._get_safe_attr(obj, "non_existing_attr") is None

        # Test case: Attribute doesn't exist, custom default
        assert client._get_safe_attr(obj, "non_existing_attr", "default") == "default"

        # Test case: Attribute access raises an exception
        assert client._get_safe_attr(obj, "error_property", "fallback") == "fallback"

        # Test case: hasattr raises exception
        with patch("builtins.hasattr", side_effect=RuntimeError("hasattr error")):
            assert (
                client._get_safe_attr(obj, "existing_attr", "fallback2") == "fallback2"
            )

    def test_safe_int_to_str(self) -> None:
        """Test the _safe_int_to_str method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Test case: Integer
        assert client._safe_int_to_str(123) == "123"

        # Test case: String
        assert client._safe_int_to_str("123") == "123"

        # Test case: None
        assert client._safe_int_to_str(None) == ""

        # Test case: Object that raises an exception when converted
        class BadObject:
            def __str__(self):
                raise ValueError("Conversion error")

        # Patch the logger for this specific assertion
        with patch("bluemastodon.mastodon.logger") as mock_logger:
            result = client._safe_int_to_str(BadObject())
            assert result == ""
            # Assert the warning was logged correctly
            mock_logger.warning.assert_called_once()
            assert (
                "Error converting value to string: Conversion error"
                in mock_logger.warning.call_args[0][0]
            )

    def test_safe_get_nested(self) -> None:
        """Test the _safe_get_nested method."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Create a nested object structure with regular objects
        class Inner:
            def __init__(self):
                self.value = "nested_value"

        class Middle:
            def __init__(self):
                self.inner = Inner()

            @property
            def error_attr(self):
                raise ValueError("Test error")

        class Outer:
            def __init__(self):
                self.middle = Middle()
                self.none_attr = None

        outer = Outer()

        # Test case: Valid path
        assert (
            client._safe_get_nested(outer, "middle", "inner", "value") == "nested_value"
        )

        # Test case: Invalid path
        assert client._safe_get_nested(outer, "middle", "missing", "value") is None

        # Test case: Invalid path with custom default
        assert (
            client._safe_get_nested(
                outer, "middle", "missing", "value", default="default"
            )
            == "default"
        )

        # Test case: Attribute access raises exception
        assert (
            client._safe_get_nested(
                outer, "middle", "error_attr", "value", default="error_default"
            )
            == "error_default"
        )

        # Test case: None in the path
        assert (
            client._safe_get_nested(
                outer, "none_attr", "anything", default="none_default"
            )
            == "none_default"
        )

    def test_convert_to_mastodon_post(self) -> None:
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
        mock_toot.application.name = "bluemastodon"
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
        assert result.application == "bluemastodon"
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

    def test_convert_to_mastodon_post_with_errors(self) -> None:
        """Test converting problematic Mastodon API responses."""
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Test case 1: Missing fields but valid ID
        # Use a custom object instead of MagicMock to avoid test issues
        class MinimalToot:
            def __init__(self):
                self.id = 12345  # Integer ID to test conversion
                # No other properties set

        minimal_toot = MinimalToot()
        result = client._convert_to_mastodon_post(minimal_toot)

        # We should get a valid post with default values
        assert isinstance(result, MastodonPost)
        assert result.id == "12345"  # Should be converted to string
        assert result.content == ""
        assert result.media_attachments == []

        # Test case 2: Problematic datetime
        class DatetimeToot:
            def __init__(self):
                self.id = "67890"
                self.created_at = "invalid-date-format"

        datetime_toot = DatetimeToot()
        result = client._convert_to_mastodon_post(datetime_toot)

        # Should fall back to current time for created_at
        assert isinstance(result, MastodonPost)
        assert result.id == "67890"
        assert isinstance(result.created_at, datetime)

        # Test case 3: Completely invalid toot causes fallback
        with patch.object(client, "_get_safe_attr", return_value="fallback"):
            with patch.object(client, "_safe_int_to_str", return_value="error"):
                # This should trigger the outer try/except fallback
                class InvalidObject:
                    pass

                result = client._convert_to_mastodon_post(InvalidObject())

                # Should create a minimal valid post
                assert isinstance(result, MastodonPost)
                assert result.id == "error"
                assert result.content == "fallback"

        # Test case 4: Media attachment processing error
        class MediaErrorToot:
            def __init__(self):
                self.id = "54321"
                self.content = "Test content"

                # Create a media attachment that will cause an error
                class BadMedia:
                    # We need to add proper attributes to control how
                    # the error is processed
                    @property
                    def type(self):
                        raise ValueError("Media type error")

                    # Need empty URL to get skipped
                    url = ""
                    description = ""

                self.media_attachments = [BadMedia()]

        # For this test, we need to patch the determining function
        # so it never gets to process our media
        with patch.object(
            client, "_determine_media_type", side_effect=Exception("Media type error")
        ):
            media_error_toot = MediaErrorToot()
            result = client._convert_to_mastodon_post(media_error_toot)

            # Should skip the problematic media but continue with the post
            assert isinstance(result, MastodonPost)
            assert result.id == "54321"
            assert result.content == "Test content"
            # Now check length instead of exact equality to handle different behavior
            assert len(result.media_attachments) == 0

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_success(
        self, mock_auth: Any, mock_convert: Any, mock_is_duplicate: Any
    ) -> None:
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
        mock_client = MagicMock()
        mock_client.status_post.return_value = mock_toot
        setattr(client, "client", mock_client)

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

        # Test 1: Post without reply parent
        result = client.post(bluesky_post)
        assert result is not None
        status, post_obj, error_msg = result

        # Assert
        assert status == "success"
        assert post_obj == mock_mastodon_post
        assert error_msg is None
        client.client.status_post.assert_called_once()
        mock_convert.assert_called_once_with(mock_toot)

        # Reset mocks
        client.client.status_post.reset_mock()
        mock_convert.reset_mock()

        # Test 2: Post with reply parent
        parent_id = "masto12345"
        result = client.post(bluesky_post, in_reply_to_id=parent_id)

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "success"
        assert post_obj == mock_mastodon_post
        assert error_msg is None
        client.client.status_post.assert_called_once()
        # Verify in_reply_to_id was passed correctly
        call_args = client.client.status_post.call_args
        assert call_args.kwargs["in_reply_to_id"] == parent_id
        mock_convert.assert_called_once_with(mock_toot)

    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_not_authenticated(self, mock_auth: Any) -> None:
        """Test post when not authenticated."""
        # Setup
        mock_auth.return_value = False

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

        # Post (both with and without in_reply_to_id)
        result1 = client.post(MagicMock())
        assert result1 is not None
        status1, post_obj1, error_msg1 = result1

        result2 = client.post(MagicMock(), in_reply_to_id="12345")
        assert result2 is not None
        status2, post_obj2, error_msg2 = result2

        # Assert
        assert status1 == "failed"
        assert post_obj1 is None
        assert error_msg1 is not None
        assert "Not authenticated" in error_msg1

        assert status2 == "failed"
        assert post_obj2 is None
        assert error_msg2 is not None
        assert "Not authenticated" in error_msg2

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_duplicate_with_existing_post(
        self, mock_auth: Any, mock_convert: Any, mock_is_duplicate: Any
    ) -> None:
        """Test post with duplicate detection (existing post available)."""
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
        setattr(client, "client", MagicMock())

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

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "duplicate"
        assert post_obj == mock_mastodon_post
        assert error_msg is None
        client.client.status_post.assert_not_called()
        mock_convert.assert_called_once_with(mock_existing_post)

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_duplicate_without_existing_post(
        self, mock_auth: Any, mock_is_duplicate: Any
    ) -> None:
        """Test post with duplicate detection (no existing post)."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (True, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "client", MagicMock())

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

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "duplicate"
        assert post_obj is not None
        assert isinstance(post_obj, MastodonPost)
        assert post_obj.id == "duplicate"
        assert post_obj.content == "This is a test post"
        assert error_msg is None
        client.client.status_post.assert_not_called()

    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_duplicate_with_conversion_error(
        self, mock_auth: Any, mock_is_duplicate: Any, mock_convert: Any
    ) -> None:
        """Test post with duplicate detection but error in conversion."""
        # Setup
        mock_auth.return_value = True
        mock_existing_post = MagicMock()
        mock_existing_post.id = "12345"
        mock_existing_post.url = "https://mastodon.test/@user/12345"
        mock_is_duplicate.return_value = (True, mock_existing_post)
        mock_convert.side_effect = Exception("Conversion error")

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "client", MagicMock())

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

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "duplicate"
        assert post_obj is not None
        assert isinstance(post_obj, MastodonPost)
        assert post_obj.id == "12345"
        assert post_obj.content == "This is a test post"
        assert post_obj.url == "https://mastodon.test/@user/12345"
        assert error_msg is None
        client.client.status_post.assert_not_called()

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_error(self, mock_auth: Any, mock_is_duplicate: Any) -> None:
        """Test post when posting fails."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_client = MagicMock()
        mock_client.status_post.side_effect = Exception("API error")
        setattr(client, "client", mock_client)

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

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "failed"
        assert post_obj is None
        assert error_msg is not None

        assert "API error" in error_msg
        client.client.status_post.assert_called_once()

    @patch.object(MastodonClient, "_safe_int_to_str")
    @patch.object(MastodonClient, "_get_safe_attr")
    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_with_conversion_error(
        self,
        mock_auth: Any,
        mock_is_duplicate: Any,
        mock_get_attr: Any,
        mock_int_to_str: Any,
    ) -> None:
        """Test post with conversion error fallback."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        # Create mock toot
        mock_toot = MagicMock()
        mock_toot.id = "12345"
        mock_toot.url = "https://mastodon.test/@user/12345"

        # Make conversion fail but still return values for the fallback
        mock_get_attr.side_effect = lambda obj, attr, default=None: (
            "No URL" if attr == "url" else default
        )
        mock_int_to_str.return_value = "12345"

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_client = MagicMock()
        mock_client.status_post.return_value = mock_toot
        setattr(client, "client", mock_client)

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

        # Trigger conversion error in _convert_to_mastodon_post
        with patch.object(
            client,
            "_convert_to_mastodon_post",
            side_effect=Exception("Conversion error"),
        ):
            # Post
            result = client.post(bluesky_post)

            assert result is not None

            status, post_obj, error_msg = result

        # Assert we get a fallback post but status is success
        assert status == "success"
        assert post_obj is not None
        assert isinstance(post_obj, MastodonPost)
        assert post_obj.id == "12345"
        assert post_obj.content == "This is a test post"  # Original content preserved
        assert error_msg is None  # Error is logged, not returned here
        client.client.status_post.assert_called_once()

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_unhandled_error(self, mock_auth: Any, mock_is_duplicate: Any) -> None:
        """Test post with unhandled error in the outer try/except."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.side_effect = RuntimeError("Unexpected critical error")

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)

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

        # Post - should be handled by the outer try/except
        result = client.post(bluesky_post)

        assert result is not None

        status, post_obj, error_msg = result

        # Assert we get 'failed' status
        assert status == "failed"
        assert post_obj is None
        assert error_msg is not None

        assert "Unexpected critical error" in error_msg

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_api_error(self, mock_auth: Any, mock_is_duplicate: Any) -> None:
        """Test post with specific API error exception."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "client", MagicMock())
        # Test MastodonAPIError specifically
        client.client.status_post.side_effect = Exception("API error message")

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
        with patch("bluemastodon.mastodon.logger") as mock_logger:
            with patch("bluemastodon.mastodon.MastodonAPIError", Exception):
                result = client.post(bluesky_post)

                assert result is not None

                status, post_obj, error_msg = result

                # Assert
                assert status == "failed"
                assert post_obj is None
                assert error_msg is not None

                assert "API error message" in error_msg
                client.client.status_post.assert_called_once()
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Mastodon API error posting" in mock_logger.error.call_args[0][0]

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_network_error(self, mock_auth: Any, mock_is_duplicate: Any) -> None:
        """Test post with specific Network error exception."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        # Create client
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        setattr(client, "client", MagicMock())
        # Test MastodonNetworkError specifically
        client.client.status_post.side_effect = Exception("Network error message")

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
        with patch("bluemastodon.mastodon.logger") as mock_logger:
            with patch("bluemastodon.mastodon.MastodonNetworkError", Exception):
                result = client.post(bluesky_post)

                assert result is not None

                status, post_obj, error_msg = result

                # Assert
                assert status == "failed"
                assert post_obj is None
                assert error_msg is not None

                assert "Network error message" in error_msg
                client.client.status_post.assert_called_once()
                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert (
                    "Mastodon network error posting"
                    in mock_logger.error.call_args[0][0]
                )

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_with_media_attachments(
        self, mock_auth: Any, mock_convert: Any, mock_is_duplicate: Any
    ) -> None:
        """Test post with media attachments."""
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
        mock_client = MagicMock()
        mock_client.status_post.return_value = mock_toot
        setattr(client, "client", mock_client)

        # Create test post with media attachments
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post with media",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            # Test visibility parameter
            visibility="unlisted",
            media_attachments=[
                MediaAttachment(
                    url="https://example.com/image.jpg",
                    alt_text="Test image",
                    media_type=MediaType.IMAGE,
                    mime_type="image/jpeg",
                ),
                MediaAttachment(
                    url="",  # Empty URL (will be skipped)
                    alt_text="Missing image",
                    media_type=MediaType.IMAGE,
                    mime_type="image/jpeg",
                ),
            ],
            links=[],
        )

        # Post
        result = client.post(bluesky_post)

        assert result is not None

        status, post_obj, error_msg = result

        # Assert
        assert status == "success"
        assert post_obj == mock_mastodon_post
        assert error_msg is None
        # Only check the visibility parameter since that's reliably passed through
        call_args = client.client.status_post.call_args
        assert call_args.kwargs["visibility"] == "unlisted"
        mock_convert.assert_called_once_with(mock_toot)

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_replaces_truncated_links(
        self, mock_auth: Any, mock_convert: Any, mock_is_duplicate: Any
    ) -> None:
        """Test that truncated links in content are replaced with full URLs."""
        # Setup
        mock_auth.return_value = True
        mock_is_duplicate.return_value = (False, None)

        mock_toot = MagicMock()
        mock_mastodon_post = MastodonPost(
            id="12345",
            content="Test content with replaced link",
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
        mock_client = MagicMock()
        mock_client.status_post.return_value = mock_toot
        setattr(client, "client", mock_client)

        # Test Case 1: Truncated link in content
        bluesky_post1 = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="Check out my project at github.com/kelp/bluemastodon...",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            links=[
                Link(
                    url="https://github.com/kelp/bluemastodon",
                    title="BlueMastodon Project",
                    description="Cross-posting tool",
                )
            ],
        )

        result1 = client.post(bluesky_post1)
        assert result1 is not None
        status1, post_obj1, error_msg1 = result1
        assert status1 == "success"
        assert post_obj1 == mock_mastodon_post
        assert error_msg1 is None

        # Verify the truncated link was replaced
        call_args = client.client.status_post.call_args
        # The status is passed as a keyword argument 'status'
        assert "github.com/kelp/bluemastodon..." not in call_args.kwargs["status"]
        assert "https://github.com/kelp/bluemastodon" in call_args.kwargs["status"]

        # Reset mocks
        client.client.status_post.reset_mock()

        # Test Case 2: Full link in content
        bluesky_post2 = BlueskyPost(
            id="test456",
            uri="at://test_user/app.bsky.feed.post/test456",
            cid="cid456",
            content="Check out my project at https://example.com/project",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            links=[
                Link(
                    url="https://example.com/project",
                    title="Example Project",
                    description="Example description",
                )
            ],
        )

        result2 = client.post(bluesky_post2)
        assert result2 is not None
        status2, post_obj2, error_msg2 = result2
        assert status2 == "success"
        assert post_obj2 == mock_mastodon_post
        assert error_msg2 is None

        # Verify the link was properly handled
        call_args = client.client.status_post.call_args
        assert "https://example.com/project" in call_args.kwargs["status"]

    @patch.object(MastodonClient, "_is_duplicate_post")
    @patch.object(MastodonClient, "_convert_to_mastodon_post")
    @patch.object(MastodonClient, "ensure_authenticated")
    def test_post_with_media_error(
        self, mock_auth: Any, mock_convert: Any, mock_is_duplicate: Any
    ) -> None:
        """Test post with media attachments that cause errors."""
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

        # Create client with mocked logging
        config = MastodonConfig(
            instance_url="https://mastodon.test", access_token="test_token"
        )
        client = MastodonClient(config)
        mock_client = MagicMock()
        mock_client.status_post.return_value = mock_toot
        setattr(client, "client", mock_client)

        # Create test post with media attachments
        bluesky_post = BlueskyPost(
            id="test123",
            uri="at://test_user/app.bsky.feed.post/test123",
            cid="cid123",
            content="This is a test post with media",
            created_at=datetime.now(),
            author_id="test_author",
            author_handle="test_author.bsky.social",
            author_display_name="Test Author",
            media_attachments=[
                MediaAttachment(
                    url="https://example.com/image.jpg",
                    alt_text="Test image",
                    media_type=MediaType.IMAGE,
                    mime_type="image/jpeg",
                )
            ],
            links=[],
        )

        # Patch only the first logger.info call to throw an exception
        # to test the media attachment error handling
        def selective_info_exception(message):
            # Only throw exception for media upload log messages
            if "Would upload media" in message:
                raise Exception("Mock media upload error")
            # Let other log messages go through

        with patch("bluemastodon.mastodon.logger.info") as mock_logger_info:
            with patch("bluemastodon.mastodon.logger.error") as mock_logger_error:
                # Set up the selective exception
                mock_logger_info.side_effect = selective_info_exception
                result = client.post(bluesky_post)

                # Verify error was logged
                assert mock_logger_error.call_count >= 1
                # The first call should be about media upload
                assert "Error uploading media to Mastodon" in str(
                    mock_logger_error.call_args_list[0]
                )

        # The post should succeed even though media attachment failed
        assert result is not None
        status, post_obj, error_msg = result  # Unpack the result tuple
        assert status == "success"
        assert post_obj == mock_mastodon_post
        assert error_msg is None
        client.client.status_post.assert_called_once()
        mock_convert.assert_called_once_with(mock_toot)
