"""Telegram bot setup using aiogram framework.

This module initializes the bot instance and creates the dispatcher with
all handlers and middleware.
"""

import asyncio
import logging
import os
import socket

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

logger = logging.getLogger(__name__)


class IPv4AiohttpSession(AiohttpSession):
    """Aiohttp session that forces IPv4 for Telegram API calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connector_init["family"] = socket.AF_INET


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
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.network_retry_attempts = int(
            os.getenv("TELEGRAM_NETWORK_RETRY_ATTEMPTS", "3")
        )
        self.network_retry_base_delay_seconds = float(
            os.getenv("TELEGRAM_NETWORK_RETRY_BASE_DELAY_SECONDS", "1.0")
        )
        self.polling_restart_delay_seconds = float(
            os.getenv("TELEGRAM_POLLING_RESTART_DELAY_SECONDS", "3.0")
        )
        self.force_ipv4 = os.getenv("TELEGRAM_FORCE_IPV4", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment")

        logger.info(
            f"Bot configured: token={'*' * 10}..., "
            f"rate_limit={self.rate_limit_requests_per_minute} req/min, "
            f"max_messages={self.max_messages_per_batch}, "
            f"network_retries={self.network_retry_attempts}, "
            f"force_ipv4={self.force_ipv4}"
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
        session = IPv4AiohttpSession() if self.config.force_ipv4 else None
        self._bot = Bot(
            token=self.config.token,
            default=DefaultBotProperties(parse_mode=self.config.parse_mode),
            session=session,
        )

        # Setup FSM storage (try Redis, fallback to Memory)
        try:
            self._storage = RedisStorage.from_url(self.config.redis_url)
            logger.info(f"Using Redis storage: {self.config.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis ({e}), using in-memory storage")
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
        from app.presentation.bot.handlers import (
            callbacks,
            commands,
            discussion,
            settings,
        )

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
                data: dict[str, Any],
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
        max_attempts = max(1, self.config.network_retry_attempts)
        base_delay = max(0.1, self.config.network_retry_base_delay_seconds)

        for attempt in range(1, max_attempts + 1):
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

            except TelegramRetryAfter as e:
                if attempt >= max_attempts:
                    logger.error(
                        f"Rate limited sending message to {chat_id} after {attempt} attempts: {e}"
                    )
                    raise

                delay = max(float(e.retry_after), base_delay)
                logger.warning(
                    f"Rate limited sending message to {chat_id}; retrying in {delay:.1f}s "
                    f"(attempt {attempt}/{max_attempts})"
                )
                await asyncio.sleep(delay)

            except TelegramNetworkError as e:
                if attempt >= max_attempts:
                    logger.error(
                        f"Network error sending message to {chat_id} after {attempt} attempts: {e}"
                    )
                    raise

                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Network error sending message to {chat_id}; retrying in {delay:.1f}s "
                    f"(attempt {attempt}/{max_attempts}): {e}"
                )
                await asyncio.sleep(delay)

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

        restart_delay = max(1.0, self.config.polling_restart_delay_seconds)

        while True:
            try:
                logger.info("Starting bot polling...")
                await self._dp.start_polling(self._bot)
                logger.info("Bot polling stopped")
                return
            except asyncio.CancelledError:
                logger.info("Bot polling cancelled")
                raise
            except TelegramNetworkError as e:
                logger.warning(
                    f"Bot polling interrupted by network error. Restarting in {restart_delay:.1f}s: {e}"
                )
                await asyncio.sleep(restart_delay)

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
