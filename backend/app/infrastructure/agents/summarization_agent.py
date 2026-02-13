"""Summarization agent for generating article summaries using OpenAI Agents SDK."""

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
    use_structured_output: bool = False,
) -> BaseAgent:
    """Create summarization agent using OpenAI Agents SDK.

    Args:
        prompt_type: Type of prompt (basic, technical, business, concise, personalized)
        model: LLM model to use
        use_structured_output: Return structured output (Pydantic SummaryOutput)

    Returns:
        Configured BaseAgent instance (wraps OpenAI Agents SDK Agent)
    """
    # Create a temporary agent to load the prompt
    temp_agent = BaseAgent(
        name="temp",
        instructions="temp",
        model=model,
    )

    # Load prompt template from markdown file
    try:
        instructions = temp_agent._load_prompt(f"summarizer_{prompt_type}")
    except FileNotFoundError:
        # Fallback to basic if variant not found
        if prompt_type != "basic":
            instructions = temp_agent._load_prompt("summarizer_basic")
        else:
            raise

    # Create agent with proper instructions and optional structured output
    agent = BaseAgent(
        name="SummarizationAgent",
        instructions=instructions,
        model=model,
        temperature=0.3,  # Lower temperature for consistency
        max_tokens=500,  # Reasonable max for 2-3 sentences
        tools=[],  # No tools for basic summarization
        output_type=SummaryOutput if use_structured_output else None,
    )

    return agent


def summarize_post(
    markdown_content: str,
    user_id: Optional[int] = None,
    prompt_type: str = "basic",
    db_session: Optional["AsyncSession"] = None,
    model: str = settings.openai_model,
    use_structured_output: bool = False,
) -> str:
    """Summarize a post using the summarization agent.

    Uses OpenAI Agents SDK for agent-based summarization with Langfuse observability.

    Args:
        markdown_content: Post content in markdown format
        user_id: User ID for token tracking
        prompt_type: Prompt variant to use (basic, technical, business, concise, personalized)
        db_session: Database session for token tracking
        model: LLM model to use (default: gpt-4o-mini)
        use_structured_output: Return structured output with SummaryOutput model

    Returns:
        Summary text or SummaryOutput if use_structured_output=True
    """
    # Create agent using OpenAI Agents SDK
    agent = create_summarization_agent(
        prompt_type=prompt_type,
        model=model,
        use_structured_output=use_structured_output,
    )

    # Wrap with tracking (token counting + Langfuse)
    tracked_agent = TrackedAgent(
        base_agent=agent,
        user_id=user_id,
        db_session=db_session,
        operation="summarize_post",
    )

    # Run agent with markdown content
    result = tracked_agent.run(
        input_text=markdown_content,
        metadata={
            "prompt_type": prompt_type,
            "content_length": len(markdown_content),
            "structured_output": use_structured_output,
        },
    )

    # Extract summary from result
    if use_structured_output and isinstance(result.output, SummaryOutput):
        return result.output.summary
    else:
        return str(result.output)
