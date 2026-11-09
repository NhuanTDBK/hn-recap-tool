"""Domain types and pure rules for daily post recommendations.

Nothing here touches the database, the network or the LLM, so every rule can be
tested directly.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# Activity actions that say something about taste. ``why`` is an interaction with a
# recommendation (the reader looked at the reason) but not a verdict either way.
ACTION_SAVE = "save"
ACTION_NOT_FOR_ME = "not_for_me"
ACTION_OPENED = "show_more"
ACTION_WHY = "why"

STRONG_ACTIONS = frozenset({ACTION_SAVE, ACTION_NOT_FOR_ME})
ENGAGED_ACTIONS = frozenset({ACTION_SAVE, ACTION_NOT_FOR_ME, ACTION_OPENED, ACTION_WHY})

REASON_MAX_CHARS = 180
INTERESTS_MAX = 8


@dataclass(frozen=True)
class PostBrief:
    """A post reduced to what the ranking model needs."""

    post_id: UUID
    hn_id: int
    title: str
    domain: str | None
    score: int
    summary: str


@dataclass
class TasteSignals:
    """What we know about the reader's taste, newest first within each list."""

    saved: list[PostBrief] = field(default_factory=list)
    not_for_me: list[PostBrief] = field(default_factory=list)
    opened: list[PostBrief] = field(default_factory=list)
    ignored: list[PostBrief] = field(default_factory=list)
    saved_total: int = 0  # all distinct saves, not just the ones shown to the model


@dataclass(frozen=True)
class RankedPick:
    """One post the model chose, with its rating and the reason shown to the reader."""

    hn_id: int
    fit: int
    reason: str


@dataclass
class RankingResult:
    """The model's answer plus what it cost."""

    interests: list[str]
    picks: list[RankedPick]
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ActivityBuckets:
    """Posts grouped by what the reader did with them, newest first."""

    saved_ids: list[UUID]
    not_for_me_ids: list[UUID]
    opened_ids: list[UUID]
    engaged_ids: set[UUID]


def classify_activity(
    rows: Iterable[tuple[UUID, str, datetime]],
) -> ActivityBuckets:
    """Reduce raw activity-log rows to one verdict per post.

    The log is append-only, so a post can carry several rows. Between ``save`` and
    ``not_for_me`` the newest one wins, which lets a changed mind override the old
    verdict. ``show_more`` only counts as "opened" for posts with no verdict.

    Args:
        rows: ``(post_id, action_type, created_at)`` in any order

    Returns:
        Post IDs per bucket, newest first, plus every post the reader touched
    """
    verdict: dict[UUID, str] = {}
    saved: list[UUID] = []
    rejected: list[UUID] = []
    opened_seen: set[UUID] = set()
    opened: list[UUID] = []
    engaged: set[UUID] = set()

    for post_id, action, _ in sorted(rows, key=lambda r: r[2], reverse=True):
        if action in ENGAGED_ACTIONS:
            engaged.add(post_id)
        if action in STRONG_ACTIONS and post_id not in verdict:
            verdict[post_id] = action
            (saved if action == ACTION_SAVE else rejected).append(post_id)
        elif action == ACTION_OPENED and post_id not in opened_seen:
            opened_seen.add(post_id)
            opened.append(post_id)

    return ActivityBuckets(
        saved_ids=saved,
        not_for_me_ids=rejected,
        opened_ids=[p for p in opened if p not in verdict],
        engaged_ids=engaged,
    )


def clip(text: str | None, limit: int) -> str:
    """Collapse whitespace and cut ``text`` to ``limit`` characters, adding an ellipsis."""
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat
    return flat[: max(0, limit - 1)].rstrip() + "…"
