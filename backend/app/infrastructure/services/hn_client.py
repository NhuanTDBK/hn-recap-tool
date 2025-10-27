"""HackerNews API client implementation."""

from typing import List, Optional
import httpx
import logging

from app.application.interfaces import HNService
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class AlgoliaHNClient(HNService):
    """HackerNews client using Algolia API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize HN API client.

        Args:
            base_url: Base URL for HN API (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = base_url or settings.hn_api_base_url
        self.timeout = timeout or settings.hn_api_timeout

    async def fetch_front_page(self, limit: int = 30) -> List[dict]:
        """Fetch front page stories from HackerNews.

        Args:
            limit: Maximum number of stories to fetch

        Returns:
            List of raw HN story data

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}/search"
        params = {
            "tags": "front_page",
            "hitsPerPage": limit
        }

        logger.info(f"Fetching {limit} front page stories from HN")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", [])

            logger.info(f"Fetched {len(hits)} stories from HN")
            return hits

    async def fetch_item(self, item_id: int) -> Optional[dict]:
        """Fetch a specific item (story/comment) by ID.

        Args:
            item_id: HN item ID

        Returns:
            Raw HN item data if found, None otherwise

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}/items/{item_id}"

        logger.debug(f"Fetching HN item {item_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"HN item {item_id} not found")
                    return None
                raise

    async def fetch_comments(self, post_id: int, limit: int = 50) -> List[dict]:
        """Fetch comments for a specific post.

        Args:
            post_id: HN post ID
            limit: Maximum number of comments to fetch

        Returns:
            List of raw HN comment data

        Raises:
            httpx.HTTPError: If request fails
        """
        url = f"{self.base_url}/search"
        params = {
            "tags": f"comment,story_{post_id}",
            "hitsPerPage": limit
        }

        logger.info(f"Fetching comments for HN post {post_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", [])

            logger.info(f"Fetched {len(hits)} comments for post {post_id}")
            return hits
