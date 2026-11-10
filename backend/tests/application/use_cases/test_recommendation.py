"""Tests for the daily recommendation use case.

Run against an in-memory repository and a recording sender, so the rules (cap, fit
cut-off, no repeats, resume after a crash) are tested without a database or Telegram.
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.application.use_cases.recommendation import DailyRecommendationUseCase
from app.domain.recommendation import PostBrief, RankedPick, RankingResult
from app.infrastructure.agents.recommendation_agent import (
    RankingError,
    RankingParseError,
)
from app.infrastructure.config.settings import settings
from app.infrastructure.database.models import Post, User

# 08:30 on 2026-11-09 in UTC+7
NOW = datetime(2026, 11, 9, 1, 30, tzinfo=timezone.utc)
TODAY = date(2026, 11, 9)
CHAT_ID = -1001234567890
TOPIC_ID = 43


class FakeRepo:
    """In-memory stand-in for PostgresRecommendationRepository."""

    def __init__(self, n_saves: int = 6, n_candidates: int = 5):
        self.briefs: dict = {}
        self.posts: dict = {}
        self.activity: list = []
        for i in range(n_saves):
            b = self._brief(1000 + i)
            self.briefs[b.post_id] = b
            self.activity.append(
                (b.post_id, "save", NOW - timedelta(days=1, minutes=i))
            )
        self.candidates = [self._brief(100 + i) for i in range(n_candidates)]
        for c in self.candidates:
            self.posts[c.post_id] = Post(
                id=c.post_id,
                hn_id=c.hn_id,
                title=c.title,
                url="https://x.com/a",
                score=50,
                comment_count=3,
            )
        self.sent_ids: list = []
        self.runs: list = []
        self.recs: list = []
        self.cutoffs: list = []

    def _brief(self, hn_id: int) -> PostBrief:
        return PostBrief(uuid4(), hn_id, f"Title {hn_id}", "x.com", 50, "summary")

    def add_candidates(self, *hn_ids: int) -> list[PostBrief]:
        """Add fresh candidate posts (brief and post row), as new summaries would be."""
        added = [self._brief(i) for i in hn_ids]
        for c in added:
            self.posts[c.post_id] = Post(
                id=c.post_id,
                hn_id=c.hn_id,
                title=c.title,
                url="https://x.com/n",
                score=50,
            )
        self.candidates = self.candidates + added
        return added

    # signals
    async def get_activity(self, user_id):
        return self.activity

    async def get_briefs(self, user_id, post_ids):
        return {i: self.briefs[i] for i in post_ids if i in self.briefs}

    async def get_recent_sent_post_ids(self, user_id, since):
        return self.sent_ids

    async def get_candidates(self, user_id, cutoff, limit):
        self.cutoffs.append(cutoff)
        taken = {r.post_id for r in self.recs}  # never recommend a post twice
        return [c for c in self.candidates if c.post_id not in taken]

    # run state
    async def delete_stale_unsent(self, user_id, before):
        stale = [
            r for r in self.recs if r.sent_at is None and r.recommended_on < before
        ]
        self.recs = [r for r in self.recs if r not in stale]
        return len(stale)

    async def get_pending(self, user_id, since):
        return sorted(
            (r for r in self.recs if r.sent_at is None and r.recommended_on >= since),
            key=lambda r: (r.recommended_on, r.rank),
        )

    async def get_last_run_at(self, user_id):
        return max((r.created_at for r in self.runs), default=None)

    async def count_for_day(self, user_id, day):
        return sum(1 for r in self.recs if r.recommended_on == day)

    async def create_run(
        self,
        user_id,
        day,
        interests,
        counts,
        model,
        input_tokens,
        output_tokens,
        started_at,
    ):
        run = SimpleNamespace(
            id=uuid4(),
            run_date=day,
            interests=interests,
            counts=counts,
            model=model,
            created_at=started_at,
        )
        self.runs.append(run)
        return run

    async def add_picks(self, run_id, user_id, day, picks):
        taken = {r.post_id for r in self.recs}  # the database's unique (user, post)
        rows = [
            SimpleNamespace(
                id=uuid4(),
                run_id=run_id,
                post_id=pid,
                rank=rank,
                fit_score=fit,
                reason=reason,
                recommended_on=day,
                sent_at=None,
                message_id=None,
            )
            for pid, rank, fit, reason in picks
            if pid not in taken
        ]
        self.recs.extend(rows)
        return rows

    async def mark_sent(self, rec_id, message_id):
        for r in self.recs:
            if r.id == rec_id:
                r.message_id, r.sent_at = message_id, NOW

    async def get_posts_with_summaries(self, user_id, post_ids):
        return {i: (self.posts[i], "summary") for i in post_ids if i in self.posts}


class FakeSender:
    def __init__(self, fail_hn_ids=()):
        self.picks: list = []
        self.fail_hn_ids = set(fail_hn_ids)
        self._next = 500

    async def send_pick(self, chat_id, topic_id, post, summary, position, total):
        if post.hn_id in self.fail_hn_ids:
            raise RuntimeError("rejected")
        self.picks.append((chat_id, topic_id, post.hn_id, position, total))
        self._next += 1
        return self._next


class FakeRanker:
    """Returns picks for the first N candidates with the given fit scores."""

    def __init__(self, fits, interests=("databases",), error=None):
        self.fits = fits
        self.interests = list(interests)
        self.error = error
        self.calls = 0
        self.last_signals = None

    async def __call__(self, signals, candidates):
        self.calls += 1
        self.last_signals = signals
        if self.error:
            raise self.error
        picks = [
            RankedPick(c.hn_id, fit, f"because {c.hn_id}")
            for c, fit in zip(candidates, self.fits, strict=False)
        ]
        return RankingResult(
            self.interests, picks, input_tokens=1000, output_tokens=100
        )


@pytest.fixture(autouse=True)
def rec_settings():
    with (
        patch.object(settings, "telegram_recommendation_topic_id", TOPIC_ID),
        patch.object(settings, "recommendation_timezone", "Asia/Ho_Chi_Minh"),
        patch.object(settings, "recommendation_daily_max", 20),
        patch.object(settings, "recommendation_min_fit", 4),
        patch.object(settings, "recommendation_min_saves", 5),
        patch.object(settings, "recommendation_lookback_hours", 36),
        patch.object(settings, "recommendation_ignored_days", 14),
        patch.object(settings, "recommendation_min_gap_minutes", 120),
    ):
        yield


def make(repo=None, sender=None, ranker=None, usage=None):
    repo = repo or FakeRepo()
    sender = sender if sender is not None else FakeSender()
    ranker = ranker or FakeRanker([5, 5, 4, 3, 5])
    uc = DailyRecommendationUseCase(
        repo, sender, ranker, model="m", usage_logger=usage, message_delay_seconds=0
    )
    return uc, repo, sender, ranker


USER = User(id=7, telegram_id=CHAT_ID)


# ------------------------------------------------------------------ selection


@pytest.mark.asyncio
async def test_sends_only_picks_meeting_the_fit_cutoff():
    uc, repo, sender, _ = make(ranker=FakeRanker([5, 4, 3, 2, 5]))
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "sent"
    assert stats["sent"] == 3  # fits 5, 4, 5 pass; 3 and 2 do not
    assert len(stats["dropped"]) == 2
    assert [p[2] for p in sender.picks] == [
        100,
        104,
        101,
    ]  # best fit first, ties in model order
    assert len(repo.runs) == 1 and all(r.sent_at is not None for r in repo.recs)


@pytest.mark.asyncio
async def test_picks_go_into_the_topic_with_no_header_message():
    uc, _, sender, _ = make(ranker=FakeRanker([5, 5], interests=["rust"]))
    await uc.run(USER, now=NOW)

    assert all(p[0] == CHAT_ID and p[1] == TOPIC_ID for p in sender.picks)
    assert [(p[3], p[4]) for p in sender.picks] == [(1, 2), (2, 2)]
    assert not hasattr(sender, "headers")


@pytest.mark.asyncio
async def test_since_overrides_the_last_run_for_a_backfill():
    uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
    repo.runs.append(SimpleNamespace(id=uuid4(), created_at=NOW - timedelta(hours=5)))
    seen = {}
    real = repo.get_candidates

    async def spy(user_id, cutoff, limit):
        seen["cutoff"] = cutoff
        return await real(user_id, cutoff, limit)

    repo.get_candidates = spy
    since = NOW - timedelta(days=2)
    await uc.run(USER, now=NOW, since=since)

    assert seen["cutoff"] == since


@pytest.mark.asyncio
async def test_daily_cap_is_a_ceiling():
    with patch.object(settings, "recommendation_daily_max", 2):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        stats = await uc.run(USER, now=NOW)

    assert stats["sent"] == 2 == len(sender.picks) == len(repo.recs)


@pytest.mark.asyncio
async def test_no_daily_cap_by_default_sends_every_strong_match():
    with patch.object(settings, "recommendation_daily_max", 0):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        stats = await uc.run(USER, now=NOW)
        repo.add_candidates(300, 301, 302)
        again = await uc.run(USER, now=NOW + timedelta(hours=4))

    assert stats["sent"] == 5
    assert again["status"] == "sent" and len(sender.picks) == 8


@pytest.mark.asyncio
async def test_fewer_strong_matches_than_cap_sends_fewer():
    uc, _, sender, _ = make(ranker=FakeRanker([5, 3, 3, 3, 3]))
    stats = await uc.run(USER, now=NOW)

    assert stats["sent"] == 1 and len(sender.picks) == 1


@pytest.mark.asyncio
async def test_nothing_qualifying_sends_nothing_but_still_records_the_run():
    uc, repo, sender, ranker = make(ranker=FakeRanker([3, 3, 2, 2, 1]))
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "no_picks"
    assert sender.picks == []
    assert len(repo.runs) == 1  # so the next run starts after these posts

    again = await uc.run(USER, now=NOW)
    assert again["status"] == "too_soon" and ranker.calls == 1


@pytest.mark.asyncio
async def test_a_run_right_after_another_makes_no_llm_call_and_sends_nothing():
    uc, _, sender, ranker = make()
    await uc.run(USER, now=NOW)
    sent_first = len(sender.picks)

    stats = await uc.run(USER, now=NOW + timedelta(minutes=30))

    assert stats["status"] == "too_soon"
    assert ranker.calls == 1 and len(sender.picks) == sent_first


@pytest.mark.asyncio
async def test_force_overrides_the_minimum_gap():
    uc, repo, _, ranker = make()
    await uc.run(USER, now=NOW)
    repo.add_candidates(300, 301)

    stats = await uc.run(USER, force=True, now=NOW + timedelta(minutes=30))

    assert stats["status"] in {"sent", "no_picks"} and ranker.calls == 2


@pytest.mark.asyncio
async def test_a_later_run_only_sees_posts_newer_than_the_last_run():
    uc, repo, _, ranker = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
    await uc.run(USER, now=NOW)
    later = NOW + timedelta(hours=4)

    await uc.run(USER, now=later)

    assert repo.cutoffs[0] == NOW - timedelta(hours=36)  # first run: the lookback
    assert repo.cutoffs[1] == NOW  # next run: since the last one started
    assert ranker.calls == 1  # every candidate was already picked, so nothing to rank


@pytest.mark.asyncio
async def test_a_post_picked_in_one_run_is_never_picked_in_the_next():
    uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
    await uc.run(USER, now=NOW)
    repo.add_candidates(300, 301)  # last run's posts are still in the feed

    await uc.run(USER, now=NOW + timedelta(hours=4))

    sent_hn = [p[2] for p in sender.picks]
    assert len(sent_hn) == len(set(sent_hn)) == 7
    assert {300, 301} <= set(sent_hn)


@pytest.mark.asyncio
async def test_daily_cap_is_shared_by_all_of_a_days_runs():
    with patch.object(settings, "recommendation_daily_max", 3):
        uc, repo, sender, ranker = make(ranker=FakeRanker([5, 5]))
        await uc.run(USER, now=NOW)  # 2 of 3
        repo.add_candidates(300, 301, 302, 303, 304)
        ranker.fits = [5, 5, 5, 5, 5]
        await uc.run(USER, now=NOW + timedelta(hours=4))  # the last 1 of 3
        calls_before = ranker.calls
        stats = await uc.run(USER, now=NOW + timedelta(hours=8))

    assert len(sender.picks) == 3
    assert stats["status"] == "daily_cap_reached"
    assert ranker.calls == calls_before  # no LLM call once the cap is used


@pytest.mark.asyncio
async def test_the_daily_cap_starts_over_the_next_local_day():
    with patch.object(settings, "recommendation_daily_max", 2):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        await uc.run(USER, now=NOW)
        repo.add_candidates(300, 301)
        stats = await uc.run(USER, now=NOW + timedelta(hours=24))

    assert stats["status"] == "sent" and len(sender.picks) == 4


@pytest.mark.asyncio
async def test_an_overlapping_run_cannot_make_a_post_go_out_twice():
    repo = FakeRepo()
    sender = FakeSender()
    inner = FakeRanker([5, 5, 5, 5, 5])

    async def ranker(signals, candidates):
        result = await inner(signals, candidates)
        # A second run stores the first candidate while this one is still ranking.
        repo.recs.append(
            SimpleNamespace(
                id=uuid4(),
                run_id=uuid4(),
                post_id=candidates[0].post_id,
                recommended_on=TODAY,
                sent_at=NOW,
                rank=1,
            )
        )
        return result

    uc = DailyRecommendationUseCase(
        repo, sender, ranker, model="m", message_delay_seconds=0
    )
    await uc.run(USER, now=NOW)

    assert 100 not in [p[2] for p in sender.picks]  # the other run owns it
    assert len(sender.picks) == 4


@pytest.mark.asyncio
async def test_force_still_respects_the_picks_already_made_today():
    with patch.object(settings, "recommendation_daily_max", 3):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        repo.runs.append(SimpleNamespace(id=uuid4(), created_at=NOW))
        repo.recs = [
            SimpleNamespace(
                id=uuid4(),
                run_id=repo.runs[0].id,
                post_id=uuid4(),
                recommended_on=TODAY,
                sent_at=NOW,
                rank=i,
            )
            for i in range(2)
        ]
        stats = await uc.run(USER, force=True, now=NOW)

    assert stats["sent"] == 1  # 3 allowed, 2 already picked


@pytest.mark.asyncio
async def test_day_is_the_local_date_not_utc():
    late_utc = datetime(
        2026, 11, 9, 18, 30, tzinfo=timezone.utc
    )  # 01:30 on the 10th in UTC+7
    uc, repo, _, _ = make()
    stats = await uc.run(USER, now=late_utc)

    assert stats["date"] == "2026-11-10"
    assert repo.runs[0].run_date == date(2026, 11, 10)


# --------------------------------------------------------------------- guards


@pytest.mark.asyncio
async def test_too_few_saves_skips_without_calling_the_model():
    uc, _, sender, ranker = make(repo=FakeRepo(n_saves=4))
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "too_few_saves"
    assert ranker.calls == 0 and sender.picks == []


@pytest.mark.asyncio
async def test_a_save_overridden_by_not_for_me_no_longer_counts():
    repo = FakeRepo(n_saves=5)
    post_id = repo.activity[0][0]
    repo.activity.append((post_id, "not_for_me", NOW))  # newest tap
    uc, _, _, ranker = make(repo=repo)

    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "too_few_saves" and ranker.calls == 0


@pytest.mark.asyncio
async def test_no_candidates_skips_without_calling_the_model():
    uc, _, _, ranker = make(repo=FakeRepo(n_candidates=0))
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "no_candidates" and ranker.calls == 0


@pytest.mark.asyncio
async def test_missing_topic_refuses_to_send_into_general():
    with patch.object(settings, "telegram_recommendation_topic_id", None):
        uc, repo, sender, ranker = make()
        stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "no_topic"
    assert ranker.calls == 0 and sender.picks == [] and repo.runs == []


# ------------------------------------------------------------ signals to model


@pytest.mark.asyncio
async def test_ignored_means_sent_but_never_touched():
    repo = FakeRepo()
    touched, untouched = uuid4(), uuid4()
    for pid, n in ((touched, 1), (untouched, 2)):
        repo.briefs[pid] = PostBrief(pid, 2000 + n, f"Old {n}", None, 1, "")
    repo.sent_ids = [touched, untouched]
    repo.activity.append((touched, "show_more", NOW - timedelta(hours=2)))
    uc, _, _, ranker = make(repo=repo)

    await uc.run(USER, now=NOW, dry_run=True)

    assert [p.post_id for p in ranker.last_signals.ignored] == [untouched]
    assert [p.post_id for p in ranker.last_signals.opened] == [touched]


@pytest.mark.asyncio
async def test_signal_counts_reported():
    uc, _, _, _ = make()
    stats = await uc.run(USER, now=NOW, dry_run=True)

    assert stats["signals"] == {"saved": 6, "not_for_me": 0, "opened": 0, "ignored": 0}
    assert stats["candidate_count"] == 5


# --------------------------------------------------------------------- dry run


@pytest.mark.asyncio
async def test_dry_run_reports_picks_but_writes_and_sends_nothing():
    uc, repo, _, ranker = make(sender=None, ranker=FakeRanker([5, 4, 3, 2, 5]))
    uc.sender = None
    stats = await uc.run(USER, now=NOW, dry_run=True)

    assert stats["status"] == "dry_run"
    assert len(stats["picks"]) == 3 and len(stats["dropped"]) == 2
    assert stats["picks"][0]["reason"].startswith("because")
    assert repo.runs == [] and repo.recs == [] and ranker.calls == 1


# --------------------------------------------------------- failures and resume


@pytest.mark.asyncio
async def test_one_failed_pick_does_not_stop_the_rest_and_stays_unsent():
    uc, repo, sender, _ = make(
        sender=FakeSender(fail_hn_ids={101}), ranker=FakeRanker([5, 5, 5, 3, 3])
    )
    stats = await uc.run(USER, now=NOW)

    assert stats["sent"] == 2 and stats["failed"] == 1
    assert [r for r in repo.recs if r.sent_at is None] and len(
        [r for r in repo.recs if r.sent_at]
    ) == 2


@pytest.mark.asyncio
async def test_unsent_picks_resume_without_llm_and_never_exceed_the_cap():
    uc, repo, sender, ranker = make(sender=FakeSender(fail_hn_ids={101}))
    await uc.run(USER, now=NOW)  # 101 fails and stays pending
    assert len(await repo.get_pending(7, TODAY)) == 1

    sender.fail_hn_ids.clear()
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "resumed" and stats["sent"] == 1
    assert ranker.calls == 1  # no second LLM call
    assert len(repo.recs) == 4 and all(r.sent_at for r in repo.recs)


def unsent(repo, days_ago: int):
    run = SimpleNamespace(
        id=uuid4(),
        interests=["old"],
        created_at=NOW - timedelta(days=days_ago, hours=10),
    )
    repo.runs.append(run)
    post_id = uuid4()
    repo.posts[post_id] = Post(
        id=post_id, hn_id=900 + days_ago, title="Old", url="https://x.com/o", score=1
    )
    rec = SimpleNamespace(
        id=uuid4(),
        run_id=run.id,
        post_id=post_id,
        recommended_on=TODAY - timedelta(days=days_ago),
        sent_at=None,
        rank=1,
    )
    repo.recs.append(rec)
    return rec


@pytest.mark.asyncio
async def test_yesterdays_unsent_pick_is_resent():
    uc, repo, sender, _ = make(ranker=FakeRanker([3, 3, 3, 3, 3]))
    rec = unsent(repo, days_ago=1)

    await uc.run(USER, now=NOW)

    assert rec.sent_at is not None and 901 in [p[2] for p in sender.picks]


@pytest.mark.asyncio
async def test_unsent_picks_older_than_yesterday_are_discarded_not_sent():
    uc, repo, sender, _ = make(ranker=FakeRanker([3, 3, 3, 3, 3]))
    unsent(repo, days_ago=2)

    await uc.run(USER, now=NOW)

    assert repo.recs == [] and sender.picks == []


@pytest.mark.asyncio
async def test_ranking_failure_sends_nothing_and_records_the_spend():
    err = RankingParseError("bad json")
    err.input_tokens, err.output_tokens = 900, 5
    calls = []

    async def usage(**kwargs):
        calls.append(kwargs)

    uc, repo, sender, _ = make(ranker=FakeRanker([], error=err), usage=usage)
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "ranking_failed"
    assert sender.picks == [] and repo.runs == []  # no fallback to "top by score"
    assert calls[0]["status"] == "error" and calls[0]["input_tokens"] == 900


@pytest.mark.asyncio
async def test_model_call_failure_is_reported_and_records_the_spend():
    err = RankingError("rate limited")
    err.input_tokens = 800
    calls = []

    async def usage(**kwargs):
        calls.append(kwargs)

    uc, repo, sender, _ = make(ranker=FakeRanker([], error=err), usage=usage)
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "ranking_failed"
    assert sender.picks == [] and repo.runs == []
    assert calls[0]["status"] == "error" and calls[0]["input_tokens"] == 800


@pytest.mark.asyncio
async def test_usage_is_recorded_on_success():
    calls = []

    async def usage(**kwargs):
        calls.append(kwargs)

    uc, _, _, _ = make(usage=usage)
    await uc.run(USER, now=NOW)

    assert calls[0]["status"] == "success"
    assert (calls[0]["input_tokens"], calls[0]["output_tokens"]) == (1000, 100)


@pytest.mark.asyncio
async def test_a_failing_usage_logger_does_not_break_the_run():
    async def usage(**kwargs):
        raise RuntimeError("db hiccup")

    uc, _, sender, _ = make(usage=usage)
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "sent" and sender.picks
