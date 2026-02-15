"""Summary preferences management use case.

This module provides functions for managing user summary style preferences.
Supports 5 styles: basic, technical, business, concise, personalized.
"""

import logging
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.database.models import User

logger = logging.getLogger(__name__)

# Valid summary styles
VALID_SUMMARY_STYLES = ["basic", "technical", "business", "concise", "personalized"]

# Style descriptions for UI
STYLE_DESCRIPTIONS = {
    "basic": {
        "name": "📝 Basic",
        "tagline": "Recommended",
        "description": "Balanced summaries for all content types",
        "example": "PostgreSQL 16 brings 2x performance improvements...",
        "target_audience": "General tech professionals",
    },
    "technical": {
        "name": "🔧 Technical",
        "tagline": "For Engineers",
        "description": "Deep technical details, architecture, benchmarks",
        "example": "Parallel query execution supports Memoize nodes...",
        "target_audience": "Senior engineers, architects, specialists",
    },
    "business": {
        "name": "💼 Business",
        "tagline": "For Leaders",
        "description": "Market impact, strategy, ROI focus",
        "example": "Performance gains eliminate objections to open-source...",
        "target_audience": "CTOs, engineering managers, product leaders",
    },
    "concise": {
        "name": "⚡ Concise",
        "tagline": "Quick Scan",
        "description": "Ultra-brief, one sentence only",
        "example": "PostgreSQL 16 doubles query performance...",
        "target_audience": "Time-constrained readers",
    },
    "personalized": {
        "name": "🎯 Personalized",
        "tagline": "Adaptive",
        "description": "Adapts to your interests and past discussions",
        "example": "Logical replication enables event-driven architectures...",
        "target_audience": "Individual users with conversation history",
    },
}


async def get_user_summary_style(
    session: AsyncSession,
    user_id: int
) -> str:
    """Get user's current summary style preference.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        Summary style string (basic, technical, business, concise, personalized)
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return "basic"

    return user.get_summary_style()


async def update_user_summary_style(
    session: AsyncSession,
    user_id: int,
    style: str
) -> bool:
    """Update user's summary style preference.

    Args:
        session: Database session
        user_id: User ID
        style: New summary style (basic, technical, business, concise, personalized)

    Returns:
        True if update successful, False otherwise

    Raises:
        ValueError: If style is not valid
    """
    # Validate style
    if style not in VALID_SUMMARY_STYLES:
        raise ValueError(
            f"Invalid summary style: {style}. "
            f"Must be one of: {', '.join(VALID_SUMMARY_STYLES)}"
        )

    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User {user_id} not found")
        return False

    # Update preferences
    user.update_summary_preferences(style=style)

    # Commit changes
    await session.commit()

    logger.info(f"Updated user {user_id} summary style to: {style}")

    return True


def get_summary_style_info(style: str) -> Optional[Dict[str, str]]:
    """Get display information for a summary style.

    Args:
        style: Summary style key

    Returns:
        Dictionary with style display information, or None if invalid
    """
    return STYLE_DESCRIPTIONS.get(style)


def get_all_styles() -> Dict[str, Dict[str, str]]:
    """Get all available summary styles with their descriptions.

    Returns:
        Dictionary mapping style key to style information
    """
    return STYLE_DESCRIPTIONS


def format_style_for_display(style: str, current: bool = False) -> str:
    """Format a style for display in bot messages.

    Args:
        style: Style key
        current: Whether this is the user's current style

    Returns:
        Formatted string for display
    """
    info = STYLE_DESCRIPTIONS.get(style)
    if not info:
        return style

    current_marker = " (Current)" if current else ""
    return (
        f"{info['name']}{current_marker} - {info['tagline']}\n"
        f"{info['description']}\n"
        f"Example: \"{info['example']}\""
    )
