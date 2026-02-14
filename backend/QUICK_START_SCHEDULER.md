# Quick Start: Triggering the Posts Collection Job

## The Simplest Way - Run the Script

```bash
cd backend
python scripts/trigger_posts_collection.py
```

**Output**:
```
2026-02-13 22:00:00,123 - trigger_posts_collection - INFO - ==================================================
2026-02-13 22:00:00,124 - trigger_posts_collection - INFO - MANUAL POSTS COLLECTION TRIGGER
2026-02-13 22:00:00,125 - trigger_posts_collection - INFO - ==================================================
2026-02-13 22:00:00,126 - trigger_posts_collection - INFO - Connecting to database...
2026-02-13 22:00:00,200 - trigger_posts_collection - INFO - Initializing scheduler...
2026-02-13 22:00:00,201 - trigger_posts_collection - INFO - Starting posts collection...
...
2026-02-13 22:00:30,456 - trigger_posts_collection - INFO - COLLECTION RESULTS:
2026-02-13 22:00:30,457 - trigger_posts_collection - INFO -   Posts fetched from HN:     100
2026-02-13 22:00:30,458 - trigger_posts_collection - INFO -   New posts saved:           18
2026-02-13 22:00:30,459 - trigger_posts_collection - INFO -   Posts cached in RocksDB:   18
2026-02-13 22:00:30,460 - trigger_posts_collection - INFO -   Duplicates skipped:        82
2026-02-13 22:00:30,461 - trigger_posts_collection - INFO -   Errors encountered:        0
2026-02-13 22:00:30,462 - trigger_posts_collection - INFO -   Collection time:           30.23 seconds
2026-02-13 22:00:30,463 - trigger_posts_collection - INFO - ✓ SUCCESS: Collected 18 new posts
2026-02-13 22:00:30,464 - trigger_posts_collection - INFO - ==================================================
```

---

## In Python Code

### Option 1: Async Function

```python
import asyncio
from app.infrastructure.jobs import SchedulerFactory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.infrastructure.config.settings import settings

async def collect_posts():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        scheduler = SchedulerFactory.create_scheduler(session)
        stats = await scheduler.hourly_collector.run_collection()
        print(f"✓ Collected {stats['posts_saved']} new posts")

        return stats

# Run it
asyncio.run(collect_posts())
```

### Option 2: In FastAPI Application

```python
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from app.infrastructure.jobs import SchedulerFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Create and start scheduler
    scheduler = SchedulerFactory.create_scheduler(app.state.db_session)
    app.state.scheduler = scheduler
    scheduler.start()
    print("✓ Scheduler started - running hourly")

    yield

    # Shutdown - Stop scheduler
    scheduler.stop()
    print("✓ Scheduler stopped")

app = FastAPI(lifespan=lifespan)

# API endpoint to manually trigger
@app.post("/api/posts/collect")
async def trigger_collection():
    try:
        stats = await app.state.scheduler.hourly_collector.run_collection()
        return {
            "status": "success",
            "posts_saved": stats['posts_saved'],
            "posts_cached": stats['posts_cached'],
            "duplicates": stats['duplicates_skipped']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Then trigger via HTTP:
```bash
curl -X POST http://localhost:8000/api/posts/collect
```

---

## What Gets Collected

Each run:
- **Fetches**: Top 100 posts from HackerNews
- **Filters**: Only posts with score ≥ 50 points
- **Checks**: PostgreSQL for duplicates
- **Saves**: New posts to PostgreSQL
- **Caches**: Metadata in RocksDB
- **Returns**: Statistics

**Typical Results**:
- 100 posts fetched
- 15-25 new posts saved
- 75-85 duplicates skipped
- Takes ~30-50 seconds

---

## Check Results

### View Latest Posts

```python
from app.infrastructure.database.models import Post
from datetime import datetime, timedelta

# Find posts collected in last hour
recent = session.query(Post).filter(
    Post.collected_at >= datetime.utcnow() - timedelta(hours=1)
).order_by(Post.score.desc()).limit(10)

for post in recent:
    print(f"{post.score:3d} ⭐ {post.title[:60]}")
```

### Check Cache Status

```python
from app.infrastructure.storage.rocksdb_store import RocksDBContentStore

store = RocksDBContentStore()
stats = store.get_stats()
print(f"Total posts cached: {stats['total_keys']}")
```

---

## What's Next

1. **See all posts**: Check PostgreSQL `posts` table
2. **Extract content**: See `CONTENT_EXTRACTION.md`
3. **Summarize**: See `SUMMARIZATION.md`
4. **Send to Telegram**: See `TELEGRAM_BOT.md`

---

## Troubleshooting

### No posts collected?
```python
# Check database connection
from app.infrastructure.config.settings import settings
print(f"Database: {settings.database_url}")

# Check HN API
from app.infrastructure.services.firebase_hn_client import FirebaseHNClient
client = FirebaseHNClient()
stories = await client.fetch_front_page(limit=10)
print(f"HN API returned {len(stories)} stories")
```

### Posts not saving?
```python
# Check PostgreSQL
from app.infrastructure.database.models import Post
session.query(Post).count()  # Should increase after collection

# Check RocksDB
rocksdb_store.get_stats()  # Should show total_keys > 0
```

### Scheduler not running?
```python
# Check status
print(f"Running: {scheduler.is_running()}")
print(f"Jobs: {len(scheduler.get_jobs())}")

for job in scheduler.get_jobs():
    print(f"  {job.id}: Next run {job.next_run_time}")
```

---

## Commands Cheat Sheet

```bash
# Trigger collection now
python scripts/trigger_posts_collection.py

# Make script executable
chmod +x scripts/trigger_posts_collection.py

# Run tests
pytest tests/infrastructure/jobs/ -v

# View scheduler logs
tail -f logs/app.log | grep -i "hourly\|collection"

# Check database
sqlite3 data/posts.db "SELECT COUNT(*) FROM posts"
```

---

**Happy collecting! 🚀**
