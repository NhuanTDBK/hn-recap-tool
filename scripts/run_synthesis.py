#!/usr/bin/env python3
"""Script to run synthesis summarization on multiple articles.

This script:
1. Loads posts from data/raw/*.jsonl files within a date range
2. Matches posts with content in data/content/text/ by ID
3. Synthesizes content into a unified overview using OpenAI
4. Saves the synthesis to data/processed/synthesis/

Usage:
    python scripts/run_synthesis.py  # Uses today's date
    python scripts/run_synthesis.py --start_time 2025-10-25 --end_time 2025-10-27
    python scripts/run_synthesis.py --start_time 2025-10-27  # From date to today
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings
import aiofiles

# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_posts_by_date(data_dir: Path, start_date: str, end_date: str) -> List[Dict]:
    """Load posts from JSONL files within a date range.

    Args:
        data_dir: Path to the data directory
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of post dictionaries with metadata
    """
    raw_dir = data_dir / "raw"

    if not raw_dir.exists():
        logger.error(f"Raw directory not found: {raw_dir}")
        return []

    # Parse dates
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return []

    posts = []
    current = start

    # Load posts from all JSONL files in the date range
    while current <= end:
        jsonl_file = raw_dir / f"{current.strftime('%Y-%m-%d')}-posts.jsonl"

        if jsonl_file.exists():
            logger.info(f"Loading posts from {jsonl_file.name}")
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                post = json.loads(line)
                                posts.append(post)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON: {e}")
                                continue
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")
        else:
            logger.debug(f"No posts file for {current.strftime('%Y-%m-%d')}")

        current += timedelta(days=1)

    logger.info(f"Loaded {len(posts)} posts from date range {start_date} to {end_date}")
    return posts


async def load_content_for_posts(data_dir: Path, posts: List[Dict]) -> List[Dict]:
    """Load content from data/content/text/ for posts by ID (async with aiofiles).

    Args:
        data_dir: Path to the data directory
        posts: List of posts with hn_id

    Returns:
        List of articles with matched content
    """
    text_dir = data_dir / "content" / "text"

    if not text_dir.exists():
        logger.error(f"Text directory not found: {text_dir}")
        return []

    async def load_file(post: Dict) -> Dict:
        """Load a single content file asynchronously."""
        hn_id = post.get("hn_id")
        title = post.get("title", "Untitled")
        content_file = text_dir / f"{hn_id}.txt"

        if content_file.exists():
            try:
                # Use aiofiles for async file I/O
                async with aiofiles.open(content_file, mode="r", encoding="utf-8") as f:
                    content = await f.read()

                logger.debug(f"Loaded content for {hn_id}: {title[:50]}...")
                return {
                    "id": hn_id,
                    "title": title,
                    "content": content,
                    "points": post.get("points", 0),
                    "num_comments": post.get("num_comments", 0),
                    "url": post.get("url"),
                }
            except Exception as e:
                logger.error(f"Error loading content for {hn_id}: {e}")
                return None
        else:
            logger.debug(f"No content file for {hn_id}: {title[:50]}...")
            return None

    # Load all files concurrently
    tasks = [load_file(post) for post in posts]
    results = await asyncio.gather(*tasks)

    # Filter out None results
    articles = [article for article in results if article is not None]

    logger.info(f"Loaded {len(articles)} articles with content")
    return articles


def save_synthesis(synthesis: str, output_dir: Path, mode: str = "general"):
    """Save synthesis to file.

    Args:
        synthesis: The synthesized text
        output_dir: Directory to save synthesis
        mode: Type of synthesis (general, topic, etc.)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_file = output_dir / f"{timestamp}-synthesis-{mode}.md"

    logger.info(f"Saving synthesis to {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Synthesis Summary ({mode.title()})\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        f.write(synthesis)
        f.write("\n")

    logger.info(f"Saved synthesis to {output_file}")
    return output_file


async def synthesize_from_articles(
    articles: List[Dict],
    model: str,
) -> str:
    """Synthesize multiple articles into one unified overview.

    Args:
        articles: List of article dictionaries with 'title' and 'content'
        model: OpenAI model to use
        api_key: OpenAI API key

    Returns:
        Synthesized text
    """
    # Load synthesis prompt
    prompts_dir = backend_dir / "app" / "infrastructure" / "services" / "prompts"
    synthesis_prompt = (prompts_dir / "general_synthesis.md").read_text()

    # Configure model
    model_settings = ModelSettings(
        max_tokens=1500,
        temperature=0.5,
    )

    # Create synthesis agent
    synthesis_agent = Agent(
        name="Content Synthesizer",
        instructions=synthesis_prompt,
        model=model,
        # model_settings=model_settings,
    )

    # Format articles
    formatted = []
    for i, item in enumerate(articles, 1):
        title = item.get("title", "Untitled")
        content = item.get("content", "")

        formatted.append(f"=== Article {i}: {title} ===")
        formatted.append(f"\nContent:\n{content}\n")
        formatted.append("-" * 80)

    formatted_content = "\n".join(formatted)

    # Create prompt
    prompt = (
        f"Synthesize insights from these {len(articles)} HackerNews articles:\n\n"
        f"{formatted_content}"
    )

    # Run synthesis
    logger.info("Running synthesis agent...")
    result = await Runner.run(synthesis_agent, input=prompt)
    synthesis = (
        result.final_output if result.final_output else "[No synthesis generated]"
    )

    return synthesis


async def synthesize_by_topic(
    articles: List[Dict], topic: str, model: str, api_key: str
) -> str:
    """Synthesize multiple articles with a topic focus.

    Args:
        articles: List of article dictionaries with 'title' and 'content'
        topic: Topic to focus on
        model: OpenAI model to use
        api_key: OpenAI API key

    Returns:
        Topic-focused synthesized text
    """
    # Load topic synthesis prompt
    prompts_dir = backend_dir / "app" / "infrastructure" / "services" / "prompts"
    synthesis_prompt = (prompts_dir / "synthesis_topic.md").read_text()

    # Configure model
    model_settings = ModelSettings(
        max_tokens=1200,
        temperature=0.5,
    )

    # Create synthesis agent
    synthesis_agent = Agent(
        name="Topic-Focused Synthesizer",
        instructions=synthesis_prompt,
        model=model,
        model_settings=model_settings,
    )

    # Format articles
    formatted = []
    for i, item in enumerate(articles, 1):
        title = item.get("title", "Untitled")
        content = item.get("content", "")

        formatted.append(f"=== Article {i}: {title} ===")
        formatted.append(f"\nContent:\n{content}\n")
        formatted.append("-" * 80)

    formatted_content = "\n".join(formatted)

    # Create prompt
    prompt = (
        f"Topic: {topic}\n\n"
        f"Synthesize insights about '{topic}' from these {len(articles)} articles:\n\n"
        f"{formatted_content}"
    )

    # Run synthesis
    logger.info(f"Running topic-focused synthesis on: {topic}...")
    result = await Runner.run(synthesis_agent, input=prompt)
    synthesis = (
        result.final_output if result.final_output else "[No synthesis generated]"
    )

    return synthesis


async def main():
    """Main function to run synthesis."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Synthesize HackerNews articles from a date range"
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

    logger.info(f"Synthesis date range: {start_date} to {end_date}")

    # Load environment variables from .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f".env file not found at {env_file}")

    # Setup paths
    data_dir = project_root / "data"
    output_dir = data_dir / "processed" / "synthesis"

    # Load posts from raw JSONL files
    logger.info("Loading posts from raw data files...")
    posts = load_posts_by_date(data_dir, start_date, end_date)

    if not posts:
        logger.error("No posts found for the specified date range")
        sys.exit(1)

    # Load content for posts
    logger.info("Matching posts with content files...")
    articles = await load_content_for_posts(data_dir, posts)

    if not articles:
        logger.error("No content found for posts")
        logger.error("Please run crawl_content.py to extract article content first")
        sys.exit(1)

    model = "gpt-5-nano"

    # Generate general synthesis
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING GENERAL SYNTHESIS")
    logger.info("=" * 60)

    synthesis = await synthesize_from_articles(articles, model)
    synthesis_file = save_synthesis(synthesis, output_dir, mode="general")

    logger.info("\n" + "=" * 60)
    logger.info("General synthesis complete!")
    logger.info(f"Output: {synthesis_file}")
    logger.info("=" * 60)

    # Optional: Generate topic-focused synthesis
    # Uncomment and modify to use
    """
    topic = "open source"
    logger.info("\n" + "=" * 60)
    logger.info(f"GENERATING TOPIC-FOCUSED SYNTHESIS: {topic}")
    logger.info("=" * 60)

    topic_synthesis = await synthesize_by_topic(articles, topic, model, api_key)
    topic_file = save_synthesis(topic_synthesis, output_dir, mode=f"topic-{topic.replace(' ', '-')}")

    logger.info("\n" + "=" * 60)
    logger.info(f"Topic synthesis complete!")
    logger.info(f"Output: {topic_file}")
    logger.info("=" * 60)
    """

    # Print preview
    logger.info("\n" + "=" * 60)
    logger.info("SYNTHESIS PREVIEW")
    logger.info("=" * 60)
    print("\n" + synthesis[:500] + "...\n")


if __name__ == "__main__":
    asyncio.run(main())
