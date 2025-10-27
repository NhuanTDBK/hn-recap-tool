"""JSONL implementation of ContentRepository for file-based content storage."""

from pathlib import Path
from typing import Optional
import logging

import aiofiles

from backend.app.application.interfaces import ContentRepository

logger = logging.getLogger(__name__)


class JSONLContentRepository(ContentRepository):
    """Content repository using file-based storage for HTML and text content."""

    def __init__(self, data_dir: str):
        """Initialize repository.

        Args:
            data_dir: Base directory for data storage (e.g., ../data)
        """
        self.data_dir = Path(data_dir)
        self.text_dir = self.data_dir / "content" / "text"
        self.html_dir = self.data_dir / "content" / "html"

        # Ensure directories exist
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized JSONLContentRepository with data_dir: {data_dir}")

    def _get_text_file_path(self, hn_id: int) -> Path:
        """Get file path for text content.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Path to text file
        """
        return self.text_dir / f"{hn_id}.txt"

    def _get_html_file_path(self, hn_id: int) -> Path:
        """Get file path for HTML content.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Path to HTML file
        """
        return self.html_dir / f"{hn_id}.html"

    async def save_text_content(self, hn_id: int, content: str) -> None:
        """Save text content for a post.

        Args:
            hn_id: HackerNews post ID
            content: Extracted text content
        """
        file_path = self._get_text_file_path(hn_id)
        try:
            async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
                await f.write(content)
            logger.debug(f"Saved text content for post {hn_id}")
        except Exception as e:
            logger.error(f"Failed to save text content for post {hn_id}: {e}")
            raise

    async def save_html_content(self, hn_id: int, html: str) -> None:
        """Save HTML content for a post.

        Args:
            hn_id: HackerNews post ID
            html: Raw HTML content
        """
        file_path = self._get_html_file_path(hn_id)
        try:
            async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
                await f.write(html)
            logger.debug(f"Saved HTML content for post {hn_id}")
        except Exception as e:
            logger.error(f"Failed to save HTML content for post {hn_id}: {e}")
            raise

    async def get_text_content(self, hn_id: int) -> Optional[str]:
        """Retrieve text content for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            Text content if exists, None otherwise
        """
        file_path = self._get_text_file_path(hn_id)

        if not file_path.exists():
            logger.debug(f"No text content found for post {hn_id}")
            return None

        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                content = await f.read()
            logger.debug(f"Retrieved text content for post {hn_id}")
            return content
        except Exception as e:
            logger.error(f"Failed to read text content for post {hn_id}: {e}")
            return None

    async def get_html_content(self, hn_id: int) -> Optional[str]:
        """Retrieve HTML content for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            HTML content if exists, None otherwise
        """
        file_path = self._get_html_file_path(hn_id)

        if not file_path.exists():
            logger.debug(f"No HTML content found for post {hn_id}")
            return None

        try:
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                html = await f.read()
            logger.debug(f"Retrieved HTML content for post {hn_id}")
            return html
        except Exception as e:
            logger.error(f"Failed to read HTML content for post {hn_id}: {e}")
            return None

    async def text_content_exists(self, hn_id: int) -> bool:
        """Check if text content exists for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            True if text content exists, False otherwise
        """
        file_path = self._get_text_file_path(hn_id)
        return file_path.exists()

    async def html_content_exists(self, hn_id: int) -> bool:
        """Check if HTML content exists for a post.

        Args:
            hn_id: HackerNews post ID

        Returns:
            True if HTML content exists, False otherwise
        """
        file_path = self._get_html_file_path(hn_id)
        return file_path.exists()
