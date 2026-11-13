"""Regression tests for the high-severity audit fixes (docs/security-and-implicit-state-audit.md)."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from aiogram import Bot, Dispatcher, Router
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser

from app.infrastructure.database.models import User
from app.presentation.bot.middleware import AccessControlMiddleware, parse_id_list

GROUP_ID = -1001234567890


# --------------------------------------------------------------------------- S-03 access control
def _update(update_id: int, user_id: int, chat_id: int, chat_type: str = "private") -> Update:
    return Update(
        update_id=update_id,
        message=Message(
            message_id=update_id,
            date=datetime.now(),
            chat=Chat(id=chat_id, type=chat_type),
            from_user=TgUser(id=user_id, is_bot=False, first_name="t"),
            text="hello",
        ),
    )


def _dispatcher(middleware: AccessControlMiddleware) -> tuple[Dispatcher, list[int]]:
    seen: list[int] = []
    router = Router()

    @router.message()
    async def handle(message: Message) -> None:
        seen.append(message.from_user.id)

    dp = Dispatcher()
    dp.update.outer_middleware(middleware)
    dp.include_router(router)
    return dp, seen


def test_parse_id_list_skips_bad_tokens():
    assert parse_id_list("1, 2 x 3,,") == frozenset({1, 2, 3})
    assert parse_id_list(None) == frozenset()


@pytest.mark.asyncio
async def test_allowlist_blocks_strangers_and_passes_listed_user():
    dp, seen = _dispatcher(AccessControlMiddleware(allowed_user_ids={42}, group_chat_id=GROUP_ID))
    bot = Bot(token="123456:TEST")

    await dp.feed_update(bot, _update(1, user_id=99, chat_id=99))  # stranger DM
    await dp.feed_update(bot, _update(2, user_id=42, chat_id=42))  # allowed DM
    await dp.feed_update(bot, _update(3, user_id=99, chat_id=GROUP_ID, chat_type="supergroup"))  # group member
    await dp.feed_update(bot, _update(4, user_id=42, chat_id=-555, chat_type="supergroup"))  # some other group

    assert seen == [42, 99]  # the allowed DM, then the configured group member


@pytest.mark.asyncio
async def test_empty_allowlist_is_open_but_other_groups_are_still_dropped():
    dp, seen = _dispatcher(AccessControlMiddleware(allowed_user_ids=(), group_chat_id=None))
    bot = Bot(token="123456:TEST")

    await dp.feed_update(bot, _update(1, user_id=7, chat_id=7))
    await dp.feed_update(bot, _update(2, user_id=7, chat_id=-555, chat_type="supergroup"))

    assert seen == [7]


@pytest.mark.asyncio
async def test_rate_limit_drops_excess_then_recovers():
    now = [0.0]
    mw = AccessControlMiddleware(allowed_user_ids=(), max_per_minute=3, clock=lambda: now[0])
    dp, seen = _dispatcher(mw)
    bot = Bot(token="123456:TEST")

    for i in range(5):
        await dp.feed_update(bot, _update(i, user_id=7, chat_id=7))
    assert len(seen) == 3

    now[0] = 61.0  # window slides past the old hits
    await dp.feed_update(bot, _update(10, user_id=7, chat_id=7))
    assert len(seen) == 4


def test_rate_limit_is_per_user_and_zero_disables():
    mw = AccessControlMiddleware(max_per_minute=1, clock=lambda: 0.0)
    assert mw.is_rate_limited(1) is False
    assert mw.is_rate_limited(1) is True
    assert mw.is_rate_limited(2) is False

    off = AccessControlMiddleware(max_per_minute=0)
    assert all(off.is_rate_limited(1) is False for _ in range(100))


# --------------------------------------------------------------------------- H-13 style persistence
def test_update_summary_preferences_assigns_a_new_dict():
    """A plain JSON column only persists on assignment, never on in-place mutation."""
    user = User(telegram_id=1, summary_preferences={"style": "basic", "detail_level": "medium"})
    before = user.summary_preferences

    user.update_summary_preferences(style="technical")

    assert user.summary_preferences is not before
    assert user.summary_preferences == {"style": "technical", "detail_level": "medium"}
    assert before["style"] == "basic"  # the old object was not mutated


# --------------------------------------------------------------------------- H-04 discussion agent
def test_discussion_agent_can_be_constructed():
    from app.infrastructure.agents.discussion_agent import create_discussion_agent

    agent = create_discussion_agent(session=MagicMock(), content_store=MagicMock(), model="test-model")

    assert agent.name == "DiscussionAgent"
    assert agent.model_settings.temperature == 0.7


# --------------------------------------------------------------------------- H-07 keyboard edits
def test_callbacks_only_use_message_methods_that_exist():
    """Message has edit_reply_markup; edit_message_reply_markup is a Bot method."""
    import inspect

    from app.presentation.bot.handlers import callbacks

    assert not hasattr(Message, "edit_message_reply_markup")
    assert hasattr(Message, "edit_reply_markup")
    assert "message.edit_message_reply_markup" not in inspect.getsource(callbacks)
    assert CallbackQuery  # imported to make sure aiogram types are the ones under test


# --------------------------------------------------------------------------- H-17 cost tracking
def test_gemini_model_is_priced_and_unknown_model_warns_once(caplog):
    from app.infrastructure.agents import token_tracker as tt

    tracker = tt.TokenTracker(MagicMock())
    assert tracker.calculate_cost("gemini-3.6-flash", 1_000_000, 1_000_000) == pytest.approx(0.75 + 3.75)

    tt._warned_models.discard("mystery-model")
    with caplog.at_level("WARNING"):
        assert tracker.calculate_cost("mystery-model", 10, 10) == 0.0
        assert tracker.calculate_cost("mystery-model", 10, 10) == 0.0
    assert sum("mystery-model" in r.message for r in caplog.records) == 1


@pytest.mark.asyncio
async def test_shared_call_is_recorded_once_without_a_user():
    from decimal import Decimal

    from app.infrastructure.agents.token_tracker import TokenTracker

    session = MagicMock()
    cost = await TokenTracker(session).track_shared_call(
        agent_name="SummarizationAgent",
        model="gemini-3.6-flash",
        input_tokens=1_000_000,
        output_tokens=0,
        operation="summarize_post",
    )

    assert cost == Decimal("0.75")
    session.add.assert_called_once()
    row = session.add.call_args.args[0]
    assert row.user_id is None and row.total_tokens == 1_000_000 and row.cost_usd == Decimal("0.75")


# --------------------------------------------------------------------------- migrations
def test_alembic_has_one_head_and_revision_ids_fit_the_version_column():
    """alembic_version.version_num is varchar(32): a longer id fails on Postgres and rolls back the upgrade."""
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parents[2]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    script = ScriptDirectory.from_config(config)

    assert len(script.get_heads()) == 1, f"multiple Alembic heads: {script.get_heads()}"
    too_long = [r.revision for r in script.walk_revisions() if len(r.revision) > 32]
    assert not too_long, f"revision ids longer than 32 chars: {too_long}"
