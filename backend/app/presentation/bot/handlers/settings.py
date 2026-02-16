"""Settings command handlers for Telegram bot.

This module contains handlers for /settings command and related callbacks.
Implements summary style selection and other preference management.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.summary_preferences import (
    get_all_styles,
    get_user_summary_style,
    update_user_summary_style,
)
from app.infrastructure.database.models import User

logger = logging.getLogger(__name__)

router = Router()


def create_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the main settings menu keyboard.

    Layout:
    [Change Summary Style] [Pause Deliveries]
    [Memory Settings]

    Returns:
        InlineKeyboardMarkup with settings buttons
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Summary Style", callback_data="settings:summary"),
            InlineKeyboardButton(text="📬 Delivery", callback_data="settings:delivery"),
        ],
        [
            InlineKeyboardButton(text="🧠 Memory", callback_data="settings:memory"),
            InlineKeyboardButton(text="🏷️ Interests", callback_data="settings:interests"),
        ],
    ])


def create_summary_style_keyboard(current_style: str = "basic") -> InlineKeyboardMarkup:
    """Create summary style picker keyboard.

    Shows all 5 styles as buttons, with current style marked.

    Layout:
    [📝 Basic] [🔧 Technical] [💼 Business]
    [⚡ Concise] [🎯 Personalized]
    [← Back]

    Args:
        current_style: User's current summary style (to mark as selected)

    Returns:
        InlineKeyboardMarkup with style selection buttons
    """
    styles = get_all_styles()

    buttons = []
    row1 = []
    row2 = []

    for style_key, style_info in styles.items():
        # Add checkmark if current style
        text = style_info["name"]
        if style_key == current_style:
            text = f"✓ {text}"

        button = InlineKeyboardButton(
            text=text,
            callback_data=f"settings:summary:{style_key}"
        )

        # First 3 buttons in row 1, rest in row 2
        if len(row1) < 3:
            row1.append(button)
        else:
            row2.append(button)

    buttons.append(row1)
    buttons.append(row2)

    # Add back button
    buttons.append([
        InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    """Handle /settings command.

    Shows settings menu for configuring preferences.

    Args:
        message: Incoming message
        session: Database session
    """
    telegram_id = message.from_user.id

    logger.info(f"/settings command from telegram_id={telegram_id}")

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer(
            "❌ User not found. Please use /start to register first."
        )
        return

    # Get current summary style
    summary_style = user.get_summary_style()
    styles = get_all_styles()
    style_info = styles.get(summary_style, {"name": "📝 Basic"})

    settings_text = f"""
⚙️ <b>Settings</b>

<b>Current Configuration:</b>
📝 Summary Style: {style_info['name']}
📬 Delivery: <b>{"▶️ Active" if user.status == "active" else "⏸ Paused"}</b>
🧠 Memory: <b>{"Enabled" if user.memory_enabled else "Disabled"}</b>
🏷️ Interests: {', '.join(user.interests) if user.interests else 'None set'}

Tap a button below to change a setting:
    """

    await message.answer(
        settings_text,
        reply_markup=create_settings_menu_keyboard()
    )


@router.callback_query(F.data == "settings:main")
async def callback_settings_main(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to return to main settings menu.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    # Get current summary style
    summary_style = user.get_summary_style()
    styles = get_all_styles()
    style_info = styles.get(summary_style, {"name": "📝 Basic"})

    settings_text = f"""
⚙️ <b>Settings</b>

<b>Current Configuration:</b>
📝 Summary Style: {style_info['name']}
📬 Delivery: <b>{"▶️ Active" if user.status == "active" else "⏸ Paused"}</b>
🧠 Memory: <b>{"Enabled" if user.memory_enabled else "Disabled"}</b>
🏷️ Interests: {', '.join(user.interests) if user.interests else 'None set'}

Tap a button below to change a setting:
    """

    await callback.message.edit_text(
        settings_text,
        reply_markup=create_settings_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "settings:summary")
async def callback_summary_style_menu(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to show summary style picker.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    logger.info(f"Summary style picker requested by telegram_id={telegram_id}")

    # Get user's current style
    current_style = await get_user_summary_style(session, telegram_id)

    # Get all styles with descriptions
    styles = get_all_styles()

    # Build message with all style descriptions
    message_parts = ["📝 <b>Choose Your Summary Style</b>\n"]

    for style_key, style_info in styles.items():
        is_current = " (Current)" if style_key == current_style else ""
        marker = "✓" if style_key == current_style else "○"

        message_parts.append(
            f"\n{marker} <b>{style_info['name']}{is_current}</b> - {style_info['tagline']}\n"
            f"{style_info['description']}\n"
            f"<i>Example: \"{style_info['example']}\"</i>"
        )

    style_picker_text = "\n".join(message_parts)

    await callback.message.edit_text(
        style_picker_text,
        reply_markup=create_summary_style_keyboard(current_style)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:summary:"))
async def callback_summary_style_selection(callback: CallbackQuery, session: AsyncSession):
    """Handle user selecting a new summary style.

    Callback data format: "settings:summary:{style}"
    where style is one of: basic, technical, business, concise, personalized

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Extract style from callback data
    style = callback.data.split(":")[-1]

    logger.info(f"Summary style selection: telegram_id={telegram_id}, style={style}")

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    try:
        # Update user's summary preferences
        success = await update_user_summary_style(session, user.id, style)

        if success:
            # Get style info for confirmation message
            styles = get_all_styles()
            style_info = styles.get(style)

            confirmation_text = f"""
✅ <b>Summary style updated!</b>

You'll now receive <b>{style_info['name']}</b> summaries.

<i>{style_info['description']}</i>

Your next digest will use this style.
            """

            # Show confirmation with back button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main")]
            ])

            await callback.message.edit_text(
                confirmation_text,
                reply_markup=keyboard
            )
            await callback.answer("✅ Style updated!", show_alert=False)

        else:
            await callback.answer("❌ Failed to update style", show_alert=True)

    except ValueError as e:
        logger.error(f"Invalid style selected: {style}, error: {e}")
        await callback.answer("❌ Invalid style", show_alert=True)


@router.callback_query(F.data == "settings:delivery")
async def callback_delivery_settings(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to show delivery settings.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    status_text = "▶️ Active" if user.status == "active" else "⏸ Paused"
    action_text = "Pause" if user.status == "active" else "Resume"
    action_callback = "settings:delivery:pause" if user.status == "active" else "settings:delivery:resume"

    delivery_text = f"""
📬 <b>Delivery Settings</b>

<b>Current Status:</b> {status_text}

When active, you'll receive daily HackerNews digests.
When paused, no digests will be delivered.
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{action_text} Deliveries", callback_data=action_callback)],
        [InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main")]
    ])

    await callback.message.edit_text(delivery_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("settings:delivery:"))
async def callback_toggle_delivery(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to toggle delivery status.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id
    action = callback.data.split(":")[-1]

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    # Toggle status
    if action == "pause":
        user.status = "paused"
        message = "⏸ Deliveries paused"
    else:  # resume
        user.status = "active"
        message = "▶️ Deliveries resumed"

    await session.commit()

    await callback.answer(message, show_alert=False)

    # Refresh the delivery settings page
    await callback_delivery_settings(callback, session)


@router.callback_query(F.data == "settings:memory")
async def callback_memory_settings(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to show memory settings.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    status_text = "🧠 Enabled" if user.memory_enabled else "💤 Disabled"
    action_text = "Disable" if user.memory_enabled else "Enable"
    action_callback = "settings:memory:toggle"

    memory_text = f"""
🧠 <b>Memory System</b>

<b>Current Status:</b> {status_text}

When enabled, the bot remembers your:
• Past discussions
• Preferences and feedback
• Topics you care about

This makes conversations more personalized over time.
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{action_text} Memory", callback_data=action_callback)],
        [InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main")]
    ])

    await callback.message.edit_text(memory_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "settings:memory:toggle")
async def callback_toggle_memory(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to toggle memory system.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    # Toggle memory
    user.memory_enabled = not user.memory_enabled
    await session.commit()

    message = "🧠 Memory enabled" if user.memory_enabled else "💤 Memory disabled"

    await callback.answer(message, show_alert=False)

    # Refresh the memory settings page
    await callback_memory_settings(callback, session)


@router.callback_query(F.data == "settings:interests")
async def callback_interests_settings(callback: CallbackQuery, session: AsyncSession):
    """Handle callback to show interests settings.

    Args:
        callback: Callback query
        session: Database session
    """
    telegram_id = callback.from_user.id

    # Get user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("User not found", show_alert=True)
        return

    interests_list = ', '.join(user.interests) if user.interests else 'None set'

    interests_text = f"""
🏷️ <b>Your Interests</b>

<b>Current interests:</b>
{interests_list}

To update your interests, use the /start command
or send a message with your new interests.

<i>Example: "Python, Machine Learning, DevOps"</i>
    """

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main")]
    ])

    await callback.message.edit_text(interests_text, reply_markup=keyboard)
    await callback.answer()
