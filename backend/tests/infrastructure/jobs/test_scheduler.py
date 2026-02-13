"""Tests for job scheduler."""

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.jobs.scheduler import JobScheduler


class MockHourlyCollector:
    """Mock hourly collector with async method."""

    async def run_collection(self):
        """Mock collection method."""
        return {"posts_saved": 5}


class TestJobScheduler:
    """Test JobScheduler functionality."""

    @pytest.fixture
    def mock_hourly_collector(self):
        """Create mock hourly collector."""
        return MockHourlyCollector()

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return JobScheduler()

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.scheduler is not None
        assert scheduler.hourly_collector is None
        assert not scheduler.is_running()

    def test_register_hourly_collector(self, scheduler, mock_hourly_collector):
        """Test registering hourly collector."""
        scheduler.register_hourly_collector(mock_hourly_collector)

        assert scheduler.hourly_collector is not None
        assert scheduler.hourly_collector == mock_hourly_collector

    def test_scheduler_structure(self, scheduler):
        """Test scheduler has proper structure."""
        assert scheduler.scheduler is not None
        assert hasattr(scheduler.scheduler, 'add_job')
        assert hasattr(scheduler.scheduler, 'get_jobs')

    def test_add_custom_job(self, scheduler):
        """Test adding custom job without starting scheduler."""
        def custom_func():
            pass

        trigger = CronTrigger(hour=12, minute=0)

        scheduler.add_job(
            custom_func,
            trigger=trigger,
            id="custom_job",
            name="Custom Job",
        )

        jobs = scheduler.get_jobs()
        assert any(j.id == "custom_job" for j in jobs)

    def test_get_jobs_empty(self, scheduler):
        """Test getting jobs when none are scheduled."""
        jobs = scheduler.get_jobs()
        assert isinstance(jobs, list)

    def test_get_jobs_after_add(self, scheduler):
        """Test getting jobs after adding one."""
        def test_func():
            pass

        trigger = CronTrigger(hour=1, minute=0)
        scheduler.add_job(test_func, trigger=trigger, id="test_job")

        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "test_job"

    def test_remove_nonexistent_job(self, scheduler):
        """Test removing a job that doesn't exist."""
        # Should not raise an error
        scheduler.remove_job("nonexistent_job")

    def test_remove_existing_job(self, scheduler):
        """Test removing an existing job."""
        def test_func():
            pass

        trigger = CronTrigger(hour=1, minute=0)
        scheduler.add_job(test_func, trigger=trigger, id="test_job")

        assert len(scheduler.get_jobs()) == 1

        scheduler.remove_job("test_job")

        assert len(scheduler.get_jobs()) == 0

    def test_pause_job_nonexistent(self, scheduler):
        """Test pausing a job that doesn't exist."""
        # Should not raise an error
        scheduler.pause_job("nonexistent_job")

    def test_resume_job_nonexistent(self, scheduler):
        """Test resuming a job that doesn't exist."""
        # Should not raise an error
        scheduler.resume_job("nonexistent_job")

    def test_is_running_initial_state(self, scheduler):
        """Test is_running initial state."""
        # Scheduler starts in non-running state
        assert not scheduler.is_running()

    def test_scheduler_configuration(self, scheduler, mock_hourly_collector):
        """Test scheduler can be configured."""
        scheduler.register_hourly_collector(mock_hourly_collector)

        assert scheduler.hourly_collector == mock_hourly_collector
        assert not scheduler.is_running()  # Not running until start() is called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
