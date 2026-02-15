"""Telegram bot presentation layer using aiogram."""

from .bot import BotManager, get_bot_manager, initialize_bot, shutdown_bot

__all__ = [
    "BotManager",
    "get_bot_manager",
    "initialize_bot",
    "shutdown_bot",
]
