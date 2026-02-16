"""DEPRECATED: Grouped delivery use case - batch summarization by delivery style.

⚠️ WARNING: This module is DEPRECATED and should NOT be used.

REASON FOR DEPRECATION:
This module contains batch summarization logic within the delivery layer, which
violates the separation of concerns principle. Summarization should happen in
a separate phase before delivery.

RECOMMENDED ALTERNATIVE:
Use the two-phase approach:
1. Summarization: scripts/run_personalized_summarization.py
2. Delivery: scripts/deliver_summaries.py

The summarization phase already handles batch processing and personalization,
making this module redundant.

See DELIVERY_ARCHITECTURE.md for the recommended architecture.
"""

import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)

# Map delivery_style to prompt_type for summarization
STYLE_TO_PROMPT_TYPE = {
    "flat_scroll": "basic",     # Detailed summaries for detailed delivery style
    "brief": "concise",          # Ultra-concise summaries for brief delivery style
}


class GroupedDeliveryUseCase:
    """Optimized delivery with batch summarization by style.

    Key optimization: Summarize posts once per delivery_style, then reuse
    summaries for all users in that style group.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        content_store: RocksDBContentStore,
    ):
        """Initialize use case.

        Args:
            db_session: Async database session
            content_store: RocksDB store for post content
        """
        self.db_session = db_session
        self.content_store = content_store

    async def batch_summarize_for_style(
        self,
        posts: List[Post],
        style: str,
        batch_size: int = 10
    ) -> Dict:
        """Batch summarize all unsummarized posts using style-specific prompt.

        Args:
            posts: List of posts to summarize
            style: Delivery style (flat_scroll, brief, etc.)
            batch_size: Number of posts per LLM call (default: 10)

        Returns:
            Statistics dict:
            {
                "total_posts": 20,
                "summarized": 18,
                "failed": 2,
                "tokens_used": 5000,
                "cost": 0.0004,
                "duration_seconds": 8.5,
                "prompt_type": "basic"
            }

        Example:
            >>> use_case = GroupedDeliveryUseCase(session, store)
            >>> stats = await use_case.batch_summarize_for_style(
            ...     posts=posts,
            ...     style="flat_scroll",
            ...     batch_size=10
            ... )
            >>> print(f"Summarized {stats['summarized']}/{stats['total_posts']} posts")
        """
        start_time = datetime.utcnow()

        # Map delivery_style to prompt_type
        prompt_type = STYLE_TO_PROMPT_TYPE.get(style, "basic")

        logger.info(
            f"Starting batch summarization for style='{style}' "
            f"(prompt_type='{prompt_type}', batch_size={batch_size})"
        )

        # Filter posts needing summaries
        unsummarized = [p for p in posts if not p.summary]

        if not unsummarized:
            logger.info(
                f"All {len(posts)} posts already have summaries for style '{style}'"
            )
            return {
                "total_posts": 0,
                "summarized": 0,
                "failed": 0,
                "tokens_used": 0,
                "cost": 0.0,
                "duration_seconds": 0.0,
                "prompt_type": prompt_type,
            }

        logger.info(
            f"Found {len(unsummarized)} posts needing summaries "
            f"(out of {len(posts)} total)"
        )

        stats = {
            "total_posts": len(unsummarized),
            "summarized": 0,
            "failed": 0,
            "tokens_used": 0,
            "cost": 0.0,
            "prompt_type": prompt_type,
            "batches_processed": 0,
        }

        # Process in batches
        for i in range(0, len(unsummarized), batch_size):
            batch = unsummarized[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(unsummarized) + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} posts) for style '{style}'"
            )

            try:
                # Summarize batch
                batch_stats = await self._summarize_batch(
                    batch,
                    prompt_type=prompt_type
                )

                # Update posts in database
                for post, summary_data in zip(batch, batch_stats["summaries"]):
                    if summary_data:
                        post.summary = summary_data["summary"]
                        post.summarized_at = datetime.utcnow()
                        self.db_session.add(post)

                await self.db_session.commit()

                # Update statistics
                stats["summarized"] += batch_stats["succeeded"]
                stats["failed"] += batch_stats["failed"]
                stats["tokens_used"] += batch_stats["tokens_used"]
                stats["cost"] += batch_stats["cost"]
                stats["batches_processed"] += 1

                logger.info(
                    f"Batch {batch_num} complete: "
                    f"{batch_stats['succeeded']} succeeded, "
                    f"{batch_stats['failed']} failed"
                )

            except Exception as e:
                logger.error(
                    f"Batch {batch_num} failed completely: {e}", exc_info=True
                )
                stats["failed"] += len(batch)
                continue

        # Calculate duration
        end_time = datetime.utcnow()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Batch summarization complete for style '{style}': "
            f"{stats['summarized']}/{stats['total_posts']} succeeded, "
            f"{stats['failed']} failed, "
            f"{stats['tokens_used']} tokens, "
            f"${stats['cost']:.4f}, "
            f"{stats['duration_seconds']:.1f}s"
        )

        return stats

    async def _summarize_batch(
        self,
        posts: List[Post],
        prompt_type: str
    ) -> Dict:
        """Summarize a batch of posts.

        Args:
            posts: List of posts to summarize
            prompt_type: Prompt type (basic, concise, technical, etc.)

        Returns:
            Batch statistics:
            {
                "succeeded": 8,
                "failed": 2,
                "summaries": [dict, dict, ..., None],  # None = failed
                "tokens_used": 5000,
                "cost": 0.0004
            }
        """
        from app.infrastructure.agents.summarization_agent import (
            create_summarization_agent,
            SummaryOutput
        )

        logger.info(
            f"Summarizing batch of {len(posts)} posts "
            f"with prompt_type='{prompt_type}'"
        )

        # Create agent for this batch
        agent = create_summarization_agent(
            prompt_type=prompt_type,
            use_structured_output=True
        )

        batch_stats = {
            "succeeded": 0,
            "failed": 0,
            "summaries": [],
            "tokens_used": 0,
            "cost": 0.0,
        }

        # Process each post in batch
        for post in posts:
            try:
                # Get markdown content
                markdown_content = self._get_post_markdown(post)

                if not markdown_content:
                    logger.warning(
                        f"Post {post.id} (hn_id={post.hn_id}) has no content, skipping"
                    )
                    batch_stats["failed"] += 1
                    batch_stats["summaries"].append(None)
                    continue

                # Call agent (wrapped with tracking)
                # Note: In production, use TrackedAgent for token counting
                result = agent._agent.run(markdown_content)

                # Extract summary
                if hasattr(result, "output") and isinstance(result.output, SummaryOutput):
                    summary_data = {
                        "summary": result.output.summary,
                        "key_points": result.output.key_points,
                        "technical_level": result.output.technical_level,
                        "confidence": result.output.confidence,
                    }
                    batch_stats["summaries"].append(summary_data)
                    batch_stats["succeeded"] += 1

                    # Estimate tokens (rough approximation)
                    # In production, use actual token counts from TrackedAgent
                    estimated_tokens = len(markdown_content) // 4 + 50
                    batch_stats["tokens_used"] += estimated_tokens
                    batch_stats["cost"] += estimated_tokens * 0.00000015  # gpt-4o-mini pricing

                    logger.debug(
                        f"Post {post.id} summarized successfully: "
                        f"{summary_data['summary'][:80]}..."
                    )
                else:
                    logger.warning(
                        f"Post {post.id} summarization returned unexpected format"
                    )
                    batch_stats["failed"] += 1
                    batch_stats["summaries"].append(None)

            except Exception as e:
                logger.error(
                    f"Failed to summarize post {post.id} (hn_id={post.hn_id}): {e}"
                )
                batch_stats["failed"] += 1
                batch_stats["summaries"].append(None)
                continue

        logger.info(
            f"Batch complete: {batch_stats['succeeded']} succeeded, "
            f"{batch_stats['failed']} failed"
        )

        return batch_stats

    def _get_post_markdown(self, post: Post) -> str:
        """Convert post to markdown for LLM.

        Args:
            post: Post object

        Returns:
            Markdown content string

        Example:
            >>> markdown = use_case._get_post_markdown(post)
            >>> print(markdown)
            # PostgreSQL 18 Released
            ## URL: https://postgresql.org/...
            ## Content
            PostgreSQL 18 was released...
        """
        # Try to read from RocksDB
        try:
            if post.has_markdown:
                content = self.content_store.get(str(post.id), "markdown")
                if content:
                    return content
        except Exception as e:
            logger.warning(
                f"Failed to read markdown from RocksDB for post {post.id}: {e}"
            )

        # Fallback: construct markdown from post fields
        markdown_parts = []

        if post.title:
            markdown_parts.append(f"# {post.title}")

        if post.url:
            markdown_parts.append(f"\n## URL: {post.url}")

        if post.domain:
            markdown_parts.append(f"Domain: {post.domain}")

        # Add metadata
        markdown_parts.append(
            f"\n## Metadata\n"
            f"- Score: {post.score}\n"
            f"- Comments: {post.comment_count}\n"
            f"- Author: {post.author}\n"
            f"- HN ID: {post.hn_id}"
        )

        # Try to get text content from RocksDB
        try:
            if post.has_text:
                text_content = self.content_store.get(str(post.id), "text")
                if text_content:
                    markdown_parts.append(f"\n## Content\n\n{text_content[:5000]}")  # Limit to 5000 chars
        except Exception as e:
            logger.warning(
                f"Failed to read text from RocksDB for post {post.id}: {e}"
            )

        markdown = "\n".join(markdown_parts)

        if not markdown.strip():
            logger.warning(f"Generated empty markdown for post {post.id}")

        return markdown
