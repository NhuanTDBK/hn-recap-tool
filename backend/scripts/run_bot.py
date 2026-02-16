#!/usr/bin/env python
"""Standalone script to run the Telegram bot in polling mode.

Usage:
    python scripts/run_bot.py

Environment variables required:
    TELEGRAM_BOT_TOKEN - Bot token from @BotFather
    DATABASE_URL - PostgreSQL connection string
    REDIS_URL - Redis connection string (optional, fallback to memory storage)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.presentation.bot.bot import BotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for bot."""
    logger.info("="*80)
    logger.info("HN PAL TELEGRAM BOT - Starting")
    logger.info("="*80)

    bot_manager = BotManager()

    try:
        # Initialize bot (loads handlers, middleware, storage)
        await bot_manager.initialize()
        logger.info("✓ Bot initialized successfully")

        # Start polling
        logger.info("✓ Bot is running in polling mode...")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*80 + "\n")

        await bot_manager.start_polling()

    except KeyboardInterrupt:
        logger.info("\n⚠ Bot stopped by user (Ctrl+C)")

    except Exception as e:
        logger.error(f"✗ Bot failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Shutdown
        await bot_manager.shutdown()
        logger.info("✓ Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
