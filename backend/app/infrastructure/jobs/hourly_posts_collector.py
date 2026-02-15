"""Hourly job for collecting top HackerNews posts by recent date.

This job:
1. Fetches top stories from HackerNews API
2. Stores posts in PostgreSQL database
3. Caches post metadata in RocksDB for quick access
4. Runs every hour to keep data fresh

Architecture:
- Uses APScheduler for hourly cron scheduling
- Async/await for non-blocking I/O
- Batch operations for efficiency
- Error handling with retries
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from app.domain.entities import Post
from app.infrastructure.services.firebase_hn_client import FirebaseHNClient
from app.infrastructure.repositories.postgres.post_repo import PostgresPostRepository
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


class HourlyPostsCollectorJob:
    """Collects top HackerNews posts hourly and stores in PostgreSQL + RocksDB."""

    def __init__(
        self,
        post_repository: PostgresPostRepository,
        rocksdb_store: RocksDBContentStore,
        hn_client: Optional[FirebaseHNClient] = None,
        score_threshold: int = 50,
        limit: int = 100,
    ):
        """Initialize hourly posts collector job.

        Args:
            post_repository: PostgreSQL repository for posts
            rocksdb_store: RocksDB store for metadata caching
            hn_client: HackerNews Firebase client (default: new instance)
            score_threshold: Minimum score to collect posts
            limit: Maximum number of posts to collect per run
        """
        self.post_repository = post_repository
        self.rocksdb_store = rocksdb_store
        self.hn_client = hn_client or FirebaseHNClient()
        self.score_threshold = score_threshold
        self.limit = limit
        self.stats = {
            "posts_fetched": 0,
            "posts_saved": 0,
            "posts_cached": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "last_run": None,
        }

    async def collect_top_posts(self) -> dict:
        """Collect and store top posts from HackerNews.

        Returns:
            Statistics dictionary with collection results
        """
        logger.info(
            f"Starting hourly posts collection "
            f"(threshold: {self.score_threshold}, limit: {self.limit})"
        )

        self.stats = {
            "posts_fetched": 0,
            "posts_saved": 0,
            "posts_cached": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "last_run": datetime.utcnow().isoformat(),
        }

        try:
            # Step 1: Fetch top stories from HN
            logger.info("Step 1: Fetching top stories from HackerNews")
            stories = await self._fetch_top_stories()
            self.stats["posts_fetched"] = len(stories)
            logger.info(f"Fetched {len(stories)} stories from HN")

            if not stories:
                logger.warning("No stories fetched from HN")
                return self.stats

            # Step 2: Check existing IDs in batch and filter duplicates
            logger.info("Step 2: Checking existing posts in batch")
            story_ids = [int(s["id"]) for s in stories if s.get("id")]
            existing_ids = await self.post_repository.find_existing_hn_ids(story_ids)
            self.stats["duplicates_skipped"] = len(existing_ids)
            logger.info(f"Found {len(existing_ids)} existing posts to skip")

            # Step 3: Convert non-duplicate stories to domain entities
            logger.info("Step 3: Processing new stories")
            posts_to_save = []
            for story in stories:
                try:
                    story_id = int(story["id"])
                    if story_id in existing_ids:
                        logger.debug(f"Post {story_id} already exists, skipping")
                        continue

                    post = self._transform_story_to_post(story)
                    posts_to_save.append(post)
                except Exception as e:
                    logger.warning(f"Failed to process story {story.get('id')}: {e}")
                    self.stats["errors"] += 1
                    continue

            logger.info(f"Processing complete: {len(posts_to_save)} new posts to save")

            if not posts_to_save:
                logger.info("No new posts to save")
                return self.stats

            # Step 4: Save posts to PostgreSQL in batch
            logger.info("Step 4: Saving posts to PostgreSQL")
            try:
                saved_posts = await self.post_repository.save_batch(posts_to_save)
                self.stats["posts_saved"] = len(saved_posts)
                logger.info(f"Saved {len(saved_posts)} posts to PostgreSQL")
            except Exception as e:
                logger.error(f"Failed to save posts to PostgreSQL: {e}")
                self.stats["errors"] += 1
                return self.stats

            # Step 5: Cache post metadata in RocksDB
            logger.info("Step 5: Caching post metadata in RocksDB")
            for post in saved_posts:
                try:
                    await self._cache_post_metadata(post)
                    self.stats["posts_cached"] += 1
                except Exception as e:
                    logger.warning(f"Failed to cache post {post.hn_id}: {e}")
                    continue

            logger.info(
                f"Hourly collection complete: "
                f"{self.stats['posts_saved']} saved, "
                f"{self.stats['posts_cached']} cached, "
                f"{self.stats['duplicates_skipped']} duplicates skipped"
            )

            return self.stats

        except Exception as e:
            logger.error(f"Hourly posts collection failed: {e}", exc_info=True)
            self.stats["errors"] += 1
            raise

    async def _fetch_top_stories(self) -> List[dict]:
        """Fetch top stories from HackerNews API.

        Returns:
            List of story dictionaries with score >= threshold
        """
        try:
            # Fetch top stories (Firebase API provides topstories)
            stories = await self.hn_client.fetch_front_page(limit=self.limit)

            # Filter by score threshold
            filtered_stories = [
                s for s in stories if s.get("score", 0) >= self.score_threshold
            ]

            logger.info(
                f"Fetched {len(stories)} stories, "
                f"{len(filtered_stories)} meet threshold"
            )
            return filtered_stories

        except Exception as e:
            logger.error(f"Failed to fetch top stories: {e}")
            raise

    def _transform_story_to_post(self, story: dict) -> Post:
        """Transform HackerNews story to domain Post entity.

        Args:
            story: Raw story dictionary from HN API

        Returns:
            Domain Post entity
        """
        # Use Firebase client's transformation method
        post_dict = FirebaseHNClient.transform_item_to_post(story)

        return Post(
            hn_id=int(post_dict["hn_id"]),
            title=post_dict["title"],
            author=post_dict["author"] or "unknown",
            url=post_dict["url"],
            points=post_dict["points"],
            num_comments=post_dict["num_comments"],
            post_type=post_dict["post_type"],
            created_at=post_dict["created_at"],
            collected_at=datetime.utcnow(),
        )

    async def _cache_post_metadata(self, post: Post) -> None:
        """Cache post metadata in RocksDB for quick access.

        Args:
            post: Post entity to cache
        """
        metadata = {
            "hn_id": int(post.hn_id),
            "title": post.title,
            "author": post.author,
            "url": post.url,
            "points": post.points,
            "num_comments": post.num_comments,
            "post_type": post.post_type,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "collected_at": datetime.utcnow().isoformat(),
        }

        # Store as JSON in RocksDB with special "metadata:" prefix
        key = f"metadata:{int(post.hn_id)}".encode("utf-8")
        value = json.dumps(metadata).encode("utf-8")

        # RocksDB store expects async but rocksdict is sync
        # We'll handle this by storing directly
        self.rocksdb_store.db[key] = value
        logger.debug(f"Cached metadata for post {post.hn_id}")

    def get_stats(self) -> dict:
        """Get collection statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats

    async def run_collection(self) -> dict:
        """Run the hourly collection job.

        This is the main entry point called by APScheduler.

        Returns:
            Statistics dictionary
        """
        logger.info("=" * 60)
        logger.info("HOURLY POSTS COLLECTION JOB STARTED")
        logger.info("=" * 60)

        try:
            stats = await self.collect_top_posts()
            logger.info("=" * 60)
            logger.info(f"COLLECTION COMPLETE - Stats: {stats}")
            logger.info("=" * 60)
            return stats
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"COLLECTION FAILED - Error: {e}")
            logger.error("=" * 60)
            raise
