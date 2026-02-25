"""Unit tests for personalized_summarization use case (Story 8.1: collected_at window)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.personalized_summarization import (
    filter_posts_for_user,
    find_posts_by_id_range,
    find_unsummarized_posts,
    get_group_post_id_window,
    get_user_last_summary_post_id,
)
from app.infrastructure.database.models import Post, User

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session():
    """Create mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_user():
    """Create a sample user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.telegram_id = 123456789
    user.username = "testuser"
    return user


@pytest.fixture
def sample_user2():
    """Create a second sample user."""
    user = MagicMock(spec=User)
    user.id = 2
    user.telegram_id = 987654321
    user.username = "testuser2"
    return user


def _setup_mock_scalar_result(mock_session, return_value):
    """Helper to setup mock scalar result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    mock_session.execute = AsyncMock(return_value=mock_result)


def _setup_mock_scalars_result(mock_session, return_values):
    """Helper to setup mock scalars result."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = return_values
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)


# ============================================================================
# Tests: get_user_last_summary_post_id
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_last_summary_post_id_with_summaries(
    mock_db_session, sample_user
):
    """Test getting last summary post_id when summaries exist."""
    # Setup mock to return post_id = 5
    _setup_mock_scalar_result(mock_db_session, 5)

    # Act
    result = await get_user_last_summary_post_id(mock_db_session, sample_user.id)

    # Assert
    assert result == 5
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_last_summary_post_id_no_summaries(mock_db_session, sample_user):
    """Test getting last summary post_id when no summaries exist."""
    # Setup mock to return None
    _setup_mock_scalar_result(mock_db_session, None)

    # Act
    result = await get_user_last_summary_post_id(mock_db_session, sample_user.id)

    # Assert
    assert result is None
    mock_db_session.execute.assert_called_once()


# ============================================================================
# Tests: get_group_post_id_window
# ============================================================================


@pytest.mark.asyncio
async def test_get_group_post_id_window_single_user(mock_db_session, sample_user):
    """Test getting group window with single user."""
    # Setup mock to return post_id = 10
    _setup_mock_scalar_result(mock_db_session, 10)

    # Act
    result = await get_group_post_id_window(mock_db_session, [sample_user])

    # Assert
    assert result == 10
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_group_post_id_window_multiple_users(
    mock_db_session, sample_user, sample_user2
):
    """Test getting group window with multiple users at different positions."""
    # Setup mock to return different values for each call
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = 15  # user1's last post_id
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = 10  # user2's last post_id

    mock_db_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

    # Act
    result = await get_group_post_id_window(
        mock_db_session, [sample_user, sample_user2]
    )

    # Assert
    assert result == 10  # Should return minimum (user2's)
    assert mock_db_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_group_post_id_window_no_summaries(
    mock_db_session, sample_user, sample_user2
):
    """Test getting group window when no users have summaries."""
    # Setup mock to return None for both users
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Act
    result = await get_group_post_id_window(
        mock_db_session, [sample_user, sample_user2]
    )

    # Assert
    assert result is None
    assert mock_db_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_group_post_id_window_mixed_users(
    mock_db_session, sample_user, sample_user2
):
    """Test group window with one user having summaries, one without."""
    # Setup mock: user1 has summaries, user2 doesn't
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = 20
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

    # Act
    result = await get_group_post_id_window(
        mock_db_session, [sample_user, sample_user2]
    )

    # Assert
    assert result == 20  # Only user1 has summaries


# ============================================================================
# Tests: find_posts_by_id_range
# ============================================================================


@pytest.mark.asyncio
async def test_find_posts_by_id_range_with_min_post_id(mock_db_session):
    """Test finding posts with hn_id > min_hn_id."""
    # Create mock posts
    posts = [MagicMock(spec=Post, id=i, score=100 + i) for i in range(6, 11)]
    _setup_mock_scalars_result(mock_db_session, posts)

    # Act: Get posts after hn_id = 5
    result = await find_posts_by_id_range(mock_db_session, min_hn_id=5)

    # Assert
    assert len(result) == 5
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_posts_by_id_range_with_limit(mock_db_session):
    """Test finding posts with limit applied."""
    # Create mock posts
    posts = [MagicMock(spec=Post, id=i, score=100 + i) for i in range(4, 6)]
    _setup_mock_scalars_result(mock_db_session, posts)

    # Act
    result = await find_posts_by_id_range(mock_db_session, min_hn_id=3, limit=2)

    # Assert
    assert len(result) == 2
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_posts_by_id_range_no_matching_posts(mock_db_session):
    """Test finding posts when all posts are before min_hn_id."""
    # Setup mock to return empty list
    _setup_mock_scalars_result(mock_db_session, [])

    # Act
    result = await find_posts_by_id_range(mock_db_session, min_hn_id=1000)

    # Assert
    assert len(result) == 0
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_posts_by_id_range_fallback_to_latest(mock_db_session):
    """Test fallback to latest posts when min_hn_id is None."""
    # Create mock posts (latest 5)
    posts = [MagicMock(spec=Post, id=i, score=100 + i) for i in range(6, 11)]
    _setup_mock_scalars_result(mock_db_session, posts)

    # Act
    result = await find_posts_by_id_range(
        mock_db_session, min_hn_id=None, fallback_to_latest=True, latest_post_limit=5
    )

    # Assert
    assert len(result) == 5
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_posts_by_id_range_no_fallback(mock_db_session):
    """Test no fallback when explicitly disabled."""
    # Act
    result = await find_posts_by_id_range(
        mock_db_session, min_hn_id=None, fallback_to_latest=False
    )

    # Assert
    assert len(result) == 0
    # No database call should be made
    mock_db_session.execute.assert_not_called()


# ============================================================================
# Integration Tests: End-to-End Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_full_pipeline_new_user(mock_db_session, sample_user):
    """Test full pipeline for new user with no summaries."""
    # Step 1: Mock get_user_last_summary_post_id to return None (called twice)
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = None
    mock_result1_repeat = MagicMock()
    mock_result1_repeat.scalar_one_or_none.return_value = None

    # Step 2: Mock find_posts_by_id_range to return fallback posts
    posts = [MagicMock(spec=Post, id=i, score=100 + i) for i in range(1, 11)]
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = posts
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value = mock_scalars

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_result1, mock_result1_repeat, mock_result2]
    )

    # Execute pipeline
    last_hn_id = await get_user_last_summary_post_id(mock_db_session, sample_user.id)
    assert last_hn_id is None

    min_hn_id = await get_group_post_id_window(mock_db_session, [sample_user])
    assert min_hn_id is None

    found_posts = await find_posts_by_id_range(
        mock_db_session, min_hn_id, fallback_to_latest=True, latest_post_limit=10
    )

    # Assert
    assert len(found_posts) == 10


@pytest.mark.asyncio
async def test_full_pipeline_existing_user(mock_db_session, sample_user):
    """Test full pipeline for existing user with summaries."""
    # Step 1: Mock get_user_last_summary_post_id to return post_id = 5 (called twice)
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = 5
    mock_result1_repeat = MagicMock()
    mock_result1_repeat.scalar_one_or_none.return_value = 5

    # Step 2: Mock find_posts_by_id_range to return posts 6-10
    new_posts = [MagicMock(spec=Post, id=i, score=100 + i) for i in range(6, 11)]
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = new_posts
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value = mock_scalars

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_result1, mock_result1_repeat, mock_result2]
    )

    # Execute pipeline
    last_hn_id = await get_user_last_summary_post_id(mock_db_session, sample_user.id)
    assert last_hn_id == 5

    min_hn_id = await get_group_post_id_window(mock_db_session, [sample_user])
    assert min_hn_id == 5

    found_posts = await find_posts_by_id_range(mock_db_session, min_hn_id)

    # Assert
    assert len(found_posts) == 5
    assert all(p.id > 5 for p in found_posts)


@pytest.mark.asyncio
async def test_full_pipeline_no_new_posts(mock_db_session, sample_user):
    """Test pipeline when user has already seen all posts."""
    # Mock: User has seen up to post_id = 100 (called twice)
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = 100
    mock_result1_repeat = MagicMock()
    mock_result1_repeat.scalar_one_or_none.return_value = 100

    # Mock: No new posts found
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value = mock_scalars

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_result1, mock_result1_repeat, mock_result2]
    )

    # Execute pipeline
    last_hn_id = await get_user_last_summary_post_id(mock_db_session, sample_user.id)
    min_hn_id = await get_group_post_id_window(mock_db_session, [sample_user])
    found_posts = await find_posts_by_id_range(mock_db_session, min_hn_id)

    # Assert
    assert last_hn_id == 100
    assert min_hn_id == 100
    assert len(found_posts) == 0


# ============================================================================
# Tests: find_unsummarized_posts (Story 8.1 — collected_at window)
# ============================================================================


@pytest.mark.asyncio
async def test_find_unsummarized_posts_returns_posts_in_window(mock_db_session):
    """Test that find_unsummarized_posts returns posts within the lookback window."""
    posts = [
        MagicMock(spec=Post, id=uuid.uuid4(), hn_id=i, score=100 + i) for i in range(3)
    ]
    _setup_mock_scalars_result(mock_db_session, posts)

    result = await find_unsummarized_posts(mock_db_session, lookback_hours=48)

    assert len(result) == 3
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_unsummarized_posts_with_limit(mock_db_session):
    """Test that find_unsummarized_posts respects the limit."""
    posts = [
        MagicMock(spec=Post, id=uuid.uuid4(), hn_id=i, score=100 + i) for i in range(2)
    ]
    _setup_mock_scalars_result(mock_db_session, posts)

    result = await find_unsummarized_posts(mock_db_session, lookback_hours=48, limit=2)

    assert len(result) == 2
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_summarizer_catches_late_arrival(mock_db_session):
    """Test that find_unsummarized_posts catches a late-arriving post.

    Regression test for Story 8.1: a post with a low hn_id (created long ago on HN)
    but a recent collected_at (only crossed the score threshold recently) must be
    returned by find_unsummarized_posts even though its hn_id falls below the old
    watermark.  The legacy find_posts_by_id_range with min_hn_id=5000 would have
    silently skipped it.
    """
    # Late arrival: old HN ID but collected just 1 hour ago
    late_arrival = MagicMock(spec=Post)
    late_arrival.id = uuid.uuid4()
    late_arrival.hn_id = 1000  # far below the old watermark of e.g. 47145963
    late_arrival.collected_at = datetime.now(timezone.utc) - timedelta(hours=1)
    late_arrival.score = 650
    late_arrival.type = "story"

    # find_unsummarized_posts uses collected_at, so it includes the late arrival
    _setup_mock_scalars_result(mock_db_session, [late_arrival])
    result = await find_unsummarized_posts(mock_db_session, lookback_hours=48)

    assert len(result) == 1
    assert result[0].hn_id == 1000, (
        "Late-arriving post should be returned despite old hn_id"
    )

    # Contrast: the old approach with min_hn_id=5000 returns nothing for this post.
    # (Simulated by resetting the mock to return an empty list.)
    _setup_mock_scalars_result(mock_db_session, [])
    old_result = await find_posts_by_id_range(mock_db_session, min_hn_id=5000)

    assert len(old_result) == 0, "Old watermark approach misses the late-arriving post"


@pytest.mark.asyncio
async def test_filter_posts_for_user_excludes_already_summarized(
    mock_db_session, sample_user
):
    """Test that filter_posts_for_user excludes posts the user already has summaries for.

    This verifies the idempotency layer (Story 8.1 AC 4): even if a post is in the
    48h window it will not be re-summarized for a user who already has a summary.
    """
    already_summarized_id = uuid.uuid4()
    new_post_id = uuid.uuid4()

    already_summarized = MagicMock(spec=Post)
    already_summarized.id = already_summarized_id

    new_post = MagicMock(spec=Post)
    new_post.id = new_post_id

    # Mock: already_summarized_id exists in summaries for this user
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [already_summarized_id]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await filter_posts_for_user(
        mock_db_session,
        sample_user,
        [already_summarized, new_post],
        prompt_type="basic",
    )

    assert len(result) == 1
    assert result[0].id == new_post_id, "Only the unsummarized post should pass through"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
