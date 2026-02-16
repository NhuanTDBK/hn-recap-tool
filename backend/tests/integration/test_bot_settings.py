"""Integration tests for bot settings handlers.

Tests the full flow of settings management including:
- /settings command
- Summary style selection
- Delivery settings
- Memory settings
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, User as TelegramUser
from sqlalchemy import select

from app.infrastructure.database.models import User
from app.presentation.bot.handlers import settings


@pytest_asyncio.fixture
async def test_user(async_session):
    """Create a test user in database."""
    user = User(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
        status="active",
        delivery_style="digest",
        summary_preferences={
            "style": "basic",
            "detail_level": "medium",
            "technical_depth": "intermediate"
        },
        interests=["Python", "AI"],
        memory_enabled=True
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_settings_command_shows_current_config(async_session, test_user):
    """Test that /settings command displays current user configuration."""
    # Create mock message
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = test_user.telegram_id
    message.answer = AsyncMock()

    # Call handler
    await settings.cmd_settings(message, async_session)

    # Verify message was sent
    message.answer.assert_called_once()
    call_args = message.answer.call_args
    text = call_args[0][0]

    # Verify content shows current settings
    assert "Settings" in text
    assert "📝 Basic" in text  # Current style
    assert "▶️ Active" in text  # User is active
    assert "Enabled" in text  # Memory enabled
    assert "Python" in text and "AI" in text  # Interests


@pytest.mark.asyncio
async def test_settings_command_user_not_found(async_session):
    """Test /settings command with non-existent user."""
    # Create mock message for non-existent user
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=TelegramUser)
    message.from_user.id = 99999  # Non-existent user
    message.answer = AsyncMock()

    # Call handler
    await settings.cmd_settings(message, async_session)

    # Verify error message was sent
    message.answer.assert_called_once()
    call_args = message.answer.call_args
    text = call_args[0][0]
    assert "User not found" in text


@pytest.mark.asyncio
async def test_summary_style_menu_shows_all_styles(async_session, test_user):
    """Test that summary style menu displays all 5 styles."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:summary"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_summary_style_menu(callback, async_session)

    # Verify message was edited
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]

    # Verify all 5 styles are shown
    assert "📝 Basic" in text
    assert "🔧 Technical" in text
    assert "💼 Business" in text
    assert "⚡ Concise" in text
    assert "🎯 Personalized" in text

    # Verify current style is marked
    assert "✓" in text or "(Current)" in text


@pytest.mark.asyncio
async def test_summary_style_selection_updates_database(async_session, test_user):
    """Test that selecting a style updates the database."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:summary:technical"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_summary_style_selection(callback, async_session)

    # Verify confirmation message was sent
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]
    assert "updated" in text.lower()
    assert "🔧 Technical" in text

    # Verify database was updated
    await async_session.refresh(test_user)
    assert test_user.get_summary_style() == "technical"
    assert test_user.summary_preferences["style"] == "technical"


@pytest.mark.asyncio
async def test_delivery_settings_shows_current_status(async_session, test_user):
    """Test that delivery settings show current status."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:delivery"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_delivery_settings(callback, async_session)

    # Verify message shows status
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]
    assert "Delivery Settings" in text
    assert "▶️ Active" in text  # User is active


@pytest.mark.asyncio
async def test_toggle_delivery_pause(async_session, test_user):
    """Test pausing delivery updates database."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:delivery:pause"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_toggle_delivery(callback, async_session)

    # Verify database was updated
    await async_session.refresh(test_user)
    assert test_user.status == "paused"

    # Verify confirmation was shown
    callback.answer.assert_called()
    call_args = callback.answer.call_args
    message = call_args[0][0]
    assert "paused" in message.lower()


@pytest.mark.asyncio
async def test_toggle_delivery_resume(async_session, test_user):
    """Test resuming delivery updates database."""
    # Set user to paused first
    test_user.status = "paused"
    await async_session.commit()

    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:delivery:resume"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_toggle_delivery(callback, async_session)

    # Verify database was updated
    await async_session.refresh(test_user)
    assert test_user.status == "active"

    # Verify confirmation was shown
    callback.answer.assert_called()
    call_args = callback.answer.call_args
    message = call_args[0][0]
    assert "resumed" in message.lower()


@pytest.mark.asyncio
async def test_memory_settings_shows_current_status(async_session, test_user):
    """Test that memory settings show current status."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:memory"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_memory_settings(callback, async_session)

    # Verify message shows status
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]
    assert "Memory System" in text
    assert "🧠 Enabled" in text  # Memory is enabled


@pytest.mark.asyncio
async def test_toggle_memory_disable(async_session, test_user):
    """Test disabling memory updates database."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:memory:toggle"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_toggle_memory(callback, async_session)

    # Verify database was updated
    await async_session.refresh(test_user)
    assert test_user.memory_enabled is False

    # Verify confirmation was shown
    callback.answer.assert_called()
    call_args = callback.answer.call_args
    message = call_args[0][0]
    assert "disabled" in message.lower()


@pytest.mark.asyncio
async def test_toggle_memory_enable(async_session, test_user):
    """Test enabling memory updates database."""
    # Set memory to disabled first
    test_user.memory_enabled = False
    await async_session.commit()

    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:memory:toggle"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_toggle_memory(callback, async_session)

    # Verify database was updated
    await async_session.refresh(test_user)
    assert test_user.memory_enabled is True

    # Verify confirmation was shown
    callback.answer.assert_called()
    call_args = callback.answer.call_args
    message = call_args[0][0]
    assert "enabled" in message.lower()


@pytest.mark.asyncio
async def test_interests_settings_displays_current(async_session, test_user):
    """Test that interests settings display current interests."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:interests"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_interests_settings(callback, async_session)

    # Verify message shows interests
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]
    assert "Your Interests" in text
    assert "Python" in text
    assert "AI" in text


@pytest.mark.asyncio
async def test_back_to_main_settings(async_session, test_user):
    """Test navigation back to main settings menu."""
    # Create mock callback
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=TelegramUser)
    callback.from_user.id = test_user.telegram_id
    callback.data = "settings:main"
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()

    # Call handler
    await settings.callback_settings_main(callback, async_session)

    # Verify main menu was shown
    callback.message.edit_text.assert_called_once()
    call_args = callback.message.edit_text.call_args
    text = call_args[0][0]
    assert "Settings" in text
    assert "Current Configuration" in text


@pytest.mark.asyncio
async def test_keyboard_creation_basic():
    """Test that keyboard creation functions work."""
    # Test main settings keyboard
    keyboard = settings.create_settings_menu_keyboard()
    assert keyboard.inline_keyboard is not None
    assert len(keyboard.inline_keyboard) > 0

    # Test summary style keyboard
    keyboard = settings.create_summary_style_keyboard("technical")
    assert keyboard.inline_keyboard is not None
    assert len(keyboard.inline_keyboard) > 0

    # Find button with checkmark for current style
    found_current = False
    for row in keyboard.inline_keyboard:
        for button in row:
            if "✓" in button.text and "Technical" in button.text:
                found_current = True
                break

    assert found_current, "Current style should be marked with checkmark"
