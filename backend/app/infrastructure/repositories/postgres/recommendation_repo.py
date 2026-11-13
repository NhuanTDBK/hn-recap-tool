"""PostgreSQL access for the daily recommendation feature."""

import logging
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Select, and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exploration import KIND_EXPLORE, SentPick
from app.domain.recommendation import (
    ENGAGED_ACTIONS,
    STRONG_ACTIONS,
    NewPick,
    PostBrief,
    clip,
)
from app.infrastructure.database.models import (
    Post,
    Recommendation,
    RecommendationRun,
    Summary,
    UserActivityLog,
)

logger = logging.getLogger(__name__)

ACTIVITY_ROW_LIMIT = 5000  # newest rows read per user; older taste is allowed to fade
SUMMARY_CHARS = 400


class PostgresRecommendationRepository:
    """Queries and writes for recommendation runs, picks and taste signals."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    # ------------------------------------------------------------------ taste

    async def get_activity(self, user_id: int) -> list[tuple[UUID, str, datetime]]:
        """Return the user's newest taste-related activity rows.

        Args:
            user_id: Feed owner

        Returns:
            ``(post_id, action_type, created_at)`` rows, newest first
        """
        stmt = (
            select(
                UserActivityLog.post_id,
                UserActivityLog.action_type,
                UserActivityLog.created_at,
            )
            .where(
                UserActivityLog.user_id == user_id,
                UserActivityLog.action_type.in_(ENGAGED_ACTIONS),
            )
            .order_by(UserActivityLog.created_at.desc())
            .limit(ACTIVITY_ROW_LIMIT)
        )
        result = await self.session.execute(stmt)
        return [(r[0], r[1], r[2]) for r in result.all()]

    async def get_posts_with_summaries(
        self, user_id: int, post_ids: list[UUID]
    ) -> dict[UUID, tuple[Post, str | None]]:
        """Load posts with the summary written for this feed.

        ``posts.summary`` is shared between feeds and holds whichever was written
        last, so it is only a fallback.

        Args:
            user_id: Feed owner
            post_ids: Posts to load

        Returns:
            ``(post, summary_text)`` keyed by post ID (missing posts are absent)
        """
        if not post_ids:
            return {}

        posts = (
            (await self.session.execute(select(Post).where(Post.id.in_(post_ids))))
            .scalars()
            .all()
        )

        summaries: dict[UUID, str] = {}
        rows = await self.session.execute(
            select(Summary.post_id, Summary.summary_text)
            .where(Summary.user_id == user_id, Summary.post_id.in_(post_ids))
            .order_by(Summary.created_at.asc())  # newest wins when the dict is filled
        )
        for post_id, text in rows.all():
            summaries[post_id] = text

        return {p.id: (p, summaries.get(p.id) or p.summary) for p in posts}

    async def get_briefs(
        self, user_id: int, post_ids: list[UUID]
    ) -> dict[UUID, PostBrief]:
        """Load posts as short briefs for the ranking prompt.

        Args:
            user_id: Feed owner
            post_ids: Posts to load

        Returns:
            Briefs keyed by post ID (posts that no longer exist are absent)
        """
        loaded = await self.get_posts_with_summaries(user_id, post_ids)
        return {
            pid: self._brief(post, summary) for pid, (post, summary) in loaded.items()
        }

    async def get_recent_sent_post_ids(self, user_id: int, since: date) -> list[UUID]:
        """Return posts recommended and sent on or after ``since``, newest first."""
        stmt = (
            select(Recommendation.post_id)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.sent_at.isnot(None),
                Recommendation.recommended_on >= since,
            )
            .order_by(Recommendation.sent_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_sent_history(self, user_id: int, since: date) -> list[SentPick]:
        """Return picks that reached the reader on or after ``since``, newest first.

        Feeds the topic records and the explore/exploit metrics.
        """
        stmt = (
            select(
                Recommendation.post_id,
                Recommendation.topic,
                Recommendation.kind,
                Recommendation.recommended_on,
            )
            .where(
                Recommendation.user_id == user_id,
                Recommendation.sent_at.isnot(None),
                Recommendation.recommended_on >= since,
            )
            .order_by(Recommendation.sent_at.desc())
        )
        rows = await self.session.execute(stmt)
        return [SentPick(r[0], r[1], r[2], r[3]) for r in rows.all()]

    # ------------------------------------------------------------- candidates

    def candidates_query(self, user_id: int, cutoff: datetime, limit: int) -> Select:
        """Build the query for today's candidate posts.

        Candidates have a summary for this feed created since ``cutoff`` and are live,
        crawled stories. Posts already saved, rejected or recommended are left out, as
        are video posts, which never have a usable summary.
        """
        decided = select(UserActivityLog.post_id).where(
            UserActivityLog.user_id == user_id,
            UserActivityLog.action_type.in_(STRONG_ACTIONS),
        )
        recommended = select(Recommendation.post_id).where(
            Recommendation.user_id == user_id
        )

        return (
            select(Post, Summary.summary_text)
            .join(Summary, and_(Summary.post_id == Post.id, Summary.user_id == user_id))
            .where(
                Summary.created_at >= cutoff,
                Post.type == "story",
                Post.is_dead.is_(False),
                Post.is_deleted.is_(False),
                Post.is_crawl_success.is_(True),
                Post.title.isnot(None),
                ~Post.title.ilike("%[video]%"),
                ~Post.id.in_(decided),
                ~Post.id.in_(recommended),
            )
            .order_by(Post.score.desc(), Summary.created_at.desc())
            .limit(
                limit * 2
            )  # a post can have several summary rows; deduplicated below
        )

    async def get_candidates(
        self, user_id: int, cutoff: datetime, limit: int
    ) -> list[PostBrief]:
        """Return up to ``limit`` candidate posts, highest score first."""
        rows = await self.session.execute(self.candidates_query(user_id, cutoff, limit))
        briefs: dict[UUID, PostBrief] = {}
        for post, summary_text in rows.all():
            if post.id not in briefs:
                briefs[post.id] = self._brief(post, summary_text)
            if len(briefs) >= limit:
                break
        return list(briefs.values())

    # ------------------------------------------------------------ run / picks

    async def delete_stale_unsent(self, user_id: int, before: date) -> int:
        """Delete picks from days before ``before`` that were never sent.

        They were never delivered, so deleting them lets those posts be considered
        again; the unique constraint would otherwise block them forever.
        """
        result = await self.session.execute(
            delete(Recommendation).where(
                Recommendation.user_id == user_id,
                Recommendation.sent_at.is_(None),
                Recommendation.recommended_on < before,
            )
        )
        await self.session.commit()
        return result.rowcount or 0

    async def get_pending(self, user_id: int, since: date) -> list[Recommendation]:
        """Return picks from ``since`` on that are stored but not sent yet, oldest first."""
        stmt = (
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.recommended_on >= since,
                Recommendation.sent_at.is_(None),
            )
            .order_by(Recommendation.recommended_on.asc(), Recommendation.rank.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_day(self, user_id: int, day: date) -> int:
        """Count picks stored for ``day`` (sent or still waiting), against the daily cap."""
        stmt = select(func.count(Recommendation.id)).where(
            Recommendation.user_id == user_id,
            Recommendation.recommended_on == day,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_explore_for_day(self, user_id: int, day: date) -> int:
        """Count explore picks stored for ``day`` (sent or waiting), against the explore ceiling."""
        stmt = select(func.count(Recommendation.id)).where(
            Recommendation.user_id == user_id,
            Recommendation.recommended_on == day,
            Recommendation.kind == KIND_EXPLORE,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_last_run_at(self, user_id: int) -> datetime | None:
        """Return when the newest run for this feed started, or None if none ran."""
        stmt = select(func.max(RecommendationRun.created_at)).where(
            RecommendationRun.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_run(
        self,
        user_id: int,
        day: date,
        interests: list[str],
        counts: dict[str, int],
        model: str,
        input_tokens: int,
        output_tokens: int,
        started_at: datetime,
    ) -> RecommendationRun:
        """Record a run (flushed, not committed, so picks can join it atomically).

        ``started_at`` is stored as ``created_at``: the next run only looks at summaries
        newer than it, so a summary written while this run was ranking is not missed.
        """
        run = RecommendationRun(
            id=uuid4(),
            user_id=user_id,
            run_date=day,
            created_at=started_at,
            interests=interests,
            saved_count=counts.get("saved", 0),
            not_for_me_count=counts.get("not_for_me", 0),
            opened_count=counts.get("opened", 0),
            ignored_count=counts.get("ignored", 0),
            candidate_count=counts.get("candidates", 0),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def add_picks(
        self,
        run_id: UUID,
        user_id: int,
        day: date,
        picks: list[NewPick],
    ) -> list[Recommendation]:
        """Store picks (unsent) and commit the run with them.

        A post already recommended to this user is skipped by the database, so two
        runs that overlap cannot both pick it.

        Args:
            run_id: Run these belong to
            user_id: Feed owner
            day: Local date of the run
            picks: Picks to store, best first

        Returns:
            The rows actually stored, best first (fewer than given if some were repeats)
        """
        if not picks:
            await self.session.commit()
            return []

        result = await self.session.execute(
            self.insert_picks_stmt(run_id, user_id, day, picks)
        )
        stored_ids = list(result.scalars().all())
        await self.session.commit()

        rows = await self.session.execute(
            select(Recommendation)
            .where(Recommendation.id.in_(stored_ids))
            .order_by(Recommendation.rank.asc())
        )
        return list(rows.scalars().all())

    @staticmethod
    def insert_picks_stmt(
        run_id: UUID,
        user_id: int,
        day: date,
        picks: list[NewPick],
    ):
        """Build the insert that skips posts already recommended to this user."""
        return (
            pg_insert(Recommendation)
            .values(
                [
                    {
                        "id": uuid4(),
                        "run_id": run_id,
                        "user_id": user_id,
                        "post_id": p.post_id,
                        "recommended_on": day,
                        "rank": p.rank,
                        "fit_score": p.fit,
                        "reason": p.reason,
                        "topic": p.topic or None,
                        "kind": p.kind,
                        "quality": p.quality,
                    }
                    for p in picks
                ]
            )
            .on_conflict_do_nothing(constraint="uq_recommendations_user_post")
            .returning(Recommendation.id)
        )

    async def mark_sent(self, rec_id: UUID, message_id: int) -> None:
        """Record that a pick reached Telegram. Committed at once so a crash cannot resend it."""
        rec = await self.session.get(Recommendation, rec_id)
        if rec is None:
            return
        rec.message_id = message_id
        rec.sent_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def get_reason(self, user_id: int, post_id: UUID) -> str | None:
        """Return the stored reason a post was picked, for the Why button."""
        stmt = select(Recommendation.reason).where(
            Recommendation.user_id == user_id,
            Recommendation.post_id == post_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_kind(self, user_id: int, post_id: UUID) -> str | None:
        """Return whether a post was picked to ``exploit`` or ``explore``, or None if not picked."""
        stmt = select(Recommendation.kind).where(
            Recommendation.user_id == user_id,
            Recommendation.post_id == post_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _brief(post: Post, summary: str | None) -> PostBrief:
        return PostBrief(
            post_id=post.id,
            hn_id=post.hn_id,
            title=clip(post.title, 200),
            domain=post.domain,
            score=post.score or 0,
            summary=clip(summary, SUMMARY_CHARS),
        )
