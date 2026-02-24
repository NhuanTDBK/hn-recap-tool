"""Command handlers for Telegram bot.

Implements bot commands:
- /start - Register user and show welcome message
- /pause - Pause digest delivery
- /resume - Resume digest delivery
- /help - Show available commands
- /saved - List bookmarked posts
- /mystats - Show token usage statistics
- /settings - Configure preferences
"""

import logging
from datetime import datetime, timezone
from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User, UserTokenUsage
from app.presentation.bot.states import BotStates

logger = logging.getLogger(__name__)

router = Router()
UTC = getattr(datetime, "UTC", timezone.utc)  # noqa: UP017


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str = None
) -> User:
    """Get existing user or create new one.

    Args:
        session: Database session
        telegram_id: Telegram user ID
        username: Telegram username (optional)

    Returns:
        User model
    """
    # Try to find existing user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"Found existing user: id={user.id}, telegram_id={telegram_id}")
        return user

    # Create new user
    user = User(
        telegram_id=telegram_id,
        username=username,
        interests=[],  # Empty by default, set during onboarding
        memory_enabled=True,
        status="active",
        delivery_style="flat_scroll",  # Default style
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"Created new user: id={user.id}, telegram_id={telegram_id}")

    return user


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Handle /start command.

    Registers user and shows welcome message. For new users, initiates onboarding.

    Args:
        message: Incoming message
        state: FSM state context
        session: Database session
    """
    telegram_id = message.from_user.id
    username = message.from_user.username

    logger.info(f"/start command from telegram_id={telegram_id}")

    # Get or create user
    user = await get_or_create_user(session, telegram_id, username)

    # Check if this is first time
    is_new_user = (
        user.created_at and (datetime.now(UTC) - user.created_at).total_seconds() < 10
    )

    if is_new_user:
        # New user: start onboarding
        await state.set_state(BotStates.ONBOARDING)
        await state.update_data(step="interests", selected_interests=[])

        await message.answer(
            "👋 <b>Welcome to HN Pal!</b>\n\n"
            "I deliver personalized HackerNews digests straight to your Telegram. "
            "Every day, you'll get AI-summarized posts tailored to your interests.\n\n"
            "<b>Let's get you set up!</b>\n\n"
            "Tell me 2-3 topics you're interested in (e.g., 'Python, LLMs, DevOps').\n\n"
            "Or type /skip to use default settings."
        )
    else:
        # Existing user: reset to IDLE state
        await state.set_state(BotStates.IDLE)
        await state.clear()

        # Show welcome back message
        display_name = escape(username or "friend")
        status = escape(user.status or "unknown")
        delivery_style = escape(user.delivery_style or "unknown")
        interests = (
            ", ".join(escape(item) for item in user.interests)
            if user.interests
            else "None set"
        )

        await message.answer(
            f"👋 <b>Welcome back, {display_name}!</b>\n\n"
            f"Status: <b>{status}</b>\n"
            f"Delivery style: <b>{delivery_style}</b>\n"
            f"Interests: {interests}\n\n"
            "Use /help to see available commands."
        )


@router.message(Command("pause"))
async def cmd_pause(message: Message, session: AsyncSession):
    """Handle /pause command.

    Toggles digest delivery on/off by updating user.status.

    Args:
        message: Incoming message
        session: Database session
    """
    telegram_id = message.from_user.id

    logger.info(f"/pause command from telegram_id={telegram_id}")

    # Find user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found. Please use /start to register first.")
        return

    # Toggle status
    if user.status == "active":
        user.status = "paused"
        await session.commit()

        await message.answer(
            "⏸ <b>Digests paused.</b>\n\n"
            "You won't receive daily digests until you resume.\n\n"
            "Use /resume to start receiving digests again."
        )
    else:
        user.status = "active"
        await session.commit()

        await message.answer(
            "▶️ <b>Digests resumed!</b>\n\n"
            "You'll receive your next digest tomorrow morning."
        )


@router.message(Command("resume"))
async def cmd_resume(message: Message, session: AsyncSession):
    """Handle /resume command.

    Resumes digest delivery by setting user.status to active.

    Args:
        message: Incoming message
        session: Database session
    """
    telegram_id = message.from_user.id

    logger.info(f"/resume command from telegram_id={telegram_id}")

    # Find user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found. Please use /start to register first.")
        return

    # Set status to active
    user.status = "active"
    await session.commit()

    await message.answer(
        "▶️ <b>Digests resumed!</b>\n\nYou'll receive your next digest tomorrow morning."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command.

    Shows list of available commands.

    Args:
        message: Incoming message
    """
    logger.info(f"/help command from telegram_id={message.from_user.id}")

    help_text = """
📖 <b>HN Pal Commands</b>

<b>Basic Commands:</b>
/start - Register or restart the bot
/pause - Pause daily digests
/resume - Resume daily digests
/help - Show this help message

<b>Digest Management:</b>
/saved - View your bookmarked posts
/mystats - View your usage statistics

<b>Settings:</b>
/settings - Configure your preferences

<b>Discussion:</b>
When viewing a post, tap 💬 <b>Discuss</b> to start a conversation about it.
Tap 🔗 <b>Read</b> to open the article.
Tap ⭐ <b>Save</b> to bookmark for later.

<b>Need Help?</b>
Having issues? Contact support or visit our docs.
    """

    await message.answer(help_text)


@router.message(Command("saved"))
async def cmd_saved(message: Message, session: AsyncSession):
    """Handle /saved command.

    Shows list of bookmarked posts.

    Args:
        message: Incoming message
        session: Database session
    """
    telegram_id = message.from_user.id

    logger.info(f"/saved command from telegram_id={telegram_id}")

    # Find user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found. Please use /start to register first.")
        return

    # TODO: Implement bookmark system
    # For now, show placeholder
    await message.answer(
        "⭐ <b>Saved Posts</b>\n\n"
        "Bookmark feature coming soon!\n\n"
        "For now, you can tap the ⭐ <b>Save</b> button on any post "
        "to bookmark it for later."
    )


@router.message(Command("mystats"))
async def cmd_mystats(message: Message, session: AsyncSession):
    """Handle /mystats command.

    Shows user's token usage and delivery statistics.

    Args:
        message: Incoming message
        session: Database session
    """
    telegram_id = message.from_user.id

    logger.info(f"/mystats command from telegram_id={telegram_id}")

    # Find user
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found. Please use /start to register first.")
        return

    # Get token usage stats
    stmt = select(UserTokenUsage).where(UserTokenUsage.user_id == user.id)
    result = await session.execute(stmt)
    usage_records = result.scalars().all()

    total_tokens = sum(r.total_tokens for r in usage_records)
    total_cost = sum(float(r.cost_usd) for r in usage_records)
    total_requests = sum(r.request_count for r in usage_records)

    # Get delivery count (last 7 days)
    from app.infrastructure.repositories.postgres.delivery_repo import (
        PostgresDeliveryRepository,
    )

    delivery_repo = PostgresDeliveryRepository(session)
    delivery_count = await delivery_repo.get_user_delivery_count(user.id, days=7)

    # Format message
    stats_text = f"""
📊 <b>Your Statistics</b>

<b>Account:</b>
Status: <b>{user.status}</b>
Joined: {user.created_at.strftime("%Y-%m-%d") if user.created_at else "Unknown"}

<b>Delivery:</b>
Posts received (last 7 days): <b>{delivery_count}</b>
Delivery style: <b>{user.delivery_style}</b>

<b>LLM Usage:</b>
Total tokens used: <b>{total_tokens:,}</b>
Total API calls: <b>{total_requests}</b>
Total cost: <b>${total_cost:.4f}</b>

<b>Interests:</b>
{", ".join(user.interests) if user.interests else "None set (use /settings)"}
    """

    await message.answer(stats_text)


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Handle /settings command.

    Shows settings menu for configuring preferences.

    Args:
        message: Incoming message
        state: FSM state context
    """
    telegram_id = message.from_user.id

    logger.info(f"/settings command from telegram_id={telegram_id}")

    await state.set_state(BotStates.SETTINGS)

    settings_text = """
⚙️ <b>Settings</b>

What would you like to configure?

1. <b>Interests</b> - Update your topic interests
2. <b>Delivery Style</b> - Change message format (flat_scroll / brief)
3. <b>Memory</b> - Toggle personalized memory system

Reply with the number or name of what you want to change.
Or type /cancel to exit settings.
    """

    await message.answer(settings_text)


# Onboarding flow handlers


@router.message(BotStates.ONBOARDING)
async def handle_onboarding(message: Message, state: FSMContext, session: AsyncSession):
    """Handle messages during onboarding flow.

    Args:
        message: Incoming message
        state: FSM state context
        session: Database session
    """
    telegram_id = message.from_user.id
    text = message.text.strip()

    # Handle /skip command
    if text.lower() == "/skip":
        await state.set_state(BotStates.IDLE)
        await state.clear()

        await message.answer(
            "✅ <b>Setup complete!</b>\n\n"
            "You're all set with default settings. "
            "You'll receive your first digest tomorrow morning.\n\n"
            "Use /settings anytime to customize your preferences."
        )
        return

    # Get onboarding data
    data = await state.get_data()
    step = data.get("step")

    if step == "interests":
        # Parse interests from user input
        interests = [
            i.strip().lower() for i in text.replace(",", " ").split() if i.strip()
        ]

        if len(interests) == 0:
            await message.answer(
                "Please enter at least one interest, or type /skip to use defaults."
            )
            return

        # Update user interests
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.interests = interests[:5]  # Limit to 5 interests
            await session.commit()

            logger.info(
                f"Updated user interests: user_id={user.id}, interests={interests[:5]}"
            )

        # Complete onboarding
        await state.set_state(BotStates.IDLE)
        await state.clear()

        await message.answer(
            f"✅ <b>Setup complete!</b>\n\n"
            f"Your interests: {', '.join(interests[:5])}\n\n"
            f"You'll receive your first digest tomorrow morning, "
            f"personalized to your interests.\n\n"
            f"Use /settings anytime to update your preferences."
        )


# Settings flow handlers


@router.message(BotStates.SETTINGS)
async def handle_settings(message: Message, state: FSMContext, session: AsyncSession):
    """Handle messages during settings flow.

    Args:
        message: Incoming message
        state: FSM state context
        session: Database session
    """
    telegram_id = message.from_user.id
    text = message.text.strip().lower()

    # Handle /cancel
    if text == "/cancel":
        await state.set_state(BotStates.IDLE)
        await state.clear()
        await message.answer("Settings cancelled.")
        return

    # Parse user choice
    if text in ["1", "interests", "interest"]:
        await message.answer(
            "📝 <b>Update Interests</b>\n\n"
            "Enter your interests separated by commas or spaces.\n"
            "Example: Python, Machine Learning, Web Development\n\n"
            "Or type /cancel to go back."
        )
        await state.update_data(editing="interests")

    elif text in ["2", "delivery style", "style"]:
        await message.answer(
            "📬 <b>Delivery Style</b>\n\n"
            "Choose your preferred digest format:\n\n"
            "1. <b>flat_scroll</b> - One post per message (detailed)\n"
            "2. <b>brief</b> - Compact multi-post messages\n\n"
            "Reply with 1 or 2, or type /cancel to go back."
        )
        await state.update_data(editing="delivery_style")

    elif text in ["3", "memory"]:
        # Toggle memory
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.memory_enabled = not user.memory_enabled
            await session.commit()

            status = "enabled" if user.memory_enabled else "disabled"
            await message.answer(f"🧠 Memory system <b>{status}</b>.")

        await state.set_state(BotStates.IDLE)
        await state.clear()

    else:
        # Check if user is updating interests or delivery style
        data = await state.get_data()
        editing = data.get("editing")

        if editing == "interests":
            # Parse interests
            interests = [
                i.strip().lower() for i in text.replace(",", " ").split() if i.strip()
            ]

            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.interests = interests[:5]
                await session.commit()

                await message.answer(
                    f"✅ Interests updated: {', '.join(interests[:5])}"
                )

            await state.set_state(BotStates.IDLE)
            await state.clear()

        elif editing == "delivery_style":
            # Parse delivery style
            if text in ["1", "flat_scroll", "flat scroll"]:
                new_style = "flat_scroll"
            elif text in ["2", "brief"]:
                new_style = "brief"
            else:
                await message.answer(
                    "Invalid choice. Please reply with 1 (flat_scroll) or 2 (brief)."
                )
                return

            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.delivery_style = new_style
                await session.commit()

                await message.answer(f"✅ Delivery style updated: <b>{new_style}</b>")

            await state.set_state(BotStates.IDLE)
            await state.clear()

        else:
            # Unknown input during settings
            await message.answer(
                "Please choose 1 (Interests), 2 (Delivery Style), or 3 (Memory).\n"
                "Or type /cancel to exit."
            )
