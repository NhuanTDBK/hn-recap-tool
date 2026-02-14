#!/usr/bin/env python
"""
Script to manually trigger HackerNews posts collection job.

Usage:
    python scripts/trigger_posts_collection.py          # Collect with defaults
    python scripts/trigger_posts_collection.py --score 100 --limit 50  # Custom settings
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.infrastructure.jobs import SchedulerFactory
from app.infrastructure.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run posts collection job immediately."""

    logger.info("=" * 70)
    logger.info("MANUAL POSTS COLLECTION TRIGGER")
    logger.info("=" * 70)

    # Create async database engine
    logger.info(f"Connecting to database: {settings.database_url}")
    engine = create_async_engine(settings.database_url, echo=False)

    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    try:
        async with async_session() as session:
            # Create scheduler
            logger.info("Initializing scheduler...")
            scheduler = SchedulerFactory.create_scheduler(
                db_session=session,
                score_threshold=50,
                posts_limit=100,
            )

            # Run collection
            logger.info("Starting posts collection...")
            logger.info("-" * 70)

            start_time = datetime.utcnow()
            stats = await scheduler.hourly_collector.run_collection()
            end_time = datetime.utcnow()

            duration = (end_time - start_time).total_seconds()

            # Display results
            logger.info("-" * 70)
            logger.info("COLLECTION RESULTS:")
            logger.info(f"  Posts fetched from HN:     {stats['posts_fetched']}")
            logger.info(f"  New posts saved:           {stats['posts_saved']}")
            logger.info(f"  Posts cached in RocksDB:   {stats['posts_cached']}")
            logger.info(f"  Duplicates skipped:        {stats['duplicates_skipped']}")
            logger.info(f"  Errors encountered:        {stats['errors']}")
            logger.info(f"  Collection time:           {duration:.2f} seconds")
            logger.info(f"  Completed at:              {stats['last_run']}")

            logger.info("=" * 70)

            if stats['posts_saved'] > 0:
                logger.info(f"✓ SUCCESS: Collected {stats['posts_saved']} new posts")
            else:
                logger.info("⚠ No new posts collected (all duplicates or low scores)")

            logger.info("=" * 70)

            return stats

    except Exception as e:
        logger.error(f"✗ ERROR: {e}", exc_info=True)
        raise

    finally:
        # Cleanup
        await engine.dispose()
        logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
