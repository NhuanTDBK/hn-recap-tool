"""Telegram notification service for sending digest summaries to channel."""

import logging
from typing import List, Dict
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Service for sending summaries to Telegram channel."""

    def __init__(self, bot_token: str, channel_id: str):
        """Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token
            channel_id: Telegram channel ID to send messages to
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_digest_summary(
        self, summaries: List[Dict], markdown_file: Path = None
    ) -> bool:
        """Send digest summary to Telegram channel.

        Args:
            summaries: List of summary dictionaries
            markdown_file: Optional path to markdown file for reference

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message with summaries
            successful = sum(1 for s in summaries if "error" not in s)
            failed = len(summaries) - successful

            message = self._format_digest_message(summaries, successful, failed)

            # Send to Telegram
            return await self._send_message(message)

        except Exception as e:
            logger.error(f"Error sending digest to Telegram: {e}")
            return False

    async def send_summary_details(self, summaries: List[Dict], limit: int = 10) -> bool:
        """Send detailed summaries to Telegram (split into multiple messages if needed).

        Args:
            summaries: List of summary dictionaries
            limit: Maximum summaries per message (Telegram has message size limits)

        Returns:
            True if all messages sent successfully
        """
        try:
            successful_summaries = [s for s in summaries if "error" not in s]

            if not successful_summaries:
                logger.warning("No successful summaries to send")
                return False

            # Send in batches
            all_sent = True
            for i in range(0, len(successful_summaries), limit):
                batch = successful_summaries[i : i + limit]
                message = self._format_summaries_message(batch)
                if not await self._send_message(message):
                    all_sent = False

            return all_sent

        except Exception as e:
            logger.error(f"Error sending detailed summaries to Telegram: {e}")
            return False

    def _format_digest_message(self, summaries: List[Dict], successful: int, failed: int) -> str:
        """Format digest statistics message.

        Args:
            summaries: List of summary dictionaries
            successful: Count of successful summaries
            failed: Count of failed summaries

        Returns:
            Formatted message string
        """
        message = f"""📰 *HackerNews Digest Summary*

📊 *Statistics:*
• Total: {len(summaries)}
• Successful: {successful} ✓
• Failed: {failed} ✗

✨ *Top Articles:*
"""

        # Add top 5 successful summaries
        count = 0
        for summary in summaries:
            if "error" not in summary and count < 5:
                title = summary.get("title", "Untitled")[:50]
                points = summary.get("points", 0)
                message += f"\n{count + 1}. {title} ({points}pts)"
                count += 1

        message += "\n\n📄 Full digest saved and ready for review."
        return message

    def _format_summaries_message(self, summaries: List[Dict]) -> str:
        """Format detailed summaries message.

        Args:
            summaries: List of summary dictionaries

        Returns:
            Formatted message string
        """
        message = "📝 *Detailed Summaries:*\n\n"

        for i, summary in enumerate(summaries, 1):
            title = summary.get("title", "Untitled")
            summary_text = summary.get("summary", "")

            # Truncate summary if too long
            if len(summary_text) > 300:
                summary_text = summary_text[:300] + "..."

            message += f"*{i}. {title}*\n{summary_text}\n\n"

        return message

    async def _send_message(self, message: str) -> bool:
        """Send message to Telegram channel.

        Args:
            message: Message text to send

        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.api_url}/sendMessage"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.channel_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info("✓ Message sent to Telegram")
                    return True
                else:
                    logger.error(f"Failed to send to Telegram: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
