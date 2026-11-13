"""The label that tells the reader a pick is outside their usual taste."""

from app.infrastructure.database.models import Post
from app.presentation.bot.formatters.digest_formatter import DigestMessageFormatter


def post() -> Post:
    return Post(
        hn_id=1, title="A title", url="https://x.com/a", score=3, comment_count=1
    )


def test_explore_pick_is_labelled_above_the_title():
    text = DigestMessageFormatter().format_recommendation_message(
        post(), "s", 1, 2, explore=True
    )
    assert text.startswith("🧭 <i>Outside your usual</i>\n<b>A title</b>")


def test_normal_pick_has_no_label():
    text = DigestMessageFormatter().format_recommendation_message(post(), "s", 1, 2)
    assert "Outside your usual" not in text and text.startswith("<b>A title</b>")


def test_full_message_keeps_the_label_and_stays_within_telegram_limit():
    long = "word " * 3000
    text = DigestMessageFormatter().format_post_message_full(
        post(), 1, 1, summary=long, explore=True
    )
    assert text.startswith("🧭") and len(text) <= 4096
