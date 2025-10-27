"""Data collection use cases - Collecting and processing HN data."""

from datetime import datetime
from typing import List
import logging

from app.domain.entities import Post, Comment, Digest
from app.domain.exceptions import (
    HNAPIError,
    ContentExtractionError,
    DigestAlreadyExistsError,
    EmptyDigestError
)
from app.application.interfaces import (
    PostRepository,
    CommentRepository,
    DigestRepository,
    HNService,
    ContentExtractor
)

logger = logging.getLogger(__name__)


class CollectPostsUseCase:
    """Use case for collecting HN front page posts."""

    def __init__(
        self,
        post_repo: PostRepository,
        hn_service: HNService
    ):
        self.post_repo = post_repo
        self.hn_service = hn_service

    async def execute(self, limit: int = 30) -> List[Post]:
        """Collect front page posts from HackerNews.

        Args:
            limit: Maximum number of posts to collect

        Returns:
            List of collected post entities

        Raises:
            HNAPIError: If HN API request fails
        """
        logger.info(f"Collecting {limit} posts from HN front page")

        # Fetch from HN API
        try:
            raw_posts = await self.hn_service.fetch_front_page(limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch posts from HN: {e}")
            raise HNAPIError(str(e))

        # Convert to domain entities
        posts = []
        collected_at = datetime.utcnow()

        for raw_post in raw_posts:
            try:
                post = Post(
                    hn_id=raw_post['objectID'],
                    title=raw_post['title'],
                    author=raw_post['author'],
                    points=raw_post.get('points', 0),
                    num_comments=raw_post.get('num_comments', 0),
                    created_at=datetime.fromisoformat(raw_post['created_at'].replace('Z', '+00:00')),
                    collected_at=collected_at,
                    url=raw_post.get('url'),
                    post_type=self._determine_post_type(raw_post)
                )
                posts.append(post)
            except Exception as e:
                logger.warning(f"Failed to parse post {raw_post.get('objectID')}: {e}")
                continue

        # Save to repository
        saved_posts = await self.post_repo.save_batch(posts)
        logger.info(f"Saved {len(saved_posts)} posts to storage")

        return saved_posts

    def _determine_post_type(self, raw_post: dict) -> str:
        """Determine post type from raw HN data."""
        title = raw_post.get('title', '').lower()
        if title.startswith('ask hn'):
            return 'ask'
        elif title.startswith('show hn'):
            return 'show'
        elif raw_post.get('url', '').endswith('/jobs'):
            return 'job'
        return 'story'


class ExtractContentUseCase:
    """Use case for extracting article content from URLs."""

    def __init__(
        self,
        post_repo: PostRepository,
        content_extractor: ContentExtractor
    ):
        self.post_repo = post_repo
        self.content_extractor = content_extractor

    async def execute(self, post_id: str) -> Post:
        """Extract and save article content for a post.

        Args:
            post_id: Post's unique identifier

        Returns:
            Updated post with extracted content

        Raises:
            PostNotFoundError: If post doesn't exist
            ContentExtractionError: If content extraction fails
        """
        # Find post
        post = await self.post_repo.find_by_id(post_id)
        if not post:
            from app.domain.exceptions import PostNotFoundError
            raise PostNotFoundError(post_id)

        # Skip if no URL
        if not post.has_external_url():
            logger.info(f"Post {post_id} has no external URL, skipping extraction")
            return post

        # Extract content
        try:
            content = await self.content_extractor.extract_content(post.url)
            if content:
                post.raw_content = content
                post.content = content[:500]  # Store preview
                logger.info(f"Extracted content for post {post_id}")
            else:
                logger.warning(f"No content extracted for post {post_id}")
        except Exception as e:
            logger.error(f"Content extraction failed for {post.url}: {e}")
            raise ContentExtractionError(post.url, str(e))

        # Update post
        updated_post = await self.post_repo.save(post)
        return updated_post


class CollectCommentsUseCase:
    """Use case for collecting comments for a post."""

    def __init__(
        self,
        comment_repo: CommentRepository,
        hn_service: HNService
    ):
        self.comment_repo = comment_repo
        self.hn_service = hn_service

    async def execute(self, post_id: str, hn_post_id: int, limit: int = 50) -> List[Comment]:
        """Collect comments for a specific HN post.

        Args:
            post_id: Our internal post ID
            hn_post_id: HackerNews post ID
            limit: Maximum number of comments to collect

        Returns:
            List of collected comment entities

        Raises:
            HNAPIError: If HN API request fails
        """
        logger.info(f"Collecting comments for HN post {hn_post_id}")

        # Fetch from HN API
        try:
            raw_comments = await self.hn_service.fetch_comments(hn_post_id, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch comments from HN: {e}")
            raise HNAPIError(str(e))

        # Convert to domain entities
        comments = []
        collected_at = datetime.utcnow()

        for raw_comment in raw_comments:
            try:
                comment = Comment(
                    hn_id=raw_comment['objectID'],
                    post_id=post_id,
                    author=raw_comment['author'],
                    text=raw_comment.get('comment_text', ''),
                    points=raw_comment.get('points', 0),
                    created_at=datetime.fromisoformat(raw_comment['created_at'].replace('Z', '+00:00')),
                    collected_at=collected_at,
                    parent_id=raw_comment.get('parent_id')
                )
                comments.append(comment)
            except Exception as e:
                logger.warning(f"Failed to parse comment {raw_comment.get('objectID')}: {e}")
                continue

        # Save to repository
        saved_comments = await self.comment_repo.save_batch(comments)
        logger.info(f"Saved {len(saved_comments)} comments to storage")

        return saved_comments


class CreateDigestUseCase:
    """Use case for creating a daily digest from collected posts."""

    def __init__(
        self,
        digest_repo: DigestRepository,
        post_repo: PostRepository
    ):
        self.digest_repo = digest_repo
        self.post_repo = post_repo

    async def execute(self, date: str) -> Digest:
        """Create a digest for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Created digest entity

        Raises:
            DigestAlreadyExistsError: If digest already exists for that date
            EmptyDigestError: If no posts were collected for that date
        """
        logger.info(f"Creating digest for {date}")

        # Check if digest already exists
        existing_digest = await self.digest_repo.find_by_date(date)
        if existing_digest:
            raise DigestAlreadyExistsError(date)

        # Get posts for the date
        posts = await self.post_repo.find_by_date(date)
        if not posts:
            raise EmptyDigestError(date)

        # Create digest
        digest = Digest(
            date=date,
            posts=posts,
            created_at=datetime.utcnow()
        )

        # Save digest
        saved_digest = await self.digest_repo.save(digest)
        logger.info(f"Created digest for {date} with {len(posts)} posts")

        return saved_digest
