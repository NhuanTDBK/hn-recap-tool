"""Factory for creating and initializing job scheduler with dependencies.

This module handles:
- Dependency injection for jobs
- Initialization of repositories and services
- Scheduler configuration
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.jobs.hourly_posts_collector import HourlyPostsCollectorJob
from app.infrastructure.jobs.scheduler import JobScheduler
from app.infrastructure.repositories.postgres.post_repo import PostgresPostRepository
from app.infrastructure.services.firebase_hn_client import FirebaseHNClient
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

logger = logging.getLogger(__name__)


class SchedulerFactory:
    """Factory for creating configured job scheduler."""

    @staticmethod
    def create_scheduler(
        db_session: AsyncSession,
        rocksdb_path: str = "data/content.rocksdb",
        score_threshold: int = 50,
        posts_limit: int = 100,
        hn_client: Optional[FirebaseHNClient] = None,
    ) -> JobScheduler:
        """Create and configure job scheduler with all dependencies.

        Args:
            db_session: Async SQLAlchemy session
            rocksdb_path: Path to RocksDB database
            score_threshold: Minimum score for posts
            posts_limit: Maximum posts to collect per run
            hn_client: Optional custom HN client

        Returns:
            Configured JobScheduler instance
        """
        logger.info("Creating job scheduler with dependencies")

        # Create repositories and services
        post_repository = PostgresPostRepository(db_session)
        rocksdb_store = RocksDBContentStore(rocksdb_path)
        hn_client = hn_client or FirebaseHNClient()

        # Create hourly collector job
        hourly_collector = HourlyPostsCollectorJob(
            post_repository=post_repository,
            rocksdb_store=rocksdb_store,
            hn_client=hn_client,
            score_threshold=score_threshold,
            limit=posts_limit,
        )

        # Create and register scheduler
        scheduler = JobScheduler()
        scheduler.register_hourly_collector(hourly_collector)

        logger.info("Job scheduler created and configured")
        return scheduler
