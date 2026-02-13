"""Enhanced Summarization Use Cases using OpenAI Agents SDK.

These use cases orchestrate the summarization of post content using the new
OpenAI Agents SDK with Langfuse observability and token tracking.
"""

import logging
from typing import List, Optional

from app.domain.entities import Post
from app.application.interfaces import PostRepository

logger = logging.getLogger(__name__)


class AgentSummarizePostsUseCase:
    """Use case for summarizing post content using OpenAI Agents SDK."""

    def __init__(
        self,
        post_repository: PostRepository,
        user_id: Optional[int] = None,
        db_session=None,
        prompt_type: str = "basic",
    ):
        """Initialize the agent-based summarization use case.

        Args:
            post_repository: Repository for post persistence
            user_id: User ID for token tracking
            db_session: Database session for token tracking
            prompt_type: Prompt variant to use (basic, technical, business, concise, personalized)
        """
        self.post_repository = post_repository
        self.user_id = user_id
        self.db_session = db_session
        self.prompt_type = prompt_type

    async def execute(
        self,
        posts: Optional[List[Post]] = None,
        date: Optional[str] = None,
    ) -> List[dict]:
        """Summarize posts using OpenAI Agents SDK and save to summaries table.

        Args:
            posts: Optional list of posts to summarize (if not provided, use date)
            date: Optional date to fetch posts (YYYY-MM-DD format)

        Returns:
            List of summary dictionaries with post_id, user_id, summary_text, etc.

        Raises:
            ValueError: If neither posts nor date is provided
        """
        from backend.app.infrastructure.agents.summarization_agent import (
            summarize_post,
        )
        from backend.app.infrastructure.database.models import Summary

        # Get posts to summarize
        if posts is None and date is None:
            raise ValueError("Either posts or date must be provided")

        posts_to_summarize = posts if posts is not None else []

        if date is not None:
            logger.info(f"Fetching posts for date: {date}")
            posts_to_summarize = await self.post_repository.find_by_date(date)

        if not posts_to_summarize:
            logger.warning("No posts found to summarize")
            return []

        logger.info(
            f"Starting agent-based summarization for {len(posts_to_summarize)} posts"
        )

        # Generate summaries using agent system
        try:
            summaries_created = []

            for post in posts_to_summarize:
                if not post.raw_content:
                    logger.warning(f"Post {post.hn_id} has no content, skipping")
                    continue

                logger.info(f"Generating {self.prompt_type} summary for post {post.hn_id}")

                # Use agent to generate summary
                summary_text = summarize_post(
                    markdown_content=post.raw_content,
                    user_id=self.user_id,
                    prompt_type=self.prompt_type,
                    db_session=self.db_session,
                )

                # Create summary record in summaries table
                summary = Summary(
                    post_id=post.id,
                    user_id=self.user_id,
                    prompt_type=self.prompt_type,
                    summary_text=summary_text,
                    token_count=None,  # Could track this from agent response
                    cost_usd=None,  # Could track this from agent response
                )

                if self.db_session:
                    self.db_session.add(summary)
                    await self.db_session.commit()

                summaries_created.append({
                    "post_id": post.id,
                    "user_id": self.user_id,
                    "prompt_type": self.prompt_type,
                    "summary_text": summary_text,
                    "post_hn_id": post.hn_id,
                })

                logger.info(f"✓ Saved {self.prompt_type} summary for post {post.hn_id}")

            logger.info(f"Successfully created {len(summaries_created)} summaries")
            return summaries_created

        except Exception as e:
            logger.error(f"Error during agent-based summarization: {e}")
            raise


class AgentSummarizeSinglePostUseCase:
    """Use case for summarizing a single post using OpenAI Agents SDK."""

    def __init__(
        self,
        post_repository: PostRepository,
        user_id: Optional[int] = None,
        db_session=None,
        prompt_type: str = "basic",
    ):
        """Initialize the agent-based single post summarization use case.

        Args:
            post_repository: Repository for post persistence
            user_id: User ID for token tracking
            db_session: Database session for token tracking
            prompt_type: Prompt variant to use
        """
        self.post_repository = post_repository
        self.user_id = user_id
        self.db_session = db_session
        self.prompt_type = prompt_type

    async def execute(
        self, post_id: str, use_structured_output: bool = False
    ) -> Optional[dict]:
        """Summarize a single post using OpenAI Agents SDK and save to summaries table.

        Args:
            post_id: ID of the post to summarize
            use_structured_output: Return structured output (SummaryOutput Pydantic model)

        Returns:
            Summary dictionary with post_id, user_id, summary_text, etc., or None if not found

        Raises:
            ValueError: If post has no content to summarize
        """
        from backend.app.infrastructure.agents.summarization_agent import (
            summarize_post,
        )
        from backend.app.infrastructure.database.models import Summary

        logger.info(f"Fetching post {post_id} for agent-based summarization")

        # Fetch the post
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            logger.warning(f"Post {post_id} not found")
            return None

        # Check if post has content
        if not post.raw_content:
            raise ValueError(f"Post {post_id} has no content to summarize")

        # Generate summary using agent
        try:
            logger.info(f"Generating {self.prompt_type} summary for post {post_id}")

            summary_text = summarize_post(
                markdown_content=post.raw_content,
                user_id=self.user_id,
                prompt_type=self.prompt_type,
                db_session=self.db_session,
                use_structured_output=use_structured_output,
            )

            # Extract text if structured output
            if not isinstance(summary_text, str):
                summary_text = summary_text.summary

            # Create summary record in summaries table
            summary = Summary(
                post_id=post.id,
                user_id=self.user_id,
                prompt_type=self.prompt_type,
                summary_text=summary_text,
                token_count=None,  # Could track this from agent response
                cost_usd=None,  # Could track this from agent response
            )

            if self.db_session:
                self.db_session.add(summary)
                await self.db_session.commit()

            logger.info(f"✓ Successfully created {self.prompt_type} summary for post {post_id}")

            return {
                "post_id": post.id,
                "user_id": self.user_id,
                "prompt_type": self.prompt_type,
                "summary_text": summary_text,
            }

        except Exception as e:
            logger.error(f"Error summarizing post {post_id}: {e}")
            raise
