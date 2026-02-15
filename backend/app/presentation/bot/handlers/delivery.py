"""Handler for sending digest messages to users."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from aiogram.types import InlineKeyboardMarkup

from app.infrastructure.database.models import Post, User
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.presentation.bot.bot import get_bot_manager
from app.presentation.bot.formatters.digest_formatter import (
    DigestMessageFormatter,
    InlineKeyboardBuilder,
)

logger = logging.getLogger(__name__)


class DigestDeliveryHandler:
    """Handler for sending digest messages to users."""

    # Rate limiting: delay between messages (seconds)
    MESSAGE_DELAY_SECONDS = 1.0

    def __init__(self, delivery_repo: PostgresDeliveryRepository):
        """Initialize handler.

        Args:
            delivery_repo: DeliveryRepository instance
        """
        self.delivery_repo = delivery_repo
        self.formatter = DigestMessageFormatter()
        self.keyboard_builder = InlineKeyboardBuilder()
        self.bot_manager = get_bot_manager()

    async def send_digest_to_user(
        self,
        user: User,
        posts: List[Post],
        batch_id: str,
    ) -> dict:
        """Send digest messages to a user.

        Sends one message per post with inline buttons and handles:
        - Rate limiting (1 msg/sec)
        - Telegram API responses
        - Delivery tracking
        - Error handling per message

        Args:
            user: User to deliver to
            posts: Posts to send
            batch_id: Batch ID (groups posts)

        Returns:
            Dictionary with delivery statistics:
            {
                "user_id": int,
                "messages_sent": int,
                "failures": List[dict],
                "message_ids": List[int],
            }
        """
        logger.info(
            f"Sending digest to user {user.id} "
            f"(telegram_id={user.telegram_id}, posts={len(posts)})"
        )

        stats = {
            "user_id": user.id,
            "messages_sent": 0,
            "failures": [],
            "message_ids": [],
            "batch_id": batch_id,
        }

        # Skip if user has no telegram_id
        if not user.telegram_id or user.telegram_id == 0:
            logger.warning(
                f"User {user.id} has no valid telegram_id, skipping delivery"
            )
            stats["failures"].append(
                {
                    "post_index": 0,
                    "reason": "User has no valid telegram_id",
                }
            )
            return stats

        total_posts = len(posts)

        # Send each post as a message
        for position, post in enumerate(posts, 1):
            try:
                # Format message
                message_text = self.formatter.format_post_message(
                    post, position, total_posts
                )

                # Build keyboard
                keyboard_dict = self.keyboard_builder.build_post_keyboard(
                    str(post.id)
                )
                keyboard_markup = InlineKeyboardMarkup(
                    inline_keyboard=keyboard_dict["inline_keyboard"]
                )

                # Send message
                message_result = await self.bot_manager.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    reply_markup=keyboard_markup,
                )

                message_id = message_result["message_id"]

                # Save delivery record
                await self.delivery_repo.save_delivery(
                    user_id=user.id,
                    post_id=str(post.id),
                    batch_id=batch_id,
                    message_id=message_id,
                )

                stats["messages_sent"] += 1
                stats["message_ids"].append(message_id)

                logger.info(
                    f"Sent post {position}/{total_posts} to user {user.id} "
                    f"(msg_id={message_id})"
                )

                # Rate limiting: delay before next message
                if position < total_posts:
                    await asyncio.sleep(self.MESSAGE_DELAY_SECONDS)

            except Exception as e:
                logger.error(
                    f"Error sending post {position}/{total_posts} to user {user.id}: {e}"
                )
                stats["failures"].append(
                    {
                        "post_index": position,
                        "post_id": str(post.id),
                        "post_title": post.title[:50] if post.title else "Unknown",
                        "reason": str(e)[:100],
                    }
                )
                # Continue with next post instead of failing entire delivery
                continue

        logger.info(
            f"Delivery to user {user.id} complete: "
            f"sent={stats['messages_sent']}, failed={len(stats['failures'])}"
        )

        return stats

    async def send_digest_to_batch_of_users(
        self,
        users: List[User],
        posts_per_user: dict,  # {user_id: [posts]}
        batch_id: Optional[str] = None,
    ) -> dict:
        """Send digest to multiple users.

        Args:
            users: List of User models
            posts_per_user: Dict mapping user_id to list of posts
            batch_id: Batch ID (optional, generated if not provided)

        Returns:
            Aggregated statistics:
            {
                "batch_id": str,
                "total_users": int,
                "users_succeeded": int,
                "users_failed": int,
                "total_messages_sent": int,
                "total_failures": int,
                "user_stats": List[dict],
            }
        """
        batch_id = batch_id or str(uuid4())

        logger.info(
            f"Starting batch delivery to {len(users)} users (batch_id={batch_id})"
        )

        stats = {
            "batch_id": batch_id,
            "total_users": len(users),
            "users_succeeded": 0,
            "users_failed": 0,
            "total_messages_sent": 0,
            "total_failures": 0,
            "user_stats": [],
        }

        for user in users:
            try:
                posts = posts_per_user.get(user.id, [])

                if not posts:
                    logger.info(f"No posts for user {user.id}, skipping")
                    continue

                user_result = await self.send_digest_to_user(user, posts, batch_id)

                stats["user_stats"].append(user_result)
                stats["total_messages_sent"] += user_result["messages_sent"]
                stats["total_failures"] += len(user_result["failures"])

                if user_result["messages_sent"] > 0:
                    stats["users_succeeded"] += 1
                else:
                    stats["users_failed"] += 1

            except Exception as e:
                logger.error(f"Error delivering to user {user.id}: {e}")
                stats["users_failed"] += 1
                stats["user_stats"].append(
                    {
                        "user_id": user.id,
                        "messages_sent": 0,
                        "failures": [{"reason": str(e)}],
                        "message_ids": [],
                    }
                )
                continue

        logger.info(
            f"Batch delivery complete (batch_id={batch_id}): "
            f"users_succeeded={stats['users_succeeded']}, "
            f"users_failed={stats['users_failed']}, "
            f"total_messages={stats['total_messages_sent']}"
        )

        return stats
