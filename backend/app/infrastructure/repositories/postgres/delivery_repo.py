"""PostgreSQL implementation of Delivery and Conversation repositories."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import DeliveryRepository, ConversationRepository
from app.infrastructure.database.models import Delivery, Conversation

logger = logging.getLogger(__name__)


class PostgresDeliveryRepository(DeliveryRepository):
    """PostgreSQL implementation of DeliveryRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def save_delivery(
        self,
        user_id: int,
        post_id: str,
        batch_id: str,
        message_id: Optional[int] = None,
    ) -> dict:
        """Save a delivery record.

        Args:
            user_id: User who received the post
            post_id: Post that was delivered
            batch_id: Batch ID
            message_id: Telegram message ID (optional)

        Returns:
            Delivery record dict
        """
        delivery = Delivery(
            id=uuid4(),
            user_id=user_id,
            post_id=post_id,
            batch_id=batch_id,
            message_id=message_id,
        )

        self.session.add(delivery)
        await self.session.commit()
        await self.session.refresh(delivery)

        logger.debug(f"Saved delivery: user={user_id}, post={post_id}, batch={batch_id}")

        return {
            "id": str(delivery.id),
            "user_id": delivery.user_id,
            "post_id": str(delivery.post_id),
            "batch_id": delivery.batch_id,
            "message_id": delivery.message_id,
            "delivered_at": delivery.delivered_at.isoformat(),
        }

    async def find_deliveries_for_user(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list:
        """Find recent deliveries for a user.

        Args:
            user_id: User ID
            limit: Maximum number to return

        Returns:
            List of delivery records
        """
        stmt = (
            select(Delivery)
            .where(Delivery.user_id == user_id)
            .order_by(desc(Delivery.delivered_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        deliveries = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "user_id": d.user_id,
                "post_id": str(d.post_id),
                "batch_id": d.batch_id,
                "message_id": d.message_id,
                "reaction": d.reaction,
                "delivered_at": d.delivered_at.isoformat(),
            }
            for d in deliveries
        ]

    async def find_deliveries_for_batch(self, batch_id: str) -> list:
        """Find all deliveries in a batch.

        Args:
            batch_id: Batch ID

        Returns:
            List of delivery records
        """
        stmt = select(Delivery).where(Delivery.batch_id == batch_id).order_by(
            desc(Delivery.delivered_at)
        )

        result = await self.session.execute(stmt)
        deliveries = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "user_id": d.user_id,
                "post_id": str(d.post_id),
                "batch_id": d.batch_id,
                "message_id": d.message_id,
                "reaction": d.reaction,
                "delivered_at": d.delivered_at.isoformat(),
            }
            for d in deliveries
        ]

    async def update_reaction(
        self,
        delivery_id: str,
        reaction: str,
    ) -> dict:
        """Update reaction on a delivery.

        Args:
            delivery_id: Delivery ID
            reaction: "up" | "down"

        Returns:
            Updated delivery record
        """
        from sqlalchemy import update

        stmt = (
            update(Delivery)
            .where(Delivery.id == delivery_id)
            .values(reaction=reaction)
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Fetch updated record
        stmt = select(Delivery).where(Delivery.id == delivery_id)
        result = await self.session.execute(stmt)
        delivery = result.scalar_one()

        logger.debug(f"Updated delivery reaction: id={delivery_id}, reaction={reaction}")

        return {
            "id": str(delivery.id),
            "user_id": delivery.user_id,
            "post_id": str(delivery.post_id),
            "batch_id": delivery.batch_id,
            "message_id": delivery.message_id,
            "reaction": delivery.reaction,
            "delivered_at": delivery.delivered_at.isoformat(),
        }

    async def get_user_delivery_count(
        self,
        user_id: int,
        days: int = 7,
    ) -> int:
        """Count deliveries in past N days.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Count of deliveries
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(Delivery).where(
            and_(
                Delivery.user_id == user_id,
                Delivery.delivered_at >= cutoff_date,
            )
        )

        result = await self.session.execute(stmt)
        deliveries = result.scalars().all()

        return len(deliveries)


class PostgresConversationRepository(ConversationRepository):
    """PostgreSQL implementation of ConversationRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def save_conversation(
        self,
        user_id: int,
        post_id: str,
        messages: list,
        token_usage: dict,
    ) -> dict:
        """Save a conversation record.

        Args:
            user_id: User in conversation
            post_id: Post being discussed
            messages: Message list
            token_usage: Token usage dict

        Returns:
            Conversation record dict
        """
        conversation = Conversation(
            id=uuid4(),
            user_id=user_id,
            post_id=post_id,
            messages=messages,
            token_usage=token_usage,
        )

        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)

        logger.debug(
            f"Saved conversation: user={user_id}, post={post_id}, "
            f"messages={len(messages)}"
        )

        return {
            "id": str(conversation.id),
            "user_id": conversation.user_id,
            "post_id": str(conversation.post_id),
            "messages": conversation.messages,
            "token_usage": conversation.token_usage,
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        }

    async def find_active_conversation(self, user_id: int) -> Optional[dict]:
        """Find active conversation for user.

        Args:
            user_id: User ID

        Returns:
            Conversation record if active, None otherwise
        """
        stmt = select(Conversation).where(
            and_(
                Conversation.user_id == user_id,
                Conversation.ended_at.is_(None),  # Active conversations have no end time
            )
        )

        result = await self.session.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        return {
            "id": str(conversation.id),
            "user_id": conversation.user_id,
            "post_id": str(conversation.post_id),
            "messages": conversation.messages,
            "token_usage": conversation.token_usage,
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        }

    async def update_messages(
        self,
        conversation_id: str,
        messages: list,
    ) -> dict:
        """Update messages in a conversation.

        Args:
            conversation_id: Conversation ID
            messages: Updated message list

        Returns:
            Updated conversation record
        """
        from sqlalchemy import update

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(messages=messages)
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Fetch updated record
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        conversation = result.scalar_one()

        logger.debug(
            f"Updated conversation messages: id={conversation_id}, "
            f"messages={len(messages)}"
        )

        return {
            "id": str(conversation.id),
            "user_id": conversation.user_id,
            "post_id": str(conversation.post_id),
            "messages": conversation.messages,
            "token_usage": conversation.token_usage,
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        }

    async def end_conversation(
        self,
        conversation_id: str,
        token_usage: dict,
    ) -> dict:
        """End a conversation.

        Args:
            conversation_id: Conversation ID
            token_usage: Final token usage dict

        Returns:
            Ended conversation record
        """
        from sqlalchemy import update

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                ended_at=datetime.utcnow(),
                token_usage=token_usage,
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Fetch ended record
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        conversation = result.scalar_one()

        logger.debug(f"Ended conversation: id={conversation_id}")

        return {
            "id": str(conversation.id),
            "user_id": conversation.user_id,
            "post_id": str(conversation.post_id),
            "messages": conversation.messages,
            "token_usage": conversation.token_usage,
            "started_at": conversation.started_at.isoformat(),
            "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        }
