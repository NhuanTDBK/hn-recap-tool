"""Tests for how the recommendation job is scheduled and how it records usage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.infrastructure.config.settings import settings
from scripts import run_recommendations
from scripts.run_scheduler import schedule_recommendations


def fire_hours() -> dict[str, str]:
    scheduler = AsyncIOScheduler()
    schedule_recommendations(scheduler)
    return {
        job.id: str(job.trigger.fields[job.trigger.FIELD_NAMES.index("hour")])
        for job in scheduler.get_jobs()
    }


def test_retry_fires_an_hour_after_the_daily_run():
    with patch.object(settings, "recommendation_hour", 8):
        assert fire_hours() == {
            "hn_pal_recommendations": "8",
            "hn_pal_recommendations_retry": "9",
        }


def test_no_retry_when_it_would_land_on_the_next_day():
    with patch.object(settings, "recommendation_hour", 23):
        assert fire_hours() == {"hn_pal_recommendations": "23"}


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
