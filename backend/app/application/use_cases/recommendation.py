"""Recommendations: pick the posts a reader will want from their own taste.

The job fires several times a day. Flow of one run:
  1. Resend unsent picks left by an earlier run, if any.
  2. Stop if the last run was too recent, or the day's cap is already used.
  3. Read taste signals (saves, "not for me", opened, ignored) from the activity log.
  4. Load candidates: summaries newer than the last run, never picked before.
  5. One LLM call ranks them; the program applies the fit cut-off and the day's room.
  6. Exploration (optional): the model also offers good posts outside the profile; the
     program decides how many to send and which, by Thompson sampling over topics.
  7. Record the run and picks, then send each pick, marking it sent as it goes.

The optional cap (RECOMMENDATION_DAILY_MAX, 0 = no limit) is a ceiling across all of a
day's runs: the number sent is however many strong matches there are. No post is picked twice: candidates exclude earlier picks,
and the database rejects a repeat.
"""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any, NamedTuple, Protocol
from zoneinfo import ZoneInfo

from app.domain.exploration import (
    EXPLORE_FIT,
    KIND_EXPLOIT,
    KIND_EXPLORE,
    TOPICS_SHOWN,
    ExplorePick,
    SentPick,
    TopicStats,
    choose_explorers,
    compute_topic_stats,
    effective_ratio,
    explore_budget,
    kind_metrics,
)
from app.domain.recommendation import (
    ActivityBuckets,
    NewPick,
    PostBrief,
    RankedPick,
    RankingResult,
    TasteSignals,
    classify_activity,
)
from app.infrastructure.agents.recommendation_agent import (
    EXPLORE_OFFERS_MAX,
    RankingError,
)
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
HISTORY_DAYS = 90  # how far back sent picks feed the topic records and the metrics

# Called as ranker(signals, candidates, explore_limit=n).
Ranker = Callable[..., Awaitable[RankingResult]]
UsageLogger = Callable[..., Awaitable[None]]


class _Loaded(NamedTuple):
    """Everything read before ranking."""

    signals: TasteSignals
    history: list[SentPick]  # picks sent in the last ``HISTORY_DAYS``
    topics: dict[str, TopicStats]
    metrics: dict[str, dict[str, int]]  # outcomes per kind, exploit vs explore


class RecommendationSender(Protocol):
    """What the use case needs from the Telegram side."""

    async def send_pick(
        self,
        chat_id: int,
        topic_id: int | None,
        post: Post,
        summary: str | None,
        position: int,
        total: int,
        explore: bool = False,
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
        rng: random.Random | None = None,
    ):
        """Initialize the use case.

        Args:
            repo: Recommendation repository
            sender: Telegram sender; may be None for a dry run
            ranker: Async function that calls the model
            model: Model name, stored on the run
            usage_logger: Optional async callback recording one LLM call's tokens
            message_delay_seconds: Pause between Telegram messages
            rng: Random source for exploring; pass a seeded one in tests
        """
        self.repo = repo
        self.sender = sender
        self.ranker = ranker
        self.model = model
        self.usage_logger = usage_logger
        self.message_delay_seconds = message_delay_seconds
        self.rng = rng or random.Random()

    async def run(
        self,
        user: User,
        *,
        dry_run: bool = False,
        force: bool = False,
        since: datetime | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Run one recommendation slot.

        Args:
            user: The feed to recommend for (the group's subscriber row)
            dry_run: Rank and report, but write and send nothing
            force: Run even if the last run was under the minimum gap ago
            since: Backfill: take candidates from here instead of the last run's start
            now: Current time (for tests)

        Returns:
            Stats with a ``status``: sent, resumed, dry_run, too_soon, daily_cap_reached,
            no_picks, too_few_saves, no_candidates, ranking_failed, send_failed, no_topic
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
            "explore": [],
            "explore_offered": [],
            "metrics": {},
            "signals": {},
        }

        if topic_id is None and not dry_run:
            logger.error(
                "TELEGRAM_RECOMMENDATION_TOPIC_ID is not set; refusing to send into General"
            )
            stats["status"] = "no_topic"
            return stats

        last_run_at = await self.repo.get_last_run_at(user.id)

        if not dry_run:
            # Unsent picks stay resendable for one more day, so a failure at the last
            # slot of a day is retried by the first slot of the next.
            keep_from = today - timedelta(days=1)
            removed = await self.repo.delete_stale_unsent(user.id, keep_from)
            if removed:
                logger.warning(
                    f"Dropped {removed} unsent pick(s) older than {keep_from}"
                )

            pending = await self.repo.get_pending(user.id, keep_from)
            if pending:
                logger.info(
                    f"Resending {len(pending)} unsent pick(s) from earlier runs"
                )
                await self._resend(user, pending, stats)
                if not stats["sent"]:
                    stats["status"] = "send_failed"
                    return stats

            min_gap = timedelta(minutes=settings.recommendation_min_gap_minutes)
            if not force and last_run_at is not None and now - last_run_at < min_gap:
                logger.info(
                    f"Last run was at {last_run_at.isoformat()}, under "
                    f"{settings.recommendation_min_gap_minutes} min ago; use force to run anyway"
                )
                stats["status"] = "too_soon" if not stats["sent"] else "resumed"
                return stats

        # RECOMMENDATION_DAILY_MAX <= 0 means no daily limit.
        room: int | None = None
        if settings.recommendation_daily_max > 0:
            room = settings.recommendation_daily_max - await self.repo.count_for_day(
                user.id, today
            )
            if room <= 0:
                logger.info(
                    f"Already picked {settings.recommendation_daily_max} today; done"
                )
                stats["status"] = (
                    "daily_cap_reached" if not stats["sent"] else "resumed"
                )
                return stats

        loaded = await self._load_signals(user.id, today)
        signals, history, topic_stats = loaded.signals, loaded.history, loaded.topics
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

        # Only summaries newer than the last run: posts the model already rated and
        # passed over are not paid for again. The lookback bounds it after a long gap.
        if since is not None:
            cutoff = since
        else:
            cutoff = now - timedelta(hours=settings.recommendation_lookback_hours)
            if last_run_at is not None:
                cutoff = max(cutoff, last_run_at)
        candidates = await self.repo.get_candidates(user.id, cutoff, CANDIDATE_LIMIT)
        stats["candidate_count"] = len(candidates)
        if not candidates:
            logger.info("No new candidate posts since the last run")
            stats["status"] = "no_candidates"
            return stats

        # Ask the model for explore offers only while the day still has explore room.
        explore_on = settings.recommendation_explore_enabled
        explored_today = 0
        explore_limit = 0
        if explore_on:
            explored_today = await self.repo.count_explore_for_day(user.id, today)
            if (
                settings.recommendation_explore_ratio > 0
                and explored_today < settings.recommendation_explore_max_per_day
                and (room is None or room > 0)
            ):
                explore_limit = EXPLORE_OFFERS_MAX

        started = time.monotonic()
        try:
            result = await self.ranker(signals, candidates, explore_limit=explore_limit)
        except RankingError as e:
            logger.error(f"Ranking failed, sending nothing this run: {e}")
            await self._log_usage(
                e.input_tokens, e.output_tokens, started, "error", str(e)
            )
            stats["status"] = "ranking_failed"
            return stats
        await self._log_usage(
            result.input_tokens, result.output_tokens, started, "success", None
        )

        chosen, dropped = self._select(result.picks)
        if room is not None:
            chosen = chosen[:room]
        by_hn = {c.hn_id: c for c in candidates}

        explored: list[ExplorePick] = []
        if explore_limit and result.explore:
            budget = explore_budget(
                len(chosen),
                explored_today,
                effective_ratio(settings.recommendation_explore_ratio, len(history)),
                settings.recommendation_explore_max_per_day,
                self.rng,
            )
            if room is not None:
                budget = min(budget, max(room - len(chosen), 0))
            explored = choose_explorers(
                result.explore,
                topic_stats,
                today=today,
                budget=budget,
                min_quality=settings.recommendation_explore_min_quality,
                cooldown_days=settings.recommendation_explore_cooldown_days,
                rng=self.rng,
                skip_hn_ids={p.hn_id for p in result.picks},
            )

        stats["interests"] = result.interests
        stats["picks"] = [self._describe(p, by_hn) for p in chosen]
        stats["dropped"] = [self._describe(p, by_hn) for p in dropped]
        stats["explore"] = [self._describe_explore(p, by_hn) for p in explored]
        stats["explore_offered"] = [
            self._describe_explore(p, by_hn) for p in result.explore
        ]
        stats["metrics"] = loaded.metrics

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
            now,
        )
        rows = await self.repo.add_picks(
            run.id,
            user.id,
            today,
            self._new_picks(chosen, explored, by_hn),
        )

        if not rows:
            logger.info("Nothing new met the fit cut-off; sending nothing")
            stats["status"] = "no_picks"
            return stats

        await self._send(user, rows, stats)
        stats["status"] = "sent" if stats["sent"] else "send_failed"
        return stats

    # ---------------------------------------------------------------- helpers

    async def _resend(
        self, user: User, pending: list[Recommendation], stats: dict[str, Any]
    ) -> None:
        """Resend unsent picks, oldest run first."""
        by_run: dict[Any, list[Recommendation]] = {}
        for rec in pending:
            by_run.setdefault(rec.run_id, []).append(rec)

        for rows in by_run.values():
            await self._send(user, rows, stats)

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
            "topic": pick.topic,
        }

    @staticmethod
    def _describe_explore(
        pick: ExplorePick, by_hn: dict[int, PostBrief]
    ) -> dict[str, Any]:
        brief = by_hn.get(pick.hn_id)
        return {
            "hn_id": pick.hn_id,
            "title": brief.title if brief else "",
            "fit": EXPLORE_FIT,
            "quality": pick.quality,
            "reason": pick.reason,
            "topic": pick.topic,
        }

    @staticmethod
    def _new_picks(
        exploit: list[RankedPick],
        explore: list[ExplorePick],
        by_hn: dict[int, PostBrief],
    ) -> list[NewPick]:
        """Number the picks best first, exploit picks before explore picks."""
        rows = [
            NewPick(
                by_hn[p.hn_id].post_id, rank, p.fit, p.reason, p.topic, KIND_EXPLOIT
            )
            for rank, p in enumerate(exploit, 1)
        ]
        rows += [
            NewPick(
                by_hn[p.hn_id].post_id,
                rank,
                EXPLORE_FIT,
                p.reason,
                p.topic,
                KIND_EXPLORE,
                p.quality,
            )
            for rank, p in enumerate(explore, len(exploit) + 1)
        ]
        return rows

    async def _load_signals(self, user_id: int, today: date) -> "_Loaded":
        """Build the taste signals shown to the model, plus the topic records and metrics."""
        buckets: ActivityBuckets = classify_activity(
            await self.repo.get_activity(user_id)
        )
        history = await self.repo.get_sent_history(
            user_id, today - timedelta(days=HISTORY_DAYS)
        )
        topic_stats = compute_topic_stats(
            history, buckets, today, settings.recommendation_topic_half_life_days
        )

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

        signals = TasteSignals(
            saved=pick(shown["saved"]),
            not_for_me=pick(shown["not_for_me"]),
            opened=pick(shown["opened"]),
            ignored=pick(shown["ignored"]),
            saved_total=len(buckets.saved_ids),
            topics=sorted(topic_stats.values(), key=lambda t: (-t.shown, t.topic))[
                :TOPICS_SHOWN
            ],
        )
        return _Loaded(
            signals, history, topic_stats, kind_metrics(history, buckets, today)
        )

    async def _send(
        self,
        user: User,
        rows: list[Recommendation],
        stats: dict[str, Any],
    ) -> None:
        """Send picks one by one, marking each sent as soon as Telegram accepts it.

        A pick that fails stays unsent. The next run resends it; after a day it is
        discarded.
        """
        assert self.sender is not None, "sender is required unless dry_run"
        topic_id = settings.telegram_recommendation_topic_id
        loaded = await self.repo.get_posts_with_summaries(
            user.id, [r.post_id for r in rows]
        )

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
                    user.telegram_id,
                    topic_id,
                    post,
                    summary,
                    position,
                    total,
                    explore=rec.kind == KIND_EXPLORE,
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
