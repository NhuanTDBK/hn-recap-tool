"""Daily recommendations: pick the posts a reader will want from their own taste.

Flow of one run:
  1. Resume today's unsent picks, if a previous run crashed mid-send.
  2. Read taste signals (saves, "not for me", opened, ignored) from the activity log.
  3. Load the last day's candidate posts.
  4. One LLM call ranks them; the program applies the fit cut-off and the daily cap.
  5. Record the run and picks, then send each pick, marking it sent as it goes.

The cap is a ceiling: the number sent is however many strong matches there are.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from app.domain.recommendation import (
    PostBrief,
    RankedPick,
    RankingResult,
    TasteSignals,
    classify_activity,
)
from app.infrastructure.agents.recommendation_agent import RankingError
from app.infrastructure.config.settings import settings
from app.infrastructure.database.models import Post, Recommendation, User
from app.infrastructure.repositories.postgres.recommendation_repo import (
    PostgresRecommendationRepository,
)

logger = logging.getLogger(__name__)

CANDIDATE_LIMIT = 150
SAVED_SHOWN = 100
NOT_FOR_ME_SHOWN = 50
OPENED_SHOWN = 50
IGNORED_SHOWN = 50

Ranker = Callable[[TasteSignals, list[PostBrief]], Awaitable[RankingResult]]
UsageLogger = Callable[..., Awaitable[None]]


class RecommendationSender(Protocol):
    """What the use case needs from the Telegram side."""

    async def send_header(
        self, chat_id: int, topic_id: int | None, count: int, interests: list[str]
    ) -> int: ...

    async def send_pick(
        self,
        chat_id: int,
        topic_id: int | None,
        post: Post,
        summary: str | None,
        position: int,
        total: int,
    ) -> int: ...


class DailyRecommendationUseCase:
    """Runs one day's recommendations for one feed."""

    def __init__(
        self,
        repo: PostgresRecommendationRepository,
        sender: RecommendationSender | None,
        ranker: Ranker,
        model: str = "",
        usage_logger: UsageLogger | None = None,
        message_delay_seconds: float = 1.0,
    ):
        """Initialize the use case.

        Args:
            repo: Recommendation repository
            sender: Telegram sender; may be None for a dry run
            ranker: Async function that calls the model
            model: Model name, stored on the run
            usage_logger: Optional async callback recording one LLM call's tokens
            message_delay_seconds: Pause between Telegram messages
        """
        self.repo = repo
        self.sender = sender
        self.ranker = ranker
        self.model = model
        self.usage_logger = usage_logger
        self.message_delay_seconds = message_delay_seconds

    async def run(
        self,
        user: User,
        *,
        dry_run: bool = False,
        force: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Run today's recommendations.

        Args:
            user: The feed to recommend for (the group's subscriber row)
            dry_run: Rank and report, but write and send nothing
            force: Run again even if today already has a run, within the remaining cap
            now: Current time (for tests)

        Returns:
            Stats with a ``status``: sent, resumed, dry_run, already_ran, no_picks,
            too_few_saves, no_candidates, ranking_failed, send_failed, no_topic
        """
        now = now or datetime.now(timezone.utc)
        today = now.astimezone(ZoneInfo(settings.recommendation_timezone)).date()
        topic_id = settings.telegram_recommendation_topic_id

        stats: dict[str, Any] = {
            "status": "",
            "date": today.isoformat(),
            "sent": 0,
            "failed": 0,
            "interests": [],
            "picks": [],
            "dropped": [],
            "signals": {},
        }

        if topic_id is None and not dry_run:
            logger.error(
                "TELEGRAM_RECOMMENDATION_TOPIC_ID is not set; refusing to send into General"
            )
            stats["status"] = "no_topic"
            return stats

        if not dry_run:
            removed = await self.repo.delete_stale_unsent(user.id, today)
            if removed:
                logger.warning(f"Dropped {removed} unsent pick(s) from earlier days")

            pending = await self.repo.get_pending(user.id, today)
            if pending:
                logger.info(
                    f"Resuming {len(pending)} unsent pick(s) from today's earlier run"
                )
                await self._send(
                    user,
                    pending,
                    await self._resume_header(user.id, today, pending),
                    stats,
                )
                stats["status"] = "resumed" if stats["sent"] else "send_failed"
                return stats

            if not force and await self.repo.has_run_on(user.id, today):
                logger.info("Recommendations already ran today; use force to run again")
                stats["status"] = "already_ran"
                return stats

        signals = await self._load_signals(user.id, today)
        stats["signals"] = {
            "saved": signals.saved_total,
            "not_for_me": len(signals.not_for_me),
            "opened": len(signals.opened),
            "ignored": len(signals.ignored),
        }

        if signals.saved_total < settings.recommendation_min_saves:
            logger.warning(
                f"Only {signals.saved_total} save(s); need {settings.recommendation_min_saves} "
                f"to learn a taste. Skipping."
            )
            stats["status"] = "too_few_saves"
            return stats

        cutoff = now - timedelta(hours=settings.recommendation_lookback_hours)
        candidates = await self.repo.get_candidates(user.id, cutoff, CANDIDATE_LIMIT)
        stats["candidate_count"] = len(candidates)
        if not candidates:
            logger.info("No candidate posts in the lookback window")
            stats["status"] = "no_candidates"
            return stats

        started = time.monotonic()
        try:
            result = await self.ranker(signals, candidates)
        except RankingError as e:
            logger.error(f"Ranking failed, sending nothing today: {e}")
            await self._log_usage(
                e.input_tokens, e.output_tokens, started, "error", str(e)
            )
            stats["status"] = "ranking_failed"
            return stats
        await self._log_usage(
            result.input_tokens, result.output_tokens, started, "success", None
        )

        chosen, dropped = self._select(result.picks)
        chosen = chosen[: await self._cap(user.id, today, force)]
        by_hn = {c.hn_id: c for c in candidates}
        stats["interests"] = result.interests
        stats["picks"] = [self._describe(p, by_hn) for p in chosen]
        stats["dropped"] = [self._describe(p, by_hn) for p in dropped]

        if dry_run:
            stats["status"] = "dry_run"
            return stats

        run = await self.repo.create_run(
            user.id,
            today,
            result.interests,
            {
                "saved": signals.saved_total,
                "not_for_me": len(signals.not_for_me),
                "opened": len(signals.opened),
                "ignored": len(signals.ignored),
                "candidates": len(candidates),
            },
            self.model,
            result.input_tokens,
            result.output_tokens,
        )
        rows = await self.repo.add_picks(
            run.id,
            user.id,
            today,
            [
                (by_hn[p.hn_id].post_id, rank, p.fit, p.reason)
                for rank, p in enumerate(chosen, 1)
            ],
        )

        if not rows:
            logger.info("Nothing met the fit cut-off today; sending nothing")
            stats["status"] = "no_picks"
            return stats

        await self._send(user, rows, (len(rows), result.interests), stats)
        stats["status"] = "sent" if stats["sent"] else "send_failed"
        return stats

    # ---------------------------------------------------------------- helpers

    async def _resume_header(
        self, user_id: int, today: date, pending: list[Recommendation]
    ) -> tuple[int, list[str]] | None:
        """Return the header for resumed picks, or None if today's list already opened."""
        if await self.repo.count_sent(user_id, today) > 0:
            return None
        return len(pending), await self.repo.get_run_interests(user_id, today)

    async def _cap(self, user_id: int, today: date, force: bool) -> int:
        """Return how many picks may still be sent today."""
        sent = await self.repo.count_sent(user_id, today) if force else 0
        return max(0, settings.recommendation_daily_max - sent)

    @staticmethod
    def _select(picks: list[RankedPick]) -> tuple[list[RankedPick], list[RankedPick]]:
        """Split picks into those meeting the fit cut-off (best first) and the rest."""
        keep = [p for p in picks if p.fit >= settings.recommendation_min_fit]
        dropped = [p for p in picks if p.fit < settings.recommendation_min_fit]
        keep.sort(key=lambda p: -p.fit)  # stable: ties keep the model's order
        return keep, dropped

    @staticmethod
    def _describe(pick: RankedPick, by_hn: dict[int, PostBrief]) -> dict[str, Any]:
        brief = by_hn.get(pick.hn_id)
        return {
            "hn_id": pick.hn_id,
            "title": brief.title if brief else "",
            "fit": pick.fit,
            "reason": pick.reason,
        }

    async def _load_signals(self, user_id: int, today: date) -> TasteSignals:
        """Build the taste signals shown to the model."""
        buckets = classify_activity(await self.repo.get_activity(user_id))

        sent_ids = await self.repo.get_recent_sent_post_ids(
            user_id, today - timedelta(days=settings.recommendation_ignored_days)
        )
        ignored_ids = [p for p in sent_ids if p not in buckets.engaged_ids][
            :IGNORED_SHOWN
        ]

        shown = {
            "saved": buckets.saved_ids[:SAVED_SHOWN],
            "not_for_me": buckets.not_for_me_ids[:NOT_FOR_ME_SHOWN],
            "opened": buckets.opened_ids[:OPENED_SHOWN],
            "ignored": ignored_ids,
        }
        briefs = await self.repo.get_briefs(
            user_id, [pid for ids in shown.values() for pid in ids]
        )

        def pick(ids: list) -> list[PostBrief]:
            return [briefs[i] for i in ids if i in briefs]

        return TasteSignals(
            saved=pick(shown["saved"]),
            not_for_me=pick(shown["not_for_me"]),
            opened=pick(shown["opened"]),
            ignored=pick(shown["ignored"]),
            saved_total=len(buckets.saved_ids),
        )

    async def _send(
        self,
        user: User,
        rows: list[Recommendation],
        header: tuple[int, list[str]] | None,
        stats: dict[str, Any],
    ) -> None:
        """Send picks one by one, marking each sent as soon as Telegram accepts it.

        A pick that fails stays unsent. The scheduler's retry job, or a manual run, resends
        it later the same day; after that day it is discarded.
        """
        assert self.sender is not None, "sender is required unless dry_run"
        topic_id = settings.telegram_recommendation_topic_id
        loaded = await self.repo.get_posts_with_summaries(
            user.id, [r.post_id for r in rows]
        )

        if header is not None:
            try:
                await self.sender.send_header(
                    user.telegram_id, topic_id, header[0], header[1]
                )
            except Exception as e:
                logger.error(
                    f"Could not send the recommendations header; leaving picks unsent: {e}"
                )
                stats["failed"] += len(rows)
                return
            await asyncio.sleep(self.message_delay_seconds)

        total = len(rows)
        for position, rec in enumerate(rows, 1):
            entry = loaded.get(rec.post_id)
            if entry is None:
                logger.error(
                    f"Post {rec.post_id} for recommendation {rec.id} no longer exists"
                )
                stats["failed"] += 1
                continue
            post, summary = entry
            try:
                message_id = await self.sender.send_pick(
                    user.telegram_id, topic_id, post, summary, position, total
                )
                await self.repo.mark_sent(rec.id, message_id)
                stats["sent"] += 1
            except Exception as e:
                logger.error(
                    f"Failed to send recommendation {position}/{total} (hn_id={post.hn_id}): {e}"
                )
                stats["failed"] += 1
                continue
            if position < total:
                await asyncio.sleep(self.message_delay_seconds)

        if stats["failed"] and not stats["sent"]:
            logger.error(
                f"RECOMMENDATION OUTAGE: {stats['failed']} pick(s) ready but none could be sent"
            )

    async def _log_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        started: float,
        status: str,
        error: str | None,
    ) -> None:
        """Record the LLM call's tokens, never letting bookkeeping break the run."""
        if self.usage_logger is None:
            return
        try:
            await self.usage_logger(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=int((time.monotonic() - started) * 1000),
                status=status,
                error_message=error,
            )
        except Exception as e:
            logger.warning(f"Failed to record recommendation token usage: {e}")
