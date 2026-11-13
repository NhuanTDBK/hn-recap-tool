"""Recommendation agent: picks the posts a reader will want from today's candidates.

One LLM call per run. The reader's saves, rejections and reactions go in as examples
of taste; the model returns picks with a 1-5 fit rating, a topic and a one-line reason,
and, when asked, a short list of good posts outside the profile to explore. The program,
not the model, decides the final count (fit cut-off, daily cap) and which explore offers
are sent (see ``app.domain.exploration``).
"""

import json
import logging
import re
import time
from html import escape
from typing import Any

from agents import Runner
from pydantic import BaseModel, Field, ValidationError

from app.domain.exploration import ExplorePick, TopicStats, normalize_topic
from app.domain.recommendation import (
    INTERESTS_MAX,
    REASON_MAX_CHARS,
    PostBrief,
    RankedPick,
    RankingResult,
    TasteSignals,
    clip,
)

from .base_agent import BaseAgent
from .config import settings
from .summarization_agent import load_prompt_content

logger = logging.getLogger(__name__)

PROMPT_NAME = "recommendation_system"
EXPLORE_OFFERS_MAX = 8  # most explore offers asked of the model per run


class RankingError(Exception):
    """Ranking produced no usable result.

    ``input_tokens`` / ``output_tokens`` carry what the failed attempts cost, so the
    caller can still record the spend.
    """

    input_tokens: int = 0
    output_tokens: int = 0


class RankingParseError(RankingError, ValueError):
    """The model's reply was not the JSON object we asked for."""


class _PickModel(BaseModel):
    hn_id: int
    fit: int = Field(ge=1, le=5)
    reason: str = Field(min_length=1)
    topic: str = ""


class _ExploreModel(BaseModel):
    hn_id: int
    topic: str = Field(min_length=1)
    quality: int = Field(ge=1, le=5)
    reason: str = Field(min_length=1)


def _post_line(p: PostBrief, *, with_summary: bool) -> str:
    domain = f" ({p.domain})" if p.domain else ""
    line = f"- {escape(p.title, quote=False)}{domain}"
    if with_summary and p.summary:
        line += f"\n  {escape(p.summary, quote=False)}"
    return line


def _topic_line(t: TopicStats) -> str:
    return (
        f"- {escape(t.topic, quote=False)} "
        f"(sent {t.shown}, saved {t.saved}, rejected {t.rejected}, ignored {t.ignored})"
    )


def build_ranking_input(
    signals: TasteSignals, candidates: list[PostBrief], explore_limit: int = 0
) -> str:
    """Render the user message for the ranking call.

    Post text is HTML-escaped so a title or summary cannot close one of our section
    tags and pose as instructions.

    Args:
        signals: The reader's taste signals
        candidates: Posts to choose from
        explore_limit: Most explore offers the model may return; 0 means none

    Returns:
        The full user message
    """
    parts = [
        "<saved>",
        *(_post_line(p, with_summary=True) for p in signals.saved),
        "</saved>",
        "<not_for_me>",
        *(_post_line(p, with_summary=False) for p in signals.not_for_me),
        "</not_for_me>",
        "<opened>",
        *(_post_line(p, with_summary=False) for p in signals.opened),
        "</opened>",
        "<ignored>",
        *(_post_line(p, with_summary=False) for p in signals.ignored),
        "</ignored>",
        "<topics>",
        *(_topic_line(t) for t in signals.topics),
        "</topics>",
        "<candidates>",
    ]
    for c in candidates:
        domain = c.domain or "unknown"
        parts.append(
            f"hn_id={c.hn_id} | score={c.score} | {domain} | {escape(c.title, quote=False)}"
            + (f"\n  {escape(c.summary, quote=False)}" if c.summary else "")
        )
    parts.append("</candidates>")
    parts.append(f"<explore_limit>{max(explore_limit, 0)}</explore_limit>")
    return "\n".join(parts)


def _extract_json(text: str) -> Any:
    """Parse the first JSON object in ``text``, tolerating code fences and chatter."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise RankingParseError("no JSON object in model reply")
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        raise RankingParseError(f"invalid JSON: {e}") from e


def parse_ranking(
    text: str, valid_hn_ids: set[int]
) -> tuple[list[str], list[RankedPick]]:
    """Validate the model's reply.

    Bad individual picks are dropped (wrong shape, unknown ``hn_id``, duplicates),
    since one slip should not cost the whole day. A reply that is not a JSON object
    with a ``picks`` list raises.

    Args:
        text: Raw model output
        valid_hn_ids: ``hn_id`` values that were actually offered

    Returns:
        ``(interests, picks)`` with picks in the model's order

    Raises:
        RankingParseError: If the reply cannot be used at all
    """
    data = _extract_json(text)
    if not isinstance(data, dict) or not isinstance(data.get("picks"), list):
        raise RankingParseError("reply is not an object with a 'picks' list")

    raw_interests = data.get("interests")
    interests = [
        clip(str(i), 60)
        for i in (raw_interests if isinstance(raw_interests, list) else [])
        if str(i).strip()
    ][:INTERESTS_MAX]

    picks: list[RankedPick] = []
    seen: set[int] = set()
    for item in data["picks"]:
        try:
            pick = _PickModel.model_validate(item)
        except ValidationError:
            logger.warning(f"Dropping malformed pick: {item!r}")
            continue
        if pick.hn_id not in valid_hn_ids:
            logger.warning(f"Dropping pick with unknown hn_id {pick.hn_id}")
            continue
        if pick.hn_id in seen:
            continue
        seen.add(pick.hn_id)
        picks.append(
            RankedPick(
                hn_id=pick.hn_id,
                fit=pick.fit,
                reason=clip(pick.reason, REASON_MAX_CHARS),
                topic=normalize_topic(pick.topic),
            )
        )
    return interests, picks


def parse_explore(
    text: str, valid_hn_ids: set[int], limit: int = EXPLORE_OFFERS_MAX
) -> list[ExplorePick]:
    """Read the model's explore offers.

    Never raises: exploring is a bonus, so a missing or broken ``explore`` list must not
    cost the run its normal picks. Bad entries are dropped.

    Args:
        text: Raw model output
        valid_hn_ids: ``hn_id`` values that were actually offered
        limit: Most offers to keep

    Returns:
        Offers in the model's order, duplicates and unknown posts removed
    """
    try:
        data = _extract_json(text)
    except RankingParseError:
        return []
    raw = data.get("explore") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []

    offers: list[ExplorePick] = []
    seen: set[int] = set()
    for item in raw:
        try:
            offer = _ExploreModel.model_validate(item)
        except ValidationError:
            logger.warning(f"Dropping malformed explore offer: {item!r}")
            continue
        topic = normalize_topic(offer.topic)
        if offer.hn_id not in valid_hn_ids or offer.hn_id in seen or not topic:
            continue
        seen.add(offer.hn_id)
        offers.append(
            ExplorePick(
                hn_id=offer.hn_id,
                topic=topic,
                quality=offer.quality,
                reason=clip(offer.reason, REASON_MAX_CHARS),
            )
        )
    return offers[:limit]


def create_recommendation_agent(model: str = settings.openai_model) -> BaseAgent:
    """Create the ranking agent. The system prompt is static so it stays cacheable."""
    return BaseAgent(
        name="RecommendationAgent",
        instructions=load_prompt_content(PROMPT_NAME),
        model=model,
        temperature=0.2,
        max_tokens=6000,
        tools=[],
    )


async def rank_candidates(
    signals: TasteSignals,
    candidates: list[PostBrief],
    model: str | None = None,
    explore_limit: int = 0,
) -> RankingResult:
    """Ask the model which candidates this reader would want.

    Retries once if the reply cannot be parsed. There is deliberately no fallback to
    "top by score": that would look like a recommendation without being one.

    Args:
        signals: The reader's taste signals
        candidates: Posts to choose from (must not be empty)
        model: Model to use; defaults to the app-wide model
        explore_limit: Most explore offers to ask for; 0 asks for none

    Returns:
        Interests, picks (unfiltered by fit), explore offers and token usage

    Raises:
        RankingParseError: If both attempts return unusable replies
        RankingError: If the model call itself fails (network, rate limit, ...)
    """
    agent = (
        create_recommendation_agent(model) if model else create_recommendation_agent()
    )
    user_input = build_ranking_input(signals, candidates, explore_limit)
    valid_ids = {c.hn_id for c in candidates}

    input_tokens = output_tokens = 0
    last_error: RankingParseError | None = None

    for attempt in (1, 2):
        started = time.monotonic()
        try:
            run = await Runner.run(agent.agent, input=user_input)
        except Exception as e:
            # Keeps the spend of an earlier attempt; the scheduler's retry job tries again.
            error = RankingError(f"Model call failed on attempt {attempt}: {e}")
            error.input_tokens = input_tokens
            error.output_tokens = output_tokens
            raise error from e
        input_tokens += sum(r.usage.input_tokens for r in run.raw_responses)
        output_tokens += sum(r.usage.output_tokens for r in run.raw_responses)
        try:
            interests, picks = parse_ranking(str(run.final_output), valid_ids)
        except RankingParseError as e:
            last_error = e
            logger.warning(
                f"Recommendation reply unusable (attempt {attempt}, {time.monotonic() - started:.1f}s): {e}"
            )
            continue
        return RankingResult(
            interests=interests,
            picks=picks,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            explore=(
                parse_explore(
                    str(run.final_output),
                    valid_ids,
                    min(explore_limit, EXPLORE_OFFERS_MAX),
                )
                if explore_limit > 0
                else []
            ),
        )

    assert last_error is not None
    last_error.input_tokens = input_tokens
    last_error.output_tokens = output_tokens
    raise last_error
