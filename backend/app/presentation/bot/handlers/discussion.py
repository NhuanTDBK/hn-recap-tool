"""Discussion message handler for DISCUSSION state.

Routes user messages during active discussions to the DiscussionAgent.
Conversations auto-expire after 30 minutes of inactivity.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.discussion import DiscussionUseCase
from app.infrastructure.database.models import User
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore
from app.presentation.bot.states import BotStates

logger = logging.getLogger(__name__)

SESSION_TIMEOUT_MINUTES = 30

router = Router()


@router.message(StateFilter(BotStates.IDLE))
async def handle_idle_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    """Catch-all handler: any non-command message in IDLE state enters DISCUSSION.

    Args:
        message: Incoming message.
        state: FSM state context.
        session: Database session.
    """
    telegram_id = message.from_user.id
    user_message = message.text

    if not user_message:
        return

    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("Welcome! Please use /start to set up your account first.")
        return

    await state.set_state(BotStates.DISCUSSION)
    await state.update_data(
        discussion_started_at=datetime.now(timezone.utc).isoformat(),
        last_message_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        f"User {user.id} entered DISCUSSION via natural message: {user_message[:80]}..."
    )

    await _process_question(message, state, session, user, user_message)


@router.message(StateFilter(BotStates.DISCUSSION))
async def handle_discussion_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    """Handle user messages during DISCUSSION state.

    Checks for session timeout first. If more than 30 minutes have passed
    since the last message, the conversation ends and a fresh one starts.

    Args:
        message: Incoming message.
        state: FSM state context.
        session: Database session.
    """
    telegram_id = message.from_user.id
    user_message = message.text

    if not user_message:
        await message.answer("Please send a text message.")
        return

    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Unknown user {telegram_id} in DISCUSSION state")
        await message.answer(
            "I don't recognize you. Please use /start to set up your account."
        )
        await state.set_state(BotStates.IDLE)
        await state.clear()
        return

    data = await state.get_data()
    last_msg_at = data.get("last_message_at")

    if last_msg_at:
        try:
            last_time = datetime.fromisoformat(last_msg_at)
            if datetime.now(timezone.utc) - last_time > timedelta(
                minutes=SESSION_TIMEOUT_MINUTES
            ):
                content_store = RocksDBContentStore(read_only=True)
                use_case = DiscussionUseCase(session, content_store)
                await use_case.end_conversation(user_id=user.id)
                await state.update_data(
                    discussion_started_at=datetime.now(timezone.utc).isoformat(),
                    last_message_at=datetime.now(timezone.utc).isoformat(),
                    active_post_id=data.get("active_post_id"),
                )
                logger.info(
                    f"Session timed out for user {user.id}, starting fresh conversation"
                )
        except (ValueError, TypeError):
            pass

    await _process_question(message, state, session, user, user_message)


async def _process_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    user_message: str,
):
    """Process a user question through the discussion agent.

    Args:
        message: Telegram message object.
        state: FSM state context.
        session: Database session.
        user: User model instance.
        user_message: The user's question text.
    """
    data = await state.get_data()
    post_id_str = data.get("active_post_id")

    post_id = None
    if post_id_str:
        try:
            post_id = UUID(post_id_str)
        except (ValueError, TypeError):
            pass

    try:
        content_store = RocksDBContentStore(read_only=True)
        use_case = DiscussionUseCase(session, content_store)

        processing_msg = await message.answer("Thinking\u2026")

        response = await use_case.ask(
            user=user,
            question=user_message,
            post_id=post_id,
        )

        await processing_msg.delete()

        max_len = 4000
        if len(response) <= max_len:
            await message.answer(response)
        else:
            for i in range(0, len(response), max_len):
                await message.answer(response[i : i + max_len])

        await state.update_data(last_message_at=datetime.now(timezone.utc).isoformat())

        logger.info(f"Discussion response sent to user {user.id}")

    except Exception as e:
        logger.error(f"Error in discussion processing: {e}", exc_info=True)
        await message.answer(
            "Sorry, I encountered an error processing your question. Please try again."
        )


__all__ = ["router"]
