"""PostgreSQL implementation of Post repository."""

from datetime import datetime
from typing import List, Optional, Set
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import PostRepository
from app.domain.entities import Post as DomainPost
from app.infrastructure.database.models import Post as PostModel


class PostgresPostRepository(PostRepository):
    """PostgreSQL implementation of PostRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def save(self, post: DomainPost) -> DomainPost:
        """Save a single post to the database.

        Args:
            post: Domain Post entity

        Returns:
            Saved Post entity with updated fields
        """
        # Convert domain entity to ORM model
        post_model = PostModel(
            id=uuid4() if not hasattr(post, 'id') else post.id,
            hn_id=int(post.hn_id),
            type=post.post_type,
            title=post.title,
            author=post.author,
            url=post.url,
            score=post.points,
            comment_count=post.num_comments,
            created_at=post.created_at,
            collected_at=datetime.utcnow(),
        )

        self.session.add(post_model)
        await self.session.commit()
        await self.session.refresh(post_model)

        # Convert back to domain entity
        return self._to_domain(post_model)

    async def save_batch(self, posts: List[DomainPost]) -> List[DomainPost]:
        """Save multiple posts to the database.

        Args:
            posts: List of domain Post entities

        Returns:
            List of saved Post entities
        """
        post_models = []
        for post in posts:
            post_model = PostModel(
                id=uuid4(),
                hn_id=int(post.hn_id),
                type=post.post_type,
                title=post.title,
                author=post.author,
                url=post.url,
                score=post.points,
                comment_count=post.num_comments,
                created_at=post.created_at,
                collected_at=datetime.utcnow(),
            )
            post_models.append(post_model)

        self.session.add_all(post_models)
        await self.session.commit()

        # Refresh all models
        for model in post_models:
            await self.session.refresh(model)

        return [self._to_domain(model) for model in post_models]

    async def find_by_id(self, post_id: str) -> Optional[DomainPost]:
        """Find post by ID.

        Args:
            post_id: Post ID (UUID)

        Returns:
            Post entity if found, None otherwise
        """
        stmt = select(PostModel).where(PostModel.id == post_id)
        result = await self.session.execute(stmt)
        post_model = result.scalar_one_or_none()

        return self._to_domain(post_model) if post_model else None

    async def find_by_hn_id(self, hn_id: int) -> Optional[DomainPost]:
        """Find post by HackerNews ID.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Post entity if found, None otherwise
        """
        stmt = select(PostModel).where(PostModel.hn_id == hn_id)
        result = await self.session.execute(stmt)
        post_model = result.scalar_one_or_none()

        return self._to_domain(post_model) if post_model else None

    async def find_existing_hn_ids(self, hn_ids: List[int]) -> Set[int]:
        """Find which HackerNews IDs already exist in database.

        Args:
            hn_ids: List of HackerNews post IDs to check

        Returns:
            Set of IDs that already exist
        """
        if not hn_ids:
            return set()

        stmt = select(PostModel.hn_id).where(PostModel.hn_id.in_(hn_ids))
        result = await self.session.execute(stmt)
        existing_ids = result.scalars().all()

        return set(existing_ids)

    async def find_by_date(self, date: str) -> List[DomainPost]:
        """Find posts collected on a specific date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            List of Post entities
        """
        # Parse date string to datetime range
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = datetime.strptime(date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )

        stmt = (
            select(PostModel)
            .where(PostModel.collected_at >= start_date)
            .where(PostModel.collected_at <= end_date)
            .order_by(PostModel.score.desc())
        )

        result = await self.session.execute(stmt)
        post_models = result.scalars().all()

        return [self._to_domain(model) for model in post_models]

    async def fetch_uncrawled_posts(self, limit: int = 200) -> List[DomainPost]:
        """Fetch posts that need crawling (never crawled or failed with retries remaining).

        Args:
            limit: Maximum number of posts to return

        Returns:
            List of Post entities needing crawl
        """
        stmt = (
            select(PostModel)
            .where(
                or_(
                    PostModel.is_crawl_success.is_(None),
                    and_(
                        PostModel.is_crawl_success == False,  # noqa: E712
                        PostModel.crawl_retry_count < 3,
                    ),
                )
            )
            .order_by(PostModel.collected_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        post_models = result.scalars().all()

        return [self._to_domain(model) for model in post_models]

    async def update_crawl_status(
        self,
        hn_id: int,
        is_success: bool,
        has_html: bool = False,
        has_text: bool = False,
        has_markdown: bool = False,
        content_length: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update crawl status for a post.

        Args:
            hn_id: HackerNews post ID
            is_success: Whether crawl was successful
            has_html: Whether HTML content exists
            has_text: Whether text content exists
            has_markdown: Whether markdown content exists
            content_length: Length of extracted content
            error: Error message if failed
        """
        stmt = (
            update(PostModel)
            .where(PostModel.hn_id == hn_id)
            .values(
                is_crawl_success=is_success,
                has_html=has_html,
                has_text=has_text,
                has_markdown=has_markdown,
                content_length=content_length,
                crawl_error=error,
                crawled_at=datetime.utcnow(),
                crawl_retry_count=PostModel.crawl_retry_count + 1
                if not is_success
                else 0,
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

    def _to_domain(self, model: PostModel) -> DomainPost:
        """Convert ORM model to domain entity.

        Args:
            model: SQLAlchemy ORM model

        Returns:
            Domain Post entity
        """
        return DomainPost(
            id=str(model.id),
            hn_id=str(model.hn_id),
            title=model.title,
            author=model.author,
            url=model.url,
            points=model.score,
            num_comments=model.comment_count,
            created_at=model.created_at,
            collected_at=model.collected_at,
            post_type=model.type,
            content=None,  # Content stored in RocksDB
            raw_content=None,
            summary=model.summary,
        )
