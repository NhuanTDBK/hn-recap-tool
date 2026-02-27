"""Message formatter for Telegram digest delivery.

Formats HN posts as Style 2 (Flat Scroll) messages per spec:
- One post per message
- Flat scrolling layout
- Inline buttons (Discuss, Read, Save)
- Reaction buttons (👍 👎)
"""

import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from app.infrastructure.database.models import Post

logger = logging.getLogger(__name__)


class DigestMessageFormatter:
    """Formats HN posts into Telegram messages (Style 2: Flat Scroll)."""

    # Telegram message character limits
    MAX_MESSAGE_LENGTH = 4096
    SUMMARY_TRUNCATE_LENGTH = 500

    def __init__(self):
        """Initialize formatter."""
        pass

    def format_post_message(
        self,
        post: Post,
        position: int,
        total: int,
    ) -> str:
        """Format a single post as a Telegram message.

        New improved format (inspired by push_to_telegram.py):
        ```
        *PostgreSQL 18 Released*
        [HN Discussion](https://news.ycombinator.com/item?id=12345)

        Major performance gains across OLTP workloads with up to 2x throughput.
        New JSON path indexing and async I/O.

        [Read Article](https://postgresql.org/about/news/...)

        ⬆️ 452 · 💬 230 · 1/8
        ```

        Args:
            post: Post model
            position: Position in digest (1-based)
            total: Total posts in digest

        Returns:
            Formatted message text (without buttons)
        """
        message_parts = []

        # Title (bold with Markdown)
        title = post.title or "Untitled"
        message_parts.append(f"*{self._escape_markdown(title)}*")

        # HackerNews discussion link
        if post.hn_id:
            hn_link = f"https://news.ycombinator.com/item?id={post.hn_id}"
            message_parts.append(f"[HN Discussion]({hn_link})")

        # Summary text
        summary = self._format_summary(post.summary)
        if summary:
            message_parts.append(f"\n{summary}")

        # External article link (if available)
        if post.url:
            # Escape special characters in URL for Markdown
            safe_url = self._escape_url_for_markdown(post.url)
            domain = self._extract_domain(post.url)
            message_parts.append(f"\n[Read Article on {domain}]({safe_url})")

        # Stats: Score, comments, and position
        stats = f"\n⬆️ {post.score} · 💬 {post.comment_count} · {position}/{total}"
        message_parts.append(stats)

        # Combine all parts
        message = "\n".join(message_parts)

        # Ensure message doesn't exceed Telegram limit
        if len(message) > self.MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Message too long for post {post.hn_id}, "
                f"truncating ({len(message)} chars)"
            )
            message = message[: self.MAX_MESSAGE_LENGTH]

        return message

    def format_post_message_full(
        self,
        post: Post,
        position: int,
        total: int,
    ) -> str:
        """Format a single post with full untruncated summary (for "Show More" expansion).

        Same structure as format_post_message() but without summary truncation.
        Respects MAX_MESSAGE_LENGTH safety limit.

        Args:
            post: Post model
            position: Position in digest (1-based)
            total: Total posts in digest

        Returns:
            Formatted message text with full summary
        """
        message_parts = []

        # Title (bold with Markdown)
        title = post.title or "Untitled"
        message_parts.append(f"*{self._escape_markdown(title)}*")

        # HackerNews discussion link
        if post.hn_id:
            hn_link = f"https://news.ycombinator.com/item?id={post.hn_id}"
            message_parts.append(f"[HN Discussion]({hn_link})")

        # Full summary text (no truncation, but apply safety limit)
        if post.summary:
            summary = post.summary.strip()
            # Apply safety limit (Telegram max 4096, leave buffer)
            if len(summary) > 4000:
                summary = summary[:4000] + "..."
            message_parts.append(f"\n{summary}")

        # External article link (if available)
        if post.url:
            # Escape special characters in URL for Markdown
            safe_url = self._escape_url_for_markdown(post.url)
            domain = self._extract_domain(post.url)
            message_parts.append(f"\n[Read Article on {domain}]({safe_url})")

        # Stats: Score, comments, and position
        stats = f"\n⬆️ {post.score} · 💬 {post.comment_count} · {position}/{total}"
        message_parts.append(stats)

        # Combine all parts
        message = "\n".join(message_parts)

        # Ensure message doesn't exceed Telegram limit
        if len(message) > self.MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Full message too long for post {post.hn_id}, "
                f"truncating ({len(message)} chars)"
            )
            message = message[: self.MAX_MESSAGE_LENGTH]

        return message

    def format_batch_header(self, total_posts: int) -> str:
        """Format header message for digest batch.

        Args:
            total_posts: Total posts in this batch

        Returns:
            Header message text
        """
        return (
            f"🔶 HN Digest — {total_posts} posts\n\n"
            f"Scroll through each post. "
            f"Tap Discuss to start a conversation."
        )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., "postgresql.org")
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove common prefixes
            if domain.startswith("www."):
                domain = domain[4:]
            return domain or "hn.algolia.com"
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return "hn.algolia.com"

    def _format_summary(self, summary: Optional[str]) -> str:
        """Format summary text for message.

        Args:
            summary: Raw summary from database

        Returns:
            Formatted summary (truncated if needed)
        """
        if not summary:
            return ""

        # Clean up summary text
        summary = summary.strip()

        # Truncate if too long
        if len(summary) > self.SUMMARY_TRUNCATE_LENGTH:
            summary = summary[: self.SUMMARY_TRUNCATE_LENGTH] + "..."

        return summary

    def _escape_markdown(self, text: str) -> str:
        """Escape Markdown special characters in text.

        Telegram uses Markdown for formatting, so we need to escape:
        * (asterisk), _ (underscore), [ (bracket), ] (bracket), ( (paren), ) (paren)

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for Markdown
        """
        if not text:
            return ""

        # Escape special Markdown characters
        escape_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')

        return text

    def _escape_url_for_markdown(self, url: str) -> str:
        """Escape URL for Markdown link format.

        Only escape ')' in URLs as other characters are allowed.

        Args:
            url: URL to escape

        Returns:
            Escaped URL
        """
        if not url:
            return ""

        # Only escape closing parenthesis in URLs
        return url.replace(')', '\\)')


class InlineKeyboardBuilder:
    """Builds inline keyboard buttons for Telegram messages."""

    def build_post_keyboard(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard for a post message (default menu).

        Returns single-row button structure:
        - [ 📖 More ] [ 🔖 Save ] [ ⚡ Actions ]

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                # Default menu: Show More, Save, Actions
                [
                    {
                        "text": "📖 More",
                        "callback_data": f"show_more_{post_id}",
                    },
                    {
                        "text": "🔖 Save",
                        "callback_data": f"save_post_{post_id}",
                    },
                    {
                        "text": "⚡ Actions",
                        "callback_data": f"actions_{post_id}",
                    },
                ],
            ]
        }

        return buttons

    def build_post_keyboard_without_more(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard after summary has been expanded.

        Returns two-button layout (without Show More):
        - [ 🔖 Save ] [ ⚡ Actions ]

        Used when user has already tapped "More" and summary is expanded.

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                # After expansion: Save and Actions only
                [
                    {
                        "text": "🔖 Save",
                        "callback_data": f"save_post_{post_id}",
                    },
                    {
                        "text": "⚡ Actions",
                        "callback_data": f"actions_{post_id}",
                    },
                ],
            ]
        }

        return buttons

    def build_reactions_keyboard(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard for reactions menu.

        Returns three-button layout:
        - [ 👍 Good Response ] [ 👎 Bad Response ] [ « Back ]

        Used when user taps "Actions" to show reactions and back button.

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                # Reactions menu
                [
                    {
                        "text": "👍 Good Response",
                        "callback_data": f"react_up_{post_id}",
                    },
                    {
                        "text": "👎 Bad Response",
                        "callback_data": f"react_down_{post_id}",
                    },
                    {
                        "text": "« Back",
                        "callback_data": f"back_{post_id}",
                    },
                ],
            ]
        }

        return buttons

    def build_batch_keyboard(self) -> Dict[str, Any]:
        """Build keyboard for batch header message.

        Returns button structure for batch actions.

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                # Single button to start viewing posts
                [
                    {
                        "text": "📖 View Posts",
                        "callback_data": "view_posts",
                    },
                ],
            ]
        }

        return buttons


def create_message_and_keyboard(
    post: Post,
    position: int,
    total: int,
) -> tuple:
    """Create both message text and keyboard for a post.

    Convenience function combining formatter and keyboard builder.

    Args:
        post: Post model
        position: Position in digest
        total: Total posts

    Returns:
        Tuple of (message_text, keyboard_dict)
    """
    formatter = DigestMessageFormatter()
    builder = InlineKeyboardBuilder()

    message_text = formatter.format_post_message(post, position, total)
    keyboard = builder.build_post_keyboard(str(post.id))

    return message_text, keyboard
