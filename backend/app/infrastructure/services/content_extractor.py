"""Article content extraction service using trafilatura."""

from typing import Optional
import trafilatura
import httpx
import logging

from app.application.interfaces import ContentExtractor
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class TrafilaturaContentExtractor(ContentExtractor):
    """Content extractor using trafilatura library."""

    def __init__(self, timeout: Optional[int] = None):
        """Initialize content extractor.

        Args:
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.timeout = timeout or settings.content_extraction_timeout

    async def extract_content(self, url: str) -> Optional[str]:
        """Extract main content from a URL.

        Args:
            url: Article URL to extract from

        Returns:
            Extracted text content if successful, None otherwise
        """
        logger.info(f"Extracting content from: {url}")

        try:
            # Fetch the URL
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

            # Extract main content
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if content:
                logger.info(f"Successfully extracted {len(content)} characters from {url}")
                return content
            else:
                logger.warning(f"No content extracted from {url}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Content extraction error for {url}: {e}")
            return None
