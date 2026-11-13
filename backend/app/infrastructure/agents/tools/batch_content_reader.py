"""Tool for searching and batch-reading HackerNews post content.

Uses PostgreSQL for post metadata search and RocksDB for content retrieval.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from agents import function_tool
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Post
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


def create_batch_content_reader(
    session: "AsyncSession",
    content_store: RocksDBContentStore,
):
    """Create a batch_content_reader tool with injected dependencies.

    Args:
        session: Async database session for PostgreSQL queries.
        content_store: RocksDB store for reading markdown content.

    Returns:
        FunctionTool for searching and reading posts.
    """

    @function_tool
    async def batch_content_reader(
        keywords: list[str],
        limit: int = 10,
        offset: int = 0,
        max_age_days: int = 30,
        max_chars_per_post: int = 3000,
    ) -> str:
        """Search HackerNews posts by keywords and return their content.

        Use this to find what HackerNews has been discussing on a given topic.
        Returns post titles, URLs, scores, dates, and content summaries.

        Args:
            keywords: Search terms - posts whose title matches any keyword (OR logic).
            limit: Maximum number of posts to return (1-20).
            offset: Pagination offset for browsing large result sets.
            max_age_days: Only return posts collected within this many days.
            max_chars_per_post: Truncate each post's content to this many characters.

        Returns:
            Formatted string with matching posts and their content.
        """
        if not keywords:
            return "Error: At least one keyword is required."

        if limit < 1 or limit > 20:
            limit = max(1, min(limit, 20))

        if max_age_days < 1:
            max_age_days = 30

        since = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        conditions = [
            Post.type == "story",
            Post.is_dead == False,  # noqa: E712
            Post.is_deleted == False,  # noqa: E712
            Post.collected_at >= since,
        ]

        keyword_conditions = [Post.title.ilike(f"%{kw}%") for kw in keywords]
        if keyword_conditions:
            from sqlalchemy import or_

            conditions.append(or_(*keyword_conditions))

        stmt = (
            select(Post)
            .where(*conditions)
            .order_by(Post.score.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await session.execute(stmt)
        posts = result.scalars().all()

        if not posts:
            return f"No posts found matching keywords {keywords} in the last {max_age_days} days."

        total_stmt = select(Post).where(*conditions)
        total_result = await session.execute(total_stmt)
        total_count = len(total_result.scalars().all())

        lines = [
            f"Found {total_count} posts (showing {offset + 1}-{offset + len(posts)}):",
        ]

        for post in posts:
            content = ""
            if post.has_markdown:
                markdown = await content_store.get_markdown_content(post.hn_id)
                if markdown:
                    content = markdown[:max_chars_per_post]
                    if len(markdown) > max_chars_per_post:
                        content += "\n... [truncated]"

            lines.append("\n---")
            lines.append(f"Title: {post.title}")
            lines.append(f"URL: {post.url or 'N/A'}")
            lines.append(f"Score: {post.score} | Comments: {post.comment_count}")
            lines.append(f"Date: {post.collected_at.strftime('%Y-%m-%d')}")
            if content:
                lines.append(f"Content: {content}")
            else:
                lines.append("Content: [No content available]")

        result_str = "\n".join(lines)
        logger.info(
            f"batch_content_reader: keywords={keywords}, found={len(posts)}/{total_count}"
        )
        return result_str

    return batch_content_reader
