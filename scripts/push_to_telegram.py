#!/usr/bin/env python3

"""Script to push HackerNews digest to Telegram channel.

This script reads summaries from JSONL file and sends each summary as a separate message
to Telegram. Each message includes:
- Article title
- HackerNews discussion link (from article ID)
- Summary text
- External article link (if available)

Usage:
    python scripts/push_to_telegram.py
    python scripts/push_to_telegram.py --jsonl data/processed/summaries/2025-10-27-224902-summaries.jsonl
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TelegramDigestPusher:
    """Push digest JSONL file to Telegram channel."""

    def __init__(self, bot_token: str, channel_id: str):
        """Initialize Telegram pusher.

        Args:
            bot_token: Telegram bot token
            channel_id: Telegram channel ID
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_jsonl_file(self, jsonl_file: Path) -> bool:
        """Send summaries from JSONL file to Telegram.

        Args:
            jsonl_file: Path to summaries JSONL file

        Returns:
            True if successful
        """
        if not jsonl_file.exists():
            logger.error(f"JSONL file not found: {jsonl_file}")
            return False

        try:
            summaries = []
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    summaries.append(data)

            logger.info(f"Loaded {len(summaries)} summaries")

            # Format summaries into messages with URLs from JSONL
            messages = []
            for summary in summaries:
                article_id = summary.get("id", "")
                title = summary.get("title", "Unknown")
                summary_text = summary.get("summary", "No summary available")
                url = summary.get("url", "")

                # Create HackerNews link from article ID
                hn_link = (
                    f"https://news.ycombinator.com/item?id={article_id}"
                    if article_id
                    else ""
                )

                # Format message with article link and external URL
                message_parts = [f"*{title}*"]

                # Add HackerNews discussion link
                if hn_link:
                    message_parts.append(f"[HN Discussion]({hn_link})")

                # Add summary
                message_parts.append(f"\n{summary_text}")

                # Add external article link if available
                if url:
                    message_parts.append(f"\n[Read Article]({url})")

                message = "\n".join(message_parts)
                messages.append(message)

            logger.info(f"Formatted {len(messages)} messages")

            # Send all messages
            all_sent = True
            for i, message in enumerate(messages, 1):
                logger.info(f"Sending message {i}/{len(messages)}...")
                if not await self._send_message(message):
                    all_sent = False
                else:
                    await asyncio.sleep(2)  # Rate limiting between messages

            return all_sent

        except Exception as e:
            logger.error(f"Error sending JSONL file: {e}")
            return False

    async def _send_message(self, message: str) -> bool:
        """Send message to Telegram.

        Args:
            message: Message text

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_url}/sendMessage"

            # Try to convert channel_id to int if it's a string
            try:
                chat_id = int(self.channel_id)
            except (ValueError, TypeError):
                chat_id = self.channel_id

            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }

            logger.debug(f"Sending to chat_id: {chat_id}")

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

                if response.status_code == 200:
                    logger.info("✓ Message sent to Telegram")
                    return True
                else:
                    logger.error(f"Failed to send: HTTP {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    logger.error(
                        "Debug: Ensure bot is added to the chat and channel_id is correct"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False


def find_latest_jsonl(summaries_dir: Path) -> Path:
    """Find the latest summaries JSONL file.

    Args:
        summaries_dir: Directory containing JSONL files

    Returns:
        Path to latest JSONL file
    """
    if not summaries_dir.exists():
        return None

    jsonl_files = sorted(summaries_dir.glob("*-summaries.jsonl"))

    if not jsonl_files:
        return None

    latest = jsonl_files[-1]
    logger.info(f"Found latest JSONL: {latest.name}")
    return latest


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Push digest summaries to Telegram")
    parser.add_argument(
        "--jsonl",
        type=str,
        default=None,
        help="Path to JSONL file to send (auto-detect if not specified)",
    )

    args = parser.parse_args()

    # Load environment
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f".env file not found at {env_file}")

    # Get Telegram credentials
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token or not channel_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not found in .env")
        logger.error("Add them to .env file:")
        logger.error("  TELEGRAM_BOT_TOKEN=your_bot_token")
        logger.error("  TELEGRAM_CHANNEL_ID=your_channel_id")
        sys.exit(1)

    # Find JSONL file
    if args.jsonl:
        jsonl_file = Path(args.jsonl)
    else:
        # Auto-detect latest JSONL file
        summaries_dir = project_root / "data" / "processed" / "summaries"
        jsonl_file = find_latest_jsonl(summaries_dir)

    if not jsonl_file:
        logger.error("No JSONL file found")
        sys.exit(1)

    # Initialize pusher
    pusher = TelegramDigestPusher(bot_token, channel_id)

    # Send JSONL file
    logger.info("Sending summaries to Telegram...")
    if await pusher.send_jsonl_file(jsonl_file):
        logger.info("✓ Summaries sent successfully")
    else:
        logger.error("✗ Failed to send summaries")
        sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("TELEGRAM PUSH COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
