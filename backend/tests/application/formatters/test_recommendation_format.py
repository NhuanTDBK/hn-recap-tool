"""Tests for recommendation messages and their keyboard."""

from uuid import uuid4

from app.infrastructure.database.models import Post
from app.presentation.bot.formatters.digest_formatter import (
    DigestMessageFormatter,
    InlineKeyboardBuilder,
)


def make_post(**kw) -> Post:
    defaults = {
        "id": uuid4(),
        "hn_id": 42,
        "title": "Plain title",
        "url": "https://example.com/a",
        "score": 120,
        "comment_count": 30,
        "summary": "SHARED COLUMN TEXT",
    }
    defaults.update(kw)
    return Post(**defaults)


def buttons(kb: dict) -> list[list[tuple[str, str]]]:
    return [
        [(b["text"], b["callback_data"]) for b in row] for row in kb["inline_keyboard"]
    ]


# ------------------------------------------------------------------- message


def test_message_uses_the_feed_summary_not_the_shared_column():
    post = make_post()
    text = DigestMessageFormatter().format_recommendation_message(
        post, "Feed summary", 2, 5
    )

    assert "Feed summary" in text and "SHARED COLUMN TEXT" not in text
    assert "2/5" in text and "Plain title" in text


def test_message_does_not_mutate_the_post():
    post = make_post()
    DigestMessageFormatter().format_recommendation_message(post, "Feed summary", 1, 1)
    assert post.summary == "SHARED COLUMN TEXT"


def test_message_escapes_title_and_summary():
    post = make_post(title="Why <div> beats <span>")
    text = DigestMessageFormatter().format_recommendation_message(
        post, "uses RefCell<T> & <script>", 1, 1
    )

    assert "<div>" not in text and "<script>" not in text and "RefCell<T>" not in text
    assert "RefCell&lt;T&gt; &amp; &lt;script&gt;" in text


def test_streaming_format_still_falls_back_to_post_summary():
    text = DigestMessageFormatter().format_post_message(make_post(), 1, 1)
    assert "SHARED COLUMN TEXT" in text


# ------------------------------------------------------------------ keyboard


def test_default_recommendation_keyboard_layout():
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(pid)

    assert buttons(kb) == [
        [("📖 More", f"show_more_{pid}"), ("🔖 Save", f"save_post_{pid}")],
        [("💡 Why", f"why_rec_{pid}"), ("👎 Not for me", f"not_for_me_{pid}")],
    ]


def test_expanded_drops_more_only():
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(pid, expanded=True)

    assert [t for row in buttons(kb) for t, _ in row] == [
        "🔖 Save",
        "💡 Why",
        "👎 Not for me",
    ]


def test_saved_and_dismissed_relabel_buttons():
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(
        pid, saved=True, dismissed=True
    )

    labels = [t for row in buttons(kb) for t, _ in row]
    assert "✅ Saved" in labels and "👎 Noted" in labels
    assert "🔖 Save" not in labels and "👎 Not for me" not in labels


def test_callback_data_fits_telegrams_64_byte_limit():
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(str(uuid4()))
    for row in kb["inline_keyboard"]:
        for b in row:
            assert len(b["callback_data"].encode()) <= 64


def test_new_callback_prefixes_do_not_collide_with_existing_handlers():
    """aiogram matches handlers by prefix in registration order; a collision would misroute taps."""
    pid = str(uuid4())
    kb = InlineKeyboardBuilder().build_recommendation_keyboard(pid)
    others = ("discuss_", "react_up_", "react_down_", "actions_", "back_", "view_posts")
    for row in kb["inline_keyboard"]:
        for b in row:
            if b["callback_data"].startswith(("why_rec_", "not_for_me_")):
                assert not b["callback_data"].startswith(others)
