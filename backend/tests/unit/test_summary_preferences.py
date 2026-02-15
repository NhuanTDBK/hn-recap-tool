"""Unit tests for summary preferences functionality."""

import pytest
from sqlalchemy import select

from app.infrastructure.database.models import User
from app.application.use_cases.summary_preferences import (
    get_user_summary_style,
    update_user_summary_style,
    get_summary_style_info,
    get_all_styles,
    format_style_for_display,
    VALID_SUMMARY_STYLES,
)


@pytest.mark.asyncio
async def test_user_get_summary_style_default(async_session):
    """Test that new users have default 'basic' summary style."""
    # Create user without explicit summary_preferences
    user = User(
        telegram_id=123456,
        username="testuser",
        interests=["databases", "python"],
    )
    async_session.add(user)
    await async_session.commit()

    # Get summary style
    style = await get_user_summary_style(async_session, user.id)

    assert style == "basic"


@pytest.mark.asyncio
async def test_user_update_summary_style(async_session):
    """Test updating user's summary style preference."""
    # Create user
    user = User(
        telegram_id=123456,
        username="testuser",
    )
    async_session.add(user)
    await async_session.commit()

    # Update to technical style
    result = await update_user_summary_style(async_session, user.id, "technical")
    assert result is True

    # Verify update
    await async_session.refresh(user)
    assert user.get_summary_style() == "technical"


@pytest.mark.asyncio
async def test_update_summary_style_invalid(async_session):
    """Test that invalid summary style raises ValueError."""
    # Create user
    user = User(
        telegram_id=123456,
        username="testuser",
    )
    async_session.add(user)
    await async_session.commit()

    # Try to update with invalid style
    with pytest.raises(ValueError, match="Invalid summary style"):
        await update_user_summary_style(async_session, user.id, "invalid_style")


@pytest.mark.asyncio
async def test_update_summary_style_nonexistent_user(async_session):
    """Test updating style for non-existent user returns False."""
    result = await update_user_summary_style(async_session, 99999, "technical")
    assert result is False


def test_get_summary_style_info():
    """Test getting style display information."""
    info = get_summary_style_info("technical")

    assert info is not None
    assert info["name"] == "🔧 Technical"
    assert "engineers" in info["target_audience"].lower()
    assert "example" in info


def test_get_all_styles():
    """Test getting all available styles."""
    styles = get_all_styles()

    # Should have all 5 styles
    assert len(styles) == 5
    assert set(styles.keys()) == set(VALID_SUMMARY_STYLES)

    # Each style should have required fields
    for style_key, style_info in styles.items():
        assert "name" in style_info
        assert "description" in style_info
        assert "example" in style_info
        assert "target_audience" in style_info


def test_format_style_for_display():
    """Test formatting style for display in bot messages."""
    # Format without current marker
    formatted = format_style_for_display("basic", current=False)
    assert "📝 Basic" in formatted
    assert "Recommended" in formatted
    assert "Example:" in formatted
    assert "(Current)" not in formatted

    # Format with current marker
    formatted_current = format_style_for_display("technical", current=True)
    assert "🔧 Technical" in formatted_current
    assert "(Current)" in formatted_current


@pytest.mark.asyncio
async def test_user_model_helper_methods(async_session):
    """Test User model helper methods for summary preferences."""
    # Create user with explicit preferences
    user = User(
        telegram_id=123456,
        username="testuser",
        summary_preferences={
            "style": "business",
            "detail_level": "detailed",
            "technical_depth": "advanced",
        },
    )
    async_session.add(user)
    await async_session.commit()

    # Test get_summary_style()
    assert user.get_summary_style() == "business"

    # Test update_summary_preferences()
    user.update_summary_preferences(style="concise", detail_level="brief")
    await async_session.commit()
    await async_session.refresh(user)

    assert user.summary_preferences["style"] == "concise"
    assert user.summary_preferences["detail_level"] == "brief"
    # Should preserve unchanged fields
    assert user.summary_preferences["technical_depth"] == "advanced"


@pytest.mark.asyncio
async def test_backward_compatibility_with_delivery_style(async_session):
    """Test that system falls back to delivery_style if summary_preferences missing."""
    from app.application.use_cases.personalized_summarization import get_prompt_type_for_user

    # Create user with old delivery_style but no summary_preferences
    user = User(
        telegram_id=123456,
        username="testuser",
        delivery_style="brief",
        summary_preferences=None,  # Simulate old user without new field
    )
    async_session.add(user)
    await async_session.commit()

    # Should fallback to delivery_style mapping
    prompt_type = get_prompt_type_for_user(user)
    assert prompt_type == "concise"  # brief maps to concise


@pytest.mark.asyncio
async def test_all_valid_styles_work(async_session):
    """Test that all valid summary styles can be set and retrieved."""
    user = User(
        telegram_id=123456,
        username="testuser",
    )
    async_session.add(user)
    await async_session.commit()

    for style in VALID_SUMMARY_STYLES:
        # Update to this style
        result = await update_user_summary_style(async_session, user.id, style)
        assert result is True

        # Verify it was saved
        await async_session.refresh(user)
        assert user.get_summary_style() == style


@pytest.mark.asyncio
async def test_migration_default_value(async_session):
    """Test that database migration sets correct default."""
    # Create user (migration should set default)
    user = User(
        telegram_id=999999,
        username="migrated_user",
    )
    async_session.add(user)
    await async_session.commit()

    # Refresh to get DB defaults
    await async_session.refresh(user)

    # Should have default summary_preferences from migration
    assert user.summary_preferences is not None
    assert isinstance(user.summary_preferences, dict)
    assert user.summary_preferences.get("style") == "basic"
    assert user.summary_preferences.get("detail_level") == "medium"
    assert user.summary_preferences.get("technical_depth") == "intermediate"
