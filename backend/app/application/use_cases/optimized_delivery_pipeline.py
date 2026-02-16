"""DEPRECATED: Optimized delivery pipeline with style-based grouping and batch summarization.

⚠️ WARNING: This module is DEPRECATED and should NOT be used.

REASON FOR DEPRECATION:
This pipeline mixes summarization and delivery concerns, which violates the separation
of concerns principle. It attempts to re-summarize posts during the delivery phase,
which is inefficient and redundant.

RECOMMENDED ALTERNATIVE:
Use the two-phase approach instead:
1. Summarization Phase: scripts/run_personalized_summarization.py
2. Delivery Phase: scripts/deliver_summaries.py

See DELIVERY_ARCHITECTURE.md for the recommended architecture.

ORIGINAL DESCRIPTION (for historical reference):
This pipeline reduces LLM API calls by 80-90% through:
1. Grouping users by delivery_style
2. Batch-summarizing posts once per style
3. Distributing summaries to all users in parallel

However, this optimization is now handled in the summarization phase, making this
pipeline unnecessary.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.delivery_grouper import DeliveryStyleGrouper
from app.application.use_cases.delivery_pipeline import DeliveryPipeline
from app.application.use_cases.delivery_selection import SelectPostsForDeliveryUseCase
from app.application.use_cases.grouped_delivery import GroupedDeliveryUseCase
from app.infrastructure.database.models import User
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresDeliveryRepository,
)
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore
from app.presentation.bot.handlers.delivery import DigestDeliveryHandler

logger = logging.getLogger(__name__)


class OptimizedDeliveryPipeline(DeliveryPipeline):
    """Enhanced delivery pipeline with style-based grouping and batch summarization.

    This pipeline significantly reduces:
    - LLM API calls (80-90% fewer)
    - Token usage (70-80% fewer)
    - Execution time (3-5x faster)
    - Cost (proportional to token reduction)

    Through intelligent grouping and batch processing.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        delivery_repo: PostgresDeliveryRepository,
        delivery_handler: DigestDeliveryHandler,
        content_store: RocksDBContentStore,
    ):
        """Initialize optimized pipeline.

        Args:
            db_session: Async database session
            delivery_repo: DeliveryRepository instance
            delivery_handler: DigestDeliveryHandler instance
            content_store: RocksDB store for post content
        """
        super().__init__(db_session, delivery_repo, delivery_handler)
        self.grouper = DeliveryStyleGrouper(db_session)
        self.grouped_use_case = GroupedDeliveryUseCase(db_session, content_store)

    async def run(
        self,
        batch_id: Optional[str] = None,
        max_posts_per_user: int = 10,
        skip_user_ids: Optional[List[int]] = None,
        dry_run: bool = False,
        enable_grouping: bool = True,
    ) -> dict:
        """Execute optimized delivery pipeline.

        Args:
            batch_id: Batch ID (optional, generated if not provided)
            max_posts_per_user: Maximum posts per user
            skip_user_ids: User IDs to skip
            dry_run: If True, don't actually send messages or update DB
            enable_grouping: If True, use optimized flow; if False, use parent flow

        Returns:
            Pipeline statistics dict with detailed metrics per style group

        Example:
            >>> pipeline = OptimizedDeliveryPipeline(...)
            >>> result = await pipeline.run(enable_grouping=True)
            >>> print(f"Delivered to {result['users_delivered']} users in {result['duration_seconds']}s")
        """
        if not enable_grouping:
            logger.info("Grouping disabled, using standard pipeline")
            return await super().run(
                batch_id=batch_id,
                max_posts_per_user=max_posts_per_user,
                skip_user_ids=skip_user_ids,
                dry_run=dry_run,
            )

        batch_id = batch_id or str(uuid4())
        start_time = datetime.utcnow()

        logger.info(
            f"Starting OPTIMIZED delivery pipeline (batch_id={batch_id}, "
            f"dry_run={dry_run}, max_posts={max_posts_per_user})"
        )

        stats = {
            "batch_id": batch_id,
            "total_users": 0,
            "users_delivered": 0,
            "users_skipped": 0,
            "total_messages_sent": 0,
            "total_posts_delivered": 0,
            "style_groups": {},
            "errors": [],
            "start_time": start_time.isoformat(),
            "optimization_enabled": True,
        }

        try:
            # PHASE 1: Load and group users by delivery_style
            logger.info("=" * 60)
            logger.info("PHASE 1: Grouping users by delivery_style")
            logger.info("=" * 60)

            stmt = select(User).where(User.status == "active")
            result = await self.db_session.execute(stmt)
            users = list(result.scalars().all())

            logger.info(f"Found {len(users)} active users")

            if skip_user_ids:
                users = [u for u in users if u.id not in skip_user_ids]
                logger.info(f"After filtering: {len(users)} users")

            stats["total_users"] = len(users)

            # Group users by delivery_style
            style_groups = await self.grouper.group_users_by_style(users)

            logger.info(
                f"Created {len(style_groups)} style groups: "
                f"{', '.join(f'{style}={len(users_in_style)}' for style, users_in_style in style_groups.items())}"
            )

            # PHASE 2: Batch summarize for each style
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 2: Batch summarization per style")
            logger.info("=" * 60)

            for style, users_in_style in style_groups.items():
                logger.info(f"\nProcessing style '{style}' ({len(users_in_style)} users)")

                # Collect unique posts for this group
                unique_posts = await self.grouper.collect_unique_posts_for_group(
                    users_in_style,
                    max_posts=max_posts_per_user * 2  # Wider window for grouping
                )

                logger.info(
                    f"Found {len(unique_posts)} unique posts for style '{style}'"
                )

                # Batch summarize (only for unsummarized posts)
                if not dry_run:
                    summary_stats = await self.grouped_use_case.batch_summarize_for_style(
                        unique_posts,
                        style=style,
                        batch_size=10
                    )
                else:
                    # Dry run: simulate summarization stats
                    unsummarized_count = len([p for p in unique_posts if not p.summary])
                    summary_stats = {
                        "total_posts": unsummarized_count,
                        "summarized": 0,
                        "failed": 0,
                        "tokens_used": 0,
                        "cost": 0.0,
                        "duration_seconds": 0.0,
                        "prompt_type": "basic" if style == "flat_scroll" else "concise",
                    }
                    logger.info(
                        f"DRY RUN: Would summarize {unsummarized_count} posts for style '{style}'"
                    )

                # Store stats for this style
                stats["style_groups"][style] = {
                    "user_count": len(users_in_style),
                    "post_count": len(unique_posts),
                    **summary_stats
                }

            # PHASE 3: Parallel delivery to all users
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 3: Parallel delivery to users")
            logger.info("=" * 60)

            # Create delivery tasks for each style group (can run in parallel)
            delivery_tasks = []
            for style, users_in_style in style_groups.items():
                task = self._deliver_to_style_group(
                    style=style,
                    users=users_in_style,
                    batch_id=batch_id,
                    max_posts_per_user=max_posts_per_user,
                    dry_run=dry_run
                )
                delivery_tasks.append(task)

            # Execute all delivery tasks in parallel
            logger.info(
                f"Starting parallel delivery for {len(delivery_tasks)} style groups"
            )
            delivery_results = await asyncio.gather(*delivery_tasks, return_exceptions=True)

            # Aggregate results
            for i, result in enumerate(delivery_results):
                if isinstance(result, Exception):
                    logger.error(f"Delivery task {i} failed: {result}")
                    stats["errors"].append({
                        "stage": f"delivery_group_{i}",
                        "error": str(result)[:100]
                    })
                else:
                    stats["users_delivered"] += result["users_delivered"]
                    stats["users_skipped"] += result["users_skipped"]
                    stats["total_messages_sent"] += result["messages_sent"]
                    stats["total_posts_delivered"] += result["posts_delivered"]
                    if result.get("errors"):
                        stats["errors"].extend(result["errors"])

        except Exception as e:
            logger.error(f"Fatal error in optimized delivery pipeline: {e}", exc_info=True)
            stats["errors"].append({
                "stage": "pipeline_error",
                "error": str(e)[:200]
            })
            raise

        finally:
            # Calculate duration
            end_time = datetime.utcnow()
            stats["end_time"] = end_time.isoformat()
            stats["duration_seconds"] = (end_time - start_time).total_seconds()

            # Log comprehensive summary
            self._log_optimized_summary(stats)

        return stats

    async def _deliver_to_style_group(
        self,
        style: str,
        users: List[User],
        batch_id: str,
        max_posts_per_user: int,
        dry_run: bool
    ) -> Dict:
        """Deliver to all users in a style group.

        Args:
            style: Delivery style
            users: Users in this style group
            batch_id: Batch ID
            max_posts_per_user: Max posts per user
            dry_run: If True, don't actually send/save

        Returns:
            Result dict with delivery statistics
        """
        logger.info(f"\nDelivering to style group '{style}' ({len(users)} users)")

        result = {
            "style": style,
            "users_delivered": 0,
            "users_skipped": 0,
            "messages_sent": 0,
            "posts_delivered": 0,
            "errors": []
        }

        selection_use_case = SelectPostsForDeliveryUseCase(self.db_session)

        for user in users:
            try:
                # Select posts for this user (with their personal filters)
                delivery_plan = await selection_use_case.select_posts_for_user(
                    user,
                    max_posts=max_posts_per_user
                )

                if not delivery_plan.posts:
                    logger.debug(f"No posts for user {user.id} in style '{style}'")
                    result["users_skipped"] += 1
                    continue

                logger.debug(
                    f"User {user.id}: {len(delivery_plan.posts)} posts to deliver"
                )

                if dry_run:
                    logger.info(
                        f"DRY RUN: Would send {len(delivery_plan.posts)} posts "
                        f"to user {user.id}"
                    )
                    result["users_delivered"] += 1
                    result["messages_sent"] += len(delivery_plan.posts)
                    result["posts_delivered"] += len(delivery_plan.posts)
                else:
                    # Send messages (all summaries already in DB!)
                    delivery_result = await self.delivery_handler.send_digest_to_user(
                        user, delivery_plan.posts, batch_id
                    )

                    result["users_delivered"] += 1
                    result["messages_sent"] += delivery_result["messages_sent"]
                    result["posts_delivered"] += delivery_result["messages_sent"]

                    if delivery_result["failures"]:
                        result["errors"].extend([
                            {
                                "user_id": user.id,
                                "failure": f,
                            }
                            for f in delivery_result["failures"]
                        ])

                    # Update user.last_delivered_at
                    user.last_delivered_at = datetime.utcnow()
                    self.db_session.add(user)
                    await self.db_session.commit()

            except Exception as e:
                logger.error(f"Error delivering to user {user.id}: {e}")
                result["errors"].append({
                    "user_id": user.id,
                    "error": str(e)[:100]
                })
                result["users_skipped"] += 1
                continue

        logger.info(
            f"Style group '{style}' complete: "
            f"{result['users_delivered']} delivered, "
            f"{result['users_skipped']} skipped"
        )

        return result

    def _log_optimized_summary(self, stats: dict) -> None:
        """Log detailed pipeline completion summary with optimization metrics.

        Args:
            stats: Statistics dictionary
        """
        logger.info("\n" + "=" * 80)
        logger.info("OPTIMIZED DELIVERY PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Batch ID: {stats['batch_id']}")
        logger.info(f"Total users: {stats['total_users']}")
        logger.info(f"Users delivered: {stats['users_delivered']}")
        logger.info(f"Users skipped: {stats['users_skipped']}")
        logger.info(f"Total messages sent: {stats['total_messages_sent']}")
        logger.info(f"Total posts delivered: {stats['total_posts_delivered']}")
        logger.info(f"Duration: {stats['duration_seconds']:.1f}s")

        logger.info("\n" + "-" * 80)
        logger.info("STYLE GROUP BREAKDOWN:")
        logger.info("-" * 80)

        total_summarized = 0
        total_tokens = 0
        total_cost = 0.0

        for style, group_stats in stats.get("style_groups", {}).items():
            logger.info(f"\nStyle: {style}")
            logger.info(f"  Users: {group_stats['user_count']}")
            logger.info(f"  Unique posts: {group_stats['post_count']}")
            logger.info(f"  Posts summarized: {group_stats.get('summarized', 0)}")
            logger.info(f"  Prompt type: {group_stats.get('prompt_type', 'N/A')}")
            logger.info(f"  Tokens used: {group_stats.get('tokens_used', 0)}")
            logger.info(f"  Cost: ${group_stats.get('cost', 0.0):.4f}")
            logger.info(f"  Duration: {group_stats.get('duration_seconds', 0.0):.1f}s")

            total_summarized += group_stats.get("summarized", 0)
            total_tokens += group_stats.get("tokens_used", 0)
            total_cost += group_stats.get("cost", 0.0)

        logger.info("\n" + "-" * 80)
        logger.info("OPTIMIZATION METRICS:")
        logger.info("-" * 80)
        logger.info(f"Total posts summarized: {total_summarized}")
        logger.info(f"Total tokens used: {total_tokens}")
        logger.info(f"Total cost: ${total_cost:.4f}")
        logger.info(f"Style groups processed: {len(stats.get('style_groups', {}))}")

        if stats.get("errors"):
            logger.warning(f"\nErrors: {len(stats['errors'])}")
            for error in stats["errors"][:5]:  # Show first 5
                logger.warning(f"  {error}")

        logger.info("=" * 80 + "\n")
