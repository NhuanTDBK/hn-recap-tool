"""Callback handlers for inline button interactions.

This module handles callbacks from inline buttons (Discuss, reactions).
Implements full functionality for all buttons.

Note: Read and Save buttons have been removed as redundant. The message now includes
direct links to the article and HN discussion.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Delivery, Post, User
from app.presentation.bot.states import BotStates

logger = logging.getLogger(__name__)

# Create router for callbacks
callback_router = Router()


@callback_router.callback_query(F.data.startswith("discuss_"))
async def handle_discuss(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle Discuss button callback.

    Transitions user to DISCUSSION state and prompts for questions about the post.

    Args:
        callback: Callback query from button press
        state: FSM state context
        session: Database session
    """
    post_id = callback.data.replace("discuss_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Discuss button pressed by user {telegram_id} for post {post_id}")

    # Load post from database
    try:
        stmt = select(Post).where(Post.id == UUID(post_id))
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Post not found.", show_alert=True)
            return

        # Transition to DISCUSSION state
        await state.set_state(BotStates.DISCUSSION)
        await state.update_data(
            active_post_id=post_id,
            discussion_started_at=datetime.now(timezone.utc).isoformat(),
            last_message_at=datetime.now(timezone.utc).isoformat(),
        )

        # Send discussion prompt
        await callback.message.answer(
            f"💬 <b>Let's discuss: {post.title}</b>\n\n"
            f"I have the full article content and can answer questions about it.\n\n"
            f"What would you like to know?\n\n"
            f"<i>Type /cancel to exit discussion mode.</i>"
        )

        await callback.answer("💬 Discussion started!", show_alert=False)

        logger.info(f"User {telegram_id} entered DISCUSSION state for post {post_id}")

    except Exception as e:
        logger.error(f"Error starting discussion: {e}", exc_info=True)
        await callback.answer("❌ Error starting discussion.", show_alert=True)


# DEPRECATED: Read and Save buttons removed from UI
# Links are now embedded directly in the message format
# Keeping handlers commented out for reference

# @callback_router.callback_query(F.data.startswith("read_"))
# async def handle_read(callback: CallbackQuery, session: AsyncSession):
#     """Handle Read button callback - DEPRECATED."""
#     pass

# @callback_router.callback_query(F.data.startswith("save_"))
# async def handle_save(callback: CallbackQuery, session: AsyncSession):
#     """Handle Save button callback - DEPRECATED."""
#     pass


@callback_router.callback_query(F.data.startswith("react_up_"))
async def handle_react_up(callback: CallbackQuery, session: AsyncSession):
    """Handle thumbs up reaction callback.

    Records positive reaction in delivery record.

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("react_up_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Upvote button pressed by user {telegram_id} for post {post_id}")

    try:
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Find delivery record
        stmt = select(Delivery).where(
            and_(
                Delivery.user_id == user.id,
                Delivery.post_id == UUID(post_id)
            )
        ).order_by(Delivery.delivered_at.desc())
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()

        if delivery:
            # Update reaction
            delivery.reaction = "up"
            await session.commit()
            logger.info(f"Updated delivery reaction: user={user.id}, post={post_id}, reaction=up")

        await callback.answer("👍 Thanks for your feedback!", show_alert=False)

    except Exception as e:
        logger.error(f"Error recording upvote: {e}", exc_info=True)
        await callback.answer("👍 Feedback noted!", show_alert=False)


@callback_router.callback_query(F.data.startswith("react_down_"))
async def handle_react_down(callback: CallbackQuery, session: AsyncSession):
    """Handle thumbs down reaction callback.

    Records negative reaction in delivery record.

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("react_down_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Downvote button pressed by user {telegram_id} for post {post_id}")

    try:
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Find delivery record
        stmt = select(Delivery).where(
            and_(
                Delivery.user_id == user.id,
                Delivery.post_id == UUID(post_id)
            )
        ).order_by(Delivery.delivered_at.desc())
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()

        if delivery:
            # Update reaction
            delivery.reaction = "down"
            await session.commit()
            logger.info(f"Updated delivery reaction: user={user.id}, post={post_id}, reaction=down")

        await callback.answer("👎 Thanks for your feedback!", show_alert=False)

    except Exception as e:
        logger.error(f"Error recording downvote: {e}", exc_info=True)
        await callback.answer("👎 Feedback noted!", show_alert=False)


@callback_router.callback_query(F.data == "view_posts")
async def handle_view_posts(callback: CallbackQuery):
    """Handle View Posts button callback.

    Args:
        callback: Callback query from button press
    """
    logger.info(f"View Posts button pressed by user {callback.from_user.id}")

    await callback.answer("📖 Posts are above!", show_alert=False)

    # This is just a helper button for batch header
    # Posts should already be visible in chat


# Export router
__all__ = ["callback_router"]
