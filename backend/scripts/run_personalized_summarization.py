#!/usr/bin/env python
"""CLI script to run personalized summarization pipeline.

This script generates personalized summaries for users grouped by delivery_style.

Key Features:
- Groups users by delivery_style to minimize API calls
- Incremental: only processes posts since user's last summary
- Writes to summaries table with user_id (NOT NULL)
- Prompt caching for efficiency
- Tracks tokens and costs
- Optional scheduled execution (daemon mode)

Usage:
    # Generate summaries for all active users
    python scripts/run_personalized_summarization.py

    # Process specific users
    python scripts/run_personalized_summarization.py --user-ids 1,2,3

    # Limit posts per group
    python scripts/run_personalized_summarization.py --post-limit 50

    # Adjust time window for first-time users
    python scripts/run_personalized_summarization.py --default-hours 12

    # Dry run
    python scripts/run_personalized_summarization.py --dry-run

    # Run as daemon with scheduled execution (keeps running)
    python scripts/run_personalized_summarization.py --daemon

    # Run as daemon with custom schedule
    python scripts/run_personalized_summarization.py --daemon --interval 30
"""

import asyncio
import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.application.use_cases.personalized_summarization import run_personalized_summarization
from app.infrastructure.config.settings import settings
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main_async(
    user_ids: list[int] = None,
    default_hours: int = 6,
    post_limit: int = None,
    dry_run: bool = False,
    verbose: bool = False
):
    """Main async function.

    Args:
        user_ids: Optional list of user IDs to process
        default_hours: Default lookback window for users without summaries
        post_limit: Maximum posts to process per group
        dry_run: If True, don't actually create summaries
        verbose: Enable verbose logging
    """
    print("="*80)
    print("PERSONALIZED SUMMARIZATION PIPELINE")
    print("="*80)
    print(f"User IDs: {user_ids or 'all active users'}")
    print(f"Default time window: {default_hours} hours")
    print(f"Post limit per group: {post_limit or 'unlimited'}")
    print(f"Dry run: {dry_run}")
    print("="*80 + "\n")

    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        try:
            # Initialize RocksDB
            content_store = RocksDBContentStore(
                db_path=str(Path(settings.data_dir) / "content.rocksdb")
            )

            # Initialize OpenAI client
            openai_client = OpenAI(api_key=settings.openai_api_key)

            # Run personalized summarization
            stats = await run_personalized_summarization(
                session=session,
                content_store=content_store,
                openai_client=openai_client,
                user_ids=user_ids,
                default_hours=default_hours,
                post_limit=post_limit,
                dry_run=dry_run
            )

            # Print per-group breakdown
            if stats["groups"]:
                print("\nPer-Group Breakdown:")
                print("-" * 80)
                for style, group_stats in stats["groups"].items():
                    print(f"  {style}:")
                    print(f"    Users: {group_stats['users']}")
                    print(f"    Posts processed: {group_stats['posts']}")
                    print(f"    Summaries created: {group_stats['summaries']}")
                    if not dry_run and 'tokens' in group_stats:
                        print(f"    Tokens: {group_stats['tokens']}")
                        print(f"    Cost: ${group_stats['cost']:.4f}")
                print("-" * 80)

            return stats

        finally:
            await engine.dispose()


async def run_once(
    user_ids: list[int],
    default_hours: int,
    post_limit: int,
    dry_run: bool,
    verbose: bool
) -> dict:
    """Run summarization once and return stats."""
    start_time = datetime.utcnow()

    stats = await main_async(
        user_ids=user_ids,
        default_hours=default_hours,
        post_limit=post_limit,
        dry_run=dry_run,
        verbose=verbose
    )

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Display results summary
    logger.info("-" * 80)
    logger.info("EXECUTION SUMMARY:")
    logger.info(f"  Total execution time:      {duration:.2f} seconds")
    logger.info(f"  Completed at:              {end_time.isoformat()}")
    logger.info("=" * 80)

    return stats


async def run_daemon(
    user_ids: list[int],
    default_hours: int,
    post_limit: int,
    dry_run: bool,
    verbose: bool,
    interval: int
):
    """Run scheduler as daemon (keeps running until interrupted).

    Args:
        user_ids: Optional list of user IDs to process
        default_hours: Default lookback window for users without summaries
        post_limit: Maximum posts to process per group
        dry_run: If True, don't actually create summaries
        verbose: Enable verbose logging
        interval: Interval in seconds between runs
    """
    # Create async engine for scheduler
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Create a wrapper job function
        async def summarization_job():
            try:
                logger.info(f"Running summarization job at {datetime.utcnow().isoformat()}")
                await main_async(
                    user_ids=user_ids,
                    default_hours=default_hours,
                    post_limit=post_limit,
                    dry_run=dry_run,
                    verbose=verbose
                )
            except Exception as e:
                logger.error(f"Summarization job failed: {e}", exc_info=True)

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
        logger.info(f"Jobs will run every {interval} seconds")
        logger.info("Press Ctrl+C to stop")
        logger.info("-" * 80)

        # Run initial summarization immediately
        logger.info("Running initial summarization...")
        await summarization_job()

        # Schedule periodic runs
        next_run = asyncio.get_event_loop().time() + interval

        try:
            while not stop_event.is_set():
                current_time = asyncio.get_event_loop().time()
                time_until_next = next_run - current_time

                if time_until_next > 0:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=time_until_next)
                        # If we get here, stop_event was set
                        break
                    except asyncio.TimeoutError:
                        # Time to run the job
                        await summarization_job()
                        next_run = asyncio.get_event_loop().time() + interval
                else:
                    # Time to run immediately
                    await summarization_job()
                    next_run = asyncio.get_event_loop().time() + interval

        finally:
            logger.info("Scheduler stopped gracefully")
            await engine.dispose()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run personalized summarization pipeline"
    )
    parser.add_argument(
        "--user-ids",
        type=str,
        default=None,
        help="Comma-separated list of user IDs to process (e.g., '1,2,3')"
    )
    parser.add_argument(
        "--default-hours",
        type=int,
        default=6,
        help="Default lookback window for users without summaries (default: 6)"
    )
    parser.add_argument(
        "--post-limit",
        type=int,
        default=None,
        help="Limit posts per group (default: unlimited)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually create summaries)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as daemon with periodic scheduler (keeps running)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval in seconds for scheduler (default: 3600 = 1 hour)"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse user IDs
    user_ids = None
    if args.user_ids:
        try:
            user_ids = [int(uid.strip()) for uid in args.user_ids.split(",")]
        except ValueError:
            print(f"✗ Error: Invalid user IDs format: {args.user_ids}")
            print("  Expected format: --user-ids 1,2,3")
            sys.exit(1)

    # Check for API key
    if not settings.openai_api_key and not args.dry_run:
        print("✗ Error: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    # Log startup info
    logger.info("=" * 80)
    if args.daemon:
        logger.info("PERSONALIZED SUMMARIZATION SCHEDULER (DAEMON MODE)")
    else:
        logger.info("MANUAL PERSONALIZED SUMMARIZATION")
    logger.info("=" * 80)
    logger.info(f"Settings: user_ids={user_ids}, default_hours={args.default_hours}, post_limit={args.post_limit}, dry_run={args.dry_run}")

    # Run
    try:
        if args.daemon:
            asyncio.run(run_daemon(
                user_ids=user_ids,
                default_hours=args.default_hours,
                post_limit=args.post_limit,
                dry_run=args.dry_run,
                verbose=args.verbose,
                interval=args.interval
            ))
        else:
            result = asyncio.run(main_async(
                user_ids=user_ids,
                default_hours=args.default_hours,
                post_limit=args.post_limit,
                dry_run=args.dry_run,
                verbose=args.verbose
            ))

            if result["total_users"] == 0:
                print("✓ No active users to process")
            elif args.dry_run:
                print("✓ Dry run complete")
            else:
                print(f"✓ Created {result['total_summaries_created']} summaries for {result['total_users']} users")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
