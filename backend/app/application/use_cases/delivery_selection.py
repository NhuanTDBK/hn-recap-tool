"""Use case for selecting posts to deliver to users.

This implements the business logic for deciding which posts to send to each user,
based on their last delivery time and interests.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import and_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post, User

logger = logging.getLogger(__name__)


@dataclass
class UserDeliveryPlan:
    """Plan for delivering posts to a user."""

    user_id: int
    posts: List[Post]
    batch_id: str
    delivery_count: int

    def __repr__(self):
        return (
            f"<UserDeliveryPlan(user_id={self.user_id}, "
            f"posts={self.delivery_count}, batch_id={self.batch_id})>"
        )


class SelectPostsForDeliveryUseCase:
    """Use case for selecting posts to deliver to users."""

    def __init__(self, db_session: AsyncSession):
        """Initialize use case.

        Args:
            db_session: Async database session
        """
        self.db_session = db_session

    async def select_posts_for_user(
        self,
        user: User,
        max_posts: int = 10,
    ) -> UserDeliveryPlan:
        """Select posts to deliver to a specific user.

        Logic:
        1. If user.last_delivered_at exists:
           - Select posts created after that time
        2. If user.last_delivered_at is NULL (never delivered):
           - Select the latest post
        3. Filter posts:
           - type = 'story' (skip ask_hn, show_hn)
           - summary IS NOT NULL (must be summarized)
           - is_dead = false
        4. Sort by score DESC (most relevant first)
        5. Limit to max_posts

        Args:
            user: User model
            max_posts: Maximum posts to select

        Returns:
            UserDeliveryPlan with selected posts
        """
        logger.info(
            f"Selecting posts for user {user.id} "
            f"(last_delivered: {user.last_delivered_at})"
        )

        # Build base query: filter by type, summary, and alive status
        base_query = select(Post).where(
            and_(
                Post.type == "story",
                Post.summary.isnot(None),
                Post.is_dead.is_(False),
                Post.is_deleted.is_(False),
                Post.is_crawl_success.is_(True),
            )
        )

        # If user was never delivered to, get latest post
        if user.last_delivered_at is None:
            logger.info(
                f"User {user.id} never delivered to, selecting latest post"
            )
            stmt = base_query.order_by(desc(Post.score)).limit(1)
        else:
            # Select posts created after last delivery
            logger.info(
                f"User {user.id} last delivered {user.last_delivered_at}, "
                f"selecting newer posts"
            )
            stmt = (
                base_query.where(Post.created_at > user.last_delivered_at)
                .order_by(desc(Post.score))
                .limit(max_posts)
            )

        result = await self.db_session.execute(stmt)
        posts = result.scalars().all()

        logger.info(
            f"Selected {len(posts)} posts for user {user.id} "
            f"(limit: {max_posts})"
        )

        # If no posts found and user was never delivered to, this is OK
        # If no posts found and user was delivered to, also OK (no new posts)
        # Both cases are handled gracefully

        batch_id = str(uuid4())

        return UserDeliveryPlan(
            user_id=user.id,
            posts=posts,
            batch_id=batch_id,
            delivery_count=len(posts),
        )

    async def select_posts_for_all_active_users(
        self,
        max_posts_per_user: int = 10,
        skip_user_ids: Optional[List[int]] = None,
    ) -> List[UserDeliveryPlan]:
        """Select posts for all active users.

        Args:
            max_posts_per_user: Maximum posts per user
            skip_user_ids: User IDs to skip (optional)

        Returns:
            List of UserDeliveryPlan objects
        """
        logger.info(
            f"Selecting posts for all active users "
            f"(max_posts: {max_posts_per_user})"
        )

        # Fetch all active users
        stmt = select(User).where(User.status == "active")
        result = await self.db_session.execute(stmt)
        users = result.scalars().all()

        logger.info(f"Found {len(users)} active users")

        # Filter out skipped users
        if skip_user_ids:
            users = [u for u in users if u.id not in skip_user_ids]
            logger.info(f"After filtering skipped users: {len(users)} remaining")

        # Select posts for each user
        delivery_plans = []
        for user in users:
            try:
                plan = await self.select_posts_for_user(user, max_posts_per_user)
                delivery_plans.append(plan)
            except Exception as e:
                logger.error(f"Error selecting posts for user {user.id}: {e}")
                continue

        logger.info(
            f"Generated {len(delivery_plans)} delivery plans "
            f"({sum(p.delivery_count for p in delivery_plans)} total posts)"
        )

        return delivery_plans

    async def filter_by_interests(
        self,
        posts: List[Post],
        interests: List[str],
    ) -> List[Post]:
        """Filter posts by user interests (optional).

        This can be used to personalize delivery based on user's
        stated interests.

        Args:
            posts: List of posts to filter
            interests: List of interest keywords

        Returns:
            Filtered list of posts (may be empty if no matches)

        Note:
            Simple keyword matching in title and summary.
            Can be enhanced with semantic similarity in future.
        """
        if not interests:
            return posts

        logger.info(f"Filtering {len(posts)} posts by {len(interests)} interests")

        filtered = []
        for post in posts:
            title_lower = post.title.lower() if post.title else ""
            summary_lower = post.summary.lower() if post.summary else ""

            # Check if any interest keyword appears in title or summary
            for interest in interests:
                interest_lower = interest.lower()
                if (
                    interest_lower in title_lower
                    or interest_lower in summary_lower
                ):
                    filtered.append(post)
                    break  # Found match, add and move to next post

        logger.info(f"Filtered to {len(filtered)} posts matching interests")

        return filtered
