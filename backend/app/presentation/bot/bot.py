"""Telegram bot setup using aiogram framework.

This module initializes the bot instance and creates the dispatcher with
all handlers and middleware.
"""

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

logger = logging.getLogger(__name__)


class BotConfig:
    """Bot configuration."""

    def __init__(self):
        """Initialize bot configuration from environment."""
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.parse_mode = ParseMode.MARKDOWN
        self.rate_limit_requests_per_minute = int(
            os.getenv("TELEGRAM_DELIVERY_RATE_LIMIT", "60")
        )
        self.max_messages_per_batch = int(
            os.getenv("TELEGRAM_MAX_MESSAGES_PER_USER", "20")
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

        logger.info(
            f"Bot configured: token={'*' * 10}..., "
            f"rate_limit={self.rate_limit_requests_per_minute} req/min, "
            f"max_messages={self.max_messages_per_batch}"
        )


class BotManager:
    """Manages bot instance, dispatcher, and handlers."""

    def __init__(self):
        """Initialize bot manager."""
        self.config = BotConfig()
        self._bot = None
        self._dp = None
        self._storage = None

    async def initialize(self):
        """Initialize bot, dispatcher, and storage."""
        # Create bot instance
        self._bot = Bot(
            token=self.config.token,
            default=DefaultBotProperties(parse_mode=self.config.parse_mode),
        )

        # Setup FSM storage (try Redis, fallback to Memory)
        try:
            self._storage = RedisStorage.from_url(self.config.redis_url)
            logger.info(f"Using Redis storage: {self.config.redis_url}")
        except Exception as e:
            logger.warning(
                f"Failed to connect to Redis ({e}), using in-memory storage"
            )
            self._storage = MemoryStorage()

        # Create dispatcher with storage
        self._dp = Dispatcher(storage=self._storage)

        # Import and register all handlers
        self._setup_handlers()

        # Setup middleware
        self._setup_middleware()

        logger.info("Bot initialized successfully")

    def _setup_handlers(self):
        """Register all handlers with dispatcher."""
        # Import handlers
        from app.presentation.bot.handlers import callbacks, commands, discussion, settings

        # Register routers in order of priority
        # 1. Commands (highest priority)
        self._dp.include_router(commands.router)

        # 2. Settings callbacks (inline buttons for settings)
        self._dp.include_router(settings.router)

        # 3. Callbacks (inline buttons)
        self._dp.include_router(callbacks.callback_router)

        # 4. Discussion messages (lowest priority, state-filtered)
        self._dp.include_router(discussion.router)

        logger.info("Handlers registered: commands, settings, callbacks, discussion")

    def _setup_middleware(self):
        """Setup middleware for database sessions."""
        from collections.abc import Awaitable, Callable
        from typing import Any

        from aiogram import BaseMiddleware
        from aiogram.types import Update
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from app.infrastructure.config.settings import settings

        # Create async engine for middleware
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )

        async_session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        class DatabaseMiddleware(BaseMiddleware):
            """Middleware to inject database session into handlers."""

            async def __call__(
                self,
                handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
                event: Update,
                data: dict[str, Any]
            ) -> Any:
                async with async_session_factory() as session:
                    data["session"] = session
                    return await handler(event, data)

        # Register middleware
        self._dp.update.middleware(DatabaseMiddleware())

        logger.info("Middleware registered: database session injection")

    def setup_dispatcher(self):
        """Setup dispatcher with handlers (legacy method).

        Returns:
            Dispatcher instance
        """
        if not self._dp:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        return self._dp

    @property
    def bot(self):
        """Get bot instance."""
        if not self._bot:
            raise RuntimeError("Bot not initialized. Call initialize() first.")
        return self._bot

    @property
    def dispatcher(self):
        """Get dispatcher instance."""
        if not self._dp:
            raise RuntimeError("Bot not initialized. Call initialize() first.")
        return self._dp

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

    async def shutdown(self):
        """Shutdown bot and close session."""
        if self._bot:
            await self._bot.session.close()
            logger.info("Bot session closed")

    async def start_polling(self):
        """Start bot in polling mode."""
        if not self._dp or not self._bot:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

        logger.info("Starting bot polling...")
        await self._dp.start_polling(self._bot)

    async def close(self):
        """Close bot session (legacy method)."""
        await self.shutdown()


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


def set_bot_manager(manager: BotManager) -> None:
    """Set the global bot manager instance.

    Args:
        manager: BotManager instance to set as global
    """
    global _bot_manager
    _bot_manager = manager


async def initialize_bot() -> BotManager:
    """Initialize bot (for FastAPI startup).

    Returns:
        BotManager instance
    """
    manager = get_bot_manager()
    await manager.initialize()
    logger.info("Bot initialized")
    return manager


async def shutdown_bot():
    """Shutdown bot (for FastAPI shutdown)."""
    manager = get_bot_manager()
    await manager.shutdown()
    logger.info("Bot shutdown complete")
