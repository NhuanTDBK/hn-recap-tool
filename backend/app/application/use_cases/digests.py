"""Digest use cases - Retrieving and displaying digests."""

from typing import List, Optional
from datetime import datetime, timedelta

from app.domain.entities import Digest, Post
from app.domain.exceptions import DigestNotFoundError, PostNotFoundError
from app.application.interfaces import (
    DigestRepository,
    PostRepository,
    CacheService
)


class GetDigestByDateUseCase:
    """Use case for retrieving a digest by date."""

    def __init__(
        self,
        digest_repo: DigestRepository,
        cache_service: Optional[CacheService] = None
    ):
        self.digest_repo = digest_repo
        self.cache_service = cache_service

    async def execute(self, date: str) -> Digest:
        """Get digest for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Digest entity for that date

        Raises:
            DigestNotFoundError: If no digest exists for that date
        """
        # Try cache first if available
        if self.cache_service:
            cache_key = f"digest:{date}"
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                return Digest.model_validate_json(cached_data)

        # Fetch from repository
        digest = await self.digest_repo.find_by_date(date)
        if not digest:
            raise DigestNotFoundError(date)

        # Cache the result
        if self.cache_service:
            await self.cache_service.set(
                cache_key,
                digest.model_dump_json(),
                ttl=3600  # 1 hour
            )

        return digest


class ListDigestsUseCase:
    """Use case for listing digests within a date range."""

    def __init__(self, digest_repo: DigestRepository):
        self.digest_repo = digest_repo

    async def execute(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> List[Digest]:
        """List digests within a date range.

        Args:
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to today)
            limit: Maximum number of digests to return

        Returns:
            List of digest entities
        """
        # Set defaults if not provided
        if not end_date:
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
        if not start_date:
            start = datetime.utcnow() - timedelta(days=30)
            start_date = start.strftime('%Y-%m-%d')

        # Fetch from repository
        digests = await self.digest_repo.list_digests(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return digests


class GetPostDetailUseCase:
    """Use case for retrieving a single post with full details."""

    def __init__(
        self,
        post_repo: PostRepository,
        cache_service: Optional[CacheService] = None
    ):
        self.post_repo = post_repo
        self.cache_service = cache_service

    async def execute(self, post_id: str) -> Post:
        """Get full details for a specific post.

        Args:
            post_id: Post's unique identifier

        Returns:
            Post entity with full details

        Raises:
            PostNotFoundError: If post doesn't exist
        """
        # Try cache first if available
        if self.cache_service:
            cache_key = f"post:{post_id}"
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                return Post.model_validate_json(cached_data)

        # Fetch from repository
        post = await self.post_repo.find_by_id(post_id)
        if not post:
            raise PostNotFoundError(post_id)

        # Cache the result
        if self.cache_service:
            await self.cache_service.set(
                cache_key,
                post.model_dump_json(),
                ttl=7200  # 2 hours
            )

        return post


class GetLatestDigestUseCase:
    """Use case for retrieving the most recent digest."""

    def __init__(self, digest_repo: DigestRepository):
        self.digest_repo = digest_repo

    async def execute(self) -> Digest:
        """Get the most recent digest available.

        Returns:
            Latest digest entity

        Raises:
            DigestNotFoundError: If no digests exist
        """
        # Get today's date
        today = datetime.utcnow().strftime('%Y-%m-%d')

        # Try to find today's digest first
        digest = await self.digest_repo.find_by_date(today)
        if digest:
            return digest

        # If not found, try yesterday
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        digest = await self.digest_repo.find_by_date(yesterday)
        if digest:
            return digest

        # If still not found, get the most recent one
        digests = await self.digest_repo.list_digests(limit=1)
        if not digests:
            raise DigestNotFoundError("latest")

        return digests[0]
