"""Tests that digest messages are valid Telegram HTML.

Regression coverage for the delivery outage where the formatter emitted
Markdown while the bot sent with ParseMode.HTML. Unescaped '<' in AI
summaries (which routinely quote code) made Telegram reject every message
with "can't parse entities", silently stopping delivery.
"""

from datetime import datetime
from html.parser import HTMLParser
from uuid import uuid4

import pytest

from app.infrastructure.database.models import Post
from app.presentation.bot.formatters.digest_formatter import DigestMessageFormatter

# Tags Telegram accepts in HTML parse mode.
TELEGRAM_ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "s", "del", "a",
    "code", "pre", "span", "tg-spoiler", "blockquote",
}


class _TelegramHTMLValidator(HTMLParser):
    """Mimics Telegram's parser: unknown tags and bad nesting are errors."""

    def __init__(self):
        super().__init__()
        self.errors = []
        self.open_tags = []

    def handle_starttag(self, tag, attrs):
        if tag not in TELEGRAM_ALLOWED_TAGS:
            self.errors.append(f"Unsupported start tag {tag!r}")
        else:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.open_tags and self.open_tags[-1] == tag:
            self.open_tags.pop()
        else:
            self.errors.append(f"Unbalanced end tag {tag!r}")


def assert_valid_telegram_html(message: str) -> None:
    validator = _TelegramHTMLValidator()
    validator.feed(message)
    assert not validator.errors, f"Telegram would reject: {validator.errors}"
    assert not validator.open_tags, f"Unclosed tags: {validator.open_tags}"


@pytest.fixture
def formatter():
    return DigestMessageFormatter()


def make_post(title="Title", summary="Summary", url="https://example.com/a"):
    return Post(
        id=uuid4(),
        hn_id=12345,
        title=title,
        author="a",
        url=url,
        type="story",
        score=100,
        comment_count=5,
        created_at=datetime.utcnow(),
        collected_at=datetime.utcnow(),
        summary=summary,
        is_dead=False,
        is_deleted=False,
        is_crawl_success=True,
    )


# Fragments taken verbatim from the production failure logs.
PRODUCTION_FAILURES = [
    "<select>", "<div>", "<box<struct", "<meta>", "<safety",
    "<script>", "$100k*", "9%)", "<usermedia\\", "<t>",
    "0.0001).", "<iframe>", "<n>", "<bool,", "<version",
    "<button>", "<refcell<t", "a<b and c>d", "AT&T", "<<<>>>",
]


@pytest.mark.parametrize("payload", PRODUCTION_FAILURES)
def test_summary_payloads_produce_valid_html(formatter, payload):
    """Summaries that broke production must now format cleanly."""
    post = make_post(summary=f"Discussion of {payload} in the article.")
    assert_valid_telegram_html(formatter.format_post_message(post, 1, 1))


@pytest.mark.parametrize("payload", PRODUCTION_FAILURES)
def test_title_payloads_produce_valid_html(formatter, payload):
    post = make_post(title=f"Post about {payload}")
    assert_valid_telegram_html(formatter.format_post_message(post, 1, 1))


@pytest.mark.parametrize("payload", PRODUCTION_FAILURES)
def test_full_message_payloads_produce_valid_html(formatter, payload):
    """The 'Show More' path had the identical bug."""
    post = make_post(title=f"T {payload}", summary=f"S {payload}")
    assert_valid_telegram_html(formatter.format_post_message_full(post, 1, 1))


def test_angle_brackets_are_escaped(formatter):
    post = make_post(summary="Use <div> not <span>.")
    message = formatter.format_post_message(post, 1, 1)
    assert "&lt;div&gt;" in message
    assert "<div>" not in message


def test_ampersand_is_escaped(formatter):
    post = make_post(title="Rust & Go")
    message = formatter.format_post_message(post, 1, 1)
    assert "Rust &amp; Go" in message


def test_url_query_ampersand_escaped_in_href(formatter):
    post = make_post(url="https://example.com/x?a=1&b=2")
    message = formatter.format_post_message(post, 1, 1)
    assert 'href="https://example.com/x?a=1&amp;b=2"' in message
    assert_valid_telegram_html(message)


def test_summary_cannot_inject_a_link(formatter):
    """A summary quoting an anchor must render as text, not markup."""
    post = make_post(summary='<a href="https://evil.test">click</a>')
    message = formatter.format_post_message(post, 1, 1)
    assert "evil.test" not in message.split("Read Article")[0].split("href=")[1]
    assert "&lt;a href=" in message
    assert_valid_telegram_html(message)


def test_title_is_bold(formatter):
    post = make_post(title="Hello")
    assert "<b>Hello</b>" in formatter.format_post_message(post, 1, 1)


def test_no_markdown_escaping_leaks_into_output(formatter):
    """The old Markdown escaper emitted backslashes that HTML mode shows raw."""
    post = make_post(title="Version 1.2 (beta) - final!", summary="Cost: $5.00.")
    message = formatter.format_post_message(post, 1, 1)
    assert "\\" not in message


@pytest.mark.parametrize("length", [3990, 4000, 4090, 4095, 4096, 4200, 6000])
def test_truncation_never_splits_markup(formatter, length):
    """Truncating must not cut inside a tag or entity."""
    post = make_post(title="T" * 50, summary="<div>&amp;x</div>" * length)
    for message in (
        formatter.format_post_message(post, 1, 1),
        formatter.format_post_message_full(post, 1, 1),
    ):
        assert len(message) <= formatter.MAX_MESSAGE_LENGTH
        assert_valid_telegram_html(message)


def test_missing_title_and_summary_still_valid(formatter):
    post = make_post(title=None, summary=None)
    message = formatter.format_post_message(post, 1, 1)
    assert "Untitled" in message
    assert_valid_telegram_html(message)
