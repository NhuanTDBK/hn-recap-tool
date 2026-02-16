"""Discussion message handler for DISCUSSION state.

Routes user messages during active discussions to the discussion agent.
Loads post content from RocksDB and tracks conversation history.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post
from app.presentation.bot.states import BotStates

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("cancel"), StateFilter(BotStates.DISCUSSION))
async def cmd_cancel_discussion(message: Message, state: FSMContext):
    """Handle /cancel command during discussion.

    Exits DISCUSSION state and returns to IDLE.

    Args:
        message: Incoming message
        state: FSM state context
    """
    telegram_id = message.from_user.id
    data = await state.get_data()
    post_id = data.get("active_post_id")

    logger.info(f"User {telegram_id} cancelled discussion for post {post_id}")

    # Return to IDLE state
    await state.set_state(BotStates.IDLE)
    await state.clear()

    await message.answer(
        "✅ <b>Discussion ended.</b>\n\n"
        "Feel free to start a new discussion by tapping 💬 <b>Discuss</b> on any post."
    )


@router.message(StateFilter(BotStates.DISCUSSION))
async def handle_discussion_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """Handle user messages during DISCUSSION state.

    Routes messages to discussion agent (placeholder for now).

    Args:
        message: Incoming message
        state: FSM state context
        session: Database session
    """
    telegram_id = message.from_user.id
    user_message = message.text

    # Get discussion state data
    data = await state.get_data()
    post_id = data.get("active_post_id")

    if not post_id:
        logger.error(f"User {telegram_id} in DISCUSSION state but no active_post_id")
        await message.answer(
            "❌ Discussion state error. Please start a new discussion."
        )
        await state.set_state(BotStates.IDLE)
        await state.clear()
        return

    logger.info(
        f"Discussion message from user {telegram_id} for post {post_id}: "
        f"{user_message[:50]}..."
    )

    try:
        # Load post from database
        stmt = select(Post).where(Post.id == UUID(post_id))
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()

        if not post:
            await message.answer("❌ Post not found. Ending discussion.")
            await state.set_state(BotStates.IDLE)
            await state.clear()
            return

        # TODO: Load post content from RocksDB
        # from app.infrastructure.storage.rocksdb_store import RocksDBStore
        # content = rocksdb_store.get(str(post.id), "markdown")

        # TODO: Call discussion agent with post content
        # For now, send placeholder response
        await message.answer(
            f"💬 <i>Discussion agent coming soon!</i>\n\n"
            f"You asked: \"{user_message}\"\n\n"
            f"For now, I can only acknowledge your message. "
            f"Full discussion features will be available in Phase 5.\n\n"
            f"You can:\n"
            f"• Continue asking questions (I'll track them)\n"
            f"• Type /cancel to exit discussion mode\n"
            f"• Tap 🔗 <b>Read</b> to open the article"
        )

        # Update last_message_at timestamp
        await state.update_data(
            last_message_at=datetime.now(timezone.utc).isoformat()
        )

        # TODO: Track conversation in conversations table
        # conversation_repo = PostgresConversationRepository(session)
        # await conversation_repo.save_conversation_message(
        #     user_id=user.id,
        #     post_id=post_id,
        #     role="user",
        #     content=user_message
        # )

        logger.info(
            f"Handled discussion message for user {telegram_id}, post {post_id}"
        )

    except Exception as e:
        logger.error(
            f"Error handling discussion message: {e}",
            exc_info=True
        )
        await message.answer(
            "❌ Sorry, I encountered an error. Please try again or type /cancel."
        )


# Export router
__all__ = ["router"]
