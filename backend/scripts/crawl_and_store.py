#!/usr/bin/env python3
"""
Crawl top 100 HN posts and store in PostgreSQL database.

This script:
1. Fetches top 100 posts from HN Firebase API
2. Stores posts in PostgreSQL database
3. Crawls content from URLs (HTML, Text, Markdown)
4. Updates database with crawl status

Usage:
    python scripts/crawl_and_store.py
    python scripts/crawl_and_store.py --limit 50
    python scripts/crawl_and_store.py --score-threshold 200
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.entities import Post as DomainPost
from app.infrastructure.database.base import engine, async_session_maker
from app.infrastructure.repositories.postgres.post_repo import PostgresPostRepository
from app.infrastructure.services.firebase_hn_client import FirebaseHNClient
from app.infrastructure.services.enhanced_content_extractor import EnhancedContentExtractor
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore
from markitdown import MarkItDown

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HNCrawler:
    """Orchestrates HN post fetching, storage, and content crawling."""

    def __init__(
        self,
        rocksdb_path: str = "data/content.rocksdb",
        max_concurrent: int = 3,
        timeout: int = 30
    ):
        """Initialize crawler.

        Args:
            rocksdb_path: Path to RocksDB database
            max_concurrent: Maximum concurrent crawl requests
            timeout: HTTP timeout in seconds
        """
        self.hn_client = FirebaseHNClient(timeout=10)
        self.content_extractor = EnhancedContentExtractor(
            timeout=timeout,
            max_retries=3,
            min_delay=1.0,
            max_delay=3.0,
            respect_robots_txt=True
        )

        # Initialize RocksDB content store
        self.content_store = RocksDBContentStore(db_path=rocksdb_path)
        self.rocksdb_path = rocksdb_path

        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.md_converter = MarkItDown()

    async def fetch_top_posts(
        self,
        limit: int = 100,
        score_threshold: int = 100
    ) -> list:
        """Fetch top posts from HN.

        Args:
            limit: Maximum number of posts to fetch
            score_threshold: Minimum score for posts

        Returns:
            List of post dictionaries
        """
        logger.info(f"Fetching top {limit} posts with score >= {score_threshold}")

        stories = await self.hn_client.fetch_front_page(limit=limit)

        # Filter by score
        filtered_stories = [
            story for story in stories
            if story.get("score", 0) >= score_threshold
        ]

        logger.info(
            f"Found {len(filtered_stories)} posts with score >= {score_threshold} "
            f"(from {len(stories)} total)"
        )

        return filtered_stories

    async def save_posts_to_db(self, stories: list) -> list:
        """Save posts to PostgreSQL database.

        Args:
            stories: List of raw story dictionaries from Firebase API

        Returns:
            List of saved domain Post entities
        """
        logger.info(f"Saving {len(stories)} posts to database...")

        async with async_session_maker() as session:
            repo = PostgresPostRepository(session)

            saved_posts = []
            for story in stories:
                # Transform to our format
                transformed = self.hn_client.transform_item_to_post(story)

                # Create domain entity
                domain_post = DomainPost(
                    id=None,
                    hn_id=str(transformed["hn_id"]),
                    title=transformed["title"],
                    author=transformed["author"],
                    url=transformed["url"],
                    points=transformed["points"],
                    num_comments=transformed["num_comments"],
                    created_at=transformed["created_at"],
                    collected_at=transformed["collected_at"],
                    post_type=transformed["post_type"],
                    content=None,
                    raw_content=None,
                    summary=None
                )

                try:
                    # Check if post already exists
                    existing = await repo.find_by_hn_id(int(domain_post.hn_id))
                    if existing:
                        logger.info(f"Post {domain_post.hn_id} already exists, skipping")
                        saved_posts.append(existing)
                        continue

                    # Save new post
                    saved_post = await repo.save(domain_post)
                    saved_posts.append(saved_post)
                    logger.info(
                        f"✓ Saved post {saved_post.hn_id}: {saved_post.title[:50]}..."
                    )

                except Exception as e:
                    logger.error(f"✗ Failed to save post {domain_post.hn_id}: {e}")
                    continue

        logger.info(f"Successfully saved {len(saved_posts)} posts to database")
        return saved_posts

    async def crawl_post_content(self, post: DomainPost) -> dict:
        """Crawl content for a single post.

        Args:
            post: Domain Post entity

        Returns:
            Dictionary with crawl results
        """
        hn_id = post.hn_id
        url = post.url

        # Check if URL exists
        if not url:
            logger.info(f"Skipping post {hn_id} - no URL (Ask/Show HN)")
            return {
                "hn_id": hn_id,
                "success": False,
                "skipped": True,
                "reason": "no_url"
            }

        async with self.semaphore:
            logger.info(f"Crawling [{hn_id}]: {post.title[:60]}...")

            try:
                # Extract content
                success, html_content, extracted_text = (
                    await self.content_extractor.extract_content(url)
                )

                has_html = False
                has_text = False
                has_markdown = False
                content_length = 0
                markdown_content = None

                # Save HTML to RocksDB
                if html_content:
                    await self.content_store.save_html_content(int(hn_id), html_content)
                    has_html = True
                    logger.info(f"  ✓ Saved HTML to RocksDB")

                # Save extracted text to RocksDB
                if extracted_text:
                    await self.content_store.save_text_content(int(hn_id), extracted_text)
                    has_text = True
                    content_length = len(extracted_text)
                    logger.info(f"  ✓ Saved text to RocksDB ({content_length} chars)")

                # Convert to Markdown and save to RocksDB
                if html_content:
                    try:
                        # Create temporary file for markitdown
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp:
                            tmp.write(html_content)
                            tmp_path = tmp.name

                        try:
                            result = self.md_converter.convert(tmp_path)
                            markdown_content = result.text_content

                            await self.content_store.save_markdown_content(int(hn_id), markdown_content)
                            has_markdown = True
                            logger.info(f"  ✓ Saved markdown to RocksDB")
                        finally:
                            # Clean up temp file
                            import os
                            os.unlink(tmp_path)
                    except Exception as e:
                        logger.warning(f"  ✗ Markdown conversion failed: {e}")

                # Update database
                async with async_session_maker() as session:
                    repo = PostgresPostRepository(session)
                    await repo.update_crawl_status(
                        hn_id=int(hn_id),
                        is_success=success,
                        has_html=has_html,
                        has_text=has_text,
                        has_markdown=has_markdown,
                        content_length=content_length,
                        error=None if success else "Content extraction failed"
                    )

                logger.info(f"  ✓ Updated database")

                return {
                    "hn_id": hn_id,
                    "success": success,
                    "has_html": has_html,
                    "has_text": has_text,
                    "has_markdown": has_markdown,
                    "content_length": content_length,
                    "skipped": False
                }

            except Exception as e:
                logger.error(f"  ✗ Error crawling {hn_id}: {e}")

                # Update database with error
                async with async_session_maker() as session:
                    repo = PostgresPostRepository(session)
                    await repo.update_crawl_status(
                        hn_id=int(hn_id),
                        is_success=False,
                        error=str(e)
                    )

                return {
                    "hn_id": hn_id,
                    "success": False,
                    "error": str(e),
                    "skipped": False
                }

    async def crawl_all_posts(self, posts: list) -> dict:
        """Crawl content for all posts.

        Args:
            posts: List of domain Post entities

        Returns:
            Statistics dictionary
        """
        logger.info(f"\nStarting content crawl for {len(posts)} posts...")
        logger.info(f"Max concurrent requests: {self.semaphore._value}\n")

        # Create tasks for all posts
        tasks = [self.crawl_post_content(post) for post in posts]

        # Run all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate statistics
        stats = {
            "total": len(posts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "with_html": 0,
            "with_text": 0,
            "with_markdown": 0
        }

        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
                continue

            if result.get("skipped"):
                stats["skipped"] += 1
            elif result.get("success"):
                stats["successful"] += 1
                if result.get("has_html"):
                    stats["with_html"] += 1
                if result.get("has_text"):
                    stats["with_text"] += 1
                if result.get("has_markdown"):
                    stats["with_markdown"] += 1
            else:
                stats["failed"] += 1

        return stats


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Crawl top HN posts and store in database"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of posts to fetch (default: 100)"
    )
    parser.add_argument(
        "--score-threshold",
        type=int,
        default=100,
        help="Minimum score for posts (default: 100)"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent crawl requests (default: 3)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("HackerNews Post Crawler & Database Importer")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  - Fetch limit: {args.limit} posts")
    print(f"  - Score threshold: >= {args.score_threshold}")
    print(f"  - Max concurrent crawls: {args.max_concurrent}")
    print(f"  - Request timeout: {args.timeout}s")
    print("=" * 70)

    try:
        # Initialize crawler
        crawler = HNCrawler(
            max_concurrent=args.max_concurrent,
            timeout=args.timeout
        )

        # Step 1: Fetch posts
        print("\n[1/3] Fetching posts from HackerNews...")
        stories = await crawler.fetch_top_posts(
            limit=args.limit,
            score_threshold=args.score_threshold
        )

        if not stories:
            print("✗ No posts found matching criteria")
            return 1

        print(f"✓ Fetched {len(stories)} posts")

        # Step 2: Save to database
        print("\n[2/3] Saving posts to PostgreSQL database...")
        saved_posts = await crawler.save_posts_to_db(stories)
        print(f"✓ Saved {len(saved_posts)} posts to database")

        # Step 3: Crawl content
        print("\n[3/3] Crawling content from URLs...")
        stats = await crawler.crawl_all_posts(saved_posts)

        # Display results
        print("\n" + "=" * 70)
        print("📊 CRAWL SUMMARY")
        print("=" * 70)
        print(f"Total posts:        {stats['total']}")
        print(f"Successful:         {stats['successful']} ✓")
        print(f"Failed:             {stats['failed']} ✗")
        print(f"Skipped (no URL):   {stats['skipped']} ⊘")
        print(f"\nContent saved:")
        print(f"  HTML files:       {stats['with_html']}")
        print(f"  Text files:       {stats['with_text']}")
        print(f"  Markdown files:   {stats['with_markdown']}")
        print("=" * 70)

        # Verify database
        print("\n📦 Database Status:")
        async with async_session_maker() as session:
            repo = PostgresPostRepository(session)
            # Count posts (we'll use a simple query)
            from sqlalchemy import select, func
            from app.infrastructure.database.models import Post as PostModel

            stmt = select(func.count()).select_from(PostModel)
            result = await session.execute(stmt)
            total_posts = result.scalar()

            stmt = select(func.count()).select_from(PostModel).where(
                PostModel.is_crawl_success == True
            )
            result = await session.execute(stmt)
            crawled_posts = result.scalar()

            print(f"  Total posts in DB:     {total_posts}")
            print(f"  Successfully crawled:  {crawled_posts}")

        print("\n✅ Pipeline completed successfully!")

        # Show RocksDB stats
        print(f"\n💾 Content Storage (RocksDB):")
        print(f"   - Database: {crawler.rocksdb_path}")
        rocksdb_stats = crawler.content_store.get_stats()
        print(f"   - HTML entries:     {rocksdb_stats['html_count']}")
        print(f"   - Text entries:     {rocksdb_stats['text_count']}")
        print(f"   - Markdown entries: {rocksdb_stats['markdown_count']}")
        print(f"   - Total keys:       {rocksdb_stats['total_keys']}")

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1
    finally:
        # Close database connections
        await engine.dispose()

        # Close RocksDB
        if 'crawler' in locals():
            crawler.content_store.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
