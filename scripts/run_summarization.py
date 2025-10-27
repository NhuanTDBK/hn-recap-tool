#!/usr/bin/env python3
"""Script to run summarization on HackerNews articles by date range.

This script:
1. Loads posts from repository within a date range
2. Filters posts that have content
3. Summarizes each article using OpenAI
4. Saves summaries to data/processed/summaries/

Usage:
    python scripts/run_summarization.py  # Uses today's date
    python scripts/run_summarization.py --start_time 2025-10-25 --end_time 2025-10-27
    python scripts/run_summarization.py --start_time 2025-10-27  # From date to today
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings

from backend.app.infrastructure.repositories.jsonl_post_repo import JSONLPostRepository
from backend.app.infrastructure.repositories.jsonl_content_repo import JSONLContentRepository
from backend.app.domain.entities import Post


# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def save_summaries(summaries: List[Dict], output_dir: Path):
    """Save summaries to JSONL file.

    Args:
        summaries: List of summary dictionaries
        output_dir: Directory to save summaries
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_file = output_dir / f"{timestamp}-summaries.jsonl"

    logger.info(f"Saving summaries to {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        for summary in summaries:
            f.write(json.dumps(summary) + "\n")

    logger.info(f"Saved {len(summaries)} summaries")

    # Also save a human-readable version
    markdown_file = output_dir / f"{timestamp}-summaries.md"
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write(f"# Article Summaries\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"Total articles: {len(summaries)}\n\n")
        f.write("---\n\n")

        for i, summary in enumerate(summaries, 1):
            f.write(f"## {i}. {summary['title']}\n\n")
            f.write(f"**Article ID:** {summary['id']}\n\n")
            f.write(f"**Summary:**\n\n{summary['summary']}\n\n")
            f.write("---\n\n")

    logger.info(f"Saved readable version to {markdown_file}")
    return markdown_file


async def main():
    """Main function to run summarization."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Summarize HackerNews articles from a date range"
    )
    parser.add_argument(
        "--start_time",
        type=str,
        default=None,
        help="Start date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format (default: today or start_time if specified)",
    )

    args = parser.parse_args()

    # Set default dates
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = args.start_time or today
    end_date = args.end_time or today

    logger.info(f"Summarization date range: {start_date} to {end_date}")

    # Load environment variables from .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f".env file not found at {env_file}")

    # Setup paths
    data_dir = project_root / "data"
    output_dir = data_dir / "processed" / "summaries"

    # Initialize repositories
    post_repo = JSONLPostRepository(str(data_dir))
    content_repo = JSONLContentRepository(str(data_dir))

    # Load posts from repository for date range
    logger.info("Loading posts from repository...")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)

    posts: List[Post] = []
    current = start

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        try:
            date_posts = await post_repo.find_by_date(date_str)
            posts.extend(date_posts)
            logger.info(f"Loaded {len(date_posts)} posts for {date_str}")
        except Exception as e:
            logger.error(f"Error loading posts for {date_str}: {e}")
        current += timedelta(days=1)

    if not posts:
        logger.error("No posts found for the specified date range")
        sys.exit(1)

    logger.info(f"Total posts loaded: {len(posts)}")

    # Load content for posts using ContentRepository
    logger.info("Loading content for posts...")
    posts_with_content = []

    for post in posts:
        # Skip posts without URLs
        if not post.url:
            print(post)
            continue

        # Try to load text content
        text_content = await content_repo.get_text_content(post.hn_id)
        if text_content:
            # Update post with loaded content
            post.content = text_content
            posts_with_content.append(post)
            logger.debug(f"Loaded text content for post {post.hn_id}")

    if not posts_with_content:
        logger.error("No posts with content found")
        logger.error("Please run crawl_content.py to extract article content first")
        sys.exit(1)

    logger.info(f"Found {len(posts_with_content)} posts with content")

    # Load system prompt from file
    logger.info("Loading summarization prompt...")
    prompts_dir = backend_dir / "app" / "infrastructure" / "services" / "prompts"
    summarizer_prompt = (prompts_dir / "summarizer.md").read_text()

    # Initialize summarization agent
    logger.info("Initializing OpenAI summarization agent...")

    model = "gpt-4o-mini"
    model_settings = ModelSettings(
        max_tokens=500,  # Shorter summaries
        temperature=0.3,
    )

    # Create summarization agent
    summarizer_agent = Agent(
        name="Article Summarizer",
        instructions=summarizer_prompt,
        model=model,
        model_settings=model_settings,
    )

    # Process posts asynchronously
    logger.info("Starting summarization...")

    async def summarize_post(post: Post) -> Dict:
        """Summarize a single post asynchronously."""
        try:
            # Post should already have content loaded
            if not post.content:
                raise ValueError("Post has no content to summarize")

            # Run the summarization agent
            prompt = f"Summarize this article:\n\n{post.content}"
            result = await Runner.run(summarizer_agent, input=prompt)
            summary_text = (
                result.final_output if result.final_output else "[No summary generated]"
            )

            logger.info(
                f"✓ Summarized post {post.hn_id}: {post.title[:60]}..."
            )

            return {
                "id": str(post.hn_id),
                "title": post.title,
                "summary": summary_text,
                "url": post.url,
                "timestamp": datetime.now().isoformat(),
                "model": model,
            }

        except Exception as e:
            logger.error(f"✗ Failed to summarize post {post.hn_id}: {e}")
            return {
                "id": str(post.hn_id),
                "title": post.title,
                "summary": f"[Error: {str(e)}]",
                "url": post.url,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    # Run all summarizations concurrently
    tasks = [summarize_post(post) for post in posts_with_content]
    summaries = await asyncio.gather(*tasks)

    # Save results
    logger.info("Saving summaries...")
    markdown_file = save_summaries(summaries, output_dir)

    # Print summary statistics
    successful = sum(1 for s in summaries if "error" not in s)
    failed = len(summaries) - successful

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total articles: {len(summaries)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"To push to Telegram, run:")
    logger.info(f"  python scripts/push_to_telegram.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
