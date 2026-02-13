"""OpenAI-based summarization service with map-reduce strategy.

This service implements content summarization using OpenAI Agents.
For long content that exceeds token limits, it uses a map-reduce approach:
1. Map: Split content into chunks and summarize each chunk
2. Reduce: Combine chunk summaries into a final comprehensive summary
"""

import logging
from pathlib import Path
from typing import List, Optional

from agents import Agent, Runner, ModelSettings, WebSearchTool

from backend.app.application.interfaces import SummarizationService
from backend.app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class OpenAISummarizationService(SummarizationService):
    """OpenAI-powered summarization service with map-reduce for long content."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        chunk_size: int = 8000,
        max_length: int = 128_000,
    ):
        """Initialize the OpenAI summarization service.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use
            max_tokens: Maximum tokens for summary output
            temperature: Model temperature (0-1, lower = more focused)
            chunk_size: Character size for content chunks
        """
        api_key = api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key is required for summarization")

        self.model = model
        self.chunk_size = chunk_size

        # Configure model settings
        model_settings = ModelSettings(
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.max_length = max_length

        # Load prompts from markdown files
        prompts_dir = Path(__file__).parent / "prompts"
        summarizer_prompt = (prompts_dir / "summarizer.md").read_text()
        reducer_prompt = (prompts_dir / "reducer.md").read_text()

        # Create summarization agent using OpenAI Agents SDK
        self.summarizer_agent = Agent(
            name="Content Summarizer",
            instructions=summarizer_prompt,
            model=self.model,
            model_settings=model_settings,
            tools=[WebSearchTool()],
        )

        # Create reducer agent for combining chunk summaries
        self.reducer_agent = Agent(
            name="Summary Reducer",
            instructions=reducer_prompt,
            model=self.model,
            model_settings=model_settings,
        )

    def _split_content(self, content: str) -> List[str]:
        """Split content into manageable chunks.

        Args:
            content: Text content to split

        Returns:
            List of content chunks
        """
        if len(content) <= self.chunk_size:
            return [content]

        chunks = []
        words = content.split()
        current_chunk = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks

    async def _summarize_chunk(self, chunk: str, chunk_index: int = 0) -> str:
        """Summarize a single content chunk.

        Args:
            chunk: Content chunk to summarize
            chunk_index: Index of this chunk (for logging)

        Returns:
            Summary of the chunk
        """
        try:
            prompt = f"Summarize the following content, search the web for more information and give your opinions on the article:\n\n{chunk}"

            # Run the agent using Runner.run() - the recommended SDK approach
            result = await Runner.run(self.summarizer_agent, input=prompt)

            summary = result.final_output if result.final_output else ""
            logger.info(f"Successfully summarized chunk {chunk_index}")
            return summary

        except Exception as e:
            logger.error(f"Error summarizing chunk {chunk_index}: {e}")
            raise

    async def _reduce_summaries(self, summaries: List[str]) -> str:
        """Reduce multiple chunk summaries into one final summary.

        Args:
            summaries: List of chunk summaries

        Returns:
            Final combined summary
        """
        if len(summaries) == 1:
            return summaries[0]

        try:
            combined = "\n\n".join(
                f"Part {i+1}:\n{summary}" for i, summary in enumerate(summaries)
            )

            prompt = f"Synthesize these partial summaries into one comprehensive summary:\n\n{combined}"

            # Run the reducer agent using Runner.run() - the recommended SDK approach
            result = await Runner.run(self.reducer_agent, input=prompt)

            final_summary = result.final_output if result.final_output else ""
            logger.info("Successfully reduced summaries into final summary")
            return final_summary

        except Exception as e:
            logger.error(f"Error reducing summaries: {e}")
            raise

    async def summarize(self, content: str) -> str:
        """Generate a summary using map-reduce if needed.

        Args:
            content: Text content to summarize

        Returns:
            Generated summary

        Raises:
            ValueError: If content is empty
            Exception: If summarization fails
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        logger.info(f"Starting summarization for content of length {len(content)}")

        try:
            # Split content into chunks
            chunks = self._split_content(content)

            # Map: Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                summary = await self._summarize_chunk(chunk, i)
                chunk_summaries.append(summary)

            # Reduce: Combine summaries if multiple chunks
            final_summary = await self._reduce_summaries(chunk_summaries)

            logger.info("Summarization completed successfully")
            return final_summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise

    async def summarize_batch(self, contents: List[str]) -> List[str]:
        """Generate summaries for multiple content items concurrently.

        Args:
            contents: List of text contents to summarize

        Returns:
            List of generated summaries in the same order
        """
        import asyncio

        logger.info(f"Starting batch summarization for {len(contents)} items")

        # Process all contents concurrently
        tasks = [self.summarize(content) for content in contents]
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any failures
        results = []
        for i, summary in enumerate(summaries):
            if isinstance(summary, Exception):
                logger.error(f"Failed to summarize item {i}: {summary}")
                results.append(f"[Summarization failed: {str(summary)}]")
            else:
                results.append(summary)

        logger.info(f"Batch summarization completed: {len(results)} items")
        return results
