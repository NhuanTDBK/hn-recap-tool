"""Tests for the Why / Not for me buttons and for Save / More on recommended posts.

Recommended and Streaming messages share the Save and More handlers; the only thing
telling them apart is the keyboard on the message, so a regression here would quietly
strip the Why / Not for me buttons the first time someone saves.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aiogram.types import InlineKeyboardMarkup

from app.infrastructure.database.models import Post, User
from app.presentation.bot.formatters.digest_formatter import InlineKeyboardBuilder
from app.presentation.bot.handlers import callbacks
from app.presentation.bot.handlers.callbacks import (
    handle_not_for_me,
    handle_save_post,
    handle_show_more,
    handle_why_recommended,
)


def _result(value):
    return MagicMock(scalar_one_or_none=MagicMock(return_value=value))


def make_callback(data: str, keyboard: dict) -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user.id = 555
    cb.message.chat.id = 555
    cb.message.reply_markup = InlineKeyboardMarkup(
        inline_keyboard=keyboard["inline_keyboard"]
    )
    cb.message.edit_text = AsyncMock()
    cb.message.edit_reply_markup = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def labels(markup) -> list[str]:
    rows = (
        markup["inline_keyboard"]
        if isinstance(markup, dict)
        else markup.inline_keyboard
    )
    return [(b["text"] if isinstance(b, dict) else b.text) for row in rows for b in row]


@pytest.fixture
def session():
    s = MagicMock()
    s.execute = AsyncMock(return_value=_result(User(id=7, telegram_id=555)))
    return s


@pytest.fixture
def activity():
    with patch.object(callbacks, "PostgresActivityLogRepository") as repo:
        repo.return_value.log_activity = AsyncMock()
        yield repo.return_value


# ------------------------------------------------------------------------ Why


@pytest.mark.asyncio
async def test_why_shows_the_stored_reason_as_a_popup(session, activity):
    pid = uuid4()
    cb = make_callback(
        f"why_rec_{pid}",
        InlineKeyboardBuilder().build_recommendation_keyboard(str(pid)),
    )

    with patch.object(callbacks, "PostgresRecommendationRepository") as repo:
        repo.return_value.get_reason = AsyncMock(
            return_value="Like your saved Postgres post"
        )
        await handle_why_recommended(cb, session)

    cb.answer.assert_awaited_once()
    assert cb.answer.await_args.args[0] == "💡 Like your saved Postgres post"
    assert cb.answer.await_args.kwargs["show_alert"] is True
    activity.log_activity.assert_awaited_once_with(7, str(pid), "why")


@pytest.mark.asyncio
async def test_why_popup_never_exceeds_telegrams_200_characters(session, activity):
    pid = uuid4()
    cb = make_callback(
        f"why_rec_{pid}",
        InlineKeyboardBuilder().build_recommendation_keyboard(str(pid)),
    )

    with patch.object(callbacks, "PostgresRecommendationRepository") as repo:
        repo.return_value.get_reason = AsyncMock(return_value="x" * 500)
        await handle_why_recommended(cb, session)

    assert len(cb.answer.await_args.args[0]) <= 200


@pytest.mark.asyncio
async def test_why_without_a_stored_reason_says_so(session, activity):
    pid = uuid4()
    cb = make_callback(
        f"why_rec_{pid}",
        InlineKeyboardBuilder().build_recommendation_keyboard(str(pid)),
    )

    with patch.object(callbacks, "PostgresRecommendationRepository") as repo:
        repo.return_value.get_reason = AsyncMock(return_value=None)
        await handle_why_recommended(cb, session)

    assert "No reason" in cb.answer.await_args.args[0]
    activity.log_activity.assert_not_awaited()


# ---------------------------------------------------------------- Not for me


@pytest.mark.asyncio
async def test_not_for_me_logs_the_signal_and_relabels_the_button(session, activity):
    pid = str(uuid4())
    cb = make_callback(
        f"not_for_me_{pid}", InlineKeyboardBuilder().build_recommendation_keyboard(pid)
    )

    await handle_not_for_me(cb, session)

    activity.log_activity.assert_awaited_once_with(7, pid, "not_for_me")
    shown = labels(cb.message.edit_reply_markup.await_args.kwargs["reply_markup"])
    assert "👎 Noted" in shown and "💡 Why" in shown and "📖 More" in shown


@pytest.mark.asyncio
async def test_not_for_me_keeps_a_saved_label(session, activity):
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(pid, saved=True)
    cb = make_callback(f"not_for_me_{pid}", kb)

    await handle_not_for_me(cb, session)

    assert "✅ Saved" in labels(
        cb.message.edit_reply_markup.await_args.kwargs["reply_markup"]
    )


# -------------------------------------------------------- Save on both feeds


@pytest.mark.asyncio
async def test_save_on_a_recommended_post_keeps_why_and_not_for_me(session, activity):
    pid = str(uuid4())
    cb = make_callback(
        f"save_post_{pid}", InlineKeyboardBuilder().build_recommendation_keyboard(pid)
    )

    await handle_save_post(cb, session)

    activity.log_activity.assert_awaited_once_with(7, pid, "save")
    shown = labels(cb.message.edit_reply_markup.await_args.kwargs["reply_markup"])
    assert shown == ["📖 More", "✅ Saved", "💡 Why", "👎 Not for me"]


@pytest.mark.asyncio
async def test_save_after_dismissing_keeps_the_noted_label(session, activity):
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(pid, dismissed=True)
    cb = make_callback(f"save_post_{pid}", kb)

    await handle_save_post(cb, session)

    shown = labels(cb.message.edit_reply_markup.await_args.kwargs["reply_markup"])
    assert "✅ Saved" in shown and "👎 Noted" in shown


@pytest.mark.asyncio
async def test_save_on_a_streaming_post_is_unchanged(session, activity):
    pid = str(uuid4())
    cb = make_callback(
        f"save_post_{pid}", InlineKeyboardBuilder().build_post_keyboard(pid)
    )

    await handle_save_post(cb, session)

    shown = labels(cb.message.edit_reply_markup.await_args.kwargs["reply_markup"])
    assert shown == ["📖 More", "✅ Saved", "⚡ Actions"]


# --------------------------------------------------------- More on both feeds


def _more_session(post: Post):
    s = MagicMock()
    s.execute = AsyncMock(
        side_effect=[
            _result(User(id=7, telegram_id=555)),
            _result(post),
            _result("Feed summary"),
        ]
    )
    return s


@pytest.mark.asyncio
async def test_more_on_a_recommended_post_drops_only_more(activity):
    pid = uuid4()
    post = Post(id=pid, hn_id=1, title="T", summary="", score=1, comment_count=0)
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(str(pid), saved=True)
    cb = make_callback(f"show_more_{pid}", kb)

    await handle_show_more(cb, _more_session(post))

    shown = labels(cb.message.edit_text.await_args.kwargs["reply_markup"])
    assert shown == ["✅ Saved", "💡 Why", "👎 Not for me"]


@pytest.mark.asyncio
async def test_more_on_a_streaming_post_is_unchanged(activity):
    pid = uuid4()
    post = Post(id=pid, hn_id=1, title="T", summary="", score=1, comment_count=0)
    cb = make_callback(
        f"show_more_{pid}", InlineKeyboardBuilder().build_post_keyboard(str(pid))
    )

    await handle_show_more(cb, _more_session(post))

    shown = labels(cb.message.edit_text.await_args.kwargs["reply_markup"])
    assert shown == ["🔖 Save", "⚡ Actions"]
