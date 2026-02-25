#!/usr/bin/env python
"""CLI script to run hourly delivery daemon for personalized digests.

This script delivers pre-generated summaries to users via Telegram.

Key Features:
- Hourly scheduled delivery (runs at top of each hour)
- Optional daemon mode (keeps running continuously)
- Dry-run mode for testing
- Per-user delivery tracking to avoid duplicates
- Rate limiting to respect Telegram API limits
- Graceful shutdown with Ctrl+C

Usage:
    # Single delivery run
    python scripts/run_delivery_daemon.py

    # Single run (specific user)
    python scripts/run_delivery_daemon.py --user-id 3

    # Dry run (show what would be sent, don't send)
    python scripts/run_delivery_daemon.py --dry-run

    # Daemon mode (runs hourly, keeps running)
    python scripts/run_delivery_daemon.py --daemon

    # Daemon with custom interval (in seconds)
    python scripts/run_delivery_daemon.py --daemon --interval 3600

    # Daemon with max posts limit
    python scripts/run_delivery_daemon.py --daemon --max-posts 5
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

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config.settings import settings
from app.infrastructure.jobs.hourly_delivery_job import HourlyDeliveryJob
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.presentation.bot.bot import BotManager, set_bot_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main_async(
    user_id: int = None,
    max_posts: int = 50,
    dry_run: bool = False,
):
    """Main async function for single delivery run.

    Args:
        user_id: Optional specific user ID (None = all active users)
        max_posts: Maximum posts to deliver per user
        dry_run: If True, don't actually send messages
    """
    print("=" * 80)
    print("HOURLY DELIVERY PIPELINE")
    print("=" * 80)
    print(f"User ID: {user_id or 'all active users'}")
    print(f"Max posts per user: {max_posts}")
    print(f"Dry run: {dry_run}")
    print("=" * 80 + "\n")

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
            # Initialize bot if not dry run
            bot_manager = None
            if not dry_run:
                bot_manager = BotManager()
                await bot_manager.initialize()
                set_bot_manager(bot_manager)
                logger.info("✓ Bot initialized")

            # Create delivery job
            delivery_repo = PostgresDeliveryRepository(session)
            delivery_job = HourlyDeliveryJob(
                db_session=session,
                delivery_repo=delivery_repo,
                max_posts_per_user=max_posts,
            )

            # If specific user, filter to that user
            if user_id:
                logger.info(f"Filtering to user ID: {user_id}")
                # Override find_active_users to return specific user
                from sqlalchemy import select
                from app.infrastructure.database.models import User

                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    logger.error(f"User {user_id} not found")
                    return {"error": f"User {user_id} not found"}

                delivery_job.stats["active_users"] = 1

                # Process single user
                delivered_post_ids = await delivery_job.get_delivered_post_ids(user.id)
                posts = await delivery_job.find_posts_with_summaries(user.id, delivered_post_ids)

                if not posts:
                    logger.info(f"No posts with summaries for user {user_id}")
                    delivery_job.stats["users_skipped"] = 1
                    return delivery_job.stats

                delivery_job.stats["users_with_posts"] = 1

                if dry_run:
                    logger.info(f"DRY RUN: Would send {len(posts)} posts to user {user_id}")
                    delivery_job.stats["users_delivered"] = 1
                    delivery_job.stats["total_messages_sent"] = len(posts)
                    return delivery_job.stats
                else:
                    batch_id = f"{datetime.utcnow().strftime('%Y-%m-%d')}-manual"
                    result = await delivery_job.deliver_to_user(user, posts, batch_id)
                    delivery_job.stats["total_messages_sent"] = result["messages_sent"]
                    delivery_job.stats["total_failures"] = len(result["failures"])
                    if result["messages_sent"] > 0:
                        delivery_job.stats["users_delivered"] = 1
                    else:
                        delivery_job.stats["users_skipped"] = 1
                    return delivery_job.stats

            # Deliver to all active users
            if dry_run:
                logger.info("Running delivery in DRY RUN mode (no messages will be sent)")

            stats = await delivery_job.deliver_summaries()

            # Print summary
            print("\n" + "=" * 80)
            print("DELIVERY COMPLETE")
            print("=" * 80)
            print(f"Active users: {stats['active_users']}")
            print(f"Users with posts: {stats['users_with_posts']}")
            print(f"Users delivered: {stats['users_delivered']}")
            print(f"Users skipped: {stats['users_skipped']}")
            print(f"Total messages: {stats['total_messages_sent']}")
            print(f"Total failures: {stats['total_failures']}")
            if stats['errors'] > 0:
                print(f"Errors: {stats['errors']}")
            print("=" * 80 + "\n")

            return stats

        finally:
            if bot_manager and bot_manager._bot:
                await bot_manager.shutdown()
            await engine.dispose()


async def run_once(
    user_id: int,
    max_posts: int,
    dry_run: bool,
) -> dict:
    """Run delivery once and return stats."""
    start_time = datetime.utcnow()

    stats = await main_async(
        user_id=user_id,
        max_posts=max_posts,
        dry_run=dry_run,
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
    user_id: int,
    max_posts: int,
    dry_run: bool,
    interval: int,
):
    """Run delivery as daemon (keeps running until interrupted).

    Args:
        user_id: Optional specific user ID
        max_posts: Maximum posts to deliver per user
        dry_run: If True, don't actually send messages
        interval: Interval in seconds between runs
    """
    # Create async engine for daemon
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
        # Initialize bot once
        bot_manager = None
        if not dry_run:
            bot_manager = BotManager()
            await bot_manager.initialize()
            set_bot_manager(bot_manager)
            logger.info("✓ Bot initialized")

        try:
            # Create a wrapper job function
            async def delivery_job():
                try:
                    logger.info(f"Running delivery job at {datetime.utcnow().isoformat()}")

                    async with async_session_factory() as job_session:
                        delivery_repo = PostgresDeliveryRepository(job_session)
                        job = HourlyDeliveryJob(
                            db_session=job_session,
                            delivery_repo=delivery_repo,
                            max_posts_per_user=max_posts,
                        )

                        if user_id:
                            logger.info(f"Filtering to user ID: {user_id}")
                            # Single user delivery
                            from sqlalchemy import select
                            from app.infrastructure.database.models import User

                            stmt = select(User).where(User.id == user_id)
                            result = await job_session.execute(stmt)
                            user = result.scalar_one_or_none()

                            if not user:
                                logger.error(f"User {user_id} not found")
                                return

                            delivered_post_ids = await job.get_delivered_post_ids(user.id)
                            posts = await job.find_posts_with_summaries(user.id, delivered_post_ids)

                            if posts:
                                if dry_run:
                                    logger.info(f"DRY RUN: Would send {len(posts)} posts to user {user.id}")
                                else:
                                    batch_id = f"{datetime.utcnow().strftime('%Y-%m-%d-%H-%M')}-hourly"
                                    result = await job.deliver_to_user(user, posts, batch_id)
                                    logger.info(f"Delivered {result['messages_sent']} messages to user {user.id}")
                        else:
                            # All users delivery
                            await job.deliver_summaries()

                except Exception as e:
                    logger.error(f"Delivery job failed: {e}", exc_info=True)

            # Set up graceful shutdown
            stop_event = asyncio.Event()

            def signal_handler():
                logger.info("Received shutdown signal, stopping scheduler...")
                stop_event.set()

            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)

            # Start daemon
            logger.info("Starting daemon in delivery mode...")
            logger.info(f"Jobs will run every {interval} seconds")
            logger.info("Press Ctrl+C to stop")
            logger.info("-" * 80)

            # Run initial delivery immediately
            logger.info("Running initial delivery...")
            await delivery_job()

            # Schedule periodic runs
            next_run = asyncio.get_event_loop().time() + interval

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
                        await delivery_job()
                        next_run = asyncio.get_event_loop().time() + interval
                else:
                    # Time to run immediately
                    await delivery_job()
                    next_run = asyncio.get_event_loop().time() + interval

        finally:
            logger.info("Daemon stopped gracefully")
            if bot_manager and bot_manager._bot:
                await bot_manager.shutdown()
            await engine.dispose()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run hourly delivery daemon for personalized digests"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Specific user ID to deliver to (default: all active users)"
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=50,
        help="Maximum posts to deliver per user (default: 50)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (don't actually send messages)"
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
        help="Interval in seconds for daemon (default: 3600 = 1 hour)"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Log startup info
    logger.info("=" * 80)
    if args.daemon:
        logger.info("HOURLY DELIVERY DAEMON (DAEMON MODE)")
    else:
        logger.info("SINGLE DELIVERY RUN")
    logger.info("=" * 80)
    logger.info(f"Settings: user_id={args.user_id}, max_posts={args.max_posts}, dry_run={args.dry_run}")

    # Check for Telegram token
    if not settings.telegram_bot_token and not args.dry_run:
        print("✗ Error: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    # Run
    try:
        if args.daemon:
            asyncio.run(run_daemon(
                user_id=args.user_id,
                max_posts=args.max_posts,
                dry_run=args.dry_run,
                interval=args.interval
            ))
        else:
            result = asyncio.run(main_async(
                user_id=args.user_id,
                max_posts=args.max_posts,
                dry_run=args.dry_run,
            ))

            if "error" in result:
                print(f"✗ {result['error']}")
            elif result.get("total_messages_sent", 0) == 0:
                print("✓ No messages sent")
            elif args.dry_run:
                print("✓ Dry run complete")
            else:
                print(f"✓ Delivered {result.get('total_messages_sent', 0)} messages to {result.get('users_delivered', 0)} users")

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
