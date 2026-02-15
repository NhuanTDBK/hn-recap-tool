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

        Format per spec (Style 2):
        ```
        🔶 1/8 · PostgreSQL 18 Released
        postgresql.org

        Major performance gains across OLTP
        workloads with up to 2x throughput.
        New JSON path indexing and async I/O.

        ⬆️ 452 · 💬 230
        ```

        Args:
            post: Post model
            position: Position in digest (1-based)
            total: Total posts in digest

        Returns:
            Formatted message text (without buttons)
        """
        # Header: Position counter and title
        title = post.title or "Untitled"
        header = f"🔶 {position}/{total} · {title}\n"

        # Domain: Extract from URL
        domain = self._extract_domain(post.url) if post.url else "hn.algolia.com"
        domain_line = f"{domain}\n"

        # Summary: Use 2-3 sentence summary from DB
        summary = self._format_summary(post.summary)
        summary_line = f"\n{summary}\n" if summary else ""

        # Stats: Score and comment count
        stats = f"\n⬆️ {post.score} · 💬 {post.comment_count}"

        # Combine all parts
        message = header + domain_line + summary_line + stats

        # Ensure message doesn't exceed Telegram limit
        if len(message) > self.MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Message too long for post {post.hn_id}, "
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


class InlineKeyboardBuilder:
    """Builds inline keyboard buttons for Telegram messages."""

    def build_post_keyboard(self, post_id: str) -> Dict[str, Any]:
        """Build inline keyboard for a post message.

        Returns button structure for:
        - Discuss button (💬)
        - Read button (🔗)
        - Save button (⭐)
        - Reaction buttons (👍 👎)

        Args:
            post_id: Post ID (UUID string)

        Returns:
            Keyboard dict for aiogram InlineKeyboardMarkup
        """
        buttons = {
            "inline_keyboard": [
                # Row 1: Action buttons
                [
                    {
                        "text": "💬 Discuss",
                        "callback_data": f"discuss_{post_id}",
                    },
                    {
                        "text": "🔗 Read",
                        "callback_data": f"read_{post_id}",
                    },
                    {
                        "text": "⭐ Save",
                        "callback_data": f"save_{post_id}",
                    },
                ],
                # Row 2: Reaction buttons
                [
                    {
                        "text": "👍",
                        "callback_data": f"react_up_{post_id}",
                    },
                    {
                        "text": "👎",
                        "callback_data": f"react_down_{post_id}",
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
