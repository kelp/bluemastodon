"""Common test fixtures and utilities."""

import json
import os
import tempfile
from datetime import datetime

import pytest

from social_sync.config import BlueskyConfig, Config, MastodonConfig
from social_sync.models import (
    BlueskyPost,
    Link,
    MastodonPost,
    MediaAttachment,
    MediaType,
)


@pytest.fixture
def sample_env_file():
    """Create a temporary .env file for testing."""
    env_content = """
    BLUESKY_USERNAME=test_user
    BLUESKY_PASSWORD=test_password
    MASTODON_INSTANCE_URL=https://mastodon.test
    MASTODON_ACCESS_TOKEN=test_token
    LOOKBACK_HOURS=12
    SYNC_INTERVAL_MINUTES=30
    MAX_POSTS_PER_RUN=10
    INCLUDE_MEDIA=true
    INCLUDE_LINKS=true
    """

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(env_content)
        temp_path = temp_file.name

    yield temp_path

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_config():
    """Create a sample configuration."""
    return Config(
        bluesky=BlueskyConfig(
            username="test_user",
            password="test_password",
        ),
        mastodon=MastodonConfig(
            instance_url="https://mastodon.test",
            access_token="test_token",
        ),
        lookback_hours=12,
        sync_interval_minutes=30,
        max_posts_per_run=10,
        include_media=True,
        include_links=True,
    )


@pytest.fixture
def sample_bluesky_post():
    """Create a sample Bluesky post for testing."""
    now = datetime.now()
    return BlueskyPost(
        id="test123",
        uri="at://test_user/app.bsky.feed.post/test123",
        cid="cid123",
        content="This is a test post with #hashtag",
        created_at=now,
        author_id="did:plc:test_user",
        author_handle="test_user.bsky.social",
        author_display_name="Test User",
        media_attachments=[
            MediaAttachment(
                url="https://example.com/image.jpg",
                alt_text="Test image",
                media_type=MediaType.IMAGE,
                mime_type="image/jpeg",
            )
        ],
        links=[
            Link(
                url="https://example.com",
                title="Example Website",
                description="An example website for testing",
            )
        ],
    )


@pytest.fixture
def sample_mastodon_post():
    """Create a sample Mastodon post for testing."""
    now = datetime.now()
    return MastodonPost(
        id="12345",
        content="This is a test post with #hashtag",
        created_at=now,
        author_id="67890",
        author_handle="test_user@mastodon.test",
        author_display_name="Test User",
        url="https://mastodon.test/@test_user/12345",
        media_attachments=[
            MediaAttachment(
                url="https://mastodon.test/media/image.jpg",
                alt_text="Test image",
                media_type=MediaType.IMAGE,
                mime_type="image/jpeg",
            )
        ],
    )


@pytest.fixture
def sample_bluesky_api_response():
    """Create a sample Bluesky API response for mocking."""
    # This is a simplified version of the actual API response
    # We'll expand it based on testing needs
    now = datetime.now()
    created_at = now.isoformat() + "Z"

    class FeedViewPost:
        class Author:
            did = "did:plc:test_user"
            handle = "test_user.bsky.social"
            displayName = "Test User"

        class Record:
            text = "This is a test post with #hashtag"
            createdAt = created_at
            reply = None

            class Embed:
                class Image:
                    class ImageData:
                        class Ref:
                            link = "image_cid"

                        class Size:
                            width = 800
                            height = 600

                        mimeType = "image/jpeg"

                    alt = "Test image"
                    image = ImageData()

                class External:
                    uri = "https://example.com"
                    title = "Example Website"
                    description = "An example website for testing"

                    class Thumb:
                        class Ref:
                            link = "thumb_cid"

                        mimeType = "image/jpeg"

                    thumb = Thumb()

                images = [Image()]
                external = External()

            embed = Embed()

        uri = "at://test_user/app.bsky.feed.post/test123"
        cid = "cid123"
        author = Author()
        record = Record()
        likeCount = 5
        repostCount = 2

    class FeedView:
        post = FeedViewPost()
        reason = None

    class Response:
        feed = [FeedView()]

    return Response()


@pytest.fixture
def sample_mastodon_api_response():
    """Create a sample Mastodon API response for mocking."""
    # This is a simplified version of the actual API response
    now = datetime.now().isoformat() + "Z"

    class MediaAttachment:
        url = "https://mastodon.test/media/image.jpg"
        description = "Test image"
        type = "image"
        mime_type = "image/jpeg"

    class Account:
        id = 67890
        acct = "test_user@mastodon.test"
        display_name = "Test User"

    class Application:
        name = "social-sync"

    class Response:
        id = 12345
        content = "This is a test post with #hashtag"
        created_at = now
        account = Account()
        url = "https://mastodon.test/@test_user/12345"
        media_attachments = [MediaAttachment()]
        application = Application()
        sensitive = False
        spoiler_text = ""
        visibility = "public"
        favourites_count = 3
        reblogs_count = 1

    return Response()


@pytest.fixture
def sample_sync_state_file():
    """Create a temporary state file for testing sync state."""
    now = datetime.now().isoformat()
    state_content = {
        "synced_posts": ["existing1", "existing2"],
        "sync_records": [
            {
                "source_id": "existing1",
                "source_platform": "bluesky",
                "target_id": "target1",
                "target_platform": "mastodon",
                "synced_at": now,
                "success": True,
                "error_message": None,
            },
            {
                "source_id": "existing2",
                "source_platform": "bluesky",
                "target_id": "target2",
                "target_platform": "mastodon",
                "synced_at": now,
                "success": True,
                "error_message": None,
            },
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        json.dump(state_content, temp_file)
        temp_path = temp_file.name

    yield temp_path

    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)
