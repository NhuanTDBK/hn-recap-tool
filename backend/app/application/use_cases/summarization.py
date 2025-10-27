"""Summarization use cases - Business logic for content summarization.

These use cases orchestrate the summarization of post content.
"""

import logging
from typing import List, Optional
from datetime import datetime

from app.domain.entities import Post
from app.application.interfaces import (
    PostRepository,
    SummarizationService,
)

logger = logging.getLogger(__name__)


class SummarizePostsUseCase:
    """Use case for summarizing post content."""

    def __init__(
        self,
        post_repository: PostRepository,
        summarization_service: SummarizationService,
    ):
        """Initialize the use case.

        Args:
            post_repository: Repository for post persistence
            summarization_service: Service for generating summaries
        """
        self.post_repository = post_repository
        self.summarization_service = summarization_service

    async def execute(
        self,
        posts: Optional[List[Post]] = None,
        date: Optional[str] = None,
    ) -> List[Post]:
        """Summarize posts and save updated versions.

        Args:
            posts: Optional list of posts to summarize (if not provided, use date)
            date: Optional date to fetch posts (YYYY-MM-DD format)

        Returns:
            List of posts with summaries

        Raises:
            ValueError: If neither posts nor date is provided
        """
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

        logger.info(f"Starting summarization for {len(posts_to_summarize)} posts")

        # Filter posts that have content but no summary
        posts_needing_summary = [
            post for post in posts_to_summarize
            if post.raw_content and not post.summary
        ]

        if not posts_needing_summary:
            logger.info("All posts already have summaries")
            return posts_to_summarize

        logger.info(f"{len(posts_needing_summary)} posts need summarization")

        # Extract content for batch processing
        contents = [post.raw_content for post in posts_needing_summary]

        # Generate summaries in batch
        try:
            summaries = await self.summarization_service.summarize_batch(contents)

            # Update posts with summaries
            updated_posts = []
            for post, summary in zip(posts_needing_summary, summaries):
                post.summary = summary
                updated_post = await self.post_repository.save(post)
                updated_posts.append(updated_post)
                logger.info(f"Saved summary for post {post.hn_id}")

            logger.info(f"Successfully summarized {len(updated_posts)} posts")
            return updated_posts

        except Exception as e:
            logger.error(f"Error during batch summarization: {e}")
            raise


class SummarizeSinglePostUseCase:
    """Use case for summarizing a single post."""

    def __init__(
        self,
        post_repository: PostRepository,
        summarization_service: SummarizationService,
    ):
        """Initialize the use case.

        Args:
            post_repository: Repository for post persistence
            summarization_service: Service for generating summaries
        """
        self.post_repository = post_repository
        self.summarization_service = summarization_service

    async def execute(self, post_id: str) -> Optional[Post]:
        """Summarize a single post by ID.

        Args:
            post_id: ID of the post to summarize

        Returns:
            Updated post with summary, or None if not found

        Raises:
            ValueError: If post has no content to summarize
        """
        logger.info(f"Fetching post {post_id} for summarization")

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

        # Generate summary
        try:
            logger.info(f"Generating summary for post {post_id}")
            summary = await self.summarization_service.summarize(post.raw_content)

            # Update and save post
            post.summary = summary
            updated_post = await self.post_repository.save(post)

            logger.info(f"Successfully summarized post {post_id}")
            return updated_post

        except Exception as e:
            logger.error(f"Error summarizing post {post_id}: {e}")
            raise
