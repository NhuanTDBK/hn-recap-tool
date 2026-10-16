"""Tests for the Show More button.

The formatter emits HTML, so the edit must use ParseMode.HTML. The expanded text
must be the summary of the feed that owns the message, not posts.summary, which
is shared between feeds and holds whichever one was delivered last.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aiogram.enums import ParseMode

from app.infrastructure.database.models import Post, User
from app.presentation.bot.handlers.callbacks import handle_show_more


def _result(value):
    return MagicMock(scalar_one_or_none=MagicMock(return_value=value))


@pytest.mark.asyncio
async def test_show_more_edits_as_html_with_feed_summary():
    post_id = uuid4()
    post = Post(
        id=post_id,
        hn_id=1,
        title="A <b> title",
        summary="SHARED COLUMN TEXT",
        score=1,
        comment_count=0,
    )
    user = User(id=7, telegram_id=555)

    session = MagicMock()
    session.execute = AsyncMock(
        side_effect=[_result(user), _result(post), _result("Feed summary with x < y")]
    )

    callback = MagicMock()
    callback.data = f"show_more_{post_id}"
    callback.from_user.id = 555
    callback.message.chat.id = 555
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    with patch(
        "app.presentation.bot.handlers.callbacks.PostgresActivityLogRepository"
    ) as repo:
        repo.return_value.log_activity = AsyncMock()
        await handle_show_more(callback, session)

    kwargs = callback.message.edit_text.await_args.kwargs
    assert kwargs["parse_mode"] == ParseMode.HTML
    assert "Feed summary with x &lt; y" in kwargs["text"]
    assert "SHARED COLUMN TEXT" not in kwargs["text"]
    assert "A &lt;b&gt; title" in kwargs["text"]


def test_full_formatter_falls_back_to_post_summary():
    from app.presentation.bot.formatters.digest_formatter import DigestMessageFormatter

    post = Post(
        id=uuid4(), hn_id=1, title="t", summary="column text", score=1, comment_count=0
    )
    formatter = DigestMessageFormatter()

    assert "column text" in formatter.format_post_message_full(post, 1, 1)
    assert "override" in formatter.format_post_message_full(
        post, 1, 1, summary="override"
    )


def test_full_summary_cap_comes_from_settings():
    from app.presentation.bot.formatters import digest_formatter

    post = Post(
        id=uuid4(), hn_id=1, title="t", summary="x" * 50, score=1, comment_count=0
    )
    with patch.object(
        digest_formatter.settings, "telegram_full_summary_max_length", 10
    ):
        text = digest_formatter.DigestMessageFormatter().format_post_message_full(
            post, 1, 1
        )

    assert "x" * 10 + "..." in text
    assert "x" * 11 not in text
