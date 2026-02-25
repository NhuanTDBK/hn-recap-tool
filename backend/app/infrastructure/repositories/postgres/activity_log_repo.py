"""PostgreSQL implementation of ActivityLogRepository."""

import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import ActivityLogRepository
from app.infrastructure.database.models import UserActivityLog

logger = logging.getLogger(__name__)


class PostgresActivityLogRepository(ActivityLogRepository):
    """PostgreSQL implementation of ActivityLogRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def log_activity(
        self,
        user_id: int,
        post_id: str,
        action_type: str,
    ) -> dict:
        """Log a user activity (rating or save).

        Args:
            user_id: User who performed the action
            post_id: Post being acted upon
            action_type: Type of action ("rate_up", "rate_down", "save")

        Returns:
            Activity log record with ID and timestamp
        """
        activity = UserActivityLog(
            id=uuid4(),
            user_id=user_id,
            post_id=post_id,
            action_type=action_type,
        )

        self.session.add(activity)
        await self.session.commit()
        await self.session.refresh(activity)

        logger.debug(
            f"Logged activity: user={user_id}, post={post_id}, action={action_type}"
        )

        return {
            "id": str(activity.id),
            "user_id": activity.user_id,
            "post_id": str(activity.post_id),
            "action_type": activity.action_type,
            "created_at": activity.created_at.isoformat(),
        }
