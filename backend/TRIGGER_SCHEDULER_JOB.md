# How to Trigger the Hourly Polling Job

This guide shows you different ways to trigger the HackerNews posts collection job.

---

## 1. Automatic Scheduling (Default)

The job runs automatically every hour at :00 minutes UTC.

**No action needed** - Just start the scheduler during application startup:

```python
# In your main application file
from app.infrastructure.jobs import SchedulerFactory

# During app initialization
scheduler = SchedulerFactory.create_scheduler(db_session)
scheduler.start()  # Runs automatically every hour

# Example: If you start at 14:30
# - First run: 15:00 UTC
# - Second run: 16:00 UTC
# - etc.
```

---

## 2. Manual Trigger Immediately

Run the collection job right now (don't wait for hourly schedule):

### Option A: Direct async call

```python
import asyncio
from app.infrastructure.jobs import SchedulerFactory

async def trigger_now():
    scheduler = SchedulerFactory.create_scheduler(db_session)

    # Run collection immediately
    stats = await scheduler.hourly_collector.run_collection()

    print(f"✓ Collected {stats['posts_saved']} new posts")
    print(f"✓ Cached {stats['posts_cached']} in RocksDB")
    print(f"✓ Skipped {stats['duplicates_skipped']} duplicates")

    return stats

# Run it
asyncio.run(trigger_now())
```

### Option B: Via FastAPI endpoint (HTTP)

```python
from fastapi import FastAPI, HTTPException
from app.infrastructure.jobs import SchedulerFactory

app = FastAPI()

@app.post("/api/posts/collect")
async def trigger_collection():
    """Manually trigger posts collection job"""
    try:
        stats = await app.state.scheduler.hourly_collector.run_collection()
        return {
            "status": "success",
            "message": f"Collected {stats['posts_saved']} new posts",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Usage:
# curl -X POST http://localhost:8000/api/posts/collect
```

### Option C: CLI command

```python
# scripts/trigger_collection.py

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.infrastructure.jobs import SchedulerFactory
from app.infrastructure.config.settings import settings

async def main():
    # Create database session
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create and trigger scheduler
        scheduler = SchedulerFactory.create_scheduler(session)

        print("Starting posts collection...")
        stats = await scheduler.hourly_collector.run_collection()

        print(f"\n✓ Collection Complete!")
        print(f"  Posts fetched: {stats['posts_fetched']}")
        print(f"  Posts saved: {stats['posts_saved']}")
        print(f"  Posts cached: {stats['posts_cached']}")
        print(f"  Duplicates skipped: {stats['duplicates_skipped']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Last run: {stats['last_run']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it**:
```bash
python scripts/trigger_collection.py
```

---

## 3. Schedule Custom Time

Run at a specific time instead of hourly:

```python
from apscheduler.triggers.cron import CronTrigger
from app.infrastructure.jobs import SchedulerFactory

scheduler = SchedulerFactory.create_scheduler(db_session)

# Remove existing hourly job
scheduler.remove_job("hourly_posts_collection")

# Schedule for specific time(s)
# Example: Run at 9:00 AM, 12:00 PM, and 6:00 PM UTC

trigger = CronTrigger(hour="9,12,18", minute=0, timezone="UTC")
scheduler.add_job(
    scheduler.hourly_collector.run_collection,
    trigger=trigger,
    id="custom_posts_collection",
    name="Custom Posts Collection",
    max_instances=1,
)

scheduler.start()
```

---

## 4. Run at Startup (One-time)

Collect posts immediately when application starts:

```python
# In your FastAPI app startup event
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.infrastructure.jobs import SchedulerFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting application...")

    # Create scheduler
    scheduler = SchedulerFactory.create_scheduler(app.state.db_session)
    app.state.scheduler = scheduler

    # Run collection immediately on startup
    print("Running initial posts collection...")
    try:
        stats = await scheduler.hourly_collector.run_collection()
        print(f"✓ Initial collection: {stats['posts_saved']} posts")
    except Exception as e:
        print(f"✗ Initial collection failed: {e}")

    # Start scheduled hourly runs
    scheduler.start()
    print("Scheduler started for hourly runs")

    yield

    # Shutdown
    print("Shutting down...")
    scheduler.stop()

app = FastAPI(lifespan=lifespan)
```

---

## 5. Run with Custom Parameters

Trigger collection with different settings:

```python
from app.infrastructure.jobs.hourly_posts_collector import HourlyPostsCollectorJob
from app.infrastructure.repositories.postgres.post_repo import PostgresPostRepository
from app.infrastructure.services.firebase_hn_client import FirebaseHNClient
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

async def trigger_with_custom_settings():
    # Create components with custom settings
    post_repository = PostgresPostRepository(db_session)
    rocksdb_store = RocksDBContentStore("data/content.rocksdb")
    hn_client = FirebaseHNClient()

    # Create collector with custom parameters
    collector = HourlyPostsCollectorJob(
        post_repository=post_repository,
        rocksdb_store=rocksdb_store,
        hn_client=hn_client,
        score_threshold=100,  # Only posts with 100+ points
        limit=50,             # Only collect top 50
    )

    # Trigger collection
    stats = await collector.run_collection()
    print(f"Collected {stats['posts_saved']} high-quality posts")

    return stats

asyncio.run(trigger_with_custom_settings())
```

---

## 6. Scheduled Task (Background Worker)

Use APScheduler directly for different intervals:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# Option A: Every 30 minutes
trigger = IntervalTrigger(minutes=30)
scheduler.add_job(
    collector.run_collection,
    trigger=trigger,
    id="posts_collection_30min",
)

# Option B: Every day at 3 AM UTC
trigger = CronTrigger(hour=3, minute=0, timezone="UTC")
scheduler.add_job(
    collector.run_collection,
    trigger=trigger,
    id="posts_collection_daily",
)

# Option C: Every Monday at 9 AM UTC
trigger = CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="UTC")
scheduler.add_job(
    collector.run_collection,
    trigger=trigger,
    id="posts_collection_weekly",
)

scheduler.start()
```

---

## 7. Monitoring & Debugging

### Check Job Status

```python
# See when next run is scheduled
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"Job: {job.name}")
    print(f"  ID: {job.id}")
    print(f"  Next run: {job.next_run_time}")
    print(f"  Trigger: {job.trigger}")
```

### View Recent Collections

```python
from datetime import datetime, timedelta
from app.infrastructure.database.models import Post

# Find posts collected in last 2 hours
recent_posts = session.query(Post).filter(
    Post.collected_at >= datetime.utcnow() - timedelta(hours=2)
).order_by(Post.collected_at.desc()).all()

print(f"Posts collected in last 2 hours: {len(recent_posts)}")
for post in recent_posts[:5]:
    print(f"  {post.score:3d} - {post.title[:60]}")
```

### Check Cache Status

```python
# View RocksDB statistics
stats = rocksdb_store.get_stats()
print(f"Total posts in cache: {stats['total_keys']}")
print(f"Database path: {stats['db_path']}")
```

---

## 8. Using curl (HTTP Endpoint)

If you implement the FastAPI endpoint:

### Simple trigger
```bash
curl -X POST http://localhost:8000/api/posts/collect
```

### With JSON response
```bash
curl -X POST http://localhost:8000/api/posts/collect \
  -H "Content-Type: application/json" | jq '.'
```

### Check response
```json
{
  "status": "success",
  "message": "Collected 15 new posts",
  "statistics": {
    "posts_fetched": 100,
    "posts_saved": 15,
    "posts_cached": 15,
    "duplicates_skipped": 85,
    "errors": 0,
    "last_run": "2026-02-13T22:00:00.123456"
  }
}
```

---

## 9. Test Triggering

Run the included tests to verify triggering works:

```bash
# Run all scheduler tests
pytest tests/infrastructure/jobs/ -v

# Run specific trigger test
pytest tests/infrastructure/jobs/test_hourly_posts_collector.py::TestHourlyPostsCollector::test_run_collection_entry_point -v

# With logging
pytest tests/infrastructure/jobs/ -v -s
```

---

## 10. Quick Reference

### ✅ What You Can Trigger

| Method | When | Use Case |
|--------|------|----------|
| **Automatic** | Every hour at :00 | Production - default behavior |
| **Manual async** | Right now | Testing, debugging |
| **HTTP endpoint** | Via API call | Web UI, external systems |
| **CLI script** | Command line | One-off collection |
| **Startup event** | App startup | Initial data load |
| **Custom schedule** | Specific times | Business requirements |

### ⚙️ Common Configurations

```python
# Run every hour (default)
trigger = CronTrigger(minute=0)

# Run every 30 minutes
trigger = IntervalTrigger(minutes=30)

# Run daily at 3 AM
trigger = CronTrigger(hour=3, minute=0)

# Run weekdays at 9 AM
trigger = CronTrigger(day_of_week="mon-fri", hour=9, minute=0)

# Run first day of month at midnight
trigger = CronTrigger(day=1, hour=0, minute=0)
```

### 📊 Monitor Collection

```python
# Get latest collection stats
latest_stats = scheduler.hourly_collector.get_stats()

# Count posts in database
post_count = session.query(Post).count()

# Check cache size
cache_stats = rocksdb_store.get_stats()
print(f"Cache contains {cache_stats['total_keys']} posts")
```

---

## Summary

**Default Behavior** (no action needed):
- Scheduler starts automatically
- Runs every hour at :00 minutes UTC
- Collects top 100 posts with score ≥ 50
- Stores in PostgreSQL, caches in RocksDB

**To Trigger Manually**:
1. **Immediately**: `await collector.run_collection()`
2. **Via HTTP**: POST `/api/posts/collect`
3. **CLI**: `python scripts/trigger_collection.py`
4. **Custom time**: Use `CronTrigger` or `IntervalTrigger`
5. **At startup**: Use FastAPI `lifespan` context manager

**Monitor Progress**:
- Check `scheduler.get_jobs()` for next run time
- Query database for recent posts
- View RocksDB cache statistics
