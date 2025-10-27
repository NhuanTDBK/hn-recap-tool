"""Enhanced content extractor with user agents, retries, and rate limiting."""

import asyncio
import random
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

logger = logging.getLogger(__name__)


class EnhancedContentExtractor:
    """Enhanced content extractor with robust crawling features."""

    # Comprehensive list of user agents
    USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        respect_robots_txt: bool = True
    ):
        """Initialize enhanced content extractor.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            respect_robots_txt: Whether to check robots.txt before crawling
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.respect_robots_txt = respect_robots_txt
        self._robots_cache = {}  # Cache robots.txt parsers

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(self.USER_AGENTS)

    async def _check_robots_txt(self, url: str) -> bool:
        """Check if crawling is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed, False otherwise
        """
        if not self.respect_robots_txt:
            return True

        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"

            # Check cache
            if robots_url in self._robots_cache:
                rp = self._robots_cache[robots_url]
            else:
                # Fetch and parse robots.txt
                rp = RobotFileParser()
                rp.set_url(robots_url)

                try:
                    # Use httpx to fetch robots.txt
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(robots_url)
                        if response.status_code == 200:
                            rp.parse(response.text.splitlines())
                        else:
                            # If robots.txt doesn't exist, allow crawling
                            return True
                except Exception:
                    # If can't fetch robots.txt, allow crawling
                    return True

                self._robots_cache[robots_url] = rp

            # Check if allowed for our user agent
            user_agent = "HNDigestBot/1.0 (+https://github.com/yourrepo)"
            allowed = rp.can_fetch(user_agent, url)

            if not allowed:
                logger.warning(f"Crawling disallowed by robots.txt: {url}")

            return allowed

        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, allow crawling (fail open)
            return True

    async def _random_delay(self) -> None:
        """Add random delay to avoid overwhelming servers."""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    async def extract_content(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Extract content from URL with retries and rate limiting.

        Args:
            url: URL to extract content from

        Returns:
            Tuple of (success: bool, html_content: str, extracted_text: str)
        """
        # Check robots.txt
        if not await self._check_robots_txt(url):
            return False, None, None

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                # Add delay before request (except first attempt)
                if attempt > 0:
                    await self._random_delay()
                    logger.info(f"Retry {attempt + 1}/{self.max_retries} for {url}")

                # Random user agent
                user_agent = self._get_random_user_agent()
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }

                logger.info(f"Fetching content from: {url}")

                # Fetch URL
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=headers
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    html_content = response.text

                    # Extract main content using trafilatura
                    extracted_text = trafilatura.extract(
                        html_content,
                        include_comments=False,
                        include_tables=True,
                        no_fallback=False
                    )

                    if extracted_text:
                        logger.info(f"✓ Successfully extracted {len(extracted_text)} characters from {url}")
                        return True, html_content, extracted_text
                    else:
                        logger.warning(f"No content extracted from {url}")
                        return False, html_content, None

            except httpx.HTTPStatusError as e:
                if e.response.status_code in [403, 404, 410]:
                    # Don't retry on client errors
                    logger.error(f"Client error {e.response.status_code} for {url}")
                    return False, None, None
                elif e.response.status_code == 429:
                    # Rate limited - wait longer
                    logger.warning(f"Rate limited for {url}, waiting longer...")
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.error(f"HTTP error {e.response.status_code} for {url}")
                    if attempt == self.max_retries - 1:
                        return False, None, None

            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching {url}")
                if attempt == self.max_retries - 1:
                    return False, None, None

            except Exception as e:
                logger.error(f"Error extracting content from {url}: {e}")
                if attempt == self.max_retries - 1:
                    return False, None, None

        # All retries failed
        logger.error(f"Failed to extract content from {url} after {self.max_retries} attempts")
        return False, None, None
