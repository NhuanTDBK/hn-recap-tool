"""Discussion use case - orchestrates the conversational HN research flow.

Handles conversation persistence, context loading, and agent invocation.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import ConversationRepository
from app.infrastructure.agents.discussion_agent import discuss
from app.infrastructure.database.models import User
from app.infrastructure.repositories.postgres.delivery_repo import (
    PostgresConversationRepository,
)
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)

MAX_CONVERSATION_MESSAGES = 40


class DiscussionUseCase:
    """Orchestrates the discussion flow: load history, call agent, save results."""

    def __init__(
        self,
        session: AsyncSession,
        content_store: RocksDBContentStore,
    ):
        self.session = session
        self.content_store = content_store
        self.conversation_repo: ConversationRepository = PostgresConversationRepository(
            session
        )

    async def ask(
        self,
        user: User,
        question: str,
        post_id: UUID | None = None,
    ) -> str:
        """Answer a user's question about HackerNews topics.

        Loads or creates a conversation, invokes the discussion agent,
        and persists the exchange.

        Args:
            user: The user asking the question.
            question: The user's question or message text.
            post_id: Optional specific post being discussed.

        Returns:
            The agent's response text.
        """
        conversation = await self._get_or_create_conversation(
            user_id=user.id,
            post_id=post_id,
        )

        conversation_history = conversation.get("messages", [])
        conversation_history = conversation_history[-MAX_CONVERSATION_MESSAGES:]

        response = await discuss(
            question=question,
            session=self.session,
            content_store=self.content_store,
            conversation_history=conversation_history,
        )

        conversation_history.append(
            {
                "role": "user",
                "content": question,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        conversation_history.append(
            {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        await self.conversation_repo.update_messages(
            conversation_id=conversation["id"],
            messages=conversation_history,
        )

        return response

    async def end_conversation(self, user_id: int) -> dict | None:
        """End the active conversation for a user.

        Args:
            user_id: The user's ID.

        Returns:
            The ended conversation record, or None if no active conversation.
        """
        conversation = await self.conversation_repo.find_active_conversation(user_id)
        if not conversation:
            return None

        token_usage = conversation.get("token_usage", {})
        token_usage.setdefault("model", "unknown")

        result = await self.conversation_repo.end_conversation(
            conversation_id=conversation["id"],
            token_usage=token_usage,
        )

        logger.info(f"Ended conversation {conversation['id']} for user {user_id}")
        return result

    async def _get_or_create_conversation(
        self,
        user_id: int,
        post_id: UUID | None = None,
    ) -> dict:
        """Get active conversation or create a new one.

        Args:
            user_id: The user's ID.
            post_id: Optional post ID to associate.

        Returns:
            Conversation record dict.
        """
        conversation = await self.conversation_repo.find_active_conversation(user_id)

        if conversation:
            return conversation

        conversation = await self.conversation_repo.save_conversation(
            user_id=user_id,
            post_id=str(post_id) if post_id else None,
            messages=[],
            token_usage={},
        )

        logger.info(f"Created new conversation for user {user_id}")
        return conversation
