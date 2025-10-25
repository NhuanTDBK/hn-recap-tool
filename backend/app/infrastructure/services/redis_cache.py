"""Redis cache service implementation."""

from typing import Optional
import redis.asyncio as redis
import logging

from app.application.interfaces import CacheService
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class RedisCacheService(CacheService):
    """Cache service using Redis."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis cache service.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection.

        Returns:
            Redis client instance
        """
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None otherwise
        """
        try:
            client = await self._get_redis()
            value = await client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
            else:
                logger.debug(f"Cache miss: {key}")
            return value
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        try:
            client = await self._get_redis()
            await client.setex(key, ttl, value)
            logger.debug(f"Cached key: {key} with TTL {ttl}s")
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key to delete
        """
        try:
            client = await self._get_redis()
            await client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")
