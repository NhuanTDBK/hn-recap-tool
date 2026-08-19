"""Tests that a delivery outage is reported loudly rather than silently.

Delivery previously counted a total send failure as "users_skipped" — the
same bucket as "nothing new to send" — and logged it at INFO. That is how a
months-long outage stayed invisible.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.database.models import User


@pytest.fixture
def job():
    with patch("app.presentation.bot.handlers.delivery.get_bot_manager"):
        from app.infrastructure.jobs.hourly_delivery_job import HourlyDeliveryJob

        session = MagicMock()
        session.commit = AsyncMock()
        session.add = MagicMock()
        j = HourlyDeliveryJob(db_session=session, delivery_repo=MagicMock())
        j.find_active_users = AsyncMock(
            return_value=[User(id=1, telegram_id=9, status="active")]
        )
        j.get_delivered_post_ids = AsyncMock(return_value=set())
        j.find_posts_with_summaries = AsyncMock(return_value=[MagicMock(), MagicMock()])
        yield j


def all_rejected(*_args, **_kwargs):
    return {
        "user_id": 1,
        "messages_sent": 0,
        "failures": [{"reason": "can't parse entities"}, {"reason": "x"}],
        "message_ids": [],
    }


def all_sent(*_args, **_kwargs):
    return {"user_id": 1, "messages_sent": 2, "failures": [], "message_ids": [1, 2]}


@pytest.mark.asyncio
async def test_total_failure_counts_as_failed_not_skipped(job):
    job.deliver_to_user = AsyncMock(side_effect=all_rejected)
    stats = await job.deliver_summaries()

    assert stats["users_failed"] == 1
    assert stats["users_skipped"] == 0, "a failure must not be filed as a skip"
    assert stats["total_messages_sent"] == 0


@pytest.mark.asyncio
async def test_total_failure_logs_at_error(job, caplog):
    job.deliver_to_user = AsyncMock(side_effect=all_rejected)
    with caplog.at_level(logging.ERROR):
        await job.deliver_summaries()

    errors = " ".join(r.message for r in caplog.records if r.levelno >= logging.ERROR)
    assert "DELIVERY OUTAGE" in errors
    assert "Delivery FAILED for user 1" in errors


@pytest.mark.asyncio
async def test_failed_delivery_does_not_stamp_last_delivered_at(job):
    """A false timestamp would hide the outage from any freshness check."""
    job.deliver_to_user = AsyncMock(side_effect=all_rejected)
    await job.deliver_summaries()

    assert job.db_session.commit.await_count == 0


@pytest.mark.asyncio
async def test_successful_delivery_stays_quiet_and_stamps_timestamp(job, caplog):
    job.deliver_to_user = AsyncMock(side_effect=all_sent)
    with caplog.at_level(logging.ERROR):
        stats = await job.deliver_summaries()

    assert stats["users_delivered"] == 1
    assert stats["users_failed"] == 0
    assert job.db_session.commit.await_count == 1
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
