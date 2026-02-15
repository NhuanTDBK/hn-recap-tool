"""Callback handlers for inline button interactions.

This module handles callbacks from inline buttons (Discuss, Read, Save, reactions).
For Phase 3.5, most are placeholders. Full implementation in Phase 4-6.
"""

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

# Create router for callbacks
callback_router = Router()


@callback_router.callback_query(F.data.startswith("discuss_"))
async def handle_discuss(callback: CallbackQuery):
    """Handle Discuss button callback.

    Args:
        callback: Callback query from button press

    Triggers: Discussion mode (Phase 5)
    """
    post_id = callback.data.replace("discuss_", "")

    logger.info(f"Discuss button pressed by user {callback.from_user.id} for post {post_id}")

    await callback.answer("💬 Discussion coming soon!", show_alert=False)

    # TODO: Phase 5 - Trigger discussion mode
    # - Load post markdown content
    # - Load user memory
    # - Set active_discussion_post_id
    # - Enter conversation loop


@callback_router.callback_query(F.data.startswith("read_"))
async def handle_read(callback: CallbackQuery):
    """Handle Read button callback.

    Args:
        callback: Callback query from button press

    Triggers: Open article URL or show expanded content (Phase 4)
    """
    post_id = callback.data.replace("read_", "")

    logger.info(f"Read button pressed by user {callback.from_user.id} for post {post_id}")

    await callback.answer("🔗 Opening article...", show_alert=False)

    # TODO: Phase 4 - Open article
    # - Fetch post URL
    # - Send inline button with URL
    # - Or show expanded summary


@callback_router.callback_query(F.data.startswith("save_"))
async def handle_save(callback: CallbackQuery):
    """Handle Save button callback.

    Args:
        callback: Callback query from button press

    Triggers: Bookmark post (Phase 4)
    """
    post_id = callback.data.replace("save_", "")

    logger.info(f"Save button pressed by user {callback.from_user.id} for post {post_id}")

    await callback.answer("⭐ Saved!", show_alert=False)

    # TODO: Phase 4 - Save post
    # - Create bookmark record
    # - Track in memory
    # - Show confirmation


@callback_router.callback_query(F.data.startswith("react_up_"))
async def handle_react_up(callback: CallbackQuery):
    """Handle thumbs up reaction callback.

    Args:
        callback: Callback query from button press

    Triggers: Record upvote (Phase 4)
    """
    post_id = callback.data.replace("react_up_", "")

    logger.info(f"Upvote button pressed by user {callback.from_user.id} for post {post_id}")

    await callback.answer("👍 Thanks for the feedback!", show_alert=False)

    # TODO: Phase 4 - Update reaction
    # - Find delivery record
    # - Update reaction = "up"
    # - Update memory/interests


@callback_router.callback_query(F.data.startswith("react_down_"))
async def handle_react_down(callback: CallbackQuery):
    """Handle thumbs down reaction callback.

    Args:
        callback: Callback query from button press

    Triggers: Record downvote (Phase 4)
    """
    post_id = callback.data.replace("react_down_", "")

    logger.info(f"Downvote button pressed by user {callback.from_user.id} for post {post_id}")

    await callback.answer("👎 Thanks for the feedback!", show_alert=False)

    # TODO: Phase 4 - Update reaction
    # - Find delivery record
    # - Update reaction = "down"
    # - Update memory/interests


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
