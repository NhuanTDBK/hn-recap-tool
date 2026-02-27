#!/usr/bin/env python
"""Send a sample digest message with the new Epic 9 button layout to Telegram.

Fetches a real post with summary from PostgreSQL and sends it using the
new inline button design: [ 📖 More ] [ 🔖 Save ] [ ⚡ Actions ]

Usage:
    python scripts/send_sample_message.py --chat-id <TELEGRAM_CHAT_ID>
    python scripts/send_sample_message.py --chat-id @hndigest
    python scripts/send_sample_message.py --chat-id @hndigest --limit 3
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup

from app.infrastructure.config.settings import settings
from app.infrastructure.database.models import Post
from app.presentation.bot.bot import BotManager, set_bot_manager
from app.presentation.bot.formatters.digest_formatter import (
    DigestMessageFormatter,
    InlineKeyboardBuilder,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


PLACEHOLDER_SUMMARY = (
    "This post is trending on Hacker News with high engagement from the community. "
    "The discussion covers key technical insights, trade-offs, and real-world implications "
    "that developers and engineers are actively debating. Community members have shared "
    "benchmarks, alternative approaches, and practical experience from production environments. "
    "The consensus leans toward a significant shift in how the ecosystem approaches this problem, "
    "with several core contributors weighing in on the direction. [Test summary — no AI summary generated yet]"
)


async def fetch_posts(session: AsyncSession, limit: int) -> list[Post]:
    """Fetch top posts from the database (with or without summaries)."""
    stmt = (
        select(Post)
        .where(Post.title.isnot(None))
        .order_by(Post.score.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    posts = result.scalars().all()

    # Inject placeholder summary for posts that don't have one
    for post in posts:
        if not post.summary:
            post.summary = PLACEHOLDER_SUMMARY

    return posts


async def send_sample(chat_id: str, limit: int = 1):
    """Send sample messages with new button layout to Telegram.

    Args:
        chat_id: Telegram chat ID or @channel username
        limit: Number of sample posts to send
    """
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Init bot
    bot_manager = BotManager()
    await bot_manager.initialize()
    set_bot_manager(bot_manager)

    formatter = DigestMessageFormatter()
    keyboard_builder = InlineKeyboardBuilder()

    try:
        async with AsyncSessionLocal() as session:
            posts = await fetch_posts(session, limit)

            if not posts:
                print("❌ No posts found in database.")
                return

            total = len(posts)
            print(f"\n✅ Found {total} post(s) with summaries. Sending to {chat_id}...\n")

            for position, post in enumerate(posts, 1):
                # Format message with truncated summary (default view)
                message_text = formatter.format_post_message(post, position, total)

                # Build new Epic 9 keyboard: [ 📖 More ] [ 🔖 Save ] [ ⚡ Actions ]
                keyboard_dict = keyboard_builder.build_post_keyboard(str(post.id))
                keyboard_markup = InlineKeyboardMarkup(
                    inline_keyboard=keyboard_dict["inline_keyboard"]
                )

                print(f"Sending post {position}/{total}: {post.title[:60]}...")
                print(f"  Post ID: {post.id}")
                print(f"  Summary length: {len(post.summary or '')} chars")
                print(f"  Message length: {len(message_text)} chars")
                print()

                result = await bot_manager.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    reply_markup=keyboard_markup,
                    parse_mode=ParseMode.MARKDOWN,
                )

                print(f"  ✅ Sent! message_id={result['message_id']}")

                if position < total:
                    await asyncio.sleep(1.0)

            print(f"\n🎉 Done! Sent {total} message(s) to {chat_id}")
            print("Check your Telegram chat to see the new button layout.")

    finally:
        await engine.dispose()
        await bot_manager.close()


def main():
    parser = argparse.ArgumentParser(description="Send sample digest message with new Epic 9 layout")
    parser.add_argument(
        "--chat-id",
        required=True,
        help="Telegram chat ID or @channel (e.g. @hndigest or 123456789)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of sample posts to send (default: 1)",
    )
    args = parser.parse_args()

    asyncio.run(send_sample(args.chat_id, args.limit))


if __name__ == "__main__":
    main()
