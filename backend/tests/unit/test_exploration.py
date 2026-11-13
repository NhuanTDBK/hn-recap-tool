"""Tests for the exploration rules: topic records, the explore budget and which offers win."""

import random
from datetime import date, timedelta
from uuid import uuid4

from app.domain.exploration import (
    COLD_START_PICKS,
    COLD_START_RATIO,
    KIND_EXPLOIT,
    KIND_EXPLORE,
    ExplorePick,
    SentPick,
    TopicStats,
    choose_explorers,
    compute_topic_stats,
    effective_ratio,
    explore_budget,
    in_cooldown,
    kind_metrics,
    normalize_topic,
)
from app.domain.recommendation import ActivityBuckets

TODAY = date(2026, 11, 10)


def buckets(saved=(), rejected=(), opened=(), engaged=()) -> ActivityBuckets:
    saved, rejected, opened = list(saved), list(rejected), list(opened)
    return ActivityBuckets(
        saved_ids=saved,
        not_for_me_ids=rejected,
        opened_ids=opened,
        engaged_ids=set(saved) | set(rejected) | set(opened) | set(engaged),
    )


def sent(topic="rust", kind=KIND_EXPLOIT, days_ago=5) -> SentPick:
    return SentPick(uuid4(), topic, kind, TODAY - timedelta(days=days_ago))


def offer(hn_id, topic, quality=5) -> ExplorePick:
    return ExplorePick(hn_id, topic, quality, "worth a look")


# ------------------------------------------------------------------ topics


def test_normalize_topic_lowercases_collapses_and_cuts():
    assert normalize_topic("  LLM   Agents ") == "llm agents"
    assert normalize_topic(None) == ""
    assert len(normalize_topic("x" * 200)) == 40


# ------------------------------------------------------------ topic records


def test_outcomes_move_the_topic_record():
    saved, rejected, opened, ignored = (sent() for _ in range(4))
    stats = compute_topic_stats(
        [saved, rejected, opened, ignored],
        buckets(
            saved=[saved.post_id], rejected=[rejected.post_id], opened=[opened.post_id]
        ),
        TODAY,
        half_life_days=0,
    )["rust"]

    assert (stats.shown, stats.saved, stats.rejected, stats.ignored) == (4, 1, 1, 1)
    assert stats.yes == 1.0 + 0.3  # a save and an open
    assert stats.no == 1.0 + 0.2  # a rejection and a silent pick
    assert stats.alpha == 1 + stats.yes and stats.beta == 1 + stats.no


def test_a_pick_sent_today_is_not_judged_yet():
    fresh = sent(days_ago=0)
    assert compute_topic_stats([fresh], buckets(), TODAY, 0) == {}


def test_looking_at_the_reason_is_neither_yes_nor_no():
    looked = sent()
    stats = compute_topic_stats([looked], buckets(engaged=[looked.post_id]), TODAY, 0)[
        "rust"
    ]
    assert (stats.shown, stats.yes, stats.no, stats.ignored) == (1, 0.0, 0.0, 0)


def test_picks_without_a_topic_are_skipped():
    assert compute_topic_stats([sent(topic=None)], buckets(), TODAY, 30) == {}


def test_old_outcomes_fade_by_the_half_life():
    old = sent(days_ago=30)
    stats = compute_topic_stats([old], buckets(saved=[old.post_id]), TODAY, 30)["rust"]
    assert abs(stats.yes - 0.5) < 1e-9


def test_only_a_rejected_explore_pick_starts_a_cooldown():
    exploit_no = sent("go", KIND_EXPLOIT, days_ago=3)
    explore_no = sent("art", KIND_EXPLORE, days_ago=3)
    stats = compute_topic_stats(
        [exploit_no, explore_no],
        buckets(rejected=[exploit_no.post_id, explore_no.post_id]),
        TODAY,
        30,
    )
    assert stats["go"].last_explore_reject is None
    assert stats["art"].last_explore_reject == TODAY - timedelta(days=3)


def test_cooldown_ends_after_the_configured_days():
    stats = TopicStats("art", last_explore_reject=TODAY - timedelta(days=29))
    assert in_cooldown(stats, TODAY, 30)
    assert not in_cooldown(stats, TODAY + timedelta(days=1), 30)
    assert not in_cooldown(None, TODAY, 30)
    assert not in_cooldown(TopicStats("x"), TODAY, 30)


# ------------------------------------------------------------------ budget


def test_ratio_is_raised_while_the_record_is_thin_and_clamped():
    assert effective_ratio(0.2, 0) == COLD_START_RATIO
    assert effective_ratio(0.2, COLD_START_PICKS) == 0.2
    assert effective_ratio(0.7, 0) == 0.7  # already above the cold-start floor
    assert effective_ratio(0, 0) == 0  # off stays off
    assert effective_ratio(5, 100) == 0.9


def test_budget_follows_the_ratio_exactly_when_it_divides_evenly():
    rng = random.Random(1)
    # ratio 0.5 means as many explore picks as exploit picks
    assert explore_budget(2, 0, 0.5, 10, rng) == 2
    assert explore_budget(4, 0, 0.5, 10, rng) == 4


def test_budget_respects_the_daily_ceiling():
    rng = random.Random(1)
    assert explore_budget(10, 0, 0.5, 3, rng) == 3
    assert explore_budget(10, 2, 0.5, 3, rng) == 1
    assert explore_budget(10, 3, 0.5, 3, rng) == 0


def test_budget_is_zero_when_off():
    rng = random.Random(1)
    assert explore_budget(5, 0, 0, 3, rng) == 0
    assert explore_budget(5, 0, 0.5, 0, rng) == 0


def test_budget_averages_out_to_the_ratio_over_many_small_runs():
    rng = random.Random(42)
    runs = 4000
    # 3 exploit picks per run at ratio 0.2: expected 0.75 explore picks per run
    total = sum(explore_budget(3, 0, 0.2, 99, rng) for _ in range(runs))
    assert abs(total / runs - 0.75) < 0.05


def test_a_run_with_no_exploit_picks_can_still_explore_sometimes():
    rng = random.Random(7)
    hits = sum(explore_budget(0, 0, 0.3, 99, rng) for _ in range(4000))
    assert 0.25 < hits / 4000 < 0.35


# ------------------------------------------------------------------ choosing


def choose(offered, stats=None, budget=5, **kw):
    kw.setdefault("rng", random.Random(0))
    return choose_explorers(
        offered,
        stats or {},
        today=TODAY,
        budget=budget,
        min_quality=kw.pop("min_quality", 4),
        cooldown_days=30,
        **kw,
    )


def test_low_quality_offers_are_never_explored():
    got = choose([offer(1, "a", quality=3), offer(2, "b", quality=4)])
    assert [o.hn_id for o in got] == [2]


def test_offers_without_a_topic_are_skipped():
    assert choose([offer(1, "")]) == []


def test_a_topic_in_cooldown_is_left_alone():
    stats = {"art": TopicStats("art", last_explore_reject=TODAY - timedelta(days=2))}
    assert [o.hn_id for o in choose([offer(1, "art"), offer(2, "film")], stats)] == [2]


def test_one_post_per_topic_per_run():
    got = choose([offer(1, "film"), offer(2, "film"), offer(3, "art")])
    assert sorted(o.topic for o in got) == ["art", "film"]


def test_budget_caps_the_result_and_zero_returns_nothing():
    offers = [offer(i, f"t{i}") for i in range(6)]
    assert len(choose(offers, budget=2)) == 2
    assert choose(offers, budget=0) == []


def test_posts_already_chosen_as_exploit_picks_are_skipped():
    assert choose([offer(1, "a"), offer(2, "b")], skip_hn_ids={1}) == [offer(2, "b")]


def test_a_topic_the_reader_keeps_rejecting_rarely_wins_over_an_untried_one():
    bad = TopicStats("bad", no=8.0)  # Beta(1, 9): mean 0.1
    wins = 0
    for seed in range(400):
        got = choose(
            [offer(1, "bad"), offer(2, "new")],
            {"bad": bad},
            budget=1,
            rng=random.Random(seed),
        )
        wins += got[0].topic == "new"
    assert wins > 320  # expected about 0.9 of 400


def test_a_topic_the_reader_keeps_saving_usually_wins():
    good = TopicStats("good", yes=8.0)  # Beta(9, 1)
    wins = 0
    for seed in range(400):
        got = choose(
            [offer(1, "good"), offer(2, "new")],
            {"good": good},
            budget=1,
            rng=random.Random(seed),
        )
        wins += got[0].topic == "good"
    assert wins > 300


# ------------------------------------------------------------------ metrics


def test_metrics_count_outcomes_per_kind_and_skip_fresh_picks():
    a, b, c, fresh = (
        sent(kind=KIND_EXPLOIT),
        sent(kind=KIND_EXPLORE),
        sent(kind=KIND_EXPLORE),
        sent(kind=KIND_EXPLORE, days_ago=0),
    )
    m = kind_metrics(
        [a, b, c, fresh],
        buckets(saved=[a.post_id, b.post_id], rejected=[c.post_id]),
        TODAY,
    )
    assert m[KIND_EXPLOIT] == {
        "judged": 1,
        "saved": 1,
        "rejected": 0,
        "opened": 0,
        "ignored": 0,
    }
    assert m[KIND_EXPLORE] == {
        "judged": 2,
        "saved": 1,
        "rejected": 1,
        "opened": 0,
        "ignored": 0,
    }
