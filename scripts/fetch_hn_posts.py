#!/usr/bin/env python3
"""
Standalone script to fetch recent HackerNews posts.

This script fetches the current front page stories from HackerNews
and saves them to a JSONL file in the data directory.

Usage:
    python scripts/fetch_hn_posts.py [--limit 30] [--output data/raw]
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import httpx


class HNFetcher:
    """Fetches posts from HackerNews Algolia API."""

    BASE_URL = "https://hn.algolia.com/api/v1"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def fetch_front_page(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Fetch front page stories from HackerNews.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of story dictionaries
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "tags": "front_page",
            "hitsPerPage": limit
        }

        print(f"Fetching {limit} front page stories from HackerNews...")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", [])

            print(f"✓ Fetched {len(hits)} stories")
            return hits

    def transform_post(self, raw_post: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw HN API data to our format.

        Args:
            raw_post: Raw post data from HN API

        Returns:
            Transformed post dictionary
        """
        # Determine post type
        title = raw_post.get('title', '').lower()
        if title.startswith('ask hn'):
            post_type = 'ask'
        elif title.startswith('show hn'):
            post_type = 'show'
        elif raw_post.get('url', '').endswith('/jobs'):
            post_type = 'job'
        else:
            post_type = 'story'

        return {
            "hn_id": raw_post.get('objectID'),
            "title": raw_post.get('title'),
            "author": raw_post.get('author'),
            "points": raw_post.get('points', 0),
            "num_comments": raw_post.get('num_comments', 0),
            "created_at": raw_post.get('created_at'),
            "url": raw_post.get('url'),
            "post_type": post_type,
            "collected_at": datetime.utcnow().isoformat()
        }

    def save_to_jsonl(self, posts: List[Dict[str, Any]], output_dir: Path) -> str:
        """Save posts to a JSONL file.

        Args:
            posts: List of post dictionaries
            output_dir: Output directory path

        Returns:
            Path to saved file
        """
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with today's date
        today = datetime.utcnow().strftime('%Y-%m-%d')
        output_file = output_dir / f"{today}-posts.jsonl"

        # Write to JSONL file
        with open(output_file, 'w', encoding='utf-8') as f:
            for post in posts:
                json_line = json.dumps(post, default=str)
                f.write(json_line + '\n')

        print(f"✓ Saved {len(posts)} posts to {output_file}")
        return str(output_file)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch recent HackerNews front page posts"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='Maximum number of posts to fetch (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/raw',
        help='Output directory (default: data/raw)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )

    args = parser.parse_args()

    try:
        # Initialize fetcher
        fetcher = HNFetcher(timeout=args.timeout)

        # Fetch posts
        raw_posts = await fetcher.fetch_front_page(limit=args.limit)

        if not raw_posts:
            print("⚠ No posts fetched")
            return 1

        # Transform posts
        print("Transforming posts...")
        posts = [fetcher.transform_post(post) for post in raw_posts]

        # Save to file
        output_dir = Path(args.output)
        output_file = fetcher.save_to_jsonl(posts, output_dir)

        print(f"\n✓ Success! Fetched {len(posts)} posts")
        print(f"  Output: {output_file}")

        # Display sample
        print("\n📊 Sample posts:")
        for i, post in enumerate(posts[:5], 1):
            print(f"  {i}. [{post['points']} pts] {post['title']}")
            print(f"     by {post['author']} | {post['num_comments']} comments")

        if len(posts) > 5:
            print(f"  ... and {len(posts) - 5} more")

        return 0

    except httpx.HTTPError as e:
        print(f"✗ HTTP error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
