"""Summarization use cases - Business logic for content summarization.

These use cases orchestrate the summarization of post content using OpenAI Agents SDK.

Story 2.3: Basic Summarization Pipeline
- Reads unsummarized posts from PostgreSQL
- Retrieves markdown content from RocksDB
- Generates summaries using SummarizationAgent
- Stores summaries back to PostgreSQL with token tracking
"""

import logging
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import (
    PostRepository,
)
from app.domain.entities import Post
from app.infrastructure.agents import SummaryOutput, summarize_post
from app.infrastructure.database.models import Post as PostModel
from app.infrastructure.database.models import Summary
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


class SummarizationPipeline:
    """Pipeline for summarizing posts using OpenAI Agents SDK."""

    def __init__(
        self,
        db_session: AsyncSession,
        rocksdb_store: RocksDBContentStore | None = None,
        prompt_type: str = "basic",
        skip_existing: bool = True,
    ):
        """Initialize summarization pipeline.

        Args:
            db_session: Async database session for PostgreSQL
            rocksdb_store: RocksDB content store (creates new if not provided)
            prompt_type: Prompt variant (basic, technical, business, concise, personalized)
            skip_existing: Whether to skip posts that already have summaries
        """
        self.db_session = db_session
        # Summarization only reads content; open RocksDB in read-only mode to avoid lock contention
        self.rocksdb_store = rocksdb_store or RocksDBContentStore(read_only=True)
        self.prompt_type = prompt_type
        self.skip_existing = skip_existing

    async def run(
        self, max_posts: int = 100, user_id: int | None = None
    ) -> dict:
        """Run the summarization pipeline.

        Args:
            max_posts: Maximum number of posts to summarize
            user_id: Optional user_id for token tracking and billing

        Returns:
            Dictionary with pipeline statistics
        """
        logger.info(
            f"Starting summarization pipeline (prompt: {self.prompt_type}, "
            f"max_posts: {max_posts})"
        )

        stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0,
            "start_time": datetime.utcnow(),
        }

        try:
            # Fetch posts needing summarization
            posts = await self._fetch_unsummarized_posts(max_posts)
            logger.info(f"Found {len(posts)} posts needing summarization")

            if not posts:
                logger.info("No posts to summarize")
                stats["end_time"] = datetime.utcnow()
                stats["duration_seconds"] = 0.0
                return stats

            # Process each post
            for post in posts:
                try:
                    # Skip if already summarized
                    if self.skip_existing and post.summary:
                        logger.info(f"Skipping post {post.hn_id} (already summarized)")
                        stats["skipped"] += 1
                        continue

                    # Retrieve markdown content from RocksDB
                    markdown = await self.rocksdb_store.get_markdown_content(
                        int(post.hn_id)
                    )

                    if not markdown:
                        logger.warning(
                            f"No markdown content for post {post.hn_id}, skipping"
                        )
                        stats["skipped"] += 1
                        continue

                    # Generate summary using OpenAI Agents SDK
                    logger.info(
                        f"Summarizing post {post.hn_id}: {post.title[:50]}..."
                    )
                    summary_output = await summarize_post(
                        markdown_content=markdown,
                        user_id=user_id,
                        prompt_type=self.prompt_type,
                        db_session=self.db_session,
                    )

                    # Save summary to database
                    await self._save_summary_to_db(post, summary_output)

                    # Update statistics
                    stats["succeeded"] += 1
                    stats["total_tokens"] += summary_output.token_count or 0
                    stats["total_cost"] += summary_output.cost_usd or 0.0

                    logger.info(
                        f"Summary saved for {post.hn_id} "
                        f"(tokens: {summary_output.token_count}, "
                        f"cost: ${summary_output.cost_usd:.4f})"
                    )

                except Exception as e:
                    logger.error(
                        f"Error summarizing post {post.hn_id}: {str(e)}", exc_info=True
                    )
                    stats["failed"] += 1
                    stats["errors"].append(
                        {
                            "hn_id": int(post.hn_id),
                            "title": post.title[:50] if post.title else "Unknown",
                            "error": str(e)[:100],
                        }
                    )

                finally:
                    stats["processed"] += 1

        except Exception as e:
            logger.error(f"Fatal error in summarization pipeline: {str(e)}", exc_info=True)
            raise

        # Calculate timing
        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()
        stats["avg_time_per_post"] = (
            stats["duration_seconds"] / stats["succeeded"]
            if stats["succeeded"] > 0
            else 0.0
        )

        # Log summary
        self._log_summary(stats)

        return stats

    async def _fetch_unsummarized_posts(self, max_posts: int) -> list[PostModel]:
        """Fetch posts that need summarization.

        Filters for posts that:
        - Have markdown content (has_markdown = True)
        - Don't have a summary yet (summary IS NULL)
        - Were successfully crawled (is_crawl_success = True)
        - Orders by score (most relevant first)

        Args:
            max_posts: Maximum number of posts to fetch

        Returns:
            List of PostModel objects
        """
        stmt = (
            select(PostModel)
            .where(
                and_(
                    PostModel.has_markdown == True,  # noqa: E712
                    PostModel.summary.is_(None),
                    PostModel.is_crawl_success == True,  # noqa: E712
                )
            )
            .order_by(PostModel.score.desc())
            .limit(max_posts)
        )

        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def _save_summary_to_db(
        self, post: PostModel, summary_output: SummaryOutput
    ) -> None:
        """Save summary to both posts and summaries tables.

        Args:
            post: Post model from database
            summary_output: Generated summary with metadata
        """
        # Update post's summary field (denormalized for quick access)
        post.summary = summary_output.summary_text
        post.summarized_at = datetime.utcnow()
        self.db_session.add(post)

        # Also save to Summary table for multi-prompt/multi-user support
        # This enables personalized summaries and A/B testing different prompts
        summary_record = Summary(
            post_id=post.id,
            user_id=None,  # Null = shared/default summary
            prompt_type=self.prompt_type,
            summary_text=summary_output.summary_text,
            key_points=summary_output.key_points or [],
            token_count=summary_output.token_count,
            cost_usd=summary_output.cost_usd,
        )
        self.db_session.add(summary_record)

        await self.db_session.commit()

    def _log_summary(self, stats: dict) -> None:
        """Log pipeline completion summary.

        Args:
            stats: Statistics dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info("SUMMARIZATION PIPELINE SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total processed: {stats['processed']}")
        logger.info(f"Succeeded: {stats['succeeded']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Duration: {stats['duration_seconds']:.1f}s")
        if stats["succeeded"] > 0:
            logger.info(f"Avg per post: {stats['avg_time_per_post']:.1f}s")
            logger.info(f"Total tokens: {stats['total_tokens']}")
            logger.info(f"Total cost: ${stats['total_cost']:.4f}")
        if stats["errors"]:
            logger.warning(f"Errors: {len(stats['errors'])} posts failed")
            for error in stats["errors"][:3]:  # Show first 3 errors
                logger.warning(f"  - Post {error['hn_id']}: {error['error']}")
        logger.info(f"{'='*60}\n")


class SummarizePostsUseCase:
    """Legacy use case for backward compatibility."""

    def __init__(
        self,
        post_repository: PostRepository,
        db_session: AsyncSession,
    ):
        """Initialize the use case.

        Args:
            post_repository: Repository for post persistence
            db_session: Database session for summarization pipeline
        """
        self.post_repository = post_repository
        self.db_session = db_session

    async def execute(
        self,
        posts: list[Post] | None = None,
        date: str | None = None,
        prompt_type: str = "basic",
    ) -> dict:
        """Summarize posts using new OpenAI Agents SDK.

        Args:
            posts: Optional list of posts to summarize
            date: Optional date to fetch posts
            prompt_type: Prompt variant to use

        Returns:
            Statistics dictionary

        Raises:
            ValueError: If neither posts nor date is provided
        """
        if posts is None and date is None:
            raise ValueError("Either posts or date must be provided")

        # Create pipeline and run
        pipeline = SummarizationPipeline(
            db_session=self.db_session,
            prompt_type=prompt_type,
        )

        return await pipeline.run(max_posts=100)


class SummarizeSinglePostUseCase:
    """Legacy use case for backward compatibility."""

    def __init__(
        self,
        post_repository: PostRepository,
        db_session: AsyncSession,
    ):
        """Initialize the use case.

        Args:
            post_repository: Repository for post persistence
            db_session: Database session for summarization
        """
        self.post_repository = post_repository
        self.db_session = db_session

    async def execute(
        self, post_id: str, prompt_type: str = "basic"
    ) -> dict | None:
        """Summarize a single post by ID.

        Args:
            post_id: ID of the post to summarize
            prompt_type: Prompt variant to use

        Returns:
            Summary output dictionary or None if post not found
        """
        logger.info(f"Fetching post {post_id} for summarization")

        # Fetch post from database
        stmt = select(PostModel).where(PostModel.id == post_id)
        result = await self.db_session.execute(stmt)
        post = result.scalar_one_or_none()

        if not post:
            logger.warning(f"Post {post_id} not found")
            return None

        # Skip if already summarized
        if post.summary:
            logger.info(f"Post {post_id} already has a summary")
            return {"summary": post.summary, "new": False}

        # Retrieve content from RocksDB
        rocksdb_store = RocksDBContentStore()
        markdown = await rocksdb_store.get_markdown_content(int(post.hn_id))

        if not markdown:
            logger.warning(f"No markdown content for post {post_id}")
            return None

        # Generate summary
        try:
            logger.info(f"Generating summary for post {post_id}")
            summary_output = await summarize_post(
                markdown_content=markdown,
                prompt_type=prompt_type,
                db_session=self.db_session,
            )

            # Save to database
            post.summary = summary_output.summary_text
            post.summarized_at = datetime.utcnow()
            self.db_session.add(post)

            summary_record = Summary(
                post_id=post.id,
                user_id=None,
                prompt_type=prompt_type,
                summary_text=summary_output.summary_text,
                key_points=summary_output.key_points or [],
                token_count=summary_output.token_count,
                cost_usd=summary_output.cost_usd,
            )
            self.db_session.add(summary_record)
            await self.db_session.commit()

            logger.info(f"Successfully summarized post {post_id}")
            return {
                "summary": summary_output.summary_text,
                "new": True,
                "tokens": summary_output.token_count,
                "cost": float(summary_output.cost_usd or 0),
            }

        except Exception as e:
            logger.error(f"Error summarizing post {post_id}: {e}")
            raise
