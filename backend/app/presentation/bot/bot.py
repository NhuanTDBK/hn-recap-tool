"""Telegram bot setup using aiogram framework.

This module initializes the bot instance and creates the router for
handling messages and callbacks.
"""

import logging
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)


class BotConfig:
    """Bot configuration."""

    def __init__(self):
        """Initialize bot configuration from environment."""
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.parse_mode = ParseMode.HTML
        self.rate_limit_requests_per_minute = int(
            os.getenv("TELEGRAM_DELIVERY_RATE_LIMIT", "60")
        )
        self.max_messages_per_batch = int(
            os.getenv("TELEGRAM_MAX_MESSAGES_PER_USER", "20")
        )

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

        logger.info(
            f"Bot configured: token={'*' * 10}..., "
            f"rate_limit={self.rate_limit_requests_per_minute} req/min, "
            f"max_messages={self.max_messages_per_batch}"
        )


class BotManager:
    """Manages bot instance and router."""

    def __init__(self):
        """Initialize bot manager."""
        self.config = BotConfig()
        self.bot = Bot(
            token=self.config.token,
            parse_mode=self.config.parse_mode,
        )
        self.router = Router()
        self.dp = None

    def setup_dispatcher(self):
        """Setup dispatcher with router.

        Returns:
            Dispatcher instance
        """
        self.dp = Dispatcher()
        self.dp.include_router(self.router)

        logger.info("Dispatcher setup complete")

        return self.dp

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup=None,
        parse_mode=None,
    ) -> dict:
        """Send a message to a user.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            reply_markup: Inline keyboard markup
            parse_mode: Parse mode (HTML, Markdown)

        Returns:
            Message dict with message_id

        Raises:
            Exception: If message send fails
        """
        try:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode or self.config.parse_mode,
            )

            logger.debug(f"Sent message to {chat_id}: msg_id={message.message_id}")

            return {
                "message_id": message.message_id,
                "chat_id": message.chat.id,
                "date": message.date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            raise

    async def close(self):
        """Close bot session."""
        await self.bot.session.close()
        logger.info("Bot session closed")


# Global bot manager instance
_bot_manager = None


def get_bot_manager() -> BotManager:
    """Get or create bot manager instance.

    Returns:
        BotManager instance
    """
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = BotManager()
    return _bot_manager


async def initialize_bot() -> BotManager:
    """Initialize bot (for FastAPI startup).

    Returns:
        BotManager instance
    """
    manager = get_bot_manager()
    manager.setup_dispatcher()
    logger.info("Bot initialized")
    return manager


async def shutdown_bot():
    """Shutdown bot (for FastAPI shutdown)."""
    manager = get_bot_manager()
    await manager.close()
    logger.info("Bot shutdown complete")
