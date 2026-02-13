"""Background job scheduling and management.

This module provides:
- APScheduler-based job scheduling
- Hourly HackerNews posts collection
- Job factory for dependency injection
- Data storage in PostgreSQL and RocksDB
"""

from app.infrastructure.jobs.factory import SchedulerFactory
from app.infrastructure.jobs.hourly_posts_collector import HourlyPostsCollectorJob
from app.infrastructure.jobs.scheduler import JobScheduler

__all__ = [
    "JobScheduler",
    "HourlyPostsCollectorJob",
    "SchedulerFactory",
]
