"""Tests for the Telegram group feed (group topic stored as a subscriber row)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.database.models import User
from app.infrastructure.services import group_subscriber
from app.infrastructure.services.group_subscriber import (
    ensure_group_subscriber,
    is_feed_enabled,
    topic_id_for,
)

GROUP_CHAT_ID = -1001234567890  # does not fit in int32
TOPIC_ID = 42


@pytest.fixture
def group_settings():
    """Configure a group feed for the duration of a test."""
    s = group_subscriber.settings
    with (
        patch.object(s, "telegram_group_chat_id", GROUP_CHAT_ID),
        patch.object(s, "telegram_group_topic_id", TOPIC_ID),
        patch.object(s, "telegram_group_summary_style", "basic"),
        patch.object(s, "telegram_dm_delivery_enabled", True),
    ):
        yield s


def test_topic_id_only_for_group_chat(group_settings):
    assert topic_id_for(GROUP_CHAT_ID) == TOPIC_ID
    assert topic_id_for(12345) is None


def test_topic_id_none_when_group_unset():
    with patch.object(group_subscriber.settings, "telegram_group_chat_id", None):
        assert topic_id_for(GROUP_CHAT_ID) is None


def test_feed_enabled_for_everyone_while_dm_delivery_on(group_settings):
    assert is_feed_enabled(User(telegram_id=12345))
    assert is_feed_enabled(User(telegram_id=GROUP_CHAT_ID))


def test_only_group_feed_enabled_when_dm_delivery_off(group_settings):
    with patch.object(group_settings, "telegram_dm_delivery_enabled", False):
        assert not is_feed_enabled(User(telegram_id=12345))
        assert is_feed_enabled(User(telegram_id=GROUP_CHAT_ID))


class FakeSession:
    """Minimal async session holding at most one User (the group row)."""

    def __init__(self):
        self.user = None
        self.commits = 0

    async def execute(self, _stmt):
        return MagicMock(scalar_one_or_none=MagicMock(return_value=self.user))

    def add(self, user):
        if self.user is None:
            user.id = 99
        self.user = user

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_ensure_group_subscriber_noop_when_unset():
    session = FakeSession()
    with patch.object(group_subscriber.settings, "telegram_group_chat_id", None):
        assert await ensure_group_subscriber(session) is None
    assert session.user is None
    assert session.commits == 0


@pytest.mark.asyncio
async def test_ensure_group_subscriber_is_idempotent(group_settings):
    session = FakeSession()
    first = await ensure_group_subscriber(session)
    second = await ensure_group_subscriber(session)

    assert first is second
    assert first.telegram_id == GROUP_CHAT_ID
    assert first.status == "active"
    assert first.get_summary_style() == "basic"
    assert session.commits == 1, "second call must not write"


@pytest.mark.asyncio
async def test_ensure_group_subscriber_syncs_style_but_keeps_status(group_settings):
    session = FakeSession()
    user = await ensure_group_subscriber(session)
    user.status = "paused"

    with patch.object(group_settings, "telegram_group_summary_style", "technical"):
        user = await ensure_group_subscriber(session)

    assert user.get_summary_style() == "technical"
    assert user.status == "paused", "a manually paused group must stay paused"


@pytest.mark.asyncio
async def test_delivery_sends_into_topic_only_for_group(group_settings):
    with patch("app.presentation.bot.handlers.delivery.get_bot_manager") as get_bm:
        from app.presentation.bot.handlers.delivery import DigestDeliveryHandler

        bot_manager = MagicMock()
        bot_manager.send_message = AsyncMock(return_value={"message_id": 1})
        get_bm.return_value = bot_manager
        handler = DigestDeliveryHandler(
            delivery_repo=MagicMock(save_delivery=AsyncMock())
        )
        handler.formatter = MagicMock(
            format_post_message=MagicMock(return_value="text")
        )
        handler.keyboard_builder = MagicMock(
            build_post_keyboard=MagicMock(return_value={"inline_keyboard": []})
        )

        await handler.send_digest_to_user(
            User(id=2, telegram_id=GROUP_CHAT_ID), [MagicMock()], "b"
        )
        await handler.send_digest_to_user(
            User(id=1, telegram_id=12345), [MagicMock()], "b"
        )

    group_call, dm_call = bot_manager.send_message.await_args_list
    assert group_call.kwargs["chat_id"] == GROUP_CHAT_ID
    assert group_call.kwargs["message_thread_id"] == TOPIC_ID
    assert dm_call.kwargs["message_thread_id"] is None
