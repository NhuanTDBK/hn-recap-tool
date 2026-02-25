#!/usr/bin/env python
"""
Script to trigger HackerNews posts collection job.

Usage:
    python scripts/trigger_posts_collection.py              # Run once and exit
    python scripts/trigger_posts_collection.py --daemon     # Start scheduler (runs hourly)
    python scripts/trigger_posts_collection.py --score 100 --limit 50  # Custom settings
"""

import argparse
import asyncio
import logging
import signal
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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Trigger HackerNews posts collection"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as daemon with hourly scheduler (keeps running)"
    )
    parser.add_argument(
        "--score", "-s",
        type=int,
        default=50,
        help="Minimum score threshold (default: 50)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Maximum posts to collect (default: 100)"
    )
    return parser.parse_args()


async def run_once(session: AsyncSession, score_threshold: int, posts_limit: int) -> dict:
    """Run posts collection once and return stats."""
    scheduler = SchedulerFactory.create_scheduler(
        db_session=session,
        score_threshold=score_threshold,
        posts_limit=posts_limit,
    )

    start_time = datetime.utcnow()
    stats = await scheduler.hourly_collector.run_collection()
    end_time = datetime.utcnow()

    duration = (end_time - start_time).total_seconds()

    # Display results
    logger.info("-" * 70)
    logger.info("COLLECTION RESULTS:")
    logger.info(f"  Posts fetched from HN:     {stats['posts_fetched']}")
    logger.info(f"  New posts saved:           {stats['posts_saved']}")
    logger.info(f"  Duplicates skipped:        {stats['duplicates_skipped']}")
    logger.info(f"  Errors encountered:        {stats['errors']}")
    logger.info(f"  Collection time:           {duration:.2f} seconds")
    logger.info(f"  Completed at:              {stats['last_run']}")
    logger.info("=" * 70)

    if stats['posts_saved'] > 0:
        logger.info(f"✓ SUCCESS: Collected {stats['posts_saved']} new posts")
    else:
        logger.info("⚠ No new posts collected (all duplicates or low scores)")

    return stats


async def run_daemon(session: AsyncSession, score_threshold: int, posts_limit: int):
    """Run scheduler as daemon (keeps running until interrupted)."""
    scheduler = SchedulerFactory.create_scheduler(
        db_session=session,
        score_threshold=score_threshold,
        posts_limit=posts_limit,
    )

    # Set up graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal, stopping scheduler...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start scheduler
    logger.info("Starting scheduler in daemon mode...")
    logger.info("Jobs will run hourly at :00 minutes (UTC)")
    logger.info("Press Ctrl+C to stop")
    logger.info("-" * 70)

    # Run initial collection immediately
    logger.info("Running initial collection...")
    await scheduler.hourly_collector.run_collection()

    # Start the scheduled jobs
    scheduler.start()

    # Wait for shutdown signal
    await stop_event.wait()

    # Graceful shutdown
    scheduler.stop()
    logger.info("Scheduler stopped gracefully")


async def main():
    """Main entry point."""
    args = parse_args()

    logger.info("=" * 70)
    if args.daemon:
        logger.info("POSTS COLLECTION SCHEDULER (DAEMON MODE)")
    else:
        logger.info("MANUAL POSTS COLLECTION TRIGGER")
    logger.info("=" * 70)
    logger.info(f"Settings: score_threshold={args.score}, limit={args.limit}")

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
            if args.daemon:
                await run_daemon(session, args.score, args.limit)
            else:
                await run_once(session, args.score, args.limit)

    except Exception as e:
        logger.error(f"✗ ERROR: {e}", exc_info=True)
        raise

    finally:
        await engine.dispose()
        logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
