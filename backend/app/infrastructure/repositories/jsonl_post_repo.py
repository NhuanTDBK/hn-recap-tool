"""JSONL implementation of PostRepository with date-partitioned storage."""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging

from app.domain.entities import Post
from app.application.interfaces import PostRepository
from app.infrastructure.repositories.jsonl_helpers import (
    read_jsonl,
    write_jsonl,
    write_jsonl_batch,
    find_by_field,
    filter_by_field
)

logger = logging.getLogger(__name__)


class JSONLPostRepository(PostRepository):
    """Post repository using date-partitioned JSONL files."""

    def __init__(self, data_dir: str):
        """Initialize repository.

        Args:
            data_dir: Base directory for data storage (e.g., ../data)
        """
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        logger.info(f"Initialized JSONLPostRepository with data_dir: {data_dir}")

    def _get_file_path(self, date: str) -> str:
        """Get file path for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Path to JSONL file for that date
        """
        return str(self.raw_dir / f"{date}-posts.jsonl")

    def _extract_date(self, post: Post) -> str:
        """Extract date from post for file partitioning.

        Args:
            post: Post entity

        Returns:
            Date string in YYYY-MM-DD format
        """
        return post.collected_at.strftime('%Y-%m-%d')

    async def save(self, post: Post) -> Post:
        """Save a post to date-partitioned storage.

        Args:
            post: Post entity to save

        Returns:
            Saved post
        """
        date = self._extract_date(post)
        file_path = self._get_file_path(date)

        post_data = post.model_dump()
        write_jsonl(file_path, post_data, append=True)

        logger.info(f"Saved post {post.hn_id} to {file_path}")
        return post

    async def save_batch(self, posts: List[Post]) -> List[Post]:
        """Save multiple posts in batch, grouped by date.

        Args:
            posts: List of post entities to save

        Returns:
            List of saved posts
        """
        # Group posts by date
        posts_by_date = {}
        for post in posts:
            date = self._extract_date(post)
            if date not in posts_by_date:
                posts_by_date[date] = []
            posts_by_date[date].append(post)

        # Save each date group
        for date, date_posts in posts_by_date.items():
            file_path = self._get_file_path(date)
            post_data_list = [p.model_dump() for p in date_posts]
            write_jsonl_batch(file_path, post_data_list, append=True)
            logger.info(f"Saved {len(date_posts)} posts to {file_path}")

        return posts

    async def find_by_id(self, post_id: str) -> Optional[Post]:
        """Find post by ID.

        Note: This requires scanning all date files. Consider adding an index for production.

        Args:
            post_id: Post's unique identifier

        Returns:
            Post if found, None otherwise
        """
        # Scan all post files in raw directory
        for file_path in sorted(self.raw_dir.glob("*-posts.jsonl"), reverse=True):
            record = find_by_field(str(file_path), "id", post_id)
            if record:
                return Post(**record)

        return None

    async def find_by_hn_id(self, hn_id: int) -> Optional[Post]:
        """Find post by HackerNews ID.

        Note: This requires scanning all date files.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Post if found, None otherwise
        """
        # Scan all post files in raw directory (most recent first)
        for file_path in sorted(self.raw_dir.glob("*-posts.jsonl"), reverse=True):
            record = find_by_field(str(file_path), "hn_id", hn_id)
            if record:
                return Post(**record)

        return None

    async def find_by_date(self, date: str) -> List[Post]:
        """Find all posts collected on a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of posts for that date
        """
        file_path = self._get_file_path(date)

        if not Path(file_path).exists():
            logger.warning(f"No posts file found for date: {date}")
            return []

        posts = []
        for record in read_jsonl(file_path):
            try:
                posts.append(Post(**record))
            except Exception as e:
                logger.error(f"Failed to parse post from {file_path}: {e}")
                continue

        logger.info(f"Found {len(posts)} posts for date {date}")
        return posts
