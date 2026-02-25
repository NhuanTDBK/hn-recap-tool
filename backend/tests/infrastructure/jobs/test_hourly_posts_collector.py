"""Tests for hourly posts collector job."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.infrastructure.jobs.hourly_posts_collector import HourlyPostsCollectorJob
from app.domain.entities import Post


class TestHourlyPostsCollector:
    """Test HourlyPostsCollectorJob functionality."""

    @pytest.fixture
    def mock_post_repository(self):
        """Create mock post repository."""
        mock = AsyncMock()
        mock.find_by_hn_id = AsyncMock(return_value=None)
        mock.save_batch = AsyncMock()
        return mock

    @pytest.fixture
    def mock_hn_client(self):
        """Create mock HN client."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def collector(self, mock_post_repository, mock_hn_client):
        """Create collector instance."""
        return HourlyPostsCollectorJob(
            post_repository=mock_post_repository,
            hn_client=mock_hn_client,
            score_threshold=50,
            limit=100,
        )

    @pytest.mark.asyncio
    async def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert collector.score_threshold == 50
        assert collector.limit == 100
        assert collector.stats["posts_fetched"] == 0
        assert collector.stats["posts_saved"] == 0

    @pytest.mark.asyncio
    async def test_fetch_top_stories(self, collector, mock_hn_client):
        """Test fetching top stories from HN."""
        mock_stories = [
            {"id": 1, "score": 100, "title": "Test 1"},
            {"id": 2, "score": 60, "title": "Test 2"},
            {"id": 3, "score": 40, "title": "Test 3"},  # Below threshold
        ]
        mock_hn_client.fetch_front_page = AsyncMock(return_value=mock_stories)

        stories = await collector._fetch_top_stories()

        # Should filter by threshold
        assert len(stories) == 2
        assert all(s["score"] >= 50 for s in stories)
        mock_hn_client.fetch_front_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_transform_story_to_post(self, collector):
        """Test transforming HN story to Post entity."""
        story = {
            "id": 12345,
            "title": "Test Article",
            "by": "test_author",
            "url": "https://example.com/article",
            "score": 100,
            "kids": ["1", "2", "3"],
            "time": 1234567890,
            "type": "story",
        }

        post = collector._transform_story_to_post(story)

        assert isinstance(post, Post)
        assert post.hn_id == 12345
        assert post.title == "Test Article"
        assert post.author == "test_author"
        assert post.points == 100
        assert post.num_comments == 3

    @pytest.mark.asyncio
    async def test_collect_top_posts_success(
        self, collector, mock_post_repository, mock_hn_client
    ):
        """Test successful collection of posts."""
        # Setup mock data
        mock_stories = [
            {
                "id": 1,
                "score": 100,
                "title": "Test 1",
                "by": "author1",
                "url": "https://example1.com",
                "kids": ["1", "2"],
                "time": 1234567890,
                "type": "story",
            },
            {
                "id": 2,
                "score": 80,
                "title": "Test 2",
                "by": "author2",
                "url": "https://example2.com",
                "kids": ["3"],
                "time": 1234567891,
                "type": "story",
            },
        ]

        mock_hn_client.fetch_front_page = AsyncMock(return_value=mock_stories)
        mock_post_repository.find_by_hn_id = AsyncMock(return_value=None)

        # Mock save_batch to return Post objects
        mock_posts = [
            Post(
                hn_id=story["id"],
                title=story["title"],
                author=story["by"],
                url=story["url"],
                points=story["score"],
                num_comments=len(story.get("kids", [])),
                post_type="story",
                created_at=datetime.fromtimestamp(story["time"]),
                collected_at=datetime.utcnow(),
            )
            for story in mock_stories
        ]
        mock_post_repository.save_batch = AsyncMock(return_value=mock_posts)

        # Run collection
        stats = await collector.collect_top_posts()

        # Verify results
        assert stats["posts_fetched"] == 2
        assert stats["posts_saved"] == 2
        assert stats["duplicates_skipped"] == 0
        assert stats["errors"] == 0
        mock_post_repository.save_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_top_posts_with_duplicates(
        self, collector, mock_post_repository, mock_hn_client
    ):
        """Test collection with duplicate posts."""
        mock_stories = [
            {
                "id": 1,
                "score": 100,
                "title": "Test 1",
                "by": "author1",
                "url": "https://example1.com",
                "kids": [],
                "time": 1234567890,
                "type": "story",
            },
            {
                "id": 2,
                "score": 80,
                "title": "Test 2",
                "by": "author2",
                "url": "https://example2.com",
                "kids": [],
                "time": 1234567891,
                "type": "story",
            },
        ]

        mock_hn_client.fetch_front_page = AsyncMock(return_value=mock_stories)

        # First story exists, second doesn't
        existing_post = Post(
            hn_id=1,
            title="Test 1",
            author="author1",
            url="https://example1.com",
            points=100,
            num_comments=0,
            post_type="story",
            created_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
        )
        mock_post_repository.find_by_hn_id = AsyncMock()
        mock_post_repository.find_by_hn_id.side_effect = [
            existing_post,  # First call: post exists
            None,  # Second call: post doesn't exist
        ]

        # Mock save_batch
        new_post = Post(
            hn_id=2,
            title="Test 2",
            author="author2",
            url="https://example2.com",
            points=80,
            num_comments=0,
            post_type="story",
            created_at=datetime.fromtimestamp(1234567891),
            collected_at=datetime.utcnow(),
        )
        mock_post_repository.save_batch = AsyncMock(return_value=[new_post])

        # Run collection
        stats = await collector.collect_top_posts()

        # Verify results
        assert stats["posts_fetched"] == 2
        assert stats["posts_saved"] == 1  # Only 1 new post saved
        assert stats["duplicates_skipped"] == 1
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_collect_top_posts_empty_results(
        self, collector, mock_post_repository, mock_hn_client
    ):
        """Test collection with no posts from HN."""
        mock_hn_client.fetch_front_page = AsyncMock(return_value=[])

        stats = await collector.collect_top_posts()

        assert stats["posts_fetched"] == 0
        assert stats["posts_saved"] == 0
        mock_post_repository.save_batch.assert_not_called()

    def test_get_stats(self, collector):
        """Test getting collection statistics."""
        collector.stats["posts_saved"] = 5
        stats = collector.get_stats()

        assert stats["posts_saved"] == 5
        assert "last_run" in stats

    @pytest.mark.asyncio
    async def test_run_collection_entry_point(
        self, collector, mock_post_repository, mock_hn_client
    ):
        """Test run_collection entry point for scheduler."""
        mock_hn_client.fetch_front_page = AsyncMock(return_value=[])

        stats = await collector.run_collection()

        assert "posts_fetched" in stats
        assert "posts_saved" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
