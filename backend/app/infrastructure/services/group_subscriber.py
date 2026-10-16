"""Telegram group feed: the group topic is stored as a subscriber row in ``users``.

The row's ``telegram_id`` is the group chat ID, so summarization and delivery treat
the group like any other active user. Settings decide which chat is the group,
which forum topic to post into, and whether DM users are still served.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config.settings import settings
from app.infrastructure.database.models import User

logger = logging.getLogger(__name__)

GROUP_USERNAME = "group:topic"


def is_group_chat(telegram_id: int | None) -> bool:
    """Return True if ``telegram_id`` is the configured group chat."""
    return (
        settings.telegram_group_chat_id is not None
        and telegram_id == settings.telegram_group_chat_id
    )


def topic_id_for(telegram_id: int | None) -> int | None:
    """Return the forum topic to post into for this chat, or None for normal chats."""
    return settings.telegram_group_topic_id if is_group_chat(telegram_id) else None


def is_feed_enabled(user: User) -> bool:
    """Return True if scheduled summaries and pushes should be produced for ``user``.

    The group feed is always on; DM users follow ``telegram_dm_delivery_enabled``.
    """
    return is_group_chat(user.telegram_id) or settings.telegram_dm_delivery_enabled


async def get_group_subscriber(session: AsyncSession) -> User | None:
    """Return the group's subscriber row, or None if unset or not created yet."""
    if settings.telegram_group_chat_id is None:
        return None
    result = await session.execute(
        select(User).where(User.telegram_id == settings.telegram_group_chat_id)
    )
    return result.scalar_one_or_none()


async def ensure_group_subscriber(session: AsyncSession) -> User | None:
    """Create or update the group's subscriber row from settings.

    Idempotent. Does nothing when ``TELEGRAM_GROUP_CHAT_ID`` is unset. An existing
    row keeps its status, so the group can be paused in the DB.

    Args:
        session: Database session

    Returns:
        The group's User row, or None if no group is configured
    """
    if settings.telegram_group_chat_id is None:
        return None

    user = await get_group_subscriber(session)
    style = settings.telegram_group_summary_style

    if user is None:
        user = User(
            telegram_id=settings.telegram_group_chat_id,
            username=GROUP_USERNAME,
            status="active",
            summary_preferences={
                "style": style,
                "detail_level": "medium",
                "technical_depth": "intermediate",
            },
        )
        session.add(user)
        await session.commit()
        logger.info(
            f"Created group subscriber (chat_id={settings.telegram_group_chat_id}, style={style})"
        )
        return user

    if user.get_summary_style() != style:
        user.summary_preferences = {**(user.summary_preferences or {}), "style": style}
        session.add(user)
        await session.commit()
        logger.info(f"Updated group subscriber {user.id} (style={style})")
    return user
