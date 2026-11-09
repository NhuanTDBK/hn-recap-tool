"""Sends the daily recommendations into their Telegram forum topic."""

import logging

from aiogram.types import InlineKeyboardMarkup

from app.infrastructure.database.models import Post
from app.presentation.bot.bot import BotManager
from app.presentation.bot.formatters.digest_formatter import (
    DigestMessageFormatter,
    InlineKeyboardBuilder,
)

logger = logging.getLogger(__name__)


class RecommendationDeliveryHandler:
    """Formats and sends recommendation messages through a ``BotManager``.

    Takes its bot manager explicitly instead of reading the global one: the hourly
    delivery job swaps and shuts down the global in the same process.
    """

    def __init__(self, bot_manager: BotManager):
        """Initialize handler.

        Args:
            bot_manager: An initialized bot manager
        """
        self.bot_manager = bot_manager
        self.formatter = DigestMessageFormatter()
        self.keyboard_builder = InlineKeyboardBuilder()

    async def send_header(
        self,
        chat_id: int,
        topic_id: int | None,
        count: int,
        interests: list[str],
    ) -> int:
        """Send the message that opens a day's picks.

        Returns:
            Telegram message ID

        Raises:
            Exception: If the send fails
        """
        result = await self.bot_manager.send_message(
            chat_id=chat_id,
            text=self.formatter.format_recommendation_header(count, interests),
            message_thread_id=topic_id,
        )
        return result["message_id"]

    async def send_pick(
        self,
        chat_id: int,
        topic_id: int | None,
        post: Post,
        summary: str | None,
        position: int,
        total: int,
    ) -> int:
        """Send one recommended post with its More / Save / Why / Not for me buttons.

        Returns:
            Telegram message ID

        Raises:
            Exception: If the send fails
        """
        keyboard = self.keyboard_builder.build_recommendation_keyboard(str(post.id))
        result = await self.bot_manager.send_message(
            chat_id=chat_id,
            text=self.formatter.format_recommendation_message(
                post, summary, position, total
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=keyboard["inline_keyboard"]
            ),
            message_thread_id=topic_id,
        )
        return result["message_id"]
