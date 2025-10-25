"""Background job for collecting HN data daily."""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.use_cases.collection import (
    CollectPostsUseCase,
    ExtractContentUseCase,
    CreateDigestUseCase
)
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class DataCollectorJob:
    """Background job for daily HN data collection."""

    def __init__(
        self,
        collect_posts_use_case: CollectPostsUseCase,
        extract_content_use_case: ExtractContentUseCase,
        create_digest_use_case: CreateDigestUseCase
    ):
        """Initialize data collector job.

        Args:
            collect_posts_use_case: Use case for collecting posts
            extract_content_use_case: Use case for extracting content
            create_digest_use_case: Use case for creating digest
        """
        self.collect_posts = collect_posts_use_case
        self.extract_content = extract_content_use_case
        self.create_digest = create_digest_use_case
        self.scheduler = AsyncIOScheduler()

    async def run_collection(self) -> None:
        """Run the data collection process.

        This method:
        1. Collects front page posts from HN
        2. Extracts article content for posts with URLs
        3. Creates a daily digest
        """
        logger.info("Starting HN data collection job")
        date = datetime.utcnow().strftime('%Y-%m-%d')

        try:
            # Step 1: Collect posts
            logger.info("Step 1: Collecting posts from HN")
            posts = await self.collect_posts.execute(limit=settings.hn_max_posts)
            logger.info(f"Collected {len(posts)} posts")

            # Step 2: Extract content for posts with URLs
            logger.info("Step 2: Extracting article content")
            content_extracted = 0
            for post in posts:
                if post.has_external_url():
                    try:
                        await self.extract_content.execute(post.id)
                        content_extracted += 1
                    except Exception as e:
                        logger.warning(f"Failed to extract content for post {post.id}: {e}")
                        continue

            logger.info(f"Extracted content for {content_extracted} posts")

            # Step 3: Create digest
            logger.info("Step 3: Creating daily digest")
            digest = await self.create_digest.execute(date)
            logger.info(f"Created digest with {len(digest.posts)} posts")

            logger.info("HN data collection job completed successfully")

        except Exception as e:
            logger.error(f"HN data collection job failed: {e}", exc_info=True)
            raise

    def start(self) -> None:
        """Start the scheduled job.

        Runs daily at 00:00 UTC.
        """
        # Schedule for midnight UTC
        trigger = CronTrigger(hour=0, minute=0, timezone="UTC")

        self.scheduler.add_job(
            self.run_collection,
            trigger=trigger,
            id="hn_data_collection",
            name="HackerNews Data Collection",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Data collector job scheduled for daily execution at 00:00 UTC")

    def stop(self) -> None:
        """Stop the scheduled job."""
        self.scheduler.shutdown()
        logger.info("Data collector job stopped")

    async def run_now(self) -> None:
        """Run the collection job immediately (for manual triggers)."""
        logger.info("Running data collection job manually")
        await self.run_collection()
