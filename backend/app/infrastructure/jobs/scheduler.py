"""APScheduler-based job scheduler for background tasks.

This module manages scheduled jobs including:
- Hourly: Collect top HackerNews posts
- Daily: Collect and process data (existing job)

Architecture:
- AsyncIOScheduler for async job support
- CronTrigger for precise scheduling
- Error handling and logging
- Graceful startup/shutdown
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.jobs.hourly_posts_collector import HourlyPostsCollectorJob
from app.infrastructure.jobs.hourly_delivery_job import HourlyDeliveryJob

logger = logging.getLogger(__name__)


class JobScheduler:
    """Manages APScheduler for background job scheduling."""

    def __init__(self):
        """Initialize job scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.hourly_collector: Optional[HourlyPostsCollectorJob] = None
        self.hourly_delivery: Optional[HourlyDeliveryJob] = None

    def register_hourly_collector(
        self, hourly_collector: HourlyPostsCollectorJob
    ) -> None:
        """Register the hourly posts collector job.

        Args:
            hourly_collector: HourlyPostsCollectorJob instance
        """
        self.hourly_collector = hourly_collector
        logger.info("Registered hourly posts collector job")

    def register_hourly_delivery(
        self, hourly_delivery: HourlyDeliveryJob
    ) -> None:
        """Register the hourly delivery job.

        Args:
            hourly_delivery: HourlyDeliveryJob instance
        """
        self.hourly_delivery = hourly_delivery
        logger.info("Registered hourly delivery job")

    def start(self) -> None:
        """Start the scheduler with all registered jobs.

        Jobs:
        - Every hour at :00 minutes: Collect top posts
        - Every hour at :05 minutes: Deliver summaries to users
        """
        jobs_registered = 0

        # Schedule hourly collection if registered
        if self.hourly_collector:
            logger.info("Scheduling hourly posts collection job")
            trigger = CronTrigger(minute=0, timezone="UTC")

            self.scheduler.add_job(
                self.hourly_collector.run_collection,
                trigger=trigger,
                id="hourly_posts_collection",
                name="Hourly HackerNews Posts Collection",
                replace_existing=True,
                max_instances=1,  # Prevent concurrent executions
            )
            jobs_registered += 1
            logger.info("Scheduled: Hourly posts collection at :00")
        else:
            logger.warning("No hourly collector registered, skipping collection job")

        # Schedule hourly delivery if registered
        if self.hourly_delivery:
            logger.info("Scheduling hourly delivery job")
            trigger = CronTrigger(minute=5, timezone="UTC")

            self.scheduler.add_job(
                self.hourly_delivery.run_delivery,
                trigger=trigger,
                id="hourly_delivery",
                name="Hourly Digest Delivery",
                replace_existing=True,
                max_instances=1,  # Prevent concurrent executions
            )
            jobs_registered += 1
            logger.info("Scheduled: Hourly delivery at :05")
        else:
            logger.warning("No hourly delivery registered, skipping delivery job")

        if jobs_registered == 0:
            logger.error("No jobs registered, scheduler will not start")
            return

        # Start scheduler
        self.scheduler.start()
        logger.info(f"Scheduler started - {jobs_registered} job(s) scheduled")

    def stop(self) -> None:
        """Stop the scheduler and all running jobs."""
        if self.scheduler.running:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        else:
            logger.info("Scheduler is not running")

    def add_job(
        self,
        func,
        trigger=None,
        id: str = None,
        name: str = None,
        **kwargs
    ) -> None:
        """Add a custom job to the scheduler.

        Args:
            func: Callable to execute
            trigger: APScheduler trigger (CronTrigger, IntervalTrigger, etc.)
            id: Unique job ID
            name: Job name
            **kwargs: Additional arguments for add_job()
        """
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=id,
            name=name,
            replace_existing=True,
            **kwargs
        )
        logger.info(f"Added job '{name}' with ID '{id}'")

    def get_jobs(self):
        """Get all scheduled jobs.

        Returns:
            List of scheduled jobs
        """
        return self.scheduler.get_jobs()

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler.

        Args:
            job_id: ID of job to remove
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job '{job_id}'")
        except Exception as e:
            logger.warning(f"Failed to remove job '{job_id}': {e}")

    def pause_job(self, job_id: str) -> None:
        """Pause a job (reschedule to never).

        Args:
            job_id: ID of job to pause
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job '{job_id}'")
        except Exception as e:
            logger.warning(f"Failed to pause job '{job_id}': {e}")

    def resume_job(self, job_id: str) -> None:
        """Resume a paused job.

        Args:
            job_id: ID of job to resume
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job '{job_id}'")
        except Exception as e:
            logger.warning(f"Failed to resume job '{job_id}': {e}")

    def trigger_job_now(self, job_id: str) -> None:
        """Manually trigger a job immediately (ignoring schedule).

        Args:
            job_id: ID of job to trigger
        """
        job = self.scheduler.get_job(job_id)
        if not job:
            logger.warning(f"Job '{job_id}' not found")
            return

        logger.info(f"Triggering job '{job_id}' immediately")
        try:
            job.func(*job.args, **job.kwargs)
        except Exception as e:
            logger.error(f"Error triggering job '{job_id}': {e}")

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if scheduler is running, False otherwise
        """
        return self.scheduler.running
