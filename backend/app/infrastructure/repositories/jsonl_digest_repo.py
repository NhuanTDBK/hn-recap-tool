"""JSONL implementation of DigestRepository."""

from pathlib import Path
from typing import Optional, List
import logging

from app.domain.entities import Digest
from app.application.interfaces import DigestRepository
from app.infrastructure.repositories.jsonl_helpers import (
    read_jsonl,
    write_jsonl
)

logger = logging.getLogger(__name__)


class JSONLDigestRepository(DigestRepository):
    """Digest repository using date-partitioned JSONL files."""

    def __init__(self, data_dir: str):
        """Initialize repository.

        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        logger.info(f"Initialized JSONLDigestRepository with data_dir: {data_dir}")

    def _get_file_path(self, date: str) -> str:
        """Get file path for a specific date's digest.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Path to digest file
        """
        return str(self.processed_dir / f"{date}-digest.jsonl")

    async def save(self, digest: Digest) -> Digest:
        """Save a digest to storage.

        Args:
            digest: Digest entity to save

        Returns:
            Saved digest
        """
        file_path = self._get_file_path(digest.date)
        digest_data = digest.model_dump()

        # Write digest (overwrite, not append)
        write_jsonl(file_path, digest_data, append=False)

        logger.info(f"Saved digest for {digest.date} with {len(digest.posts)} posts")
        return digest

    async def find_by_date(self, date: str) -> Optional[Digest]:
        """Find digest by date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Digest if found, None otherwise
        """
        file_path = self._get_file_path(date)

        if not Path(file_path).exists():
            return None

        # Read first (and only) line
        for record in read_jsonl(file_path):
            try:
                return Digest(**record)
            except Exception as e:
                logger.error(f"Failed to parse digest from {file_path}: {e}")
                return None

        return None

    async def list_digests(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Digest]:
        """List digests within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of digests to return

        Returns:
            List of digests sorted by date (newest first)
        """
        digests = []

        # Get all digest files, sorted by date (newest first)
        digest_files = sorted(
            self.processed_dir.glob("*-digest.jsonl"),
            reverse=True
        )

        for file_path in digest_files:
            # Extract date from filename (YYYY-MM-DD-digest.jsonl)
            date_str = file_path.stem.replace('-digest', '')

            # Filter by date range if provided
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue

            # Read digest
            for record in read_jsonl(str(file_path)):
                try:
                    digest = Digest(**record)
                    digests.append(digest)

                    if len(digests) >= limit:
                        return digests
                except Exception as e:
                    logger.error(f"Failed to parse digest from {file_path}: {e}")
                    continue

        logger.info(f"Found {len(digests)} digests in range {start_date} to {end_date}")
        return digests
