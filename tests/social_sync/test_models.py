"""Tests for the models module."""

from datetime import datetime

# No unused imports

from social_sync.models import (BlueskyPost, Link, MastodonPost,
                                MediaAttachment, MediaType, SocialPost,
                                SyncRecord)


class TestModels:
    """Test the models module."""

    def test_media_type_enum(self):
        """Test the MediaType enum."""
        assert MediaType.IMAGE == "image"
        assert MediaType.VIDEO == "video"
        assert MediaType.AUDIO == "audio"
        assert MediaType.OTHER == "other"

        # Test comparison
        assert MediaType.IMAGE == MediaType.IMAGE
        assert MediaType.IMAGE != MediaType.VIDEO

    def test_media_attachment_model(self):
        """Test the MediaAttachment model."""
        # Test with minimal fields
        media = MediaAttachment(
            url="https://example.com/image.jpg",
            media_type=MediaType.IMAGE,
        )
        assert media.url == "https://example.com/image.jpg"
        assert media.media_type == MediaType.IMAGE
        assert media.alt_text is None
        assert media.mime_type is None
        assert media.width is None
        assert media.height is None
        assert media.size_bytes is None

        # Test with all fields
        media = MediaAttachment(
            url="https://example.com/image.jpg",
            alt_text="Test image",
            mime_type="image/jpeg",
            media_type=MediaType.IMAGE,
            width=800,
            height=600,
            size_bytes=12345,
        )
        assert media.url == "https://example.com/image.jpg"
        assert media.alt_text == "Test image"
        assert media.mime_type == "image/jpeg"
        assert media.media_type == MediaType.IMAGE
        assert media.width == 800
        assert media.height == 600
        assert media.size_bytes == 12345

    def test_link_model(self):
        """Test the Link model."""
        # Test with minimal fields
        link = Link(url="https://example.com")
        assert link.url == "https://example.com"
        assert link.title is None
        assert link.description is None
        assert link.image_url is None

        # Test with all fields
        link = Link(
            url="https://example.com",
            title="Example Website",
            description="An example website for testing",
            image_url="https://example.com/image.jpg",
        )
        assert link.url == "https://example.com"
        assert link.title == "Example Website"
        assert link.description == "An example website for testing"
        assert link.image_url == "https://example.com/image.jpg"

    def test_social_post_base_model(self):
        """Test the SocialPost base model."""
        now = datetime.now()

        # Test with required fields
        post = SocialPost(
            id="123",
            content="Test post",
            created_at=now,
            platform="test",
            author_id="user123",
            author_handle="user@example.com",
        )
        assert post.id == "123"
        assert post.content == "Test post"
        assert post.created_at == now
        assert post.platform == "test"
        assert post.author_id == "user123"
        assert post.author_handle == "user@example.com"
        assert post.author_display_name is None
        assert post.media_attachments == []
        assert post.links == []
        assert post.is_reply is False
        assert post.is_repost is False
        assert post.in_reply_to_id is None
        assert post.repost_of_id is None
        assert post.language is None
        assert post.visibility is None

        # Test with all fields
        media = MediaAttachment(
            url="https://example.com/image.jpg", media_type=MediaType.IMAGE
        )
        link = Link(url="https://example.com")

        post = SocialPost(
            id="123",
            content="Test post",
            created_at=now,
            platform="test",
            author_id="user123",
            author_handle="user@example.com",
            author_display_name="User Name",
            media_attachments=[media],
            links=[link],
            is_reply=True,
            is_repost=False,
            in_reply_to_id="456",
            repost_of_id=None,
            language="en",
            visibility="public",
        )
        assert post.author_display_name == "User Name"
        assert len(post.media_attachments) == 1
        assert post.media_attachments[0].url == "https://example.com/image.jpg"
        assert len(post.links) == 1
        assert post.links[0].url == "https://example.com"
        assert post.is_reply is True
        assert post.in_reply_to_id == "456"
        assert post.language == "en"
        assert post.visibility == "public"

    def test_bluesky_post_model(self):
        """Test the BlueskyPost model."""
        now = datetime.now()

        post = BlueskyPost(
            id="123",
            content="Test post",
            created_at=now,
            author_id="did:plc:123",
            author_handle="user.bsky.social",
            uri="at://did:plc:123/app.bsky.feed.post/123",
            cid="cid123",
        )

        assert post.platform == "bluesky"  # Default value
        assert post.uri == "at://did:plc:123/app.bsky.feed.post/123"
        assert post.cid == "cid123"
        assert post.reply_root is None
        assert post.reply_parent is None
        assert post.like_count is None
        assert post.repost_count is None

        # Test with all fields
        post = BlueskyPost(
            id="123",
            content="Test post",
            created_at=now,
            author_id="did:plc:123",
            author_handle="user.bsky.social",
            uri="at://did:plc:123/app.bsky.feed.post/123",
            cid="cid123",
            reply_root="root123",
            reply_parent="parent123",
            like_count=5,
            repost_count=2,
        )

        assert post.reply_root == "root123"
        assert post.reply_parent == "parent123"
        assert post.like_count == 5
        assert post.repost_count == 2

    def test_mastodon_post_model(self):
        """Test the MastodonPost model."""
        now = datetime.now()

        post = MastodonPost(
            id="123",
            content="Test post",
            created_at=now,
            author_id="user123",
            author_handle="user@example.com",
            url="https://example.com/@user/123",
        )

        assert post.platform == "mastodon"  # Default value
        assert post.url == "https://example.com/@user/123"
        assert post.application is None
        assert post.sensitive is False
        assert post.spoiler_text is None
        assert post.favourites_count is None
        assert post.reblogs_count is None

        # Test with all fields
        post = MastodonPost(
            id="123",
            content="Test post",
            created_at=now,
            author_id="user123",
            author_handle="user@example.com",
            url="https://example.com/@user/123",
            application="TestApp",
            sensitive=True,
            spoiler_text="Spoiler",
            favourites_count=5,
            reblogs_count=2,
        )

        assert post.application == "TestApp"
        assert post.sensitive is True
        assert post.spoiler_text == "Spoiler"
        assert post.favourites_count == 5
        assert post.reblogs_count == 2

    def test_sync_record_model(self):
        """Test the SyncRecord model."""
        # Test with required fields
        record = SyncRecord(
            source_id="src123",
            source_platform="bluesky",
            target_id="tgt456",
            target_platform="mastodon",
        )

        assert record.source_id == "src123"
        assert record.source_platform == "bluesky"
        assert record.target_id == "tgt456"
        assert record.target_platform == "mastodon"
        assert record.synced_at is not None  # Should have default current time
        assert record.success is True  # Default value
        assert record.error_message is None

        # Test with all fields
        now = datetime.now()
        record = SyncRecord(
            source_id="src123",
            source_platform="bluesky",
            target_id="tgt456",
            target_platform="mastodon",
            synced_at=now,
            success=False,
            error_message="Error message",
        )

        assert record.synced_at == now
        assert record.success is False
        assert record.error_message == "Error message"
