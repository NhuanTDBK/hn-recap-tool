"""Tests for the pure recommendation rules: how raw taps become taste signals."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.recommendation import classify_activity, clip

T0 = datetime(2026, 11, 1, tzinfo=timezone.utc)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_repeated_saves_count_once():
    a = uuid4()
    buckets = classify_activity(
        [(a, "save", at(1)), (a, "save", at(2)), (a, "save", at(3))]
    )
    assert buckets.saved_ids == [a]


def test_newest_verdict_wins_save_after_not_for_me():
    a = uuid4()
    buckets = classify_activity([(a, "not_for_me", at(1)), (a, "save", at(2))])
    assert buckets.saved_ids == [a]
    assert buckets.not_for_me_ids == []


def test_newest_verdict_wins_not_for_me_after_save():
    a = uuid4()
    buckets = classify_activity([(a, "save", at(1)), (a, "not_for_me", at(2))])
    assert buckets.saved_ids == []
    assert buckets.not_for_me_ids == [a]


def test_input_order_does_not_matter():
    a = uuid4()
    rows = [(a, "save", at(2)), (a, "not_for_me", at(1))]
    assert (
        classify_activity(rows).saved_ids
        == classify_activity(list(reversed(rows))).saved_ids
        == [a]
    )


def test_buckets_are_newest_first():
    old, mid, new = uuid4(), uuid4(), uuid4()
    buckets = classify_activity(
        [(old, "save", at(1)), (new, "save", at(9)), (mid, "save", at(5))]
    )
    assert buckets.saved_ids == [new, mid, old]


def test_opened_only_counts_without_a_verdict():
    saved, rejected, only_opened = uuid4(), uuid4(), uuid4()
    buckets = classify_activity(
        [
            (saved, "show_more", at(1)),
            (saved, "save", at(2)),
            (rejected, "show_more", at(3)),
            (rejected, "not_for_me", at(4)),
            (only_opened, "show_more", at(5)),
        ]
    )
    assert buckets.opened_ids == [only_opened]


def test_why_marks_engaged_but_is_not_a_verdict():
    a = uuid4()
    buckets = classify_activity([(a, "why", at(1))])
    assert a in buckets.engaged_ids
    assert buckets.saved_ids == buckets.not_for_me_ids == buckets.opened_ids == []


def test_unrelated_actions_are_ignored():
    a = uuid4()
    buckets = classify_activity([(a, "rate_up", at(1)), (a, "rate_down", at(2))])
    assert a not in buckets.engaged_ids


def test_clip_collapses_whitespace_and_adds_ellipsis():
    assert clip("a  b\n\nc", 50) == "a b c"
    out = clip("x" * 100, 10)
    assert len(out) == 10 and out.endswith("…")
    assert clip(None, 5) == ""
