#!/usr/bin/env python3
"""Full automation script for HackerNews digest pipeline.

This script runs the complete flow:
1. Fetch HackerNews posts
2. Crawl article content
3. Generate AI summaries
4. Push to Telegram

Usage:
    python scripts/run_full_flow.py
    python scripts/run_full_flow.py --date 2025-10-27
    python scripts/run_full_flow.py --start_date 2025-10-25 --end_date 2025-10-27
    python scripts/run_full_flow.py --skip-fetch  # Skip fetching, use existing data
    python scripts/run_full_flow.py --skip-push   # Don't push to Telegram
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def run_command(script_name: str, *args) -> bool:
    """Run a Python script as a subprocess.

    Args:
        script_name: Name of the script to run
        *args: Additional arguments for the script

    Returns:
        True if successful, False otherwise
    """
    script_path = project_root / "scripts" / script_name

    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + list(args)
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            logger.info(f"Output:\n{stdout.decode()}")
        if stderr:
            logger.error(f"Errors:\n{stderr.decode()}")

        if process.returncode == 0:
            logger.info(f"✓ {script_name} completed successfully")
            return True
        else:
            logger.error(f"✗ {script_name} failed with return code {process.returncode}")
            return False

    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")
        return False


async def main():
    """Main function to run the full pipeline."""
    parser = argparse.ArgumentParser(
        description="Run full HackerNews digest pipeline"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Single date to process (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="Start date for date range (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date for date range (YYYY-MM-DD format)",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip fetching posts (use existing data)",
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip crawling content (use existing content)",
    )
    parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip pushing to Telegram",
    )

    args = parser.parse_args()

    # Determine date range
    if args.date:
        start_date = args.date
        end_date = args.date
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.start_date:
        start_date = args.start_date
        end_date = datetime.now().strftime("%Y-%m-%d")
    else:
        # Default to today
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = start_date

    logger.info("=" * 60)
    logger.info("STARTING HACKERNEWS DIGEST PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Skip fetch: {args.skip_fetch}")
    logger.info(f"Skip crawl: {args.skip_crawl}")
    logger.info(f"Skip push: {args.skip_push}")
    logger.info("=" * 60)

    # Step 1: Fetch HackerNews posts
    if not args.skip_fetch:
        logger.info("\n[Step 1/4] Fetching HackerNews posts...")
        if not await run_command("fetch_hn_posts.py"):
            logger.error("Failed to fetch posts. Exiting.")
            sys.exit(1)
    else:
        logger.info("\n[Step 1/4] Skipping fetch (using existing data)")

    # Step 2: Crawl article content
    if not args.skip_crawl:
        logger.info("\n[Step 2/4] Crawling article content...")
        if not await run_command("crawl_content.py"):
            logger.error("Failed to crawl content. Exiting.")
            sys.exit(1)
    else:
        logger.info("\n[Step 2/4] Skipping crawl (using existing content)")

    # Step 3: Generate summaries
    logger.info("\n[Step 3/4] Generating AI summaries...")
    summarization_args = ["--start_time", start_date, "--end_time", end_date]
    if not await run_command("run_summarization.py", *summarization_args):
        logger.error("Failed to generate summaries. Exiting.")
        sys.exit(1)

    # Step 4: Push to Telegram
    if not args.skip_push:
        logger.info("\n[Step 4/4] Pushing to Telegram...")
        if not await run_command("push_to_telegram.py"):
            logger.error("Failed to push to Telegram. Exiting.")
            sys.exit(1)
    else:
        logger.info("\n[Step 4/4] Skipping Telegram push")

    # Success!
    logger.info("\n" + "=" * 60)
    logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info("All steps completed:")
    if not args.skip_fetch:
        logger.info("  ✓ Fetched HackerNews posts")
    if not args.skip_crawl:
        logger.info("  ✓ Crawled article content")
    logger.info("  ✓ Generated AI summaries")
    if not args.skip_push:
        logger.info("  ✓ Pushed to Telegram")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nPipeline failed with error: {e}")
        sys.exit(1)
