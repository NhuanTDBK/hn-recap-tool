#!/usr/bin/env python
"""Test script to verify bot setup and get your Telegram ID.

Usage:
    python scripts/test_bot_setup.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_bot_setup():
    """Test bot configuration and connection."""
    print("=" * 80)
    print("HN PAL BOT SETUP TEST")
    print("=" * 80)

    # Check environment variables
    print("\n📋 Checking environment variables...")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        print(f"✅ TELEGRAM_BOT_TOKEN: {bot_token[:10]}...{bot_token[-10:]}")
    else:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return False

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print(f"✅ DATABASE_URL: {database_url[:30]}...")
    else:
        print("❌ DATABASE_URL not found in .env")
        return False

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"✅ REDIS_URL: {redis_url}")

    # Test bot connection
    print("\n🤖 Testing bot connection...")

    try:
        from aiogram import Bot

        bot = Bot(token=bot_token)
        me = await bot.get_me()

        print(f"✅ Bot connected successfully!")
        print(f"   Bot ID: {me.id}")
        print(f"   Bot username: @{me.username}")
        print(f"   Bot name: {me.first_name}")

        await bot.session.close()

        print(f"\n🔗 Your bot link: https://t.me/{me.username}")

    except Exception as e:
        print(f"❌ Failed to connect to bot: {e}")
        return False

    # Test database connection
    print("\n🗄️  Testing database connection...")

    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        from app.infrastructure.database.models import User

        engine = create_async_engine(database_url, echo=False)
        async_session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_factory() as session:
            stmt = select(User).limit(1)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            print("✅ Database connection successful!")

            if user:
                print(f"   Found {user.id} user(s) in database")
                print(f"   Sample user: telegram_id={user.telegram_id}, username={user.username}")
            else:
                print("   No users in database yet (will be created on /start)")

        await engine.dispose()

    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False

    # Test Redis connection
    print("\n🔴 Testing Redis connection...")

    try:
        from aiogram.fsm.storage.redis import RedisStorage

        storage = RedisStorage.from_url(redis_url)
        print("✅ Redis connection successful!")
        print("   FSM state will be stored in Redis")

    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("   Will fallback to in-memory storage (states won't persist)")

    # Summary
    print("\n" + "=" * 80)
    print("✅ SETUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run the bot: python scripts/run_bot.py")
    print("2. Open Telegram and search for your bot")
    print("3. Send /start to begin")
    print("\nTo find your Telegram ID:")
    print("- Search for @userinfobot in Telegram")
    print("- Start the bot and it will show your ID")
    print("\n" + "=" * 80)

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_bot_setup())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
