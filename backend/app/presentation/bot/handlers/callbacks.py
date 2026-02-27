"""Callback handlers for inline button interactions.

This module handles callbacks from inline buttons (Discuss, reactions, save).
Implements full functionality for all buttons.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import ActivityLogRepository
from app.infrastructure.database.models import Delivery, Post, User
from app.infrastructure.repositories.postgres.activity_log_repo import (
    PostgresActivityLogRepository,
)
from app.presentation.bot.states import BotStates
from app.presentation.bot.formatters.digest_formatter import DigestMessageFormatter, InlineKeyboardBuilder

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

    Records positive reaction in delivery record and logs activity.

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
            # Update reaction on delivery (preserve existing behavior)
            delivery.reaction = "up"
            await session.commit()
            logger.info(f"Updated delivery reaction: user={user.id}, post={post_id}, reaction=up")

        # Log activity to activity_log table
        activity_repo = PostgresActivityLogRepository(session)
        try:
            await activity_repo.log_activity(user.id, post_id, "rate_up")
            logger.info(f"Logged activity: user={user.id}, post={post_id}, action=rate_up")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")
            # Continue - do not fail user feedback on logging error

        # Swap keyboard back to default menu (best-effort, don't fail UX)
        try:
            SUMMARY_TRUNCATE_LENGTH = 500
            message_text = callback.message.text or ""
            is_expanded = len(message_text) > (SUMMARY_TRUNCATE_LENGTH + 50)

            builder = InlineKeyboardBuilder()
            keyboard = (
                builder.build_post_keyboard_without_more(post_id)
                if is_expanded
                else builder.build_post_keyboard(post_id)
            )
            await callback.message.edit_message_reply_markup(reply_markup=keyboard)
            logger.debug(f"Swapped keyboard back to default for post {post_id}")
        except Exception as keyboard_error:
            logger.warning(f"Failed to swap keyboard back: {keyboard_error}")
            # Continue - keyboard swap is best-effort

        await callback.answer("👍 Summary rated helpful — thanks!", show_alert=False)

    except Exception as e:
        logger.error(f"Error recording upvote: {e}", exc_info=True)
        await callback.answer("👍 Feedback noted!", show_alert=False)


@callback_router.callback_query(F.data.startswith("react_down_"))
async def handle_react_down(callback: CallbackQuery, session: AsyncSession):
    """Handle thumbs down reaction callback.

    Records negative reaction in delivery record and logs activity.

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
            # Update reaction on delivery (preserve existing behavior)
            delivery.reaction = "down"
            await session.commit()
            logger.info(f"Updated delivery reaction: user={user.id}, post={post_id}, reaction=down")

        # Log activity to activity_log table
        activity_repo = PostgresActivityLogRepository(session)
        try:
            await activity_repo.log_activity(user.id, post_id, "rate_down")
            logger.info(f"Logged activity: user={user.id}, post={post_id}, action=rate_down")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")
            # Continue - do not fail user feedback on logging error

        # Swap keyboard back to default menu (best-effort, don't fail UX)
        try:
            SUMMARY_TRUNCATE_LENGTH = 500
            message_text = callback.message.text or ""
            is_expanded = len(message_text) > (SUMMARY_TRUNCATE_LENGTH + 50)

            builder = InlineKeyboardBuilder()
            keyboard = (
                builder.build_post_keyboard_without_more(post_id)
                if is_expanded
                else builder.build_post_keyboard(post_id)
            )
            await callback.message.edit_message_reply_markup(reply_markup=keyboard)
            logger.debug(f"Swapped keyboard back to default for post {post_id}")
        except Exception as keyboard_error:
            logger.warning(f"Failed to swap keyboard back: {keyboard_error}")
            # Continue - keyboard swap is best-effort

        await callback.answer("👎 Noted — thanks for the feedback!", show_alert=False)

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


@callback_router.callback_query(F.data.startswith("save_post_"))
async def handle_save_post(callback: CallbackQuery, session: AsyncSession):
    """Handle Save for later button callback.

    Logs a 'save' activity to track user interest without affecting delivery.

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("save_post_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Save button pressed by user {telegram_id} for post {post_id}")

    try:
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Log activity to activity_log table
        activity_repo = PostgresActivityLogRepository(session)
        try:
            await activity_repo.log_activity(user.id, post_id, "save")
            logger.info(f"Logged activity: user={user.id}, post={post_id}, action=save")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")
            # Continue - do not fail user feedback on logging error

        await callback.answer("🔖 Post saved for later reading!", show_alert=False)

    except Exception as e:
        logger.error(f"Error saving post: {e}", exc_info=True)
        await callback.answer("🔖 Save noted!", show_alert=False)


@callback_router.callback_query(F.data.startswith("show_more_"))
async def handle_show_more(callback: CallbackQuery, session: AsyncSession):
    """Handle Show More button callback.

    Expands truncated summary inline by editing the message text and keyboard.
    Uses format_post_message_full() to display the complete summary.
    Removes the 'More' button from keyboard after expansion.
    Logs activity as 'show_more' event.

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("show_more_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Show More button pressed by user {telegram_id} for post {post_id}")

    try:
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Load post from database
        stmt = select(Post).where(Post.id == UUID(post_id))
        result = await session.execute(stmt)
        post = result.scalar_one_or_none()

        if not post:
            await callback.answer("❌ Post not found.", show_alert=True)
            return

        # Format the full message with untruncated summary
        formatter = DigestMessageFormatter()
        # We need position and total for formatting, but we can infer from message or use defaults
        # For now, use reasonable defaults (1/1 since we're just showing the post)
        full_text = formatter.format_post_message_full(post, position=1, total=1)

        # Build keyboard without "More" button
        builder = InlineKeyboardBuilder()
        keyboard = builder.build_post_keyboard_without_more(post_id)

        # Update message with expanded summary and new keyboard
        try:
            await callback.message.edit_message_text(text=full_text)
            await callback.message.edit_message_reply_markup(reply_markup=keyboard)
            logger.info(f"Expanded message for post {post_id}")
        except Exception as edit_error:
            logger.warning(f"Failed to edit message: {edit_error}")
            # Gracefully handle if message can't be edited (too old, etc.)
            await callback.answer("⚠️ Unable to expand (message too old).", show_alert=False)
            return

        # Log activity to activity_log table
        activity_repo = PostgresActivityLogRepository(session)
        try:
            await activity_repo.log_activity(user.id, post_id, "show_more")
            logger.info(f"Logged activity: user={user.id}, post={post_id}, action=show_more")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")
            # Continue - do not fail user feedback on logging error

        await callback.answer("📖 Full summary loaded", show_alert=False)

    except Exception as e:
        logger.error(f"Error expanding summary: {e}", exc_info=True)
        await callback.answer("❌ Error loading summary.", show_alert=True)


@callback_router.callback_query(F.data.startswith("actions_"))
async def handle_actions_menu(callback: CallbackQuery):
    """Handle Actions button callback.

    Swaps the keyboard from default menu to reactions menu.
    Shows: [ 👍 Good Response ] [ 👎 Bad Response ] [ « Back ]

    Args:
        callback: Callback query from button press
    """
    post_id = callback.data.replace("actions_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Actions button pressed by user {telegram_id} for post {post_id}")

    try:
        # Build reactions keyboard
        builder = InlineKeyboardBuilder()
        keyboard = builder.build_reactions_keyboard(post_id)

        # Swap the keyboard
        try:
            await callback.message.edit_message_reply_markup(reply_markup=keyboard)
            logger.info(f"Swapped to reactions menu for post {post_id}")
        except Exception as edit_error:
            logger.warning(f"Failed to edit message keyboard: {edit_error}")
            # Gracefully handle if message can't be edited
            await callback.answer("⚠️ Unable to show menu (message too old).", show_alert=False)
            return

        await callback.answer("Choose a reaction", show_alert=False)

    except Exception as e:
        logger.error(f"Error swapping to actions menu: {e}", exc_info=True)
        await callback.answer("❌ Error showing menu.", show_alert=True)


@callback_router.callback_query(F.data.startswith("back_"))
async def handle_back_to_default(callback: CallbackQuery):
    """Handle Back button callback.

    Swaps keyboard from reactions menu back to default menu.
    Determines whether to show the 'More' button based on current message state:
    - If summary is expanded (message text length > SUMMARY_TRUNCATE_LENGTH + buffer),
      use keyboard without 'More' button
    - If summary is truncated, use keyboard with 'More' button

    Args:
        callback: Callback query from button press
    """
    post_id = callback.data.replace("back_", "")
    telegram_id = callback.from_user.id

    logger.info(f"Back button pressed by user {telegram_id} for post {post_id}")

    try:
        # Check if summary was expanded by examining message text length
        # SUMMARY_TRUNCATE_LENGTH is 500; full summaries typically > 800-1000
        # Add buffer to account for title, links, and stats
        SUMMARY_TRUNCATE_LENGTH = 500
        message_text = callback.message.text or ""
        is_expanded = len(message_text) > (SUMMARY_TRUNCATE_LENGTH + 50)

        # Build appropriate keyboard
        builder = InlineKeyboardBuilder()
        if is_expanded:
            # Summary is expanded, use keyboard without 'More' button
            keyboard = builder.build_post_keyboard_without_more(post_id)
            logger.debug(f"Summary is expanded for post {post_id}, using keyboard without More")
        else:
            # Summary is truncated, use default keyboard with 'More' button
            keyboard = builder.build_post_keyboard(post_id)
            logger.debug(f"Summary is truncated for post {post_id}, using default keyboard")

        # Swap the keyboard
        try:
            await callback.message.edit_message_reply_markup(reply_markup=keyboard)
            logger.info(f"Returned to default menu for post {post_id}")
        except Exception as edit_error:
            logger.warning(f"Failed to edit message keyboard: {edit_error}")
            # Gracefully handle if message can't be edited
            await callback.answer("⚠️ Unable to show menu (message too old).", show_alert=False)
            return

        # Silent callback answer (no toast shown to user)
        await callback.answer(show_alert=False)

    except Exception as e:
        logger.error(f"Error returning to default menu: {e}", exc_info=True)
        await callback.answer("❌ Error showing menu.", show_alert=True)


# Export router
__all__ = ["callback_router"]
