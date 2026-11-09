"""Tests for how the recommendation job is scheduled and how it records usage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.infrastructure.config.settings import settings
from scripts import run_recommendations
from scripts.run_scheduler import recommendation_hours, schedule_recommendations


def scheduled() -> dict[str, str]:
    scheduler = AsyncIOScheduler()
    schedule_recommendations(scheduler)
    return {
        job.id: str(job.trigger.fields[job.trigger.FIELD_NAMES.index("hour")])
        for job in scheduler.get_jobs()
    }


def test_one_job_fires_at_each_listed_hour():
    with patch.object(settings, "recommendation_hours", "8,12,16,20"):
        assert scheduled() == {"hn_pal_recommendations": "8,12,16,20"}


def test_hours_are_sorted_and_deduplicated():
    with patch.object(settings, "recommendation_hours", " 20, 8,8 ,12"):
        assert recommendation_hours() == [8, 12, 20]


@pytest.mark.parametrize("bad", ["", " , ", "24", "-1", "8;12"])
def test_bad_hours_are_refused_at_startup(bad):
    with patch.object(settings, "recommendation_hours", bad):
        with pytest.raises(ValueError):
            recommendation_hours()


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
