"""Summarization agent for generating article summaries."""

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel

from .base_agent import BaseAgent, TrackedAgent
from .config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SummaryOutput(BaseModel):
    """Structured summary output."""

    summary: str
    key_points: List[str] = []
    technical_level: str = "intermediate"  # beginner, intermediate, advanced
    confidence: float = 0.8


def create_summarization_agent(
    prompt_type: str = "basic",
    model: str = settings.openai_model,
) -> BaseAgent:
    """Create summarization agent.

    Args:
        prompt_type: Type of prompt (basic, technical, business, concise, personalized)
        model: LLM model to use

    Returns:
        Configured BaseAgent instance
    """
    agent = BaseAgent(
        name="SummarizationAgent",
        model=model,
        temperature=0.3,  # Lower temperature for consistency
        max_tokens=500,  # Reasonable max for 2-3 sentences
    )

    # Load prompt template (will be stored in prompts directory)
    try:
        agent.prompt_template = agent._load_prompt(f"summarizer_{prompt_type}")
    except FileNotFoundError:
        # Fallback to basic if variant not found
        if prompt_type != "basic":
            agent.prompt_template = agent._load_prompt("summarizer_basic")
        else:
            raise

    return agent


async def summarize_post(
    markdown_content: str,
    user_id: Optional[int] = None,
    prompt_type: str = "basic",
    db_session: Optional["AsyncSession"] = None,
    model: str = settings.openai_model,
) -> str:
    """Summarize a post using the summarization agent.

    Args:
        markdown_content: Post content in markdown format
        user_id: User ID for token tracking
        prompt_type: Prompt variant to use
        db_session: Database session for token tracking
        model: LLM model to use

    Returns:
        Summary text
    """
    # Create agent
    agent = create_summarization_agent(prompt_type=prompt_type, model=model)

    # Wrap with tracking
    tracked_agent = TrackedAgent(
        agent=agent,
        user_id=user_id,
        db_session=db_session,
        operation="summarize_post",
    )

    # Prepare input
    prompt = f"{agent.prompt_template}\n\nContent:\n{markdown_content}"

    # Run agent
    result = await tracked_agent.run(
        input_text=prompt,
        metadata={"prompt_type": prompt_type, "content_length": len(markdown_content)},
    )

    return result
