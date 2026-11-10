#!/usr/bin/env python3
"""Unified APScheduler workflow — runs the full HN Pal pipeline every hour.

Pipeline steps (sequential):
  1. collect  — fetch top HN posts → PostgreSQL
  2. crawl    — extract content from URLs → RocksDB
  3. summarize — AI summarization → PostgreSQL
  4. deliver   — send summaries to users via Telegram
  5. recommend — send picks learned from saves to their own topic (when
                 RECOMMENDATION_ENABLED=true), on the same hourly schedule

Each step is called from its existing script module. One APScheduler trigger
(CronTrigger minute=0) fires the whole pipeline. Individual steps fail
independently so a crawl failure doesn't block delivery of already-ready content.

Usage:
    python scripts/run_scheduler.py
"""

import asyncio
import logging
import signal
import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config.settings import settings
from scripts.crawl_and_store import HNCrawler
from scripts.crawl_and_store import run_once as crawl_run_once
from scripts.run_delivery_daemon import main_async as deliver
from scripts.run_personalized_summarization import main_async as summarize
from scripts.run_recommendations import FAILURE_STATUSES as RECOMMENDATION_FAILURES
from scripts.run_recommendations import main_async as recommend
from scripts.trigger_posts_collection import run_once as collect_run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def pipeline() -> None:
    """Run all pipeline steps sequentially."""
    logger.info("=" * 60)
    logger.info("HN PAL PIPELINE — START")
    logger.info("=" * 60)

    # Step 1: Collect posts
    logger.info("[1/4] Collecting HN posts...")
    try:
        engine = create_async_engine(
            settings.database_url, echo=False, pool_pre_ping=True
        )
        session_factory = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as session:
            await collect_run_once(session, score_threshold=50, posts_limit=100)
        await engine.dispose()
        logger.info("[1/4] Collection complete")
    except Exception:
        logger.exception("[1/4] Collection failed — continuing to next step")

    # Step 2: Crawl content
    logger.info("[2/4] Crawling post content...")
    crawler = None
    try:
        crawler = HNCrawler()
        # daemon=True tells run_once to skip HN fetch (collection already done above)
        crawl_args = Namespace(daemon=True, limit=100, score_threshold=100)
        await crawl_run_once(crawl_args, crawler)
        logger.info("[2/4] Crawl complete")
    except Exception:
        logger.exception("[2/4] Crawl failed — continuing to next step")
    finally:
        if crawler is not None:
            crawler.content_store.close()

    # Step 3: Summarize
    logger.info("[3/4] Running summarization...")
    try:
        await summarize()
        logger.info("[3/4] Summarization complete")
    except Exception:
        logger.exception("[3/4] Summarization failed — continuing to next step")

    # Step 4: Deliver
    logger.info("[4/4] Delivering summaries...")
    try:
        stats = await deliver()
        # deliver() returns None only on the early-exit paths; treat a run that
        # sent nothing while posts were queued as a failure, not a success.
        if isinstance(stats, dict) and (
            stats.get("users_failed") or stats.get("total_failures")
        ):
            logger.error(
                "[4/4] Delivery FAILED: sent=%s, failures=%s, users_failed=%s",
                stats.get("total_messages_sent", 0),
                stats.get("total_failures", 0),
                stats.get("users_failed", 0),
            )
        else:
            logger.info("[4/4] Delivery complete")
    except Exception:
        logger.exception("[4/4] Delivery failed")

    # Step 5: Recommend (after delivery, so it sees this hour's new summaries)
    if settings.recommendation_enabled:
        await recommend_step()

    logger.info("=" * 60)
    logger.info("HN PAL PIPELINE — DONE")
    logger.info("=" * 60)


async def recommend_step() -> None:
    """Send the new hour's recommended posts. A failure here never fails the pipeline."""
    logger.info("[5/5] Recommending posts...")
    try:
        # force: the pipeline fires hourly, under the CLI's minimum gap between runs.
        stats = await recommend(force=True)
    except Exception:
        logger.exception("[5/5] Recommendations crashed")
        return
    status = stats.get("status")
    logger.log(
        logging.ERROR if status in RECOMMENDATION_FAILURES else logging.INFO,
        "[5/5] Recommendations — %s (sent=%s, failed=%s)",
        status,
        stats.get("sent", 0),
        stats.get("failed", 0),
    )


async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_shutdown() -> None:
        logger.info("Shutdown signal received — stopping scheduler...")
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _handle_shutdown)
    loop.add_signal_handler(signal.SIGINT, _handle_shutdown)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        pipeline,
        trigger=CronTrigger(minute=0, timezone="UTC"),
        id="hn_pal_pipeline",
        name="HN Pal Hourly Pipeline",
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started — pipeline fires every hour at :00 UTC (recommendations: %s)",
        "on" if settings.recommendation_enabled else "off",
    )

    await stop_event.wait()
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
