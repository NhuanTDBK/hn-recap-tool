"""Base agent wrapper with Langfuse tracking and token counting."""

import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from agents import Agent

from .config import settings
from .token_tracker import TokenTracker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base agent class using OpenAI Agents SDK."""

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = settings.openai_model,
        temperature: float = settings.openai_default_temperature,
        max_tokens: int = settings.openai_default_max_tokens,
        tools: Optional[list] = None,
        output_type: Optional[Any] = None,
    ):
        """Initialize base agent using OpenAI Agents SDK.

        Args:
            name: Agent name
            instructions: Agent system instructions
            model: LLM model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
            tools: List of agent tools (optional)
            output_type: Pydantic model for structured output (optional)
        """
        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.instructions = instructions

        # Create agent using OpenAI Agents SDK
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools or [],
            output_type=output_type,
        )

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt from markdown file.

        Args:
            prompt_file: Path to prompt file (relative to prompts directory)

        Returns:
            Prompt text
        """
        from pathlib import Path

        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_path = prompts_dir / f"{prompt_file}.md"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")


class TrackedAgent:
    """Agent wrapper with Langfuse tracking and token counting using OpenAI Agents SDK."""

    def __init__(
        self,
        base_agent: BaseAgent,
        user_id: Optional[int] = None,
        db_session: Optional["AsyncSession"] = None,
        operation: Optional[str] = None,
    ):
        """Initialize tracked agent.

        Args:
            base_agent: BaseAgent instance (has OpenAI Agents SDK Agent)
            user_id: User ID for tracking
            db_session: Database session for token tracking
            operation: Operation name (e.g., 'summarize_post')
        """
        self.base_agent = base_agent
        self.agent = base_agent.agent  # The OpenAI Agents SDK Agent
        self.user_id = user_id
        self.operation = operation
        self.db = db_session

        # Initialize token tracking
        self.token_tracker = TokenTracker(db_session) if db_session else None

        # Initialize Langfuse if configured
        self.langfuse = None
        if settings.langfuse_enabled and settings.langfuse_public_key:
            try:
                from langfuse import Langfuse

                self.langfuse = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.langfuse = None

    def run(self, input_text: str, metadata: Optional[dict] = None) -> Any:
        """Run agent with tracking using OpenAI Agents SDK.

        Args:
            input_text: Input text for the agent
            metadata: Additional metadata for tracing

        Returns:
            Agent result (from agent.run())
        """
        trace = None
        generation = None
        start_time = time.time()

        try:
            # Start Langfuse trace
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"agent_{self.base_agent.name}",
                    user_id=str(self.user_id) if self.user_id else None,
                    metadata={
                        **(metadata or {}),
                        "operation": self.operation,
                        "agent_name": self.base_agent.name,
                        "model": self.base_agent.model,
                    },
                )
                generation = trace.generation(
                    name="agent_execution",
                    model=self.base_agent.model,
                    input=input_text,
                    temperature=self.base_agent.temperature,
                    max_tokens=self.base_agent.max_tokens,
                )

            # Run agent using OpenAI Agents SDK
            result = self.agent.run(input_text)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage from agent result
            # The agent.run() returns a result with usage information
            input_tokens = getattr(result.usage, "input_tokens", 0)
            output_tokens = getattr(result.usage, "output_tokens", 0)
            output_content = getattr(result, "output", str(result))

            # Update Langfuse
            if generation:
                generation.end(
                    output=str(output_content),
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    },
                )

            # Track tokens
            if self.token_tracker and self.user_id:
                self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.base_agent.name,
                    model=self.base_agent.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    latency_ms=latency_ms,
                    status="success",
                )

            logger.info(
                f"Agent {self.base_agent.name} completed: "
                f"{input_tokens} input + {output_tokens} output tokens, "
                f"{latency_ms}ms latency"
            )

            return result

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Track error
            if self.token_tracker and self.user_id:
                self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.base_agent.name,
                    model=self.base_agent.model,
                    input_tokens=0,
                    output_tokens=0,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(e),
                )

            logger.error(f"Agent {self.base_agent.name} failed: {e}")
            raise
