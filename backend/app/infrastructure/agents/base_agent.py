"""Base agent wrapper with Langfuse tracking and token counting."""

import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from openai import OpenAI, AsyncOpenAI

from .config import settings
from .token_tracker import TokenTracker

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base agent class with common functionality."""

    def __init__(
        self,
        name: str,
        model: str = settings.openai_model,
        temperature: float = settings.openai_default_temperature,
        max_tokens: int = settings.openai_default_max_tokens,
    ):
        """Initialize base agent.

        Args:
            name: Agent name
            model: LLM model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
        """
        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=settings.openai_api_key)

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
    """Agent wrapper with Langfuse tracking and token counting."""

    def __init__(
        self,
        agent: BaseAgent,
        user_id: Optional[int] = None,
        db_session: Optional["AsyncSession"] = None,
        operation: Optional[str] = None,
    ):
        """Initialize tracked agent.

        Args:
            agent: Base agent instance
            user_id: User ID for tracking
            db_session: Database session for token tracking
            operation: Operation name (e.g., 'summarize_post')
        """
        self.agent = agent
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

    async def run(
        self, input_text: str, metadata: Optional[dict] = None
    ) -> Any:
        """Run agent with tracking.

        Args:
            input_text: Input text for the agent
            metadata: Additional metadata for tracing

        Returns:
            Agent result
        """
        trace = None
        generation = None
        start_time = time.time()

        try:
            # Start Langfuse trace
            if self.langfuse:
                trace = self.langfuse.trace(
                    name=f"agent_{self.agent.name}",
                    user_id=str(self.user_id) if self.user_id else None,
                    metadata={
                        **(metadata or {}),
                        "operation": self.operation,
                        "agent_name": self.agent.name,
                        "model": self.agent.model,
                    },
                )
                generation = trace.generation(
                    name="agent_execution",
                    model=self.agent.model,
                    input=input_text,
                    temperature=self.agent.temperature,
                    max_tokens=self.agent.max_tokens,
                )

            # Run agent (basic completion for now)
            response = self.agent.client.chat.completions.create(
                model=self.agent.model,
                messages=[{"role": "user", "content": input_text}],
                temperature=self.agent.temperature,
                max_tokens=self.agent.max_tokens,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            result_text = response.choices[0].message.content

            # Update Langfuse
            if generation:
                generation.end(
                    output=result_text,
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    },
                )

            # Track tokens
            if self.token_tracker and self.user_id:
                await self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.agent.name,
                    model=self.agent.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    latency_ms=latency_ms,
                    status="success",
                )

            logger.info(
                f"Agent {self.agent.name} completed: "
                f"{input_tokens} input + {output_tokens} output tokens, "
                f"{latency_ms}ms latency"
            )

            return result_text

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Track error
            if self.token_tracker and self.user_id:
                await self.token_tracker.track_usage(
                    user_id=self.user_id,
                    agent_name=self.agent.name,
                    model=self.agent.model,
                    input_tokens=0,
                    output_tokens=0,
                    trace_id=trace.id if trace else None,
                    operation=self.operation,
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(e),
                )

            logger.error(f"Agent {self.agent.name} failed: {e}")
            raise
