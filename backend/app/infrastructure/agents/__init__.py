"""Agent infrastructure package for OpenAI Agents SDK integration."""

import os

from agents import set_default_openai_api, set_tracing_disabled

from .config import AgentSettings, settings


def _configure_provider() -> None:
    """Point the OpenAI Agents SDK at Gemini's OpenAI-compatible endpoint.

    Gemini's compat endpoint only supports the chat_completions API (not the
    Responses API) and 401s against OpenAI's tracing platform, so both must
    be set before any Agent is constructed. Mirrors receipt-pal's
    app/services/agent.py::configure_provider().
    """
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    os.environ.setdefault("OPENAI_BASE_URL", settings.openai_base_url)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


_configure_provider()

from .token_tracker import TokenTracker, PRICING
from .base_agent import BaseAgent, TrackedAgent
from .summarization_agent import (
    SummaryOutput,
    create_summarization_agent,
    summarize_post,
)

__all__ = [
    "AgentSettings",
    "settings",
    "TokenTracker",
    "PRICING",
    "BaseAgent",
    "TrackedAgent",
    "SummaryOutput",
    "create_summarization_agent",
    "summarize_post",
]
