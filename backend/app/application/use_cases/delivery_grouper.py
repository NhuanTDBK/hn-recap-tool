"""Delivery style grouper - groups users and collects posts by delivery_style.

This module provides utilities to group users by their delivery preferences
and collect unique posts for batch processing.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post, User

logger = logging.getLogger(__name__)


class DeliveryStyleGrouper:
    """Groups users and posts by delivery style for batch processing.

    This class enables the optimization of delivery by grouping users
    who share the same delivery_style preference, allowing for:
    - Batch summarization once per style (not per user)
    - Reduced LLM API calls (80-90% fewer)
    - Faster delivery time (parallel processing)
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize grouper.

        Args:
            db_session: Async database session
        """
        self.db_session = db_session

    async def group_users_by_style(
        self,
        users: List[User]
    ) -> Dict[str, List[User]]:
        """Group users by delivery_style.

        Args:
            users: List of User objects

        Returns:
            Dict mapping delivery_style to list of users:
            {
                "flat_scroll": [user1, user2, ...],
                "brief": [user3, user4, ...],
            }

        Example:
            >>> grouper = DeliveryStyleGrouper(session)
            >>> groups = await grouper.group_users_by_style(users)
            >>> print(groups)
            {
                "flat_scroll": [<User id=1>, <User id=5>, ...],
                "brief": [<User id=3>, <User id=8>, ...]
            }
        """
        if not users:
            logger.info("No users to group")
            return {}

        groups: Dict[str, List[User]] = {}

        for user in users:
            # Default to flat_scroll if style is NULL
            style = user.delivery_style or "flat_scroll"

            if style not in groups:
                groups[style] = []

            groups[style].append(user)

        # Sort users by ID within each group (deterministic ordering)
        for style in groups:
            groups[style].sort(key=lambda u: u.id)

        logger.info(
            f"Grouped {len(users)} users into {len(groups)} style groups: "
            f"{', '.join(f'{style}={len(users_in_style)}' for style, users_in_style in groups.items())}"
        )

        return groups

    async def collect_unique_posts_for_group(
        self,
        users: List[User],
        max_posts: int = 100
    ) -> List[Post]:
        """Collect union of posts for user group.

        This method finds all posts that should be delivered to at least one
        user in the group. It uses the minimum time window (earliest user's
        last_delivered_at) to ensure no user misses posts.

        Args:
            users: List of users in the same style group
            max_posts: Maximum posts to return (default: 100)

        Returns:
            List of unique posts ordered by score DESC

        Example:
            >>> users = [user1, user2, user3]  # All have delivery_style="flat_scroll"
            >>> posts = await grouper.collect_unique_posts_for_group(users)
            >>> print(f"Found {len(posts)} unique posts for group")
        """
        if not users:
            logger.info("No users in group, returning empty post list")
            return []

        logger.info(
            f"Collecting unique posts for group of {len(users)} users"
        )

        # Find earliest last_delivered_at in group
        delivered_times = [
            u.last_delivered_at for u in users if u.last_delivered_at
        ]

        # Build base query with post filters
        base_query = select(Post).where(
            and_(
                Post.type == "story",
                Post.is_dead.is_(False),
                Post.is_deleted.is_(False),
                Post.is_crawl_success.is_(True),
            )
        )

        if not delivered_times:
            # All users never delivered to, get latest post only
            logger.info(
                "All users in group never delivered to, selecting latest post"
            )
            stmt = base_query.order_by(desc(Post.score)).limit(1)
        else:
            # Use earliest time window to ensure no user misses posts
            earliest_time = min(delivered_times)
            logger.info(
                f"Using earliest delivery time: {earliest_time} "
                f"(covers time window for all {len(users)} users)"
            )

            stmt = (
                base_query.where(Post.created_at > earliest_time)
                .order_by(desc(Post.score))
                .limit(max_posts)
            )

        result = await self.db_session.execute(stmt)
        posts = list(result.scalars().all())

        logger.info(
            f"Found {len(posts)} unique posts for group "
            f"(limit: {max_posts})"
        )

        return posts

    async def get_unique_delivery_styles(self) -> List[str]:
        """Get all delivery_style values currently in use.

        Returns:
            Sorted list of distinct delivery styles

        Example:
            >>> styles = await grouper.get_unique_delivery_styles()
            >>> print(styles)
            ['brief', 'flat_scroll']
        """
        stmt = select(User.delivery_style).distinct()
        result = await self.db_session.execute(stmt)
        styles = [s for s in result.scalars().all() if s]  # Filter NULL

        # Add default style if not present
        if "flat_scroll" not in styles:
            styles.append("flat_scroll")

        styles.sort()

        logger.info(f"Found {len(styles)} unique delivery styles: {styles}")

        return styles

    async def count_users_per_style(self) -> Dict[str, int]:
        """Count number of users per delivery_style.

        Returns:
            Dict mapping delivery_style to count:
            {
                "flat_scroll": 60,
                "brief": 40,
            }

        Example:
            >>> counts = await grouper.count_users_per_style()
            >>> print(f"flat_scroll: {counts['flat_scroll']} users")
        """
        stmt = select(User).where(User.status == "active")
        result = await self.db_session.execute(stmt)
        users = result.scalars().all()

        counts: Dict[str, int] = {}
        for user in users:
            style = user.delivery_style or "flat_scroll"
            counts[style] = counts.get(style, 0) + 1

        logger.info(
            f"User counts per style: "
            f"{', '.join(f'{style}={count}' for style, count in counts.items())}"
        )

        return counts
