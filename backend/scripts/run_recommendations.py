#!/usr/bin/env python
"""CLI script for the recommendations: picks learned from the group's saves.

Reads the group's Save / "Not for me" / More taps, asks the model which posts summarized
since the last run the reader would want, and sends only the strong matches (no daily limit
unless RECOMMENDATION_DAILY_MAX is set above 0) to their own forum topic. The scheduler runs it
several times a day.

Usage:
    # Preview: one LLM call, nothing is written or sent
    python scripts/run_recommendations.py --dry-run

    # Real run (does nothing if the last run was under the minimum gap ago)
    python scripts/run_recommendations.py

    # Run anyway, still within the day's remaining cap, if one is set
    python scripts/run_recommendations.py --force
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.application.use_cases.recommendation import DailyRecommendationUseCase
from app.infrastructure.agents.config import settings as agent_settings
from app.infrastructure.agents.recommendation_agent import rank_candidates
from app.infrastructure.agents.token_tracker import TokenTracker
from app.infrastructure.config.settings import settings
from app.infrastructure.repositories.postgres.recommendation_repo import (
    PostgresRecommendationRepository,
)
from app.infrastructure.services.group_subscriber import get_group_subscriber
from app.presentation.bot.bot import BotManager
from app.presentation.bot.handlers.recommendation_delivery import (
    RecommendationDeliveryHandler,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Statuses that mean the run should have produced something and did not.
FAILURE_STATUSES = {"ranking_failed", "send_failed", "no_topic", "no_group"}


def _print_report(stats: dict) -> None:
    """Print what a run decided, so a dry run can be judged before anything is sent."""
    print("=" * 80)
    print(f"RECOMMENDATIONS — {stats['date']} — status: {stats['status']}")
    print("=" * 80)
    if stats.get("signals"):
        s = stats["signals"]
        print(
            f"Signals: saved={s['saved']} not_for_me={s['not_for_me']} "
            f"opened={s['opened']} ignored={s['ignored']}  "
            f"candidates={stats.get('candidate_count', 0)}"
        )
    if stats.get("interests"):
        print("Inferred interests: " + ", ".join(stats["interests"]))
    for label, key in (
        ("Picks", "picks"),
        (f"Dropped (fit < {settings.recommendation_min_fit})", "dropped"),
    ):
        items = stats.get(key) or []
        print(f"\n{label}: {len(items)}")
        for item in items:
            print(f"  [{item['fit']}] {item['title']}\n      {item['reason']}")
    print(f"\nSent: {stats['sent']}  Failed: {stats['failed']}")
    print("=" * 80)


def make_usage_logger(
    session_factory: Callable[[], AsyncSession], user_id: int, model: str
) -> Callable[..., Awaitable[None]]:
    """Build the token usage recorder for one run.

    Each write gets its own session: a failed write there cannot leave the run's session
    needing a rollback, and rolling that one back would expire the objects it still uses.

    Args:
        session_factory: Creates async sessions
        user_id: Feed owner the usage is charged to
        model: Model name recorded with the usage

    Returns:
        Async callable taking the token counts and call outcome
    """

    async def usage_logger(**kwargs) -> None:
        async with session_factory() as usage_session:
            await TokenTracker(usage_session).track_usage(
                user_id=user_id,
                agent_name="RecommendationAgent",
                model=model,
                operation="recommend_posts",
                **kwargs,
            )

    return usage_logger


async def main_async(dry_run: bool = False, force: bool = False) -> dict:
    """Run today's recommendations once.

    Args:
        dry_run: Rank and report, but write and send nothing
        force: Run again even if today already has a run

    Returns:
        Stats dict from the use case; ``status`` says what happened
    """
    engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    bot_manager = None

    try:
        async with session_factory() as session:
            user = await get_group_subscriber(session)
            if user is None:
                logger.error(
                    "No group subscriber row: set TELEGRAM_GROUP_CHAT_ID and run summarization once"
                )
                return {"status": "no_group", "date": "", "sent": 0, "failed": 0}

            sender = None
            if not dry_run:
                # Own manager, never set as the global: the hourly delivery job swaps
                # and shuts down the global one in this same process.
                bot_manager = BotManager()
                await bot_manager.initialize()
                sender = RecommendationDeliveryHandler(bot_manager)

            model = settings.recommendation_model or agent_settings.openai_model
            use_case = DailyRecommendationUseCase(
                repo=PostgresRecommendationRepository(session),
                sender=sender,
                ranker=partial(rank_candidates, model=model),
                model=model,
                usage_logger=make_usage_logger(session_factory, user.id, model),
            )
            stats = await use_case.run(user, dry_run=dry_run, force=force)
            _print_report(stats)
            return stats
    finally:
        if bot_manager is not None and bot_manager._bot:
            await bot_manager.shutdown()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send today's recommended HN posts")
    parser.add_argument(
        "--dry-run", action="store_true", help="Rank and report; write and send nothing"
    )
    parser.add_argument(
        "--force", action="store_true", help="Run even if the last run was very recent"
    )
    args = parser.parse_args()

    stats = asyncio.run(main_async(dry_run=args.dry_run, force=args.force))
    sys.exit(1 if stats.get("status") in FAILURE_STATUSES else 0)


if __name__ == "__main__":
    main()
