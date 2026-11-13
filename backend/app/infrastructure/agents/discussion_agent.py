"""Discussion agent for conversational HackerNews research.

Uses OpenAI Agents SDK with tools for reading batch content,
writing intermediate results, and reading back saved analyses.
"""

import logging
from typing import TYPE_CHECKING

from agents import Agent, ModelSettings, Runner

from .base_agent import BaseAgent
from .config import settings
from .tools import (
    create_batch_content_reader,
    create_file_reader,
    create_file_writer,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


def load_prompt_content(prompt_name: str) -> str:
    """Load prompt content from markdown file.

    Args:
        prompt_name: Name of the prompt file (without extension).

    Returns:
        Content of the prompt file.
    """
    temp_agent = BaseAgent(
        name="temp",
        instructions="temp",
        model=settings.openai_model,
    )
    return temp_agent._load_prompt(prompt_name)


def create_discussion_agent(
    session: "AsyncSession",
    content_store: "RocksDBContentStore",
    model: str = settings.openai_model,
) -> Agent:
    """Create a discussion agent with tools for HN research.

    Args:
        session: Async database session for PostgreSQL queries.
        content_store: RocksDB store for reading markdown content.
        model: LLM model to use (default from settings).

    Returns:
        Configured openai-agents SDK Agent with tools attached.
    """
    system_prompt = load_prompt_content("discussion_system")

    system_prompt = system_prompt.replace(
        "{context_window_tokens}", str(settings.context_window_tokens)
    )

    tools = [
        create_batch_content_reader(session, content_store),
        create_file_writer(),
        create_file_reader(),
    ]

    agent = Agent(
        name="DiscussionAgent",
        instructions=system_prompt,
        model=model,
        model_settings=ModelSettings(temperature=0.7),
        tools=tools,
    )

    logger.info(
        f"Created DiscussionAgent (model={model}, "
        f"context_window={settings.context_window_tokens} tokens)"
    )
    return agent


async def discuss(
    question: str,
    session: "AsyncSession",
    content_store: "RocksDBContentStore",
    conversation_history: list[dict] | None = None,
    model: str = settings.openai_model,
) -> str:
    """Run the discussion agent to answer a question about HackerNews.

    Uses Runner.run() for async execution with tool support.

    Args:
        question: The user's question or message.
        session: Async database session.
        content_store: RocksDB content store.
        conversation_history: Previous messages for multi-turn context.
        model: LLM model to use.

    Returns:
        The agent's response text.
    """
    agent = create_discussion_agent(
        session=session,
        content_store=content_store,
        model=model,
    )

    if conversation_history:
        formatted = []
        for msg in conversation_history[-20:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"[{role}]: {content}")

        history_text = "\n".join(formatted)
        input_text = f"Previous conversation:\n{history_text}\n\n[user]: {question}"
    else:
        input_text = question

    logger.info(
        f"Discussion: question='{question[:80]}...', "
        f"history_messages={len(conversation_history or [])}"
    )

    run_result = await Runner.run(agent, input=input_text)

    response = str(run_result.final_output)

    input_tokens = 0
    output_tokens = 0
    for r in run_result.raw_responses:
        if hasattr(r, "usage"):
            input_tokens += getattr(r.usage, "input_tokens", 0)
            output_tokens += getattr(r.usage, "output_tokens", 0)

    logger.info(
        f"Discussion complete: {input_tokens} input + {output_tokens} output tokens"
    )

    return response
