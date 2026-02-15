"""Unit tests for DigestMessageFormatter and InlineKeyboardBuilder."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.presentation.bot.formatters.digest_formatter import (
    DigestMessageFormatter,
    InlineKeyboardBuilder,
    create_message_and_keyboard,
)
from app.infrastructure.database.models import Post


class TestDigestMessageFormatter:
    """Test DigestMessageFormatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return DigestMessageFormatter()

    @pytest.fixture
    def sample_post(self):
        """Create sample post for testing."""
        return Post(
            id=uuid4(),
            hn_id=12345,
            title="PostgreSQL 18 Released",
            author="pg_author",
            url="https://www.postgresql.org/about/news/postgresql-18-released/",
            type="story",
            score=452,
            comment_count=230,
            created_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            summary="PostgreSQL 18 introduces major performance gains across OLTP workloads. "
            "New JSON path indexing and async I/O improve throughput by up to 2x.",
            is_dead=False,
            is_deleted=False,
            is_crawl_success=True,
        )

    @pytest.fixture
    def sample_post_no_url(self):
        """Create post without URL."""
        return Post(
            id=uuid4(),
            hn_id=12346,
            title="Test Post",
            author="author",
            type="story",
            score=100,
            comment_count=50,
            created_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            summary="Test summary",
            is_dead=False,
            is_deleted=False,
            is_crawl_success=True,
        )

    def test_formatter_initialization(self, formatter):
        """Test formatter initialization."""
        assert formatter.MAX_MESSAGE_LENGTH == 4096
        assert formatter.SUMMARY_TRUNCATE_LENGTH == 500

    def test_format_post_message_basic(self, formatter, sample_post):
        """Test formatting a post message with all fields."""
        message = formatter.format_post_message(sample_post, position=1, total=8)

        # Verify message contains all expected components
        assert "🔶 1/8" in message  # Position counter
        assert "PostgreSQL 18 Released" in message  # Title
        assert "postgresql.org" in message  # Domain
        assert "OLTP workloads" in message  # Summary content
        assert "⬆️ 452" in message  # Score
        assert "💬 230" in message  # Comment count

    def test_format_post_message_position_tracking(self, formatter, sample_post):
        """Test that position counter is correctly formatted."""
        message1 = formatter.format_post_message(sample_post, position=1, total=10)
        message5 = formatter.format_post_message(sample_post, position=5, total=10)
        message10 = formatter.format_post_message(sample_post, position=10, total=10)

        # Verify position is updated
        assert "🔶 1/10" in message1
        assert "🔶 5/10" in message5
        assert "🔶 10/10" in message10

    def test_format_post_message_no_summary(self, formatter, sample_post):
        """Test formatting post without summary."""
        sample_post.summary = None

        message = formatter.format_post_message(sample_post, position=1, total=1)

        # Should still have header and stats
        assert "🔶 1/1" in message
        assert "PostgreSQL 18 Released" in message
        assert "⬆️ 452" in message
        assert "💬 230" in message

    def test_format_post_message_empty_summary(self, formatter, sample_post):
        """Test formatting post with empty summary."""
        sample_post.summary = ""

        message = formatter.format_post_message(sample_post, position=1, total=1)

        # Should handle empty summary gracefully
        assert "🔶 1/1" in message
        assert "⬆️ 452" in message

    def test_format_post_message_no_title(self, formatter, sample_post):
        """Test formatting post without title."""
        sample_post.title = None

        message = formatter.format_post_message(sample_post, position=1, total=1)

        # Should use "Untitled" as fallback
        assert "Untitled" in message

    def test_format_post_message_no_url(self, formatter, sample_post_no_url):
        """Test formatting post without URL."""
        message = formatter.format_post_message(sample_post_no_url, position=1, total=1)

        # Should use default domain
        assert "hn.algolia.com" in message

    def test_extract_domain_basic(self, formatter):
        """Test domain extraction from standard URLs."""
        urls = [
            ("https://www.postgresql.org/news/article", "postgresql.org"),
            ("https://github.com/user/repo", "github.com"),
            ("https://example.com/page", "example.com"),
            ("http://blog.example.org/post", "blog.example.org"),
        ]

        for url, expected_domain in urls:
            domain = formatter._extract_domain(url)
            assert domain == expected_domain

    def test_extract_domain_removes_www_prefix(self, formatter):
        """Test that www prefix is removed from domains."""
        domain = formatter._extract_domain("https://www.example.com/page")
        assert domain == "example.com"
        assert not domain.startswith("www.")

    def test_extract_domain_invalid_url(self, formatter):
        """Test domain extraction with invalid URL."""
        domain = formatter._extract_domain("not-a-url")
        assert domain == "hn.algolia.com"

    def test_extract_domain_none_url(self, formatter):
        """Test domain extraction with None."""
        domain = formatter._extract_domain("")
        assert domain == "hn.algolia.com"

    def test_format_summary_normal(self, formatter):
        """Test formatting a normal summary."""
        summary = "This is a test summary with useful information."
        formatted = formatter._format_summary(summary)

        assert formatted == summary

    def test_format_summary_whitespace_trimming(self, formatter):
        """Test that summary whitespace is trimmed."""
        summary = "  Test summary with spaces  "
        formatted = formatter._format_summary(summary)

        assert formatted == "Test summary with spaces"

    def test_format_summary_truncation(self, formatter):
        """Test that long summaries are truncated."""
        # Create a summary longer than SUMMARY_TRUNCATE_LENGTH
        long_summary = "a" * 600

        formatted = formatter._format_summary(long_summary)

        # Should be truncated with ellipsis
        assert len(formatted) == formatter.SUMMARY_TRUNCATE_LENGTH + 3  # +3 for "..."
        assert formatted.endswith("...")

    def test_format_summary_exactly_at_limit(self, formatter):
        """Test summary that is exactly at truncation limit."""
        summary = "a" * formatter.SUMMARY_TRUNCATE_LENGTH
        formatted = formatter._format_summary(summary)

        # Should not be truncated if exactly at limit
        assert formatted == summary

    def test_format_summary_just_over_limit(self, formatter):
        """Test summary that is just over truncation limit."""
        summary = "a" * (formatter.SUMMARY_TRUNCATE_LENGTH + 1)
        formatted = formatter._format_summary(summary)

        # Should be truncated with ellipsis
        assert formatted.endswith("...")
        assert len(formatted) == formatter.SUMMARY_TRUNCATE_LENGTH + 3

    def test_format_summary_empty(self, formatter):
        """Test formatting empty summary."""
        formatted = formatter._format_summary("")
        assert formatted == ""

    def test_format_summary_none(self, formatter):
        """Test formatting None summary."""
        formatted = formatter._format_summary(None)
        assert formatted == ""

    def test_format_batch_header(self, formatter):
        """Test batch header formatting."""
        message = formatter.format_batch_header(total_posts=8)

        # Should contain emoji and post count
        assert "🔶 HN Digest" in message
        assert "8 posts" in message
        assert "Discuss" in message

    def test_message_length_compliance(self, formatter, sample_post):
        """Test that formatted messages don't exceed Telegram limit."""
        message = formatter.format_post_message(sample_post, position=1, total=100)

        # Should comply with Telegram's message length limit
        assert len(message) <= formatter.MAX_MESSAGE_LENGTH

    def test_message_structure(self, formatter, sample_post):
        """Test the structure of formatted message."""
        message = formatter.format_post_message(sample_post, position=3, total=5)

        # Verify message has proper line structure
        lines = message.split("\n")
        assert len(lines) >= 3  # At least header, domain, and stats

        # First line should be position
        assert lines[0].startswith("🔶 3/5")

        # Should have score and comment stats
        assert any("⬆️" in line for line in lines)
        assert any("💬" in line for line in lines)


class TestInlineKeyboardBuilder:
    """Test InlineKeyboardBuilder functionality."""

    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return InlineKeyboardBuilder()

    def test_builder_initialization(self, builder):
        """Test builder initialization."""
        assert builder is not None

    def test_build_post_keyboard_structure(self, builder):
        """Test post keyboard structure."""
        post_id = "test-post-id-123"
        keyboard = builder.build_post_keyboard(post_id)

        # Should have inline_keyboard key
        assert "inline_keyboard" in keyboard
        assert isinstance(keyboard["inline_keyboard"], list)

        # Should have 2 rows (actions and reactions)
        assert len(keyboard["inline_keyboard"]) == 2

        # First row should have 3 buttons
        assert len(keyboard["inline_keyboard"][0]) == 3

        # Second row should have 2 buttons
        assert len(keyboard["inline_keyboard"][1]) == 2

    def test_build_post_keyboard_action_buttons(self, builder):
        """Test that action buttons are correctly configured."""
        post_id = "test-123"
        keyboard = builder.build_post_keyboard(post_id)

        first_row = keyboard["inline_keyboard"][0]

        # Check button texts
        texts = [btn["text"] for btn in first_row]
        assert "💬 Discuss" in texts
        assert "🔗 Read" in texts
        assert "⭐ Save" in texts

    def test_build_post_keyboard_action_callbacks(self, builder):
        """Test that action button callbacks are correct."""
        post_id = "test-123"
        keyboard = builder.build_post_keyboard(post_id)

        first_row = keyboard["inline_keyboard"][0]

        # Check callback data
        callbacks = {btn["text"]: btn["callback_data"] for btn in first_row}

        assert callbacks["💬 Discuss"] == "discuss_test-123"
        assert callbacks["🔗 Read"] == "read_test-123"
        assert callbacks["⭐ Save"] == "save_test-123"

    def test_build_post_keyboard_reaction_buttons(self, builder):
        """Test that reaction buttons are correctly configured."""
        post_id = "test-123"
        keyboard = builder.build_post_keyboard(post_id)

        second_row = keyboard["inline_keyboard"][1]

        # Check reaction button texts
        texts = [btn["text"] for btn in second_row]
        assert "👍" in texts
        assert "👎" in texts

    def test_build_post_keyboard_reaction_callbacks(self, builder):
        """Test that reaction button callbacks are correct."""
        post_id = "test-123"
        keyboard = builder.build_post_keyboard(post_id)

        second_row = keyboard["inline_keyboard"][1]

        # Check callback data
        callbacks = {btn["text"]: btn["callback_data"] for btn in second_row}

        assert callbacks["👍"] == "react_up_test-123"
        assert callbacks["👎"] == "react_down_test-123"

    def test_build_post_keyboard_with_uuid(self, builder):
        """Test keyboard with UUID post ID."""
        post_id = "550e8400-e29b-41d4-a716-446655440000"
        keyboard = builder.build_post_keyboard(post_id)

        first_row = keyboard["inline_keyboard"][0]
        callbacks = {btn["text"]: btn["callback_data"] for btn in first_row}

        # Should handle UUID properly
        assert post_id in callbacks["💬 Discuss"]

    def test_build_batch_keyboard_structure(self, builder):
        """Test batch header keyboard structure."""
        keyboard = builder.build_batch_keyboard()

        # Should have inline_keyboard key
        assert "inline_keyboard" in keyboard
        assert isinstance(keyboard["inline_keyboard"], list)

        # Should have 1 row with 1 button
        assert len(keyboard["inline_keyboard"]) == 1
        assert len(keyboard["inline_keyboard"][0]) == 1

    def test_build_batch_keyboard_button(self, builder):
        """Test batch keyboard button configuration."""
        keyboard = builder.build_batch_keyboard()

        button = keyboard["inline_keyboard"][0][0]

        # Check button text and callback
        assert button["text"] == "📖 View Posts"
        assert button["callback_data"] == "view_posts"


class TestCreateMessageAndKeyboard:
    """Test the convenience function."""

    @pytest.fixture
    def sample_post(self):
        """Create sample post for testing."""
        return Post(
            id=uuid4(),
            hn_id=12345,
            title="Test Post",
            author="author",
            url="https://example.com",
            type="story",
            score=100,
            comment_count=50,
            created_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            summary="Test summary",
            is_dead=False,
            is_deleted=False,
            is_crawl_success=True,
        )

    def test_create_message_and_keyboard_returns_tuple(self, sample_post):
        """Test that function returns tuple."""
        result = create_message_and_keyboard(sample_post, position=1, total=5)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_create_message_and_keyboard_content(self, sample_post):
        """Test message and keyboard content."""
        message, keyboard = create_message_and_keyboard(sample_post, position=1, total=5)

        # Message should be formatted
        assert "🔶 1/5" in message
        assert "Test Post" in message
        assert "⬆️ 100" in message

        # Keyboard should be valid
        assert "inline_keyboard" in keyboard
        assert len(keyboard["inline_keyboard"]) == 2

    def test_create_message_and_keyboard_post_id_in_callbacks(self, sample_post):
        """Test that post ID is used in callbacks."""
        message, keyboard = create_message_and_keyboard(sample_post, position=1, total=1)

        # Get post ID from keyboard callbacks
        first_button = keyboard["inline_keyboard"][0][0]
        callback_data = first_button["callback_data"]

        # Should contain post ID
        assert str(sample_post.id) in callback_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
