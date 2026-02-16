"""Hourly job for delivering personalized digests to users.

This job:
1. Finds all active users
2. Gets posts with summaries for each user (already generated)
3. Filters out already-delivered posts
4. Delivers summaries via Telegram
5. Tracks delivery statistics

Architecture:
- Uses APScheduler for hourly cron scheduling
- Async/await for non-blocking I/O
- Batch operations for efficiency
- Reuses existing delivery pipeline
- Rate limiting to avoid Telegram API limits
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Delivery, Post, Summary, User
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.presentation.bot.bot import get_bot_manager
from app.presentation.bot.handlers.delivery import DigestDeliveryHandler

logger = logging.getLogger(__name__)


class HourlyDeliveryJob:
    """Delivers personalized digests to users hourly."""

    def __init__(
        self,
        db_session: AsyncSession,
        delivery_repo: PostgresDeliveryRepository,
        max_posts_per_user: int = 10,
        batch_size: int = 5,
    ):
        """Initialize hourly delivery job.

        Args:
            db_session: Async SQLAlchemy session
            delivery_repo: PostgreSQL repository for delivery tracking
            max_posts_per_user: Maximum posts to deliver per user per run
            batch_size: Number of users to process before rate limiting
        """
        self.db_session = db_session
        self.delivery_repo = delivery_repo
        self.max_posts_per_user = max_posts_per_user
        self.batch_size = batch_size
        self.delivery_handler = DigestDeliveryHandler(delivery_repo)
        self.stats = {
            "active_users": 0,
            "users_with_posts": 0,
            "users_delivered": 0,
            "users_skipped": 0,
            "total_messages_sent": 0,
            "total_failures": 0,
            "errors": 0,
            "last_run": None,
        }

    async def find_active_users(self) -> List[User]:
        """Find all active users.

        Returns:
            List of active User entities
        """
        try:
            stmt = select(User).where(User.status == "active")
            result = await self.db_session.execute(stmt)
            users = list(result.scalars().all())
            self.stats["active_users"] = len(users)
            logger.info(f"Found {len(users)} active users")
            return users
        except Exception as e:
            logger.error(f"Failed to find active users: {e}")
            raise

    async def get_delivered_post_ids(self, user_id: int) -> set:
        """Get set of post IDs already delivered to user.

        Args:
            user_id: User ID

        Returns:
            Set of post IDs that have been delivered
        """
        try:
            stmt = select(Delivery.post_id).where(Delivery.user_id == user_id)
            result = await self.db_session.execute(stmt)
            return {row[0] for row in result.fetchall()}
        except Exception as e:
            logger.warning(f"Failed to get delivered posts for user {user_id}: {e}")
            return set()

    async def find_posts_with_summaries(
        self, user_id: int, exclude_post_ids: set
    ) -> List[Post]:
        """Find posts with summaries for a user (excluding already delivered).

        Args:
            user_id: User ID
            exclude_post_ids: Set of post IDs to exclude

        Returns:
            List of Post entities with summaries attached
        """
        try:
            # Query posts with summaries for this user
            stmt = (
                select(Post)
                .join(Summary, Summary.post_id == Post.id)
                .where(
                    and_(
                        Summary.user_id == user_id,
                        Post.type == "story",
                        Post.is_dead == False,
                        Post.is_deleted == False,
                        (
                            ~Post.id.in_(exclude_post_ids)
                            if exclude_post_ids
                            else True
                        ),
                    )
                )
                .order_by(Post.score.desc())
                .limit(self.max_posts_per_user)
            )

            result = await self.db_session.execute(stmt)
            posts = list(result.scalars().all())

            # Load summaries into posts
            for post in posts:
                summary_stmt = select(Summary).where(
                    and_(Summary.user_id == user_id, Summary.post_id == post.id)
                )
                summary_result = await self.db_session.execute(summary_stmt)
                summary = summary_result.scalar_one_or_none()
                if summary:
                    post.summary = summary.summary_text

            logger.debug(f"Found {len(posts)} posts with summaries for user {user_id}")
            return posts

        except Exception as e:
            logger.error(f"Failed to find posts with summaries for user {user_id}: {e}")
            return []

    async def deliver_to_user(self, user: User, posts: List[Post], batch_id: str) -> dict:
        """Deliver posts to a single user.

        Args:
            user: User entity
            posts: Posts to deliver
            batch_id: Batch ID for tracking

        Returns:
            Delivery result dictionary
        """
        try:
            result = await self.delivery_handler.send_digest_to_user(user, posts, batch_id)
            return result
        except Exception as e:
            logger.error(f"Error delivering to user {user.id}: {e}")
            return {
                "user_id": user.id,
                "messages_sent": 0,
                "failures": [{"reason": str(e)}],
                "message_ids": [],
            }

    async def deliver_summaries(self) -> dict:
        """Deliver existing summaries to users.

        Returns:
            Statistics dictionary with delivery results
        """
        logger.info(
            f"Starting hourly delivery "
            f"(max_posts_per_user: {self.max_posts_per_user})"
        )

        self.stats = {
            "active_users": 0,
            "users_with_posts": 0,
            "users_delivered": 0,
            "users_skipped": 0,
            "total_messages_sent": 0,
            "total_failures": 0,
            "errors": 0,
            "last_run": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Get active users
            users = await self.find_active_users()

            if not users:
                logger.warning("No active users found")
                return self.stats

            # Create batch ID for tracking this delivery run
            batch_id = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M')}-hourly"

            # Process each user
            for idx, user in enumerate(users, 1):
                logger.info(f"[{idx}/{len(users)}] Processing user {user.id}")

                try:
                    # Get already delivered posts
                    delivered_post_ids = await self.get_delivered_post_ids(user.id)
                    logger.debug(f"User {user.id} already has {len(delivered_post_ids)} delivered posts")

                    # Find posts with summaries
                    posts = await self.find_posts_with_summaries(user.id, delivered_post_ids)

                    if not posts:
                        logger.info(f"No posts with summaries for user {user.id}, skipping")
                        self.stats["users_skipped"] += 1
                        continue

                    self.stats["users_with_posts"] += 1
                    logger.info(f"Found {len(posts)} posts with summaries for user {user.id}")

                    # Deliver posts
                    result = await self.deliver_to_user(user, posts, batch_id)

                    # Update statistics
                    self.stats["total_messages_sent"] += result["messages_sent"]
                    self.stats["total_failures"] += len(result["failures"])

                    if result["messages_sent"] > 0:
                        self.stats["users_delivered"] += 1
                        logger.info(
                            f"Delivered {result['messages_sent']} messages to user {user.id}"
                        )
                    else:
                        self.stats["users_skipped"] += 1
                        logger.warning(f"No messages sent to user {user.id}")

                    # Update last_delivered_at timestamp
                    try:
                        user.last_delivered_at = datetime.now(timezone.utc)
                        self.db_session.add(user)
                        await self.db_session.commit()
                    except Exception as e:
                        logger.warning(f"Failed to update last_delivered_at for user {user.id}: {e}")

                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {e}")
                    self.stats["errors"] += 1
                    continue

            logger.info(
                f"Hourly delivery complete: "
                f"delivered={self.stats['users_delivered']}, "
                f"skipped={self.stats['users_skipped']}, "
                f"messages={self.stats['total_messages_sent']}, "
                f"failures={self.stats['total_failures']}"
            )

            return self.stats

        except Exception as e:
            logger.error(f"Hourly delivery failed: {e}", exc_info=True)
            self.stats["errors"] += 1
            raise

    def get_stats(self) -> dict:
        """Get delivery statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats

    async def run_delivery(self) -> dict:
        """Run the hourly delivery job.

        This is the main entry point called by APScheduler.

        Returns:
            Statistics dictionary
        """
        logger.info("=" * 60)
        logger.info("HOURLY DELIVERY JOB STARTED")
        logger.info("=" * 60)

        try:
            stats = await self.deliver_summaries()
            logger.info("=" * 60)
            logger.info(f"DELIVERY COMPLETE - Stats: {stats}")
            logger.info("=" * 60)
            return stats
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"DELIVERY FAILED - Error: {e}")
            logger.error("=" * 60)
            raise
