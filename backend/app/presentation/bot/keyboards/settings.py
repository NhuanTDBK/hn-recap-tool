"""Inline keyboards for settings UI.

This module will contain inline keyboard definitions for settings menus.
To be implemented in Epic 3 - Telegram Bot Foundation.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_settings_menu_keyboard() -> "InlineKeyboardMarkup":
    """Create the main settings menu keyboard.

    Layout:
    ```
    [Change Summary Style] [Pause Deliveries]
    [Memory Settings]
    ```

    Returns:
        InlineKeyboardMarkup with settings buttons
    """
    # TODO: Implement in Epic 3
    # from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    #
    # return InlineKeyboardMarkup(inline_keyboard=[
    #     [
    #         InlineKeyboardButton(text="Change Summary Style", callback_data="settings:summary"),
    #         InlineKeyboardButton(text="Pause Deliveries", callback_data="settings:pause"),
    #     ],
    #     [
    #         InlineKeyboardButton(text="Memory Settings", callback_data="settings:memory"),
    #     ],
    # ])
    pass


def create_summary_style_keyboard(current_style: str = "basic") -> "InlineKeyboardMarkup":
    """Create summary style picker keyboard.

    Shows all 5 styles as buttons, with current style marked.

    Layout:
    ```
    [📝 Basic] [🔧 Technical] [💼 Business]
    [⚡ Concise] [🎯 Personalized]
    ```

    Callback data format: "settings:summary:{style}"

    Args:
        current_style: User's current summary style (to mark as selected)

    Returns:
        InlineKeyboardMarkup with style selection buttons
    """
    # TODO: Implement in Epic 3
    # from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    # from app.application.use_cases.summary_preferences import STYLE_DESCRIPTIONS
    #
    # buttons = []
    # row1 = []
    # row2 = []
    #
    # for style_key, style_info in STYLE_DESCRIPTIONS.items():
    #     # Add checkmark if current style
    #     text = style_info["name"]
    #     if style_key == current_style:
    #         text = f"✓ {text}"
    #
    #     button = InlineKeyboardButton(
    #         text=text,
    #         callback_data=f"settings:summary:{style_key}"
    #     )
    #
    #     # First 3 buttons in row 1, rest in row 2
    #     if len(row1) < 3:
    #         row1.append(button)
    #     else:
    #         row2.append(button)
    #
    # return InlineKeyboardMarkup(inline_keyboard=[row1, row2])
    pass


def create_style_confirmation_keyboard() -> "InlineKeyboardMarkup":
    """Create confirmation keyboard after style selection.

    Layout:
    ```
    [← Back to Settings] [Preview Example]
    ```

    Returns:
        InlineKeyboardMarkup with confirmation buttons
    """
    # TODO: Implement in Epic 3
    # from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    #
    # return InlineKeyboardMarkup(inline_keyboard=[
    #     [
    #         InlineKeyboardButton(text="← Back to Settings", callback_data="settings:main"),
    #         InlineKeyboardButton(text="Preview Example", callback_data="settings:preview"),
    #     ],
    # ])
    pass
