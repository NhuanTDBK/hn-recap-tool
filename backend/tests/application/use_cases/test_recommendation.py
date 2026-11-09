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

    def _brief(self, hn_id: int) -> PostBrief:
        return PostBrief(uuid4(), hn_id, f"Title {hn_id}", "x.com", 50, "summary")

    # signals
    async def get_activity(self, user_id):
        return self.activity

    async def get_briefs(self, user_id, post_ids):
        return {i: self.briefs[i] for i in post_ids if i in self.briefs}

    async def get_recent_sent_post_ids(self, user_id, since):
        return self.sent_ids

    async def get_candidates(self, user_id, cutoff, limit):
        return self.candidates

    # run state
    async def delete_stale_unsent(self, user_id, today):
        stale = [r for r in self.recs if r.sent_at is None and r.recommended_on < today]
        self.recs = [r for r in self.recs if r not in stale]
        return len(stale)

    async def get_pending(self, user_id, today):
        return [r for r in self.recs if r.sent_at is None and r.recommended_on == today]

    async def has_run_on(self, user_id, day):
        return any(r.run_date == day for r in self.runs)

    async def count_sent(self, user_id, day):
        return sum(
            1 for r in self.recs if r.sent_at is not None and r.recommended_on == day
        )

    async def get_run_interests(self, user_id, day):
        return next((r.interests for r in reversed(self.runs) if r.run_date == day), [])

    async def create_run(
        self, user_id, day, interests, counts, model, input_tokens, output_tokens
    ):
        run = SimpleNamespace(
            id=uuid4(), run_date=day, interests=interests, counts=counts, model=model
        )
        self.runs.append(run)
        return run

    async def add_picks(self, run_id, user_id, day, picks):
        rows = [
            SimpleNamespace(
                id=uuid4(),
                post_id=pid,
                rank=rank,
                fit_score=fit,
                reason=reason,
                recommended_on=day,
                sent_at=None,
                message_id=None,
            )
            for pid, rank, fit, reason in picks
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
    def __init__(self, fail_hn_ids=(), fail_header=False):
        self.headers: list = []
        self.picks: list = []
        self.fail_hn_ids = set(fail_hn_ids)
        self.fail_header = fail_header
        self._next = 500

    async def send_header(self, chat_id, topic_id, count, interests):
        if self.fail_header:
            raise RuntimeError("telegram down")
        self.headers.append((chat_id, topic_id, count, interests))
        self._next += 1
        return self._next

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
async def test_header_sent_once_with_count_and_interests_into_the_topic():
    uc, _, sender, _ = make(ranker=FakeRanker([5, 5], interests=["rust", "databases"]))
    await uc.run(USER, now=NOW)

    assert sender.headers == [(CHAT_ID, TOPIC_ID, 2, ["rust", "databases"])]
    assert all(p[0] == CHAT_ID and p[1] == TOPIC_ID for p in sender.picks)
    assert [(p[3], p[4]) for p in sender.picks] == [(1, 2), (2, 2)]


@pytest.mark.asyncio
async def test_daily_cap_is_a_ceiling():
    with patch.object(settings, "recommendation_daily_max", 2):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        stats = await uc.run(USER, now=NOW)

    assert stats["sent"] == 2 == len(sender.picks) == len(repo.recs)


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
    assert sender.headers == [] and sender.picks == []
    assert len(repo.runs) == 1  # so a rerun today does not pay for another LLM call

    again = await uc.run(USER, now=NOW)
    assert again["status"] == "already_ran" and ranker.calls == 1


@pytest.mark.asyncio
async def test_second_run_same_day_makes_no_llm_call_and_sends_nothing():
    uc, _, sender, ranker = make()
    await uc.run(USER, now=NOW)
    sent_first = len(sender.picks)

    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "already_ran"
    assert ranker.calls == 1 and len(sender.picks) == sent_first


@pytest.mark.asyncio
async def test_force_respects_what_was_already_sent_today():
    with patch.object(settings, "recommendation_daily_max", 3):
        uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
        repo.runs.append(SimpleNamespace(run_date=TODAY))
        repo.recs = [
            SimpleNamespace(
                id=uuid4(), post_id=uuid4(), recommended_on=TODAY, sent_at=NOW, rank=i
            )
            for i in range(2)
        ]
        stats = await uc.run(USER, force=True, now=NOW)

    assert stats["sent"] == 1  # 3 allowed, 2 already sent


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
async def test_header_failure_leaves_every_pick_unsent():
    uc, repo, sender, _ = make(sender=FakeSender(fail_header=True))
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "send_failed" and stats["sent"] == 0
    assert sender.picks == [] and all(r.sent_at is None for r in repo.recs)


@pytest.mark.asyncio
async def test_unsent_picks_resume_without_llm_or_header_and_never_exceed_the_cap():
    uc, repo, sender, ranker = make(sender=FakeSender(fail_hn_ids={101}))
    await uc.run(USER, now=NOW)  # 101 fails and stays pending
    assert len(await repo.get_pending(7, TODAY)) == 1

    sender.fail_hn_ids.clear()
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "resumed" and stats["sent"] == 1
    assert ranker.calls == 1  # no second LLM call
    assert len(sender.headers) == 1  # no second header
    assert len(repo.recs) == 4 and all(r.sent_at for r in repo.recs)


@pytest.mark.asyncio
async def test_resume_after_a_failed_header_sends_the_header_without_llm():
    uc, repo, sender, ranker = make(
        sender=FakeSender(fail_header=True),
        ranker=FakeRanker([5, 5, 3, 3, 3], interests=["rust"]),
    )
    await uc.run(USER, now=NOW)
    assert sender.headers == [] and sender.picks == []

    sender.fail_header = False
    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "resumed" and stats["sent"] == 2
    assert sender.headers == [(CHAT_ID, TOPIC_ID, 2, ["rust"])]
    assert ranker.calls == 1 and all(r.sent_at for r in repo.recs)


@pytest.mark.asyncio
async def test_header_failing_again_on_resume_keeps_picks_for_a_later_try():
    uc, repo, sender, _ = make(sender=FakeSender(fail_header=True))
    await uc.run(USER, now=NOW)

    stats = await uc.run(USER, now=NOW)

    assert stats["status"] == "send_failed" and sender.picks == []
    assert repo.recs and all(r.sent_at is None for r in repo.recs)


@pytest.mark.asyncio
async def test_unsent_picks_from_an_earlier_day_are_discarded_not_sent():
    uc, repo, sender, _ = make(ranker=FakeRanker([5, 5, 5, 5, 5]))
    repo.recs = [
        SimpleNamespace(
            id=uuid4(),
            post_id=uuid4(),
            recommended_on=TODAY - timedelta(days=1),
            sent_at=None,
            rank=1,
        )
    ]
    await uc.run(USER, now=NOW)

    assert all(r.recommended_on == TODAY for r in repo.recs)  # the stale one is gone


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
