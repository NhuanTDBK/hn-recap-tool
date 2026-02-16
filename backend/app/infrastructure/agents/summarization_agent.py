"""Summarization agent for generating article summaries using OpenAI Agents SDK."""

from typing import TYPE_CHECKING, Dict, List, Optional

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


def load_prompt_content(prompt_name: str) -> str:
    """Load prompt content from markdown file.

    Args:
        prompt_name: Name of the prompt file (without extension)

    Returns:
        Content of the prompt file
    """
    # Create a temporary agent to use the _load_prompt method
    temp_agent = BaseAgent(
        name="temp",
        instructions="temp",
        model=settings.openai_model,
    )
    return temp_agent._load_prompt(prompt_name)


def create_summarization_agent(
    prompt_type: str = "basic",
    model: str = settings.openai_model,
    use_structured_output: bool = False,
    user_context: Optional[Dict[str, str]] = None,
) -> BaseAgent:
    """Create summarization agent using two-part prompt structure with caching.

    The agent uses a two-part prompt structure optimized for prompt caching:
    1. Base system prompt (1200+ tokens, cacheable) - shared across all types
    2. Type-specific instructions (small delta) - varies by prompt_type
    3. Dynamic content (article) - always at the end

    Args:
        prompt_type: Type of prompt (basic, technical, business, concise, personalized)
        model: LLM model to use
        use_structured_output: Return structured output (Pydantic SummaryOutput)
        user_context: Optional dict with 'user_topics' and 'user_style' for personalized prompts

    Returns:
        Configured BaseAgent instance with cacheable instructions
    """
    # Load base system prompt (cacheable, 1200+ tokens)
    base_system_prompt = load_prompt_content("summarizer_system_base")

    # Load type-specific instructions (small delta)
    try:
        type_specific_instructions = load_prompt_content(f"summarizer_{prompt_type}")
    except FileNotFoundError:
        # Fallback to basic if variant not found
        if prompt_type != "basic":
            type_specific_instructions = load_prompt_content("summarizer_basic")
        else:
            raise

    # For personalized prompts, inject user context
    if prompt_type == "personalized" and user_context:
        user_topics = user_context.get("user_topics", "Not specified")
        user_style = user_context.get("user_style", "Standard")
        type_specific_instructions = type_specific_instructions.replace(
            "{user_topics}", user_topics
        ).replace(
            "{user_style}", user_style
        )

    # Combine: base (cacheable) + type-specific (small)
    # Article content will be added by the caller as user message
    full_instructions = f"{base_system_prompt}\n\n{type_specific_instructions}"

    # Create agent with combined instructions
    agent = BaseAgent(
        name="SummarizationAgent",
        instructions=full_instructions,
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
