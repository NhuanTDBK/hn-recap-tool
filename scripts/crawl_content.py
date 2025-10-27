#!/usr/bin/env python3
"""
Crawl and extract content from HackerNews posts.

This script reads HN posts from JSONL files and uses the CrawlContentUseCase
to extract content with proper rate limiting, retries, and robots.txt compliance.

Usage:
    python scripts/crawl_content.py data/raw/2025-10-25-posts.jsonl
    python scripts/crawl_content.py data/raw/2025-10-25-posts.jsonl --skip-crawled --max-concurrent 3
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import List
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.entities import Post
from app.application.use_cases.crawl_content import CrawlContentUseCase
from app.infrastructure.services.enhanced_content_extractor import EnhancedContentExtractor
from app.infrastructure.services.crawl_status_tracker import CrawlStatusTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_posts_from_jsonl(posts_file: str) -> List[Post]:
    """Load posts from JSONL file and convert to Post entities.

    Args:
        posts_file: Path to posts JSONL file

    Returns:
        List of Post entities
    """
    posts = []
    with open(posts_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    # Convert to Post entity
                    post = Post(
                        hn_id=int(data['hn_id']),
                        title=data['title'],
                        author=data['author'],
                        points=data['points'],
                        num_comments=data['num_comments'],
                        created_at=data['created_at'],
                        collected_at=data['collected_at'],
                        url=data.get('url'),
                        post_type=data.get('post_type', 'story')
                    )
                    posts.append(post)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.error(f"Error parsing post: {e}")
                    continue

    logger.info(f"Loaded {len(posts)} posts from {posts_file}")
    return posts


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Crawl and extract content from HackerNews posts"
    )
    parser.add_argument(
        "posts_file",
        help="Path to posts JSONL file (e.g., data/raw/2025-10-25-posts.jsonl)"
    )
    parser.add_argument(
        "--output",
        default="data/content",
        help="Output directory for extracted content (default: data/content)"
    )
    parser.add_argument(
        "--status-file",
        default="data/crawl_status.jsonl",
        help="Path to crawl status file (default: data/crawl_status.jsonl)"
    )
    parser.add_argument(
        "--skip-crawled",
        action="store_true",
        help="Skip posts that have already been successfully crawled"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=3,
        help="Maximum concurrent requests (default: 3)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: 3)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.0,
        help="Minimum delay between requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=3.0,
        help="Maximum delay between requests in seconds (default: 3.0)"
    )

    args = parser.parse_args()

    try:
        # Load posts
        posts = load_posts_from_jsonl(args.posts_file)

        if not posts:
            logger.error("No posts found")
            return 1

        # Initialize services
        extractor = EnhancedContentExtractor(
            timeout=args.timeout,
            max_retries=args.max_retries,
            min_delay=args.min_delay,
            max_delay=args.max_delay,
            respect_robots_txt=True
        )

        tracker = CrawlStatusTracker(status_file=args.status_file)

        # Initialize use case
        crawl_use_case = CrawlContentUseCase(
            extractor=extractor,
            tracker=tracker,
            output_dir=args.output,
            max_concurrent=args.max_concurrent
        )

        # Crawl all posts
        stats = await crawl_use_case.crawl_posts(
            posts=posts,
            skip_if_crawled=args.skip_crawled
        )

        # Display results
        print("\n" + "="*60)
        print("📊 CRAWL SUMMARY")
        print("="*60)
        print(f"Total posts:        {stats['total']}")
        print(f"Successful:         {stats['successful']} ✓")
        print(f"Failed:             {stats['failed']} ✗")
        print(f"Skipped:            {stats['skipped']} ⊘")
        print(f"With content:       {stats['with_content']}")
        print(f"Without content:    {stats['without_content']}")
        print("="*60)

        # Display overall tracker statistics
        tracker_stats = tracker.get_crawl_statistics()
        print("\n📈 OVERALL STATISTICS")
        print("="*60)
        print(f"Total crawls:       {tracker_stats['total_crawls']}")
        print(f"Unique posts:       {tracker_stats['unique_posts']}")
        print(f"Unique URLs:        {tracker_stats['unique_urls']}")
        print(f"Success rate:       {tracker_stats['successful']}/{tracker_stats['total_crawls']}")
        print("="*60)

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
