"""Firebase HackerNews API client for incremental scanning."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.application.interfaces import HNService

logger = logging.getLogger(__name__)


class FirebaseHNClient(HNService):
    """HackerNews client using Firebase API for incremental scanning.

    The Firebase API provides more reliable access to HN data with:
    - /v0/maxitem endpoint for latest item ID
    - /v0/item/{id} endpoint for individual items
    - No rate limits documented
    - Better for incremental scanning (only fetch new items)
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, timeout: int = 10):
        """Initialize Firebase HN client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    async def get_max_item_id(self) -> Optional[int]:
        """Get the current maximum item ID from HN.

        Returns:
            Latest item ID, or None if request fails
        """
        url = f"{self.BASE_URL}/maxitem.json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                max_id = response.json()
                logger.info(f"Max item ID: {max_id}")
                return max_id
        except Exception as e:
            logger.error(f"Failed to get max item ID: {e}")
            return None

    async def fetch_item(self, item_id: int) -> Optional[dict]:
        """Fetch a specific item by ID.

        Args:
            item_id: HN item ID

        Returns:
            Item data if found, None otherwise
        """
        url = f"{self.BASE_URL}/item/{item_id}.json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Item {item_id} not found (404)")
                return None
            logger.error(f"HTTP error fetching item {item_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching item {item_id}: {e}")
            return None

    async def fetch_items_batch(
        self, start_id: int, end_id: int, max_concurrent: int = 10
    ) -> List[dict]:
        """Fetch multiple items in parallel.

        Args:
            start_id: Starting item ID (inclusive)
            end_id: Ending item ID (inclusive)
            max_concurrent: Maximum concurrent requests

        Returns:
            List of item dictionaries (only successful fetches)
        """
        logger.info(f"Fetching items {start_id} to {end_id} ({end_id - start_id + 1} items)")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(item_id: int):
            async with semaphore:
                return await self.fetch_item(item_id)

        # Create tasks for all IDs
        tasks = [fetch_with_semaphore(i) for i in range(start_id, end_id + 1)]

        # Fetch all items
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch fetch: {result}")
                continue
            if result is not None:
                items.append(result)

        logger.info(f"Successfully fetched {len(items)} items")
        return items

    async def fetch_new_items(
        self, last_id: int, score_threshold: int = 100, max_items: int = 1000
    ) -> List[dict]:
        """Fetch new items since last_id, filtering by score.

        Args:
            last_id: Last processed item ID
            score_threshold: Minimum score for posts
            max_items: Maximum number of items to process

        Returns:
            List of filtered story items
        """
        # Get current max ID
        max_id = await self.get_max_item_id()
        if max_id is None:
            logger.error("Failed to get max item ID")
            return []

        # Calculate range to fetch
        start_id = last_id + 1
        end_id = min(start_id + max_items - 1, max_id)

        if start_id > max_id:
            logger.info(f"No new items (last: {last_id}, current max: {max_id})")
            return []

        logger.info(f"Scanning {end_id - start_id + 1} new items ({start_id} → {end_id})")

        # Fetch items in batches
        items = await self.fetch_items_batch(start_id, end_id)

        # Filter for stories with score >= threshold
        stories = []
        for item in items:
            if not item:
                continue

            # Only process stories (not comments, jobs, polls)
            if item.get("type") != "story":
                continue

            # Skip deleted or dead items
            if item.get("deleted") or item.get("dead"):
                continue

            # Check score threshold
            score = item.get("score", 0)
            if score < score_threshold:
                continue

            stories.append(item)

        logger.info(
            f"Found {len(stories)} stories with score >= {score_threshold} "
            f"(from {len(items)} total items)"
        )
        return stories

    async def fetch_front_page(self, limit: int = 30) -> List[dict]:
        """Fetch front page stories from HackerNews.

        Note: This is a compatibility method. For production, use fetch_new_items()
        for incremental scanning.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of story dictionaries
        """
        url = f"{self.BASE_URL}/topstories.json"

        logger.info(f"Fetching top {limit} stories from HN")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get list of top story IDs
                response = await client.get(url)
                response.raise_for_status()
                story_ids = response.json()[:limit]

                logger.info(f"Got {len(story_ids)} story IDs")

                # Fetch each story
                stories = []
                for story_id in story_ids:
                    story = await self.fetch_item(story_id)
                    if story:
                        stories.append(story)

                logger.info(f"Fetched {len(stories)} stories")
                return stories

        except Exception as e:
            logger.error(f"Error fetching front page: {e}")
            return []

    async def fetch_comments(self, post_id: int, limit: int = 50) -> List[dict]:
        """Fetch comments for a specific post.

        Args:
            post_id: HN post ID
            limit: Maximum number of comments to fetch

        Returns:
            List of comment dictionaries
        """
        # First get the post to get comment IDs
        post = await self.fetch_item(post_id)
        if not post or "kids" not in post:
            logger.info(f"No comments for post {post_id}")
            return []

        comment_ids = post["kids"][:limit]
        logger.info(f"Fetching {len(comment_ids)} comments for post {post_id}")

        # Fetch comments in parallel
        comments = []
        for comment_id in comment_ids:
            comment = await self.fetch_item(comment_id)
            if comment:
                comments.append(comment)

        logger.info(f"Fetched {len(comments)} comments")
        return comments

    @staticmethod
    def transform_item_to_post(item: dict) -> dict:
        """Transform Firebase API item to our post format.

        Args:
            item: Raw item from Firebase API

        Returns:
            Transformed post dictionary
        """
        # Extract domain from URL
        domain = None
        url = item.get("url")
        if url:
            parsed = urlparse(url)
            domain = parsed.netloc

        # Determine post type
        title = item.get("title", "").lower()
        if title.startswith("ask hn"):
            post_type = "ask"
        elif title.startswith("show hn"):
            post_type = "show"
        elif item.get("type") == "job":
            post_type = "job"
        else:
            post_type = "story"

        return {
            "hn_id": item.get("id"),
            "title": item.get("title"),
            "author": item.get("by"),
            "url": url,
            "domain": domain,
            "points": item.get("score", 0),
            "num_comments": len(item.get("kids", [])),
            "created_at": datetime.fromtimestamp(item.get("time", 0)),
            "post_type": post_type,
            "collected_at": datetime.utcnow(),
        }
