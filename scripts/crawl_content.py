#!/usr/bin/env python3
"""
Crawl and extract content from HackerNews posts.

This script reads HN posts from JSONL files and uses the CrawlContentUseCase
to extract content with proper rate limiting, retries, and robots.txt compliance.

Usage:
    python scripts/crawl_content.py --start-time 2025-10-25
    python scripts/crawl_content.py --start-time 2025-10-25 --end-time 2025-10-28
    python scripts/crawl_content.py --skip-crawled --max-concurrent 3
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List
from datetime import datetime, timedelta
import logging

from backend.app.domain.entities import Post
from backend.app.application.use_cases.crawl_content import CrawlContentUseCase
from backend.app.infrastructure.services.enhanced_content_extractor import (
    EnhancedContentExtractor,
)
from backend.app.infrastructure.services.crawl_status_tracker import CrawlStatusTracker
from backend.app.infrastructure.repositories.jsonl_post_repo import JSONLPostRepository


# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def load_posts_from_repository(
    repo: JSONLPostRepository, start_date: str, end_date: str
) -> List[Post]:
    """Load posts from repository for a date range.

    Args:
        repo: Post repository
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of Post entities
    """
    posts = []
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        date_posts = await repo.find_by_date(date_str)
        posts.extend(date_posts)
        current += timedelta(days=1)

    logger.info(f"Loaded {len(posts)} posts from {start_date} to {end_date}")
    return posts


async def main():
    """Main entry point."""
    # Get today's date as default
    today = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(
        description="Crawl and extract content from HackerNews posts"
    )
    parser.add_argument(
        "--start-time",
        default=today,
        help=f"Start date in YYYY-MM-DD format (default: today = {today})",
    )
    parser.add_argument(
        "--end-time",
        default=today,
        help=f"End date in YYYY-MM-DD format (default: today = {today})",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Base data directory (default: data)",
    )
    parser.add_argument(
        "--output",
        default="data/content",
        help="Output directory for extracted content (default: data/content)",
    )
    parser.add_argument(
        "--status-file",
        default="data/crawl_status.jsonl",
        help="Path to crawl status file (default: data/crawl_status.jsonl)",
    )
    parser.add_argument(
        "--skip-crawled",
        action="store_true",
        help="Skip posts that have already been successfully crawled",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent requests (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts (default: 3)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.0,
        help="Minimum delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=3.0,
        help="Maximum delay between requests in seconds (default: 3.0)",
    )

    args = parser.parse_args()

    try:
        # Validate date format
        try:
            datetime.strptime(args.start_time, "%Y-%m-%d")
            datetime.strptime(args.end_time, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Invalid date format. Use YYYY-MM-DD: {e}")
            return 1

        # Initialize repository
        repo = JSONLPostRepository(data_dir=args.data_dir)

        # Load posts from repository
        posts = await load_posts_from_repository(repo, args.start_time, args.end_time)

        if not posts:
            logger.error("No posts found")
            return 1

        # Initialize services
        extractor = EnhancedContentExtractor(
            timeout=args.timeout,
            max_retries=args.max_retries,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            respect_robots_txt=True,
        )

        tracker = CrawlStatusTracker(status_file=args.status_file)

        # Initialize use case
        crawl_use_case = CrawlContentUseCase(
            extractor=extractor,
            tracker=tracker,
            output_dir=args.output,
            max_concurrent=args.max_concurrent,
        )

        # Crawl all posts
        stats = await crawl_use_case.crawl_posts(
            posts=posts, skip_if_crawled=args.skip_crawled
        )

        # Display results
        print("\n" + "=" * 60)
        print("📊 CRAWL SUMMARY")
        print("=" * 60)
        print(f"Total posts:        {stats['total']}")
        print(f"Successful:         {stats['successful']} ✓")
        print(f"Failed:             {stats['failed']} ✗")
        print(f"Skipped:            {stats['skipped']} ⊘")
        print(f"With content:       {stats['with_content']}")
        print(f"Without content:    {stats['without_content']}")
        print("=" * 60)

        # Display overall tracker statistics
        tracker_stats = tracker.get_crawl_statistics()
        print("\n📈 OVERALL STATISTICS")
        print("=" * 60)
        print(f"Total crawls:       {tracker_stats['total_crawls']}")
        print(f"Unique posts:       {tracker_stats['unique_posts']}")
        print(f"Unique URLs:        {tracker_stats['unique_urls']}")
        print(
            f"Success rate:       {tracker_stats['successful']}/{tracker_stats['total_crawls']}"
        )
        print("=" * 60)

        print(f"\n💾 Content saved to:")
        print(f"   HTML:  {args.output}/html/")
        print(f"   Text:  {args.output}/text/")
        print(f"   Status: {args.status_file}")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
