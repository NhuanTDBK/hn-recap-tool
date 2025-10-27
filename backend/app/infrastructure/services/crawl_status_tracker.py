"""Crawl status tracker for recording content extraction status."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CrawlStatusTracker:
    """Tracks the status of content crawling for each URL."""

    def __init__(self, status_file: str = "data/crawl_status.jsonl"):
        """Initialize status tracker.

        Args:
            status_file: Path to JSONL file for storing crawl status
        """
        self.status_file = Path(status_file)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure status file and directory exist."""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.status_file.exists():
            self.status_file.touch()

    def record_crawl(
        self,
        post_id: str,
        url: str,
        success: bool,
        has_content: bool,
        error: Optional[str] = None,
        content_length: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record crawl status for a URL.

        Args:
            post_id: HN post ID
            url: URL that was crawled
            success: Whether the crawl was successful
            has_content: Whether content was extracted
            error: Error message if failed
            content_length: Length of extracted content in characters
            metadata: Additional metadata
        """
        status_record = {
            "post_id": post_id,
            "url": url,
            "success": success,
            "has_content": has_content,
            "error": error,
            "content_length": content_length,
            "crawled_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        # Append to JSONL file
        with open(self.status_file, 'a', encoding='utf-8') as f:
            json_line = json.dumps(status_record, default=str)
            f.write(json_line + '\n')

        logger.info(f"Recorded crawl status for {post_id}: success={success}, has_content={has_content}")

    def get_crawl_status(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent crawl status for a post.

        Args:
            post_id: HN post ID

        Returns:
            Crawl status record if found, None otherwise
        """
        if not self.status_file.exists():
            return None

        # Read file in reverse to find most recent entry
        matching_record = None
        with open(self.status_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get('post_id') == post_id:
                        matching_record = record
                except json.JSONDecodeError:
                    continue

        return matching_record

    def is_already_crawled(self, post_id: str, success_only: bool = True) -> bool:
        """Check if a post has already been successfully crawled.

        Args:
            post_id: HN post ID
            success_only: If True, only consider successful crawls

        Returns:
            True if already crawled, False otherwise
        """
        status = self.get_crawl_status(post_id)
        if not status:
            return False

        if success_only:
            return status.get('success', False) and status.get('has_content', False)
        else:
            return True

    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get overall crawl statistics.

        Returns:
            Dictionary with crawl statistics
        """
        stats = {
            "total_crawls": 0,
            "successful": 0,
            "failed": 0,
            "with_content": 0,
            "without_content": 0,
            "unique_urls": set(),
            "unique_posts": set()
        }

        if not self.status_file.exists():
            return {k: v if not isinstance(v, set) else len(v) for k, v in stats.items()}

        with open(self.status_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    stats["total_crawls"] += 1

                    if record.get('success'):
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1

                    if record.get('has_content'):
                        stats["with_content"] += 1
                    else:
                        stats["without_content"] += 1

                    stats["unique_urls"].add(record.get('url'))
                    stats["unique_posts"].add(record.get('post_id'))

                except json.JSONDecodeError:
                    continue

        # Convert sets to counts
        return {
            "total_crawls": stats["total_crawls"],
            "successful": stats["successful"],
            "failed": stats["failed"],
            "with_content": stats["with_content"],
            "without_content": stats["without_content"],
            "unique_urls": len(stats["unique_urls"]),
            "unique_posts": len(stats["unique_posts"])
        }
