"""Callback handlers for inline button interactions.

This module handles callbacks from inline buttons (Discuss, reactions, save).
Implements full functionality for all buttons.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import ActivityLogRepository
from app.infrastructure.database.models import Delivery, Post, Summary, User
from app.infrastructure.repositories.postgres.activity_log_repo import (
    PostgresActivityLogRepository,
)
from app.infrastructure.repositories.postgres.recommendation_repo import (
    PostgresRecommendationRepository,
)
from app.infrastructure.services.group_subscriber import is_group_chat
from app.presentation.bot.states import BotStates
from app.presentation.bot.formatters.digest_formatter import DigestMessageFormatter, InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Create router for callbacks
callback_router = Router()


async def _resolve_feed_user(session: AsyncSession, callback: CallbackQuery) -> Optional[User]:
    """Return the User a button press belongs to.

    In the group topic, buttons act on the group's feed row (the chat), so members
    who never ran /start can still react. Elsewhere, it is the person who pressed.
    """
    chat_id = callback.message.chat.id if callback.message else None
    telegram_id = chat_id if is_group_chat(chat_id) else callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


WHY_POPUP_MAX_CHARS = 200  # Telegram's limit for a callback answer shown as an alert


def _keyboard_state(callback: CallbackQuery) -> dict:
    """Read which buttons a message currently shows.

    Messages carry no state of their own, so the keyboard is the only record of
    whether a post was expanded, saved or dismissed. Recommended messages are told
    apart from Streaming ones by their Why button.
    """
    state = {"recommended": False, "has_more": False, "saved": False, "dismissed": False}
    try:
        for row in callback.message.reply_markup.inline_keyboard:
            for btn in row:
                data = btn.callback_data or ""
                if data.startswith("why_rec_"):
                    state["recommended"] = True
                elif data.startswith("show_more_"):
                    state["has_more"] = True
                elif data.startswith("save_post_"):
                    state["saved"] = btn.text.startswith("✅")
                elif data.startswith("not_for_me_"):
                    state["dismissed"] = "Noted" in btn.text
    except (AttributeError, TypeError):
        pass
    return state


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
        # Find user (in the group topic this is the group's feed row)
        user = await _resolve_feed_user(session, callback)

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Find delivery record
        stmt = select(Delivery).where(
            and_(
                Delivery.user_id == user.id,
                Delivery.post_id == UUID(post_id)
            )
        ).order_by(Delivery.delivered_at.desc()).limit(1)
        result = await session.execute(stmt)
        delivery = result.scalars().first()

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
            await callback.message.edit_reply_markup(reply_markup=keyboard)
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
        # Find user (in the group topic this is the group's feed row)
        user = await _resolve_feed_user(session, callback)

        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        # Find delivery record
        stmt = select(Delivery).where(
            and_(
                Delivery.user_id == user.id,
                Delivery.post_id == UUID(post_id)
            )
        ).order_by(Delivery.delivered_at.desc()).limit(1)
        result = await session.execute(stmt)
        delivery = result.scalars().first()

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
            await callback.message.edit_reply_markup(reply_markup=keyboard)
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
        # Find user (in the group topic this is the group's feed row)
        user = await _resolve_feed_user(session, callback)

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

        # Update button text to "✅ Saved"
        try:
            state = _keyboard_state(callback)
            builder = InlineKeyboardBuilder()
            if state["recommended"]:
                saved_keyboard = builder.build_recommendation_keyboard(
                    post_id,
                    expanded=not state["has_more"],
                    saved=True,
                    dismissed=state["dismissed"],
                )
            elif state["has_more"]:
                saved_keyboard = builder.build_post_keyboard_saved(post_id)
            else:
                saved_keyboard = builder.build_post_keyboard_without_more_saved(post_id)
            await callback.message.edit_reply_markup(reply_markup=saved_keyboard)
        except Exception as edit_error:
            logger.warning(f"Failed to update Save button label: {edit_error}")

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
        # Find user (in the group topic this is the group's feed row)
        user = await _resolve_feed_user(session, callback)

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

        # Use the summary written for this feed (DM user or group). posts.summary is shared
        # and holds whichever feed was delivered last.
        stmt = (
            select(Summary.summary_text)
            .where(and_(Summary.user_id == user.id, Summary.post_id == post.id))
            .order_by(Summary.created_at.desc())
            .limit(1)
        )
        summary_text = (await session.execute(stmt)).scalar_one_or_none()

        # Format the full message with untruncated summary
        formatter = DigestMessageFormatter()
        # We need position and total for formatting, but we can infer from message or use defaults
        # For now, use reasonable defaults (1/1 since we're just showing the post)
        builder = InlineKeyboardBuilder()
        state = _keyboard_state(callback)

        # An explore pick keeps its "Outside your usual" label when expanded.
        is_explore = False
        if state["recommended"]:
            try:
                kind = await PostgresRecommendationRepository(session).get_kind(user.id, post.id)
                is_explore = kind == "explore"
            except Exception as kind_error:
                logger.warning(f"Could not look up the pick kind for the label: {kind_error}")
        full_text = formatter.format_post_message_full(
            post, position=1, total=1, summary=summary_text, explore=is_explore
        )

        # Build keyboard without "More" button (recommended posts keep Why / Not for me)
        if state["recommended"]:
            keyboard = builder.build_recommendation_keyboard(
                post_id,
                expanded=True,
                saved=state["saved"],
                dismissed=state["dismissed"],
            )
        else:
            keyboard = builder.build_post_keyboard_without_more(post_id)

        # Update message with expanded summary and new keyboard
        try:
            await callback.message.edit_text(
                text=full_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,  # the formatter emits HTML, same as delivery
            )
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


@callback_router.callback_query(F.data.startswith("why_rec_"))
async def handle_why_recommended(callback: CallbackQuery, session: AsyncSession):
    """Show why a post was recommended, as a popup.

    The reason was written during the daily ranking and stored with the pick, so
    this costs no LLM call. Logs a ``why`` activity, which only marks the pick as
    looked at (it is not a verdict either way).

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("why_rec_", "")
    logger.info(f"Why button pressed by user {callback.from_user.id} for post {post_id}")

    try:
        user = await _resolve_feed_user(session, callback)
        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        reason = await PostgresRecommendationRepository(session).get_reason(user.id, UUID(post_id))
        if not reason:
            await callback.answer("No reason was stored for this post.", show_alert=True)
            return

        try:
            await PostgresActivityLogRepository(session).log_activity(user.id, post_id, "why")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")

        await callback.answer(f"💡 {reason}"[:WHY_POPUP_MAX_CHARS], show_alert=True)

    except Exception as e:
        logger.error(f"Error showing recommendation reason: {e}", exc_info=True)
        await callback.answer("❌ Could not load the reason.", show_alert=True)


@callback_router.callback_query(F.data.startswith("not_for_me_"))
async def handle_not_for_me(callback: CallbackQuery, session: AsyncSession):
    """Record that a recommended post is not wanted, and relabel the button.

    A strong negative signal for the next daily run. A later Save on the same post
    overrides it (the newest verdict wins).

    Args:
        callback: Callback query from button press
        session: Database session
    """
    post_id = callback.data.replace("not_for_me_", "")
    logger.info(f"Not for me pressed by user {callback.from_user.id} for post {post_id}")

    try:
        user = await _resolve_feed_user(session, callback)
        if not user:
            await callback.answer("❌ User not found.", show_alert=True)
            return

        try:
            await PostgresActivityLogRepository(session).log_activity(user.id, post_id, "not_for_me")
        except Exception as log_error:
            logger.warning(f"Failed to log activity: {log_error}")

        try:
            state = _keyboard_state(callback)
            keyboard = InlineKeyboardBuilder().build_recommendation_keyboard(
                post_id,
                expanded=not state["has_more"],
                saved=state["saved"],
                dismissed=True,
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except Exception as edit_error:
            logger.warning(f"Failed to update Not for me label: {edit_error}")

        await callback.answer("👎 Noted — fewer posts like this.", show_alert=False)

    except Exception as e:
        logger.error(f"Error recording not-for-me: {e}", exc_info=True)
        await callback.answer("👎 Noted!", show_alert=False)


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
            await callback.message.edit_reply_markup(reply_markup=keyboard)
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
            await callback.message.edit_reply_markup(reply_markup=keyboard)
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
