"""Pure rules for exploring: how topics earn or lose a share of the picks.

Each topic is one arm of a bandit. A topic's record comes from what happened to the
posts we sent for it (saved, rejected, opened, ignored), faded with a half-life so an old
rejection eventually stops counting. The model only labels topics and rates quality; the
decision of how much to explore and what to explore is made here, with an injectable
random source so every rule can be tested.

Nothing here touches the database, the network or the LLM.
"""

import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:  # recommendation.py imports this module, so import it for typing only
    from app.domain.recommendation import ActivityBuckets

KIND_EXPLOIT = "exploit"
KIND_EXPLORE = "explore"

# fit_score stored on explore picks. The prompt defines fit 2 as "a stretch", which is
# exactly what an explore pick is: it does not match the profile, it is only good.
EXPLORE_FIT = 2

TOPIC_MAX_CHARS = 40
TOPICS_SHOWN = 40  # topic vocabulary offered to the model

# How much one outcome moves a topic's record. A save or a rejection is a verdict;
# an open is a hint; silence is noisy, so it barely counts.
WEIGHT_SAVE = 1.0
WEIGHT_NOT_FOR_ME = 1.0
WEIGHT_OPENED = 0.3
WEIGHT_IGNORED = 0.2

# A pick younger than this has had no real chance to be reacted to yet.
IGNORED_GRACE_DAYS = 1

# While the record is thin, explore more: there is little taste to exploit yet.
COLD_START_PICKS = 20
COLD_START_RATIO = 0.4
MAX_RATIO = 0.9

OUTCOME_SAVE = "save"
OUTCOME_NOT_FOR_ME = "not_for_me"
OUTCOME_OPENED = "opened"
OUTCOME_ENGAGED = "engaged"  # looked at (e.g. Why) but no verdict
OUTCOME_IGNORED = "ignored"
OUTCOME_PENDING = "pending"  # too new to judge


@dataclass(frozen=True)
class SentPick:
    """One recommendation that reached the reader, as the exploration rules see it."""

    post_id: UUID
    topic: str | None
    kind: str
    recommended_on: date


@dataclass(frozen=True)
class ExplorePick:
    """A post the model offered for exploring: good, but outside the reader's profile."""

    hn_id: int
    topic: str
    quality: int
    reason: str


@dataclass
class TopicStats:
    """What happened to the posts sent for one topic."""

    topic: str
    shown: int = 0
    saved: int = 0
    rejected: int = 0
    ignored: int = 0
    yes: float = 0.0  # faded weight of positive outcomes
    no: float = 0.0  # faded weight of negative outcomes
    last_explore_reject: date | None = None

    @property
    def alpha(self) -> float:
        """Beta prior 1 plus the faded yes weight."""
        return 1.0 + self.yes

    @property
    def beta(self) -> float:
        """Beta prior 1 plus the faded no weight."""
        return 1.0 + self.no


def normalize_topic(raw: object) -> str:
    """Lower-case, collapse whitespace and cut a topic label so equal topics compare equal."""
    text = " ".join(str(raw or "").lower().split())
    return text[:TOPIC_MAX_CHARS].rstrip()


def _fade(age_days: int, half_life_days: float) -> float:
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (max(age_days, 0) / half_life_days)


def compute_topic_stats(
    history: Iterable[SentPick],
    buckets: "ActivityBuckets",
    today: date,
    half_life_days: float,
) -> dict[str, TopicStats]:
    """Build each topic's record from the picks that were sent.

    Picks without a topic (sent before exploring existed) are skipped.

    Args:
        history: Sent picks
        buckets: The reader's activity, one verdict per post
        today: Local date now
        half_life_days: Days for a pick's weight to halve; 0 or less disables fading

    Returns:
        Stats keyed by topic
    """
    sets = _OutcomeLookup(buckets)
    stats: dict[str, TopicStats] = {}
    for pick in history:
        if not pick.topic:
            continue
        outcome = sets.outcome(pick.post_id, pick.recommended_on, today)
        if outcome == OUTCOME_PENDING:
            continue
        entry = stats.setdefault(pick.topic, TopicStats(topic=pick.topic))
        entry.shown += 1
        weight = _fade((today - pick.recommended_on).days, half_life_days)
        if outcome == OUTCOME_SAVE:
            entry.saved += 1
            entry.yes += WEIGHT_SAVE * weight
        elif outcome == OUTCOME_NOT_FOR_ME:
            entry.rejected += 1
            entry.no += WEIGHT_NOT_FOR_ME * weight
            if pick.kind == KIND_EXPLORE and (
                entry.last_explore_reject is None
                or pick.recommended_on > entry.last_explore_reject
            ):
                entry.last_explore_reject = pick.recommended_on
        elif outcome == OUTCOME_OPENED:
            entry.yes += WEIGHT_OPENED * weight
        elif outcome == OUTCOME_IGNORED:
            entry.ignored += 1
            entry.no += WEIGHT_IGNORED * weight
    return stats


class _OutcomeLookup:
    """``outcome_of`` with the bucket sets built once, not per pick."""

    def __init__(self, buckets: "ActivityBuckets"):
        self.saved = set(buckets.saved_ids)
        self.rejected = set(buckets.not_for_me_ids)
        self.opened = set(buckets.opened_ids)
        self.engaged = buckets.engaged_ids

    def outcome(self, post_id: UUID, recommended_on: date, today: date) -> str:
        if post_id in self.saved:
            return OUTCOME_SAVE
        if post_id in self.rejected:
            return OUTCOME_NOT_FOR_ME
        if post_id in self.opened:
            return OUTCOME_OPENED
        if post_id in self.engaged:
            return OUTCOME_ENGAGED
        if (today - recommended_on).days < IGNORED_GRACE_DAYS:
            return OUTCOME_PENDING
        return OUTCOME_IGNORED


def in_cooldown(stats: TopicStats | None, today: date, cooldown_days: int) -> bool:
    """True if an exploration pick for this topic was rejected too recently to try again."""
    if stats is None or stats.last_explore_reject is None:
        return False
    return (today - stats.last_explore_reject).days < cooldown_days


def effective_ratio(ratio: float, total_sent: int) -> float:
    """The explore share to use: the configured one, raised while the record is thin."""
    ratio = min(max(ratio, 0.0), MAX_RATIO)
    if ratio > 0 and total_sent < COLD_START_PICKS:
        ratio = max(ratio, COLD_START_RATIO)
    return ratio


def explore_budget(
    exploit_count: int,
    explored_today: int,
    ratio: float,
    max_per_day: int,
    rng: random.Random,
) -> int:
    """How many explore picks this run may send.

    ``ratio`` is the share of all picks that explore. With ``e`` exploit picks that
    means ``ratio / (1 - ratio) * e`` explore picks, rounded up or down at random so
    small runs still average out to the ratio. A run with no exploit picks may still
    explore once, with probability ``ratio``.

    Args:
        exploit_count: Exploit picks this run will send
        explored_today: Explore picks already stored for today
        ratio: Share of picks that explore, 0 to 1 (already adjusted for cold start)
        max_per_day: Hard ceiling on explore picks per day; 0 or less disables
        rng: Random source

    Returns:
        Number of explore picks to send, never negative
    """
    if ratio <= 0 or max_per_day <= 0:
        return 0
    remaining = max_per_day - explored_today
    if remaining <= 0:
        return 0
    expected = ratio / (1.0 - ratio) * exploit_count if exploit_count else ratio
    whole = math.floor(expected)
    count = whole + (1 if rng.random() < expected - whole else 0)
    return min(count, remaining)


def choose_explorers(
    offered: list[ExplorePick],
    stats: dict[str, TopicStats],
    *,
    today: date,
    budget: int,
    min_quality: int,
    cooldown_days: int,
    rng: random.Random,
    skip_hn_ids: Iterable[int] = (),
) -> list[ExplorePick]:
    """Choose which offered posts to explore, by Thompson sampling over topics.

    A topic is drawn from Beta(1 + yes, 1 + no). Topics with no record, or a mixed one,
    have a wide spread and win often; topics the reader keeps rejecting or ignoring win
    almost never. At most one post per topic, so one run does not spend its whole budget
    on a single guess.

    Args:
        offered: The model's explore offers, in its order
        stats: Topic records
        today: Local date now
        budget: Most posts to return
        min_quality: Lowest quality rating that may be explored
        cooldown_days: Days a rejected explore topic is left alone
        rng: Random source
        skip_hn_ids: Posts to leave out (already chosen as exploit picks)

    Returns:
        The chosen posts, best draw first
    """
    if budget <= 0:
        return []
    skip = set(skip_hn_ids)
    scored: list[tuple[float, int, ExplorePick]] = []
    for order, offer in enumerate(offered):
        if offer.hn_id in skip or not offer.topic or offer.quality < min_quality:
            continue
        topic_stats = stats.get(offer.topic)
        if in_cooldown(topic_stats, today, cooldown_days):
            continue
        alpha = topic_stats.alpha if topic_stats else 1.0
        beta = topic_stats.beta if topic_stats else 1.0
        scored.append((rng.betavariate(alpha, beta), order, offer))

    # Best draw first; on equal draws, higher quality, then the model's order.
    scored.sort(key=lambda s: (-s[0], -s[2].quality, s[1]))

    chosen: list[ExplorePick] = []
    used_topics: set[str] = set()
    for _, _, offer in scored:
        if offer.topic in used_topics:
            continue
        used_topics.add(offer.topic)
        chosen.append(offer)
        if len(chosen) >= budget:
            break
    return chosen


def kind_metrics(
    history: Iterable[SentPick], buckets: "ActivityBuckets", today: date
) -> dict[str, dict[str, int]]:
    """Count outcomes per kind, to judge whether exploring earns its share.

    Args:
        history: Sent picks (topic not required)
        buckets: The reader's activity, one verdict per post
        today: Local date now

    Returns:
        ``{kind: {judged, saved, rejected, opened, ignored}}``; picks too new to judge
        are left out of every count
    """
    lookup = _OutcomeLookup(buckets)
    metrics: dict[str, dict[str, int]] = {}
    for pick in history:
        outcome = lookup.outcome(pick.post_id, pick.recommended_on, today)
        if outcome == OUTCOME_PENDING:
            continue
        row = metrics.setdefault(
            pick.kind,
            {"judged": 0, "saved": 0, "rejected": 0, "opened": 0, "ignored": 0},
        )
        row["judged"] += 1
        key = {
            OUTCOME_SAVE: "saved",
            OUTCOME_NOT_FOR_ME: "rejected",
            OUTCOME_OPENED: "opened",
            OUTCOME_IGNORED: "ignored",
        }.get(outcome)
        if key:
            row[key] += 1
    return metrics
