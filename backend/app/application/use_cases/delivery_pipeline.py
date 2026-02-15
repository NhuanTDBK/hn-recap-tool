"""Delivery pipeline orchestrator - coordinates entire delivery workflow.

This is the main orchestration use case that ties together:
1. Selecting posts (per user based on last_delivered_at)
2. Formatting messages (Style 2: flat scroll)
3. Sending via Telegram bot
4. Tracking deliveries
5. Updating user.last_delivered_at
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.delivery_selection import SelectPostsForDeliveryUseCase
from app.infrastructure.database.models import User
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.presentation.bot.handlers.delivery import DigestDeliveryHandler

logger = logging.getLogger(__name__)


class DeliveryPipeline:
    """Orchestrates the entire delivery pipeline."""

    def __init__(
        self,
        db_session: AsyncSession,
        delivery_repo: PostgresDeliveryRepository,
        delivery_handler: DigestDeliveryHandler,
    ):
        """Initialize pipeline.

        Args:
            db_session: Async database session
            delivery_repo: DeliveryRepository instance
            delivery_handler: DigestDeliveryHandler instance
        """
        self.db_session = db_session
        self.delivery_repo = delivery_repo
        self.delivery_handler = delivery_handler
        self.selection_use_case = SelectPostsForDeliveryUseCase(db_session)

    async def run(
        self,
        batch_id: Optional[str] = None,
        max_posts_per_user: int = 10,
        skip_user_ids: Optional[List[int]] = None,
        dry_run: bool = False,
    ) -> dict:
        """Execute the delivery pipeline end-to-end.

        Flow:
        1. Generate batch_id
        2. Load all active users
        3. For each user:
           a. Select posts (SelectPostsForDeliveryUseCase)
           b. Send messages (DigestDeliveryHandler)
           c. Track deliveries (DeliveryRepository)
           d. Update user.last_delivered_at
        4. Return statistics

        Args:
            batch_id: Batch ID (optional, generated if not provided)
            max_posts_per_user: Maximum posts per user
            skip_user_ids: User IDs to skip
            dry_run: If True, don't actually send messages or update DB

        Returns:
            Pipeline statistics dict:
            {
                "batch_id": str,
                "total_users": int,
                "users_delivered": int,
                "users_skipped": int,
                "total_messages_sent": int,
                "total_posts_delivered": int,
                "errors": List[dict],
                "duration_seconds": float,
            }
        """
        batch_id = batch_id or str(uuid4())
        start_time = datetime.utcnow()

        logger.info(
            f"Starting delivery pipeline (batch_id={batch_id}, "
            f"dry_run={dry_run}, max_posts={max_posts_per_user})"
        )

        stats = {
            "batch_id": batch_id,
            "total_users": 0,
            "users_delivered": 0,
            "users_skipped": 0,
            "total_messages_sent": 0,
            "total_posts_delivered": 0,
            "errors": [],
            "start_time": start_time.isoformat(),
        }

        try:
            # Fetch all active users
            stmt = select(User).where(User.status == "active")
            result = await self.db_session.execute(stmt)
            users = result.scalars().all()

            logger.info(f"Found {len(users)} active users")

            stats["total_users"] = len(users)

            # Filter out skipped users
            if skip_user_ids:
                users = [u for u in users if u.id not in skip_user_ids]
                logger.info(f"After filtering: {len(users)} users")

            # Process each user
            for user in users:
                try:
                    logger.info(f"Processing user {user.id}")

                    # Select posts for this user
                    delivery_plan = (
                        await self.selection_use_case.select_posts_for_user(
                            user, max_posts_per_user
                        )
                    )

                    if not delivery_plan.posts:
                        logger.info(f"No posts to deliver for user {user.id}")
                        stats["users_skipped"] += 1
                        continue

                    logger.info(
                        f"Selected {len(delivery_plan.posts)} posts for user {user.id}"
                    )

                    if dry_run:
                        logger.info(f"DRY RUN: Would send {len(delivery_plan.posts)} posts to user {user.id}")
                        stats["users_delivered"] += 1
                        stats["total_messages_sent"] += len(delivery_plan.posts)
                        stats["total_posts_delivered"] += len(delivery_plan.posts)
                    else:
                        # Send messages
                        delivery_result = await self.delivery_handler.send_digest_to_user(
                            user, delivery_plan.posts, batch_id
                        )

                        stats["users_delivered"] += 1
                        stats["total_messages_sent"] += delivery_result["messages_sent"]
                        stats["total_posts_delivered"] += delivery_result["messages_sent"]

                        if delivery_result["failures"]:
                            stats["errors"].extend(
                                [
                                    {
                                        "user_id": user.id,
                                        "failure": f,
                                    }
                                    for f in delivery_result["failures"]
                                ]
                            )

                        # Update user.last_delivered_at
                        user.last_delivered_at = datetime.utcnow()
                        self.db_session.add(user)
                        await self.db_session.commit()

                        logger.info(
                            f"Updated user {user.id} last_delivered_at: "
                            f"{user.last_delivered_at}"
                        )

                except Exception as e:
                    logger.error(f"Error processing user {user.id}: {e}")
                    stats["errors"].append(
                        {
                            "user_id": user.id,
                            "error": str(e)[:100],
                        }
                    )
                    stats["users_skipped"] += 1
                    continue

        except Exception as e:
            logger.error(f"Fatal error in delivery pipeline: {e}")
            stats["errors"].append(
                {
                    "stage": "pipeline_init",
                    "error": str(e)[:100],
                }
            )
            raise

        finally:
            # Calculate duration
            end_time = datetime.utcnow()
            stats["end_time"] = end_time.isoformat()
            stats["duration_seconds"] = (end_time - start_time).total_seconds()

            # Log summary
            self._log_summary(stats)

        return stats

    def _log_summary(self, stats: dict) -> None:
        """Log pipeline completion summary.

        Args:
            stats: Statistics dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info("DELIVERY PIPELINE COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Batch ID: {stats['batch_id']}")
        logger.info(f"Total users: {stats['total_users']}")
        logger.info(f"Users delivered: {stats['users_delivered']}")
        logger.info(f"Users skipped: {stats['users_skipped']}")
        logger.info(f"Total messages sent: {stats['total_messages_sent']}")
        logger.info(f"Total posts delivered: {stats['total_posts_delivered']}")
        logger.info(f"Duration: {stats['duration_seconds']:.1f}s")

        if stats["errors"]:
            logger.warning(f"Errors: {len(stats['errors'])}")
            for error in stats["errors"][:5]:  # Show first 5
                logger.warning(f"  {error}")

        logger.info(f"{'='*60}\n")
