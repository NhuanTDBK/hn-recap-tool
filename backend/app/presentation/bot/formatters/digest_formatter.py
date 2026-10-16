"""Message formatter for Telegram digest delivery.

Formats HN posts as Style 2 (Flat Scroll) messages per spec:
- One post per message
- Flat scrolling layout
- Inline buttons (Discuss, Read, Save)
- Reaction buttons (👍 👎)
"""

import html
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from app.infrastructure.config.settings import settings
from app.infrastructure.database.models import Post

logger = logging.getLogger(__name__)


class DigestMessageFormatter:
    """Formats HN posts into Telegram messages (Style 2: Flat Scroll)."""

    # Telegram message character limits
    MAX_MESSAGE_LENGTH = 4096
    SUMMARY_TRUNCATE_LENGTH = 500

    def __init__(self):
        """Initialize formatter."""
        self.full_summary_max_length = settings.telegram_full_summary_max_length

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

        # Title (bold with HTML)
        title = post.title or "Untitled"
        message_parts.append(f"<b>{self._escape_html(title)}</b>")

        # HackerNews discussion link
        if post.hn_id:
            hn_link = f"https://news.ycombinator.com/item?id={post.hn_id}"
            message_parts.append(f'<a href="{hn_link}">HN Discussion</a>')

        # Summary text (escaped — AI summaries often quote raw HTML/code)
        summary = self._format_summary(post.summary)
        if summary:
            message_parts.append(f"\n{self._escape_html(summary)}")

        # External article link (if available)
        if post.url:
            safe_url = self._escape_url_for_html(post.url)
            domain = self._escape_html(self._extract_domain(post.url))
            message_parts.append(
                f'\n<a href="{safe_url}">Read Article on {domain}</a>'
            )

        # Stats: Score, comments, and position
        stats = f"\n⬆️ {post.score} · 💬 {post.comment_count} · {position}/{total}"
        message_parts.append(stats)

        # Combine all parts
        message = "\n".join(message_parts)

        # Ensure message doesn't exceed Telegram limit
        message = self._truncate_to_limit(message, post.hn_id)

        return message

    def format_post_message_full(
        self,
        post: Post,
        position: int,
        total: int,
        summary: Optional[str] = None,
    ) -> str:
        """Format a single post with full untruncated summary (for "Show More" expansion).

        Same structure as format_post_message() but without summary truncation.
        Respects MAX_MESSAGE_LENGTH safety limit.

        Args:
            post: Post model
            position: Position in digest (1-based)
            total: Total posts in digest
            summary: Summary text to show; defaults to post.summary

        Returns:
            Formatted message text with full summary
        """
        summary_text = summary if summary is not None else post.summary
        message_parts = []

        # Title (bold with HTML)
        title = post.title or "Untitled"
        message_parts.append(f"<b>{self._escape_html(title)}</b>")

        # HackerNews discussion link
        if post.hn_id:
            hn_link = f"https://news.ycombinator.com/item?id={post.hn_id}"
            message_parts.append(f'<a href="{hn_link}">HN Discussion</a>')

        # Full summary text (no truncation, but apply safety limit)
        if summary_text:
            summary = summary_text.strip()
            # Apply safety limit (Telegram max 4096, leave buffer)
            if len(summary) > self.full_summary_max_length:
                summary = summary[: self.full_summary_max_length] + "..."
            # Escape after truncating so entities are never split
            message_parts.append(f"\n{self._escape_html(summary)}")

        # External article link (if available)
        if post.url:
            safe_url = self._escape_url_for_html(post.url)
            domain = self._escape_html(self._extract_domain(post.url))
            message_parts.append(
                f'\n<a href="{safe_url}">Read Article on {domain}</a>'
            )

        # Stats: Score, comments, and position
        stats = f"\n⬆️ {post.score} · 💬 {post.comment_count} · {position}/{total}"
        message_parts.append(stats)

        # Combine all parts
        message = "\n".join(message_parts)

        # Ensure message doesn't exceed Telegram limit
        message = self._truncate_to_limit(message, post.hn_id)

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

    def _truncate_to_limit(self, message: str, hn_id: Optional[int] = None) -> str:
        """Truncate a message to Telegram's limit without splitting HTML markup.

        A naive slice can land inside a tag ("<b") or an entity ("&lt"), which
        makes Telegram reject the message with "can't parse entities" — the very
        failure this formatter exists to avoid. Since truncation only ever cuts
        the trailing stats line (summaries are already bounded), it is safe to
        back off to the last character that leaves markup intact.

        Args:
            message: Fully formatted message
            hn_id: Post's HN ID, for logging

        Returns:
            Message no longer than MAX_MESSAGE_LENGTH
        """
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return message

        logger.warning(
            f"Message too long for post {hn_id}, "
            f"truncating ({len(message)} chars)"
        )

        truncated = message[: self.MAX_MESSAGE_LENGTH]

        # Back off past an unterminated tag or entity introduced by the cut.
        for opener, closer in (("<", ">"), ("&", ";")):
            start = truncated.rfind(opener)
            if start != -1 and truncated.find(closer, start) == -1:
                truncated = truncated[:start]

        # Close the title's bold tag if the cut landed inside it.
        if truncated.count("<b>") > truncated.count("</b>"):
            truncated += "</b>"

        return truncated

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

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters in text.

        The bot sends messages with ParseMode.HTML, so any literal <, > or &
        in post titles or summaries must be escaped or Telegram rejects the
        whole message with "can't parse entities". AI summaries of HN posts
        routinely quote code containing tags like <div> or <script>.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for Telegram's HTML parse mode
        """
        if not text:
            return ""

        # quote=False: we only interpolate into text nodes, never attributes
        return html.escape(text, quote=False)

    def _escape_url_for_html(self, url: str) -> str:
        """Escape a URL for use in an HTML href attribute.

        Args:
            url: URL to escape

        Returns:
            Escaped URL safe for an href attribute
        """
        if not url:
            return ""

        return html.escape(url, quote=True)


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

    def build_post_keyboard_saved(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard for a post message after Save has been tapped.

        Returns single-row button structure:
        - [ 📖 More ] [ ✅ Saved ] [ ⚡ Actions ]

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                [
                    {
                        "text": "📖 More",
                        "callback_data": f"show_more_{post_id}",
                    },
                    {
                        "text": "✅ Saved",
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

    def build_post_keyboard_without_more_saved(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard after summary expanded and Save has been tapped.

        Returns two-button layout:
        - [ ✅ Saved ] [ ⚡ Actions ]

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Saved",
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
