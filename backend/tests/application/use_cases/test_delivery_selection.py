"""Unit tests for SelectPostsForDeliveryUseCase."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.delivery_selection import (
    SelectPostsForDeliveryUseCase,
    UserDeliveryPlan,
)
from app.infrastructure.database.models import Post, User


class TestSelectPostsForDeliveryUseCase:
    """Test SelectPostsForDeliveryUseCase functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def use_case(self, mock_db_session):
        """Create use case instance."""
        return SelectPostsForDeliveryUseCase(mock_db_session)

    @pytest.fixture
    def sample_post(self):
        """Create sample post for testing."""
        return Post(
            hn_id=12345,
            title="Test Post Title",
            author="test_author",
            url="https://example.com/article",
            type="story",
            score=100,
            comment_count=50,
            created_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            summary="This is a test summary of the post.",
            is_dead=False,
            is_deleted=False,
            is_crawl_success=True,
        )

    @pytest.fixture
    def sample_user_never_delivered(self):
        """Create user who has never been delivered to."""
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "test_user"
        user.status = "active"
        user.last_delivered_at = None
        user.delivery_style = "detail-summary"
        user.interests = ["python", "databases"]
        return user

    @pytest.fixture
    def sample_user_previously_delivered(self):
        """Create user who has been delivered to before."""
        user = MagicMock(spec=User)
        user.id = 2
        user.username = "test_user_2"
        user.status = "active"
        user.last_delivered_at = datetime.utcnow() - timedelta(days=1)
        user.delivery_style = "detail-summary"
        user.interests = ["javascript", "web"]
        return user

    def _setup_mock_execute(self, mock_db_session, return_value):
        """Helper to setup mock execute with proper structure."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = return_value

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_db_session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_use_case_initialization(self, use_case, mock_db_session):
        """Test use case initialization."""
        assert use_case.db_session == mock_db_session

    @pytest.mark.asyncio
    async def test_select_posts_for_user_never_delivered(
        self, use_case, mock_db_session, sample_user_never_delivered, sample_post
    ):
        """Test selecting posts for a user who was never delivered to.

        Should select the latest post regardless of time.
        """
        self._setup_mock_execute(mock_db_session, [sample_post])

        # Execute
        plan = await use_case.select_posts_for_user(sample_user_never_delivered)

        # Verify
        assert isinstance(plan, UserDeliveryPlan)
        assert plan.user_id == 1
        assert len(plan.posts) == 1
        assert plan.posts[0].hn_id == 12345
        assert plan.delivery_count == 1
        assert plan.batch_id is not None

        # Verify query was called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_posts_for_user_previously_delivered(
        self, use_case, mock_db_session, sample_user_previously_delivered, sample_post
    ):
        """Test selecting posts for a user who was previously delivered to.

        Should select posts created after last_delivered_at.
        """
        self._setup_mock_execute(mock_db_session, [sample_post])

        # Execute
        plan = await use_case.select_posts_for_user(
            sample_user_previously_delivered, max_posts=10
        )

        # Verify
        assert isinstance(plan, UserDeliveryPlan)
        assert plan.user_id == 2
        assert len(plan.posts) == 1
        assert plan.delivery_count == 1

        # Verify execute was called
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_posts_multiple_posts(
        self, use_case, mock_db_session, sample_user_never_delivered
    ):
        """Test selecting multiple posts for a user."""
        # Create multiple posts
        posts = [
            Post(
                hn_id=12345 + i,
                title=f"Post {i}",
                author="author",
                url=f"https://example.com/{i}",
                type="story",
                score=100 - i * 10,
                comment_count=50,
                created_at=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                summary=f"Summary {i}",
                is_dead=False,
                is_deleted=False,
                is_crawl_success=True,
            )
            for i in range(5)
        ]

        self._setup_mock_execute(mock_db_session, posts)

        # Execute
        plan = await use_case.select_posts_for_user(
            sample_user_never_delivered, max_posts=10
        )

        # Verify
        assert len(plan.posts) == 5
        assert plan.delivery_count == 5
        for i, post in enumerate(plan.posts):
            assert post.hn_id == 12345 + i

    @pytest.mark.asyncio
    async def test_select_posts_no_posts_found(
        self, use_case, mock_db_session, sample_user_never_delivered
    ):
        """Test selecting posts when no posts match criteria."""
        self._setup_mock_execute(mock_db_session, [])

        # Execute
        plan = await use_case.select_posts_for_user(sample_user_never_delivered)

        # Verify
        assert plan.user_id == 1
        assert len(plan.posts) == 0
        assert plan.delivery_count == 0

    @pytest.mark.asyncio
    async def test_select_posts_respects_max_posts(
        self, use_case, mock_db_session, sample_user_never_delivered
    ):
        """Test that max_posts parameter is respected."""
        # Create 20 posts but only return 10
        posts = [
            Post(
                hn_id=12345 + i,
                title=f"Post {i}",
                author="author",
                url=f"https://example.com/{i}",
                type="story",
                score=100,
                comment_count=50,
                created_at=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                summary=f"Summary {i}",
                is_dead=False,
                is_deleted=False,
                is_crawl_success=True,
            )
            for i in range(10)
        ]

        self._setup_mock_execute(mock_db_session, posts)

        # Execute with max_posts=10
        plan = await use_case.select_posts_for_user(
            sample_user_never_delivered, max_posts=10
        )

        # Verify only 10 posts returned
        assert len(plan.posts) == 10
        assert plan.delivery_count == 10

    @pytest.mark.asyncio
    async def test_select_posts_for_all_active_users(
        self, use_case, mock_db_session, sample_user_never_delivered, sample_post
    ):
        """Test selecting posts for all active users."""
        # Setup first call for users query
        users_scalars = MagicMock()
        users_scalars.all.return_value = [sample_user_never_delivered]
        users_result = MagicMock()
        users_result.scalars.return_value = users_scalars

        # Setup second call for posts query
        posts_scalars = MagicMock()
        posts_scalars.all.return_value = [sample_post]
        posts_result = MagicMock()
        posts_result.scalars.return_value = posts_scalars

        mock_db_session.execute = AsyncMock(
            side_effect=[users_result, posts_result]
        )

        # Execute
        plans = await use_case.select_posts_for_all_active_users(max_posts_per_user=10)

        # Verify
        assert len(plans) == 1
        assert isinstance(plans[0], UserDeliveryPlan)
        assert plans[0].user_id == 1
        assert len(plans[0].posts) == 1

    @pytest.mark.asyncio
    async def test_select_posts_for_all_active_users_skip_user_ids(
        self, use_case, mock_db_session, sample_user_never_delivered
    ):
        """Test selecting posts for all users while skipping some."""
        # Create multiple users
        users = [
            sample_user_never_delivered,  # id=1
            MagicMock(spec=User, id=2, status="active", last_delivered_at=None),
            MagicMock(spec=User, id=3, status="active", last_delivered_at=None),
        ]

        # Setup first call for users query
        users_scalars = MagicMock()
        users_scalars.all.return_value = users
        users_result = MagicMock()
        users_result.scalars.return_value = users_scalars

        # Setup calls for posts query (return empty for efficiency)
        posts_scalars = MagicMock()
        posts_scalars.all.return_value = []
        posts_result = MagicMock()
        posts_result.scalars.return_value = posts_scalars

        mock_db_session.execute = AsyncMock(
            side_effect=[users_result, posts_result, posts_result]
        )

        # Execute, skipping user with id=2
        plans = await use_case.select_posts_for_all_active_users(
            max_posts_per_user=10, skip_user_ids=[2]
        )

        # Verify only users 1 and 3 are processed (2 is skipped)
        assert len(plans) == 2
        user_ids = [p.user_id for p in plans]
        assert 1 in user_ids
        assert 3 in user_ids
        assert 2 not in user_ids

    @pytest.mark.asyncio
    async def test_select_posts_for_all_active_users_empty(self, use_case, mock_db_session):
        """Test selecting posts when no active users exist."""
        # Setup mock for empty users result
        users_scalars = MagicMock()
        users_scalars.all.return_value = []
        users_result = MagicMock()
        users_result.scalars.return_value = users_scalars

        mock_db_session.execute = AsyncMock(return_value=users_result)

        # Execute
        plans = await use_case.select_posts_for_all_active_users(max_posts_per_user=10)

        # Verify
        assert len(plans) == 0

    @pytest.mark.asyncio
    async def test_filter_by_interests_with_matching_keywords(
        self, use_case, sample_post
    ):
        """Test filtering posts by matching interests."""
        # Create posts with relevant content
        posts = [
            MagicMock(
                spec=Post,
                id=1,
                title="Python Best Practices",
                summary="Guide to writing Python code",
            ),
            MagicMock(
                spec=Post,
                id=2,
                title="JavaScript Async Patterns",
                summary="Mastering async in JS",
            ),
            MagicMock(
                spec=Post,
                id=3,
                title="Database Optimization",
                summary="Making databases faster with indexes",
            ),
        ]

        interests = ["python", "database"]

        # Execute
        filtered = await use_case.filter_by_interests(posts, interests)

        # Verify - should match posts 1 and 3
        assert len(filtered) == 2
        filtered_ids = [p.id for p in filtered]
        assert 1 in filtered_ids
        assert 3 in filtered_ids
        assert 2 not in filtered_ids

    @pytest.mark.asyncio
    async def test_filter_by_interests_no_matches(self, use_case):
        """Test filtering posts when interests don't match."""
        posts = [
            MagicMock(
                spec=Post,
                id=1,
                title="Python Basics",
                summary="Learning Python",
            ),
            MagicMock(
                spec=Post,
                id=2,
                title="JavaScript Advanced",
                summary="Advanced JS techniques",
            ),
        ]

        interests = ["rust", "golang"]

        # Execute
        filtered = await use_case.filter_by_interests(posts, interests)

        # Verify
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_filter_by_interests_empty_interests(self, use_case):
        """Test filtering with empty interests returns all posts."""
        posts = [
            MagicMock(spec=Post, id=1, title="Post 1", summary="Summary 1"),
            MagicMock(spec=Post, id=2, title="Post 2", summary="Summary 2"),
        ]

        interests = []

        # Execute
        filtered = await use_case.filter_by_interests(posts, interests)

        # Verify - all posts returned when no interests specified
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_filter_by_interests_case_insensitive(self, use_case):
        """Test that interest filtering is case-insensitive."""
        posts = [
            MagicMock(
                spec=Post,
                id=1,
                title="PYTHON Programming Guide",
                summary="Learning python language",
            ),
        ]

        interests = ["Python", "PYTHON", "python"]

        # Execute
        filtered = await use_case.filter_by_interests(posts, interests)

        # Verify - should match despite case differences
        assert len(filtered) == 1
        assert filtered[0].id == 1

    @pytest.mark.asyncio
    async def test_select_posts_sorts_by_score(
        self, use_case, mock_db_session, sample_user_never_delivered
    ):
        """Test that selected posts are sorted by score (highest first)."""
        # Create posts with different scores
        posts = [
            MagicMock(spec=Post, id=1, score=50),
            MagicMock(spec=Post, id=2, score=100),
            MagicMock(spec=Post, id=3, score=75),
        ]

        # Database should return posts in score order (highest to lowest)
        self._setup_mock_execute(mock_db_session, [posts[1], posts[2], posts[0]])

        # Execute
        plan = await use_case.select_posts_for_user(sample_user_never_delivered)

        # Verify posts are in score order
        assert len(plan.posts) == 3
        # Assuming database returns them in correct order
        assert plan.posts[0].score == 100
        assert plan.posts[1].score == 75
        assert plan.posts[2].score == 50

    @pytest.mark.asyncio
    async def test_user_delivery_plan_repr(self):
        """Test UserDeliveryPlan string representation."""
        plan = UserDeliveryPlan(
            user_id=1,
            posts=[],
            batch_id="test-batch-123",
            delivery_count=5,
        )

        repr_str = repr(plan)

        # Verify repr contains key information
        assert "user_id=1" in repr_str
        assert "batch_id=test-batch-123" in repr_str
        assert "posts=5" in repr_str

    @pytest.mark.asyncio
    async def test_select_posts_for_user_with_custom_max_posts(
        self, use_case, mock_db_session, sample_user_previously_delivered
    ):
        """Test selecting posts with custom max_posts limit."""
        posts = [MagicMock(spec=Post, id=i, hn_id=12345+i) for i in range(5)]

        self._setup_mock_execute(mock_db_session, posts)

        # Execute with max_posts=5
        plan = await use_case.select_posts_for_user(
            sample_user_previously_delivered, max_posts=5
        )

        # Verify
        assert plan.delivery_count == 5
        assert len(plan.posts) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
