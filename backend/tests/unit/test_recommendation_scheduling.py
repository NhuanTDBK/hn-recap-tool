"""Tests for the recommend step in the hourly pipeline and how usage is recorded."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts import run_recommendations, run_scheduler


@pytest.mark.asyncio
async def test_step_forces_the_run_so_the_hourly_gap_guard_cannot_skip_it():
    recommend = AsyncMock(return_value={"status": "sent", "sent": 3, "failed": 0})
    with patch.object(run_scheduler, "recommend", recommend):
        await run_scheduler.recommend_step()

    recommend.assert_awaited_once_with(force=True)


@pytest.mark.asyncio
async def test_step_swallows_a_crash():
    with patch.object(
        run_scheduler, "recommend", AsyncMock(side_effect=RuntimeError("boom"))
    ):
        await run_scheduler.recommend_step()  # must not raise


@pytest.mark.asyncio
async def test_usage_is_written_in_its_own_session():
    usage_session = MagicMock(name="usage_session")
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=usage_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    tracker = MagicMock()
    tracker.return_value.track_usage = AsyncMock()

    with patch.object(run_recommendations, "TokenTracker", tracker):
        logger = run_recommendations.make_usage_logger(factory, 7, "m")
        await logger(input_tokens=10, output_tokens=2, status="success")

    tracker.assert_called_once_with(usage_session)
    kwargs = tracker.return_value.track_usage.await_args.kwargs
    assert (kwargs["user_id"], kwargs["model"], kwargs["input_tokens"]) == (7, "m", 10)
