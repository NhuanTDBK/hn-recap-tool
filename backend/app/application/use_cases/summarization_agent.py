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
    ) -> List[Post]:
        """Summarize posts using OpenAI Agents SDK and save updated versions.

        Args:
            posts: Optional list of posts to summarize (if not provided, use date)
            date: Optional date to fetch posts (YYYY-MM-DD format)

        Returns:
            List of posts with summaries

        Raises:
            ValueError: If neither posts nor date is provided
        """
        from backend.app.infrastructure.agents.summarization_agent import (
            summarize_post,
        )

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

        # Filter posts that have content but no summary
        posts_needing_summary = [
            post for post in posts_to_summarize
            if post.raw_content and not post.summary
        ]

        if not posts_needing_summary:
            logger.info("All posts already have summaries")
            return posts_to_summarize

        logger.info(f"{len(posts_needing_summary)} posts need summarization")

        # Generate summaries using agent system
        try:
            updated_posts = []

            for post in posts_needing_summary:
                logger.info(f"Generating summary for post {post.hn_id}")

                # Use agent to generate summary
                summary = summarize_post(
                    markdown_content=post.raw_content,
                    user_id=self.user_id,
                    prompt_type=self.prompt_type,
                    db_session=self.db_session,
                )

                # Update and save post
                post.summary = summary
                post.summarized_at = None  # Will be set by database
                updated_post = await self.post_repository.save(post)
                updated_posts.append(updated_post)

                logger.info(f"✓ Saved summary for post {post.hn_id}")

            logger.info(f"Successfully summarized {len(updated_posts)} posts")
            return updated_posts

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
    ) -> Optional[Post]:
        """Summarize a single post using OpenAI Agents SDK.

        Args:
            post_id: ID of the post to summarize
            use_structured_output: Return structured output (SummaryOutput Pydantic model)

        Returns:
            Updated post with summary, or None if not found

        Raises:
            ValueError: If post has no content to summarize
        """
        from backend.app.infrastructure.agents.summarization_agent import (
            summarize_post,
        )

        logger.info(f"Fetching post {post_id} for agent-based summarization")

        # Fetch the post
        post = await self.post_repository.find_by_id(post_id)
        if not post:
            logger.warning(f"Post {post_id} not found")
            return None

        # Check if post has content
        if not post.raw_content:
            raise ValueError(f"Post {post_id} has no content to summarize")

        # Check if already summarized
        if post.summary:
            logger.info(f"Post {post_id} already has a summary")
            return post

        # Generate summary using agent
        try:
            logger.info(f"Generating agent-based summary for post {post_id}")

            summary = summarize_post(
                markdown_content=post.raw_content,
                user_id=self.user_id,
                prompt_type=self.prompt_type,
                db_session=self.db_session,
                use_structured_output=use_structured_output,
            )

            # Update and save post
            post.summary = (
                summary
                if isinstance(summary, str)
                else summary.summary
            )
            updated_post = await self.post_repository.save(post)

            logger.info(f"✓ Successfully summarized post {post_id}")
            return updated_post

        except Exception as e:
            logger.error(f"Error summarizing post {post_id}: {e}")
            raise
