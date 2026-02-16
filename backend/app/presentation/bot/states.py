"""FSM states for the Telegram bot.

Defines conversation states for state machine routing:
- IDLE: Default state (waiting for commands/digest)
- DISCUSSION: Active discussion about a post
- ONBOARDING: First-time user setup
- SETTINGS: Configuring user preferences
"""

from aiogram.fsm.state import State, StatesGroup


class BotStates(StatesGroup):
    """Bot conversation states."""

    IDLE = State()
    """Default state: waiting for commands or digest delivery."""

    DISCUSSION = State()
    """Active discussion about a specific post."""

    ONBOARDING = State()
    """First-time user setup (interest selection)."""

    SETTINGS = State()
    """User is configuring preferences."""


# State data structure examples:
#
# IDLE state data:
# {}  # No extra data
#
# DISCUSSION state data:
# {
#     "active_post_id": "uuid",
#     "discussion_started_at": "2026-02-15T10:00:00Z",
#     "last_message_at": "2026-02-15T10:15:22Z"
# }
#
# ONBOARDING state data:
# {
#     "step": "interests",  # or "delivery_style"
#     "selected_interests": ["python", "llm"]
# }
#
# SETTINGS state data:
# {
#     "editing": "delivery_style"  # or "interests"
# }
