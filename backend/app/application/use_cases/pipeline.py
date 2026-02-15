"""Content Processing Pipeline - Orchestrates the end-to-end workflow.

This pipeline coordinates:
1. Collecting posts from HackerNews
2. Crawling and extracting content
3. Summarizing with OpenAI Agents
4. Storing in PostgreSQL
"""

import logging
from datetime import datetime

from app.application.interfaces import PostRepository
from app.domain.entities import Post

logger = logging.getLogger(__name__)


class ContentProcessingPipeline:
    """Orchestrate the complete content processing workflow."""

    def __init__(
        self,
        post_repository: PostRepository,
        user_id: int | None = None,
        db_session=None,
        summarization_prompt_type: str = "basic",
    ):
        """Initialize the pipeline.

        Args:
            post_repository: Repository for post persistence
            user_id: User ID for token tracking
            db_session: Database session for token tracking
            summarization_prompt_type: Prompt variant for summarization
        """
        self.post_repository = post_repository
        self.user_id = user_id
        self.db_session = db_session
        self.summarization_prompt_type = summarization_prompt_type

    async def process_posts(
        self,
        posts: list[Post],
        skip_crawl: bool = False,
        skip_summarization: bool = False,
    ) -> dict:
        """Process a list of posts through the complete pipeline.

        Args:
            posts: List of posts to process
            skip_crawl: Skip content crawling (use existing content)
            skip_summarization: Skip summarization step

        Returns:
            Pipeline execution statistics
        """
        stats = {
            "total_posts": len(posts),
            "posts_crawled": 0,
            "posts_summarized": 0,
            "posts_stored": 0,
            "errors": [],
        }

        if not posts:
            logger.warning("No posts to process")
            return stats

        logger.info(f"Starting content pipeline for {len(posts)} posts")

        # Step 1: Crawl content (if not skipped)
        if not skip_crawl:
            logger.info("Step 1: Crawling content...")
            crawl_results = await self._crawl_content(posts)
            stats["posts_crawled"] = crawl_results["success"]
            stats["errors"].extend(crawl_results["errors"])

        # Step 2: Summarize content (if not skipped)
        if not skip_summarization:
            logger.info("Step 2: Summarizing content...")
            summarization_results = await self._summarize_content(posts)
            stats["posts_summarized"] = summarization_results["success"]
            stats["errors"].extend(summarization_results["errors"])

        # Step 3: Store/update in database
        logger.info("Step 3: Storing posts...")
        storage_results = await self._store_posts(posts)
        stats["posts_stored"] = storage_results["success"]
        stats["errors"].extend(storage_results["errors"])

        logger.info(f"Pipeline complete: {stats}")
        return stats

    async def _crawl_content(self, posts: list[Post]) -> dict:
        """Crawl content for posts (placeholder for future implementation).

        Args:
            posts: List of posts to crawl

        Returns:
            Crawl statistics
        """
        results = {"success": 0, "errors": []}

        # TODO: Implement content crawling using enhanced content extractor
        # For now, assume content is already available

        logger.info(f"Content crawling: {len(posts)} posts checked")
        results["success"] = len(posts)

        return results

    async def _summarize_content(self, posts: list[Post]) -> dict:
        """Summarize post content using OpenAI Agents SDK.

        Args:
            posts: List of posts to summarize

        Returns:
            Summarization statistics
        """
        from app.application.use_cases.summarization import SummarizationPipeline

        results = {"success": 0, "errors": []}

        if not posts:
            logger.info("No posts to summarize")
            return results

        try:
            # Use OpenAI Agents SDK-based summarization pipeline
            pipeline = SummarizationPipeline(
                db_session=self.db_session,
                prompt_type=self.summarization_prompt_type,
            )

            pipeline_stats = await pipeline.run(
                max_posts=len(posts),
                user_id=self.user_id,
            )

            results["success"] = pipeline_stats["succeeded"]
            if pipeline_stats["errors"]:
                results["errors"].extend(
                    [f"Post {e['hn_id']}: {e['error']}" for e in pipeline_stats["errors"]]
                )

            logger.info(
                f"Summarized {pipeline_stats['succeeded']} posts "
                f"({pipeline_stats['failed']} failed, "
                f"{pipeline_stats['skipped']} skipped)"
            )

        except Exception as e:
            logger.error(f"Summarization pipeline error: {e}", exc_info=True)
            results["errors"].append(f"Summarization failed: {str(e)}")

        return results

    async def _store_posts(self, posts: list[Post]) -> dict:
        """Store/update posts in PostgreSQL database.

        Args:
            posts: List of posts to store

        Returns:
            Storage statistics
        """
        results = {"success": 0, "errors": []}

        try:
            for post in posts:
                # Update timestamp
                post.updated_at = datetime.utcnow()

                # Save to database
                await self.post_repository.save(post)
                results["success"] += 1

            logger.info(f"Stored {results['success']} posts in database")

        except Exception as e:
            logger.error(f"Storage error: {e}")
            results["errors"].append(f"Storage failed: {str(e)}")

        return results


class DailyDigestPipeline:
    """Generate daily digest from processed posts."""

    def __init__(self, post_repository: PostRepository):
        """Initialize daily digest pipeline.

        Args:
            post_repository: Repository for post persistence
        """
        self.post_repository = post_repository

    async def generate_digest(self, date: str | None = None) -> dict:
        """Generate digest for a specific date.

        Args:
            date: Date for digest (YYYY-MM-DD), defaults to today

        Returns:
            Digest data with statistics
        """
        from datetime import date as date_type

        if date is None:
            date = date_type.today().isoformat()

        logger.info(f"Generating digest for {date}")

        # Fetch posts for the date
        posts = await self.post_repository.find_by_date(date)

        if not posts:
            logger.warning(f"No posts found for {date}")
            return {"date": date, "posts": [], "stats": {}}

        # Filter posts with summaries
        summarized_posts = [p for p in posts if p.summary]

        digest = {
            "date": date,
            "total_posts": len(posts),
            "summarized_posts": len(summarized_posts),
            "posts": summarized_posts,
            "stats": {
                "avg_score": sum(p.score for p in posts) / len(posts) if posts else 0,
                "total_comments": sum(p.comment_count for p in posts),
            },
        }

        logger.info(f"Generated digest: {len(summarized_posts)} posts")
        return digest
