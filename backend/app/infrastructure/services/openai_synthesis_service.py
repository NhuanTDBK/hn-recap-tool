"""OpenAI-based synthesis summarization service.

This service generates synthesized summaries from multiple posts,
identifying common themes, patterns, and connections across articles.
"""

import logging
from pathlib import Path
from typing import List, Optional

from agents import Agent, Runner, ModelSettings

from app.application.interfaces import SynthesisSummarizationService
from app.domain.entities import Post
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class OpenAISynthesisService(SynthesisSummarizationService):
    """OpenAI-powered synthesis service for multi-post summarization."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 1000,
        temperature: float = 0.5,
    ):
        """Initialize the OpenAI synthesis service.

        Args:
            api_key: OpenAI API key (defaults to settings)
            model: OpenAI model to use
            max_tokens: Maximum tokens for synthesis output
            temperature: Model temperature (0-1, higher = more creative)
        """
        api_key = api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key is required for synthesis")

        self.model = model

        # Configure model settings
        model_settings = ModelSettings(
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Load prompts from markdown files
        prompts_dir = Path(__file__).parent / "prompts"
        synthesis_prompt = (prompts_dir / "synthesis.md").read_text()
        synthesis_topic_prompt = (prompts_dir / "synthesis_topic.md").read_text()

        # Create synthesis agent using OpenAI Agents SDK
        self.synthesis_agent = Agent(
            name="Content Synthesizer",
            instructions=synthesis_prompt,
            model=self.model,
            model_settings=model_settings,
        )

        # Create topic-focused synthesis agent
        self.topic_synthesis_agent = Agent(
            name="Topic-Focused Synthesizer",
            instructions=synthesis_topic_prompt,
            model=self.model,
            model_settings=model_settings,
        )

    def _format_posts_for_synthesis(self, posts: List[Post]) -> str:
        """Format posts into a structured text for synthesis.

        Args:
            posts: List of Post entities

        Returns:
            Formatted text with all post information
        """
        formatted = []
        for i, post in enumerate(posts, 1):
            formatted.append(f"=== Article {i}: {post.title} ===")
            formatted.append(f"URL: {post.url or 'N/A'}")
            formatted.append(f"Points: {post.points} | Comments: {post.num_comments}")

            if post.content:
                formatted.append(f"\nContent:\n{post.content}\n")
            else:
                formatted.append("\n[No content available]\n")

            formatted.append("-" * 80)

        return "\n".join(formatted)

    def _format_summaries_for_synthesis(self, summaries: List[dict]) -> str:
        """Format individual summaries into structured text.

        Args:
            summaries: List of dicts with 'title', 'summary', and optional 'url'

        Returns:
            Formatted text with all summaries
        """
        formatted = []
        for i, item in enumerate(summaries, 1):
            title = item.get("title", "Untitled")
            summary = item.get("summary", "")
            url = item.get("url", "")

            formatted.append(f"=== Article {i}: {title} ===")
            if url:
                formatted.append(f"URL: {url}")
            formatted.append(f"\nSummary:\n{summary}\n")
            formatted.append("-" * 80)

        return "\n".join(formatted)

    async def synthesize(self, posts: List[Post]) -> str:
        """Generate a synthesis summary from multiple posts.

        Args:
            posts: List of Post entities to synthesize

        Returns:
            Synthesized summary combining insights from all posts

        Raises:
            ValueError: If posts list is empty
            Exception: If synthesis fails
        """
        if not posts:
            raise ValueError("Cannot synthesize from empty posts list")

        logger.info(f"Starting synthesis of {len(posts)} posts")

        try:
            # Format posts for synthesis
            formatted_content = self._format_posts_for_synthesis(posts)

            # Create synthesis prompt
            prompt = (
                f"Synthesize insights from these {len(posts)} HackerNews articles:\n\n"
                f"{formatted_content}"
            )

            # Run the synthesis agent
            result = await Runner.run(
                self.synthesis_agent,
                input=prompt
            )

            synthesis = result.final_output if result.final_output else ""
            logger.info(f"Successfully synthesized {len(posts)} posts")
            return synthesis

        except Exception as e:
            logger.error(f"Error synthesizing posts: {e}")
            raise

    async def synthesize_by_topic(self, posts: List[Post], topic: str) -> str:
        """Generate a topic-focused synthesis from multiple posts.

        Args:
            posts: List of Post entities to synthesize
            topic: Topic or theme to focus on

        Returns:
            Topic-focused synthesized summary

        Raises:
            ValueError: If posts list is empty or topic is empty
            Exception: If synthesis fails
        """
        if not posts:
            raise ValueError("Cannot synthesize from empty posts list")

        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")

        logger.info(f"Starting topic-focused synthesis of {len(posts)} posts on: {topic}")

        try:
            # Format posts for synthesis
            formatted_content = self._format_posts_for_synthesis(posts)

            # Create topic-focused synthesis prompt
            prompt = (
                f"Topic: {topic}\n\n"
                f"Synthesize insights about '{topic}' from these {len(posts)} articles:\n\n"
                f"{formatted_content}"
            )

            # Run the topic synthesis agent
            result = await Runner.run(
                self.topic_synthesis_agent,
                input=prompt
            )

            synthesis = result.final_output if result.final_output else ""
            logger.info(f"Successfully synthesized {len(posts)} posts on topic: {topic}")
            return synthesis

        except Exception as e:
            logger.error(f"Error synthesizing posts by topic '{topic}': {e}")
            raise

    async def synthesize_from_summaries(self, summaries: List[dict]) -> str:
        """Generate a synthesis from individual post summaries.

        Args:
            summaries: List of dicts with 'title', 'summary', and optional 'url'

        Returns:
            Synthesized summary combining all individual summaries

        Raises:
            ValueError: If summaries list is empty
            Exception: If synthesis fails
        """
        if not summaries:
            raise ValueError("Cannot synthesize from empty summaries list")

        logger.info(f"Starting synthesis from {len(summaries)} summaries")

        try:
            # Format summaries for synthesis
            formatted_content = self._format_summaries_for_synthesis(summaries)

            # Create synthesis prompt
            prompt = (
                f"Synthesize insights from these {len(summaries)} article summaries:\n\n"
                f"{formatted_content}"
            )

            # Run the synthesis agent
            result = await Runner.run(
                self.synthesis_agent,
                input=prompt
            )

            synthesis = result.final_output if result.final_output else ""
            logger.info(f"Successfully synthesized {len(summaries)} summaries")
            return synthesis

        except Exception as e:
            logger.error(f"Error synthesizing summaries: {e}")
            raise
