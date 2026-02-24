"""Use case for crawling and extracting content from HN posts."""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from markitdown import MarkItDown

from app.domain.entities import Post
from app.infrastructure.services.enhanced_content_extractor import (
    EnhancedContentExtractor,
)
from app.infrastructure.services.crawl_status_tracker import CrawlStatusTracker

logger = logging.getLogger(__name__)


class CrawlContentUseCase:
    """Use case for crawling and extracting content from posts."""

    def __init__(
        self,
        extractor: EnhancedContentExtractor,
        tracker: CrawlStatusTracker,
        output_dir: str = "data/content",
        max_concurrent: int = 3,
    ):
        """Initialize crawl content use case.

        Args:
            extractor: Content extractor service
            tracker: Crawl status tracker
            output_dir: Directory to save extracted content
            max_concurrent: Maximum concurrent requests
        """
        self.extractor = extractor
        self.tracker = tracker
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.html_dir = self.output_dir / "html"
        self.text_dir = self.output_dir / "text"
        self.markdown_dir = self.output_dir / "markdown"
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def crawl_post(
        self, post: Post, skip_if_crawled: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Crawl and extract content from a single post.

        Args:
            post: Post entity to crawl
            skip_if_crawled: If True, skip already crawled posts

        Returns:
            Tuple of (success: bool, result: dict)
        """
        post_id = str(post.hn_id)
        url = post.url
        title = post.title

        # Check if it's a text post (no URL)
        if not post.has_external_url():
            logger.info(f"Skipping text post: {post_id} - {title}")
            return False, {"post_id": post_id, "skipped": True, "reason": "no_url"}

        # Check if already crawled
        if skip_if_crawled and self.tracker.is_already_crawled(post_id):
            logger.info(f"Skipping already crawled: {post_id} - {title}")
            return False, {
                "post_id": post_id,
                "skipped": True,
                "reason": "already_crawled",
            }

        # Use semaphore for rate limiting
        async with self.semaphore:
            logger.info(f"Crawling [{post_id}]: {title}")
            logger.info(f"URL: {url}")

            try:
                # Extract content
                success, html_content, extracted_text = (
                    await self.extractor.extract_content(url)
                )

                # Save HTML content if available
                html_file = None
                if html_content:
                    html_file = self.html_dir / f"{post_id}.html"
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    logger.info(f"✓ Saved HTML: {html_file}")

                # Save extracted text if available
                text_file = None
                content_length = 0
                if extracted_text:
                    text_file = self.text_dir / f"{post_id}.txt"
                    with open(text_file, "w", encoding="utf-8") as f:
                        f.write(extracted_text)
                    content_length = len(extracted_text)
                    logger.info(
                        f"✓ Saved extracted text ({content_length} chars): {text_file}"
                    )

                # Convert HTML to Markdown
                markdown_file = None
                if html_content:
                    try:
                        md = MarkItDown()
                        # Save HTML to temp file for conversion
                        temp_html = self.html_dir / f"{post_id}.html"
                        result = md.convert(str(temp_html))
                        markdown_content = result.text_content

                        markdown_file = self.markdown_dir / f"{post_id}.md"
                        with open(markdown_file, "w", encoding="utf-8") as f:
                            f.write(markdown_content)
                        logger.info(f"✓ Saved markdown: {markdown_file}")
                    except Exception as e:
                        logger.warning(f"Failed to convert to markdown: {e}")

                # Record status
                self.tracker.record_crawl(
                    post_id=post_id,
                    url=url,
                    success=success,
                    has_content=extracted_text is not None,
                    error=None if success else "Content extraction failed",
                    content_length=content_length,
                    metadata={
                        "title": title,
                        "author": post.author,
                        "points": post.points,
                        "html_saved": html_file is not None,
                        "text_saved": text_file is not None,
                        "markdown_saved": markdown_file is not None,
                    },
                )

                return success, {
                    "post_id": post_id,
                    "success": success,
                    "has_content": extracted_text is not None,
                    "content_length": content_length,
                    "skipped": False,
                }

            except Exception as e:
                logger.error(f"✗ Error crawling {post_id}: {e}")

                # Record failure
                self.tracker.record_crawl(
                    post_id=post_id,
                    url=url,
                    success=False,
                    has_content=False,
                    error=str(e),
                )

                return False, {
                    "post_id": post_id,
                    "success": False,
                    "error": str(e),
                    "skipped": False,
                }

    async def crawl_posts(
        self, posts: List[Post], skip_if_crawled: bool = False
    ) -> Dict[str, Any]:
        """Crawl multiple posts concurrently.

        Args:
            posts: List of post entities to crawl
            skip_if_crawled: If True, skip already crawled posts

        Returns:
            Summary statistics
        """
        logger.info(f"Starting crawl of {len(posts)} posts")
        logger.info(f"Max concurrent requests: {self.semaphore._value}")

        # Create tasks for all posts
        tasks = [
            self.crawl_post(post, skip_if_crawled=skip_if_crawled) for post in posts
        ]

        # Run all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate statistics
        stats = {
            "total": len(posts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "with_content": 0,
            "without_content": 0,
        }

        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                continue

            success, result_data = result

            if result_data.get("skipped"):
                stats["skipped"] += 1
            elif result_data.get("success"):
                stats["successful"] += 1
                if result_data.get("has_content"):
                    stats["with_content"] += 1
                else:
                    stats["without_content"] += 1
            else:
                stats["failed"] += 1

        return stats
