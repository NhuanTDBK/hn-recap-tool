# Activity 1.1: Set up HN API polling system

**Phase**: 1 - Ingest Pipeline
**Status**: ✅ Completed
**Owner**: Engineering Team
**Estimated Effort**: N/A (Already Implemented)

---

## Overview

The HN API polling system fetches front page stories from HackerNews using the Algolia API on a scheduled basis. This forms the entry point for the entire content ingestion pipeline, collecting raw post data that downstream activities will filter, crawl, and process.

**Current Implementation**: Uses APScheduler with AsyncIO for daily collection at midnight UTC. The system follows Clean Architecture with separate layers for domain entities, use cases, and infrastructure services.

---

## Prerequisites

### Infrastructure
- [x] Python 3.11+ runtime environment
- [x] HackerNews Algolia API access (public, no auth required)
- [x] JSONL file storage for posts

### Dependencies
- None (this is the first activity in Phase 1)

### Required Libraries
- [x] `httpx` - Async HTTP client for API calls
- [x] `pydantic` - Data validation and domain models
- [x] `apscheduler` - Task scheduling for cron-like execution

---

## Objectives

1. ✅ **Reliable API Integration**: Connect to HN Algolia API for front page stories with proper error handling
2. ✅ **Scheduled Execution**: Daily collection at midnight UTC using APScheduler
3. ✅ **Domain Model Creation**: Transform raw API data into validated Post entities
4. ✅ **Data Persistence**: Save posts to JSONL storage for downstream processing
5. ✅ **Clean Architecture**: Separate concerns across domain, application, and infrastructure layers

---

## Technical Details

### Architecture Decisions

**API Choice: Firebase API vs Algolia API**

Current implementation uses **Algolia API**, but **Firebase API is recommended** for production:

**Firebase API Advantages (Recommended):**
- `/v0/maxitem` endpoint provides the latest item ID
- Can scan incrementally for new posts by tracking max ID
- Native support for change notifications
- No rate limits documented
- Direct access to HN's internal data structures
- Better for periodic polling (scan from last ID to current max)

**Algolia API (Current):**
- Simpler for MVP (single call returns full posts)
- Good for front page snapshot
- No incremental scanning capability

**Migration Strategy:**
1. Keep Algolia for initial MVP
2. Switch to Firebase `/v0/maxitem` + `/v0/item/{id}` for production
3. Track last processed ID in database
4. Poll every 2 hours, fetch items from last_id to maxitem

**Why APScheduler instead of Vercel Cron?**
- Current implementation runs standalone (not deployed to Vercel yet)
- APScheduler provides flexible async/await support
- Can run locally or on any Python hosting environment
- Easy to migrate to Vercel Cron later if needed

**Storage: PostgreSQL vs JSONL**
- **Current**: JSONL file storage (MVP)
- **Recommended**: PostgreSQL with proper schema
  - Unique constraint on `hn_id` for automatic deduplication
  - Indexed queries for fast lookups
  - Transactional integrity
  - Ready for production scale

### Data Models

**HN Firebase API Response**
```json
{
  "id": 39301285,
  "type": "story",
  "by": "username",
  "time": 1707396000,
  "title": "PostgreSQL 18 Released",
  "url": "https://postgresql.org/...",
  "score": 452,
  "descendants": 230
}
```

**HN Algolia API Response (Current MVP)**
```json
{
  "objectID": "39301285",
  "title": "PostgreSQL 18 Released",
  "author": "username",
  "points": 452,
  "num_comments": 230,
  "created_at": "2025-02-08T10:00:00.000Z",
  "url": "https://postgresql.org/..."
}
```

**Domain Entity (Post)**
```python
class Post(BaseModel):
    hn_id: int
    title: str
    author: str
    points: int
    num_comments: int
    created_at: datetime
    collected_at: datetime
    url: Optional[str]
    post_type: str  # story, ask, show, job
    content: Optional[str]
    raw_content: Optional[str]
    summary: Optional[str]
    id: str  # UUID
```

### Component Architecture

**Implemented Module Structure**
```
backend/app/
  ├── domain/                           # Business entities
  │   └── entities.py                   # Post, Comment, Digest entities
  ├── application/                      # Use cases
  │   ├── interfaces.py                 # Abstract interfaces
  │   └── use_cases/
  │       └── collection.py             # CollectPostsUseCase
  ├── infrastructure/                   # External systems
  │   ├── services/
  │   │   └── hn_client.py             # AlgoliaHNClient
  │   ├── repositories/
  │   │   └── jsonl_post_repo.py       # JSONL storage
  │   └── jobs/
  │       └── data_collector.py         # DataCollectorJob scheduler
  └── scripts/
      └── fetch_hn_posts.py             # Standalone CLI tool
```

---

## Implementation Flow

### Current Flow (Algolia API - MVP)

```
┌─────────────────────────────────────────────────────────┐
│ 1. SCHEDULED TRIGGER (APScheduler)                      │
│    Runs daily at 00:00 UTC                              │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. DataCollectorJob.run_collection()                    │
│    Orchestrates the full pipeline                       │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CollectPostsUseCase.execute(limit=30)                │
│    • Calls AlgoliaHNClient.fetch_front_page()           │
│    • Transforms raw API data → Post entities            │
│    • Determines post_type (story/ask/show/job)          │
│    • Validates with Pydantic                            │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 4. AlgoliaHNClient.fetch_front_page(limit)              │
│    GET https://hn.algolia.com/api/v1/search             │
│    ?tags=front_page&hitsPerPage=30                      │
│                                                          │
│    Returns: List of raw post dictionaries               │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 5. PostRepository.save_batch(posts)                     │
│    Writes Post entities to JSONL file:                  │
│    data/raw/{YYYY-MM-DD}-posts.jsonl                    │
│                                                          │
│    Format: One JSON object per line                     │
└─────────────────────────────────────────────────────────┘
```

### Recommended Flow (Firebase API - Production)

```
┌─────────────────────────────────────────────────────────┐
│ 1. SCHEDULED TRIGGER (Vercel Cron)                      │
│    Runs every 2 hours                                   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Get Current State                                    │
│    SELECT MAX(hn_id) FROM posts;                        │
│    → last_processed_id = 39301285                       │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Fetch Max Item ID                                    │
│    GET /v0/maxitem.json                                 │
│    → current_max_id = 39305000                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Calculate Range                                      │
│    new_items = range(39301286, 39305001)                │
│    → 3,715 new items to process                         │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Fetch Items in Batches (parallel)                    │
│    For each ID in new_items:                            │
│      GET /v0/item/{id}.json                             │
│                                                          │
│    • Filter: type = "story" only                        │
│    • Skip: deleted, dead, Ask HN, Show HN               │
│    • Use asyncio.gather for parallel fetching           │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Bulk Insert to PostgreSQL                            │
│    INSERT INTO posts (hn_id, title, ...)                │
│    ON CONFLICT (hn_id) DO UPDATE ...                    │
│                                                          │
│    • Automatic deduplication via unique constraint      │
│    • Update existing posts (score, comment count)       │
└─────────────────────────────────────────────────────────┘
```

**Benefits of Firebase Approach:**
- ✅ Only fetches new posts since last run
- ✅ No duplicate processing
- ✅ Efficient incremental scanning
- ✅ Can run every 2 hours without wasting API calls
- ✅ Database handles deduplication automatically

### Post Type Determination Logic

```python
# Implemented in CollectPostsUseCase._determine_post_type()

title = post['title'].lower()

if title.startswith('ask hn'):     → post_type = 'ask'
elif title.startswith('show hn'):  → post_type = 'show'
elif url.endswith('/jobs'):        → post_type = 'job'
else:                              → post_type = 'story'
```

---

## Testing & Validation

### Manual Testing

**Run Standalone Script**
```bash
python scripts/fetch_hn_posts.py --limit 30 --output data/raw
```

Expected output:
- Fetches 30 front page stories from HN
- Saves to `data/raw/YYYY-MM-DD-posts.jsonl`
- Displays sample posts with points and comment counts

**Run Scheduled Job Manually**
```python
from backend.app.infrastructure.jobs.data_collector import DataCollectorJob

# Inject dependencies and run
await job.run_now()
```

### Validation Checklist

- [x] AlgoliaHNClient successfully fetches front page stories
- [x] Post entities are created with all required fields
- [x] post_type is correctly determined (story/ask/show/job)
- [x] JSONL files are written to data/raw/ directory
- [x] APScheduler triggers at midnight UTC
- [x] Error handling logs failures without crashing
- [x] Pydantic validation catches malformed data

---

## Acceptance Criteria

- [x] HN Algolia API client fetches front page stories successfully
- [x] Raw API data is transformed into validated Post domain entities
- [x] post_type is correctly determined from title and URL patterns
- [x] Posts are persisted to JSONL files in data/raw/ directory
- [x] Scheduled job runs daily at midnight UTC via APScheduler
- [x] Error handling prevents job crashes on API failures
- [x] CollectPostsUseCase follows Clean Architecture principles
- [x] Can run standalone via scripts/fetch_hn_posts.py CLI
- [x] Logs provide visibility into collection process

---

## Rollout Notes

### Deployment Considerations

**Current State: Standalone Execution**
- Runs as Python script or scheduled job
- No external hosting required yet
- JSONL storage requires local filesystem access

**Future Migration Path (Phase 3)**
- Move to Vercel Cron for serverless execution
- Replace JSONL with PostgreSQL (Supabase)
- Add cron secret authentication

### Monitoring & Observability

**Current Logging**
```python
logger.info(f"Collecting {limit} posts from HN front page")
logger.info(f"Fetched {len(hits)} stories from HN")
logger.info(f"Saved {len(saved_posts)} posts to storage")
```

**Key Metrics**
- Posts fetched per run
- API response time
- Failed API calls
- File write errors

**Deduplication Note**
⚠️ **Important**: The current JSONL implementation appends posts to daily files. Posts with the same `hn_id` from previous runs are NOT automatically skipped during collection. Deduplication happens in **Activity 1.2** (content filtering) when processing posts for crawling.

Future PostgreSQL implementation will check `hn_id` uniqueness constraint to skip existing posts.

---

## Related Activities

**Downstream Dependencies**
- ✅ **Activity 1.2**: Implement content filtering logic (uses collected posts)
- ✅ **Activity 1.3**: Build URL crawler and HTML fetcher (processes filtered posts)

**Related Files**
- `backend/app/domain/entities.py` - Post entity definition
- `backend/app/application/use_cases/collection.py` - Collection logic
- `backend/app/infrastructure/services/hn_client.py` - HN API client
- `backend/app/infrastructure/jobs/data_collector.py` - Scheduler

**Reference Documents**
- [HN Algolia API Documentation](https://hn.algolia.com/api)
- docs/spec.md (Section: Ingest Pipeline Flow)

---

## Recommended PostgreSQL Schema

### Database Migration with Alembic

**Setup Alembic**
```bash
# Install Alembic
pip install alembic asyncpg psycopg2-binary

# Initialize Alembic
alembic init alembic

# Configure alembic.ini
# Edit: sqlalchemy.url = postgresql+asyncpg://user:pass@host/db
```

**Alembic Migration Script**

Create migration: `alembic/versions/001_create_posts_table.py`

```python
"""Create posts table

Revision ID: 001
Revises:
Create Date: 2025-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create posts table
    op.create_table(
        'posts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hn_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('author', sa.String()),
        sa.Column('url', sa.Text()),
        sa.Column('domain', sa.String()),
        sa.Column('score', sa.Integer(), server_default='0'),
        sa.Column('comment_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('collected_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),

        # Filtering flags
        sa.Column('is_dead', sa.Boolean(), server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), server_default='false'),

        # Content (populated by Activity 1.3)
        sa.Column('html_content', sa.Text()),
        sa.Column('markdown_content', sa.Text()),

        # Summary (populated by Activity 2.1)
        sa.Column('summary', sa.Text()),
        sa.Column('summarized_at', sa.TIMESTAMP(timezone=True)),

        # Metadata
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'))
    )

    # Create indexes
    op.create_index('idx_posts_hn_id', 'posts', ['hn_id'])
    op.create_index('idx_posts_created_at', 'posts', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('idx_posts_type', 'posts', ['type'])
    op.create_index('idx_posts_score', 'posts', ['score'], postgresql_ops={'score': 'DESC'})

    # Create trigger function for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
           NEW.updated_at = NOW();
           RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER update_posts_updated_at
        BEFORE UPDATE ON posts
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    op.drop_index('idx_posts_score', table_name='posts')
    op.drop_index('idx_posts_type', table_name='posts')
    op.drop_index('idx_posts_created_at', table_name='posts')
    op.drop_index('idx_posts_hn_id', table_name='posts')
    op.execute('DROP TRIGGER IF EXISTS update_posts_updated_at ON posts')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column')
    op.drop_table('posts')
```

**Run Migration**
```bash
# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1

# Check current version
alembic current
```

### Raw SQL Schema (for reference)

```sql
CREATE TABLE posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hn_id INT UNIQUE NOT NULL,
  type TEXT NOT NULL,                    -- story, comment, job, poll
  title TEXT,
  author TEXT,                           -- HN username ('by' field)
  url TEXT,
  domain TEXT,                            -- extracted from URL
  score INT DEFAULT 0,
  comment_count INT DEFAULT 0,           -- 'descendants' field
  created_at TIMESTAMPTZ NOT NULL,       -- from 'time' field (unix timestamp)
  collected_at TIMESTAMPTZ DEFAULT NOW(),

  -- Filtering flags
  is_dead BOOLEAN DEFAULT FALSE,
  is_deleted BOOLEAN DEFAULT FALSE,

  -- Content (populated by Activity 1.3)
  html_content TEXT,
  markdown_content TEXT,

  -- Summary (populated by Activity 2.1)
  summary TEXT,
  summarized_at TIMESTAMPTZ,

  -- Metadata
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_posts_hn_id ON posts(hn_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_type ON posts(type);
CREATE INDEX idx_posts_score ON posts(score DESC);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### SQLAlchemy Model

**File**: `backend/app/infrastructure/models/post.py`

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = 'posts'

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    hn_id = Column(Integer, unique=True, nullable=False, index=True)
    type = Column(String, nullable=False, index=True)
    title = Column(Text)
    author = Column(String)
    url = Column(Text)
    domain = Column(String)
    score = Column(Integer, default=0, index=True)
    comment_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    collected_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Filtering flags
    is_dead = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    # Content
    html_content = Column(Text)
    markdown_content = Column(Text)

    # Summary
    summary = Column(Text)
    summarized_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

---

## Notes & Assumptions

**Current State (MVP)**
- Using Algolia API for simplicity (single call returns 30 posts)
- JSONL file storage (no database yet)
- Daily collection at midnight UTC
- No incremental scanning

**Recommended Production Approach**
- ✅ **Firebase API** for incremental scanning via `/v0/maxitem`
- ✅ **PostgreSQL** with unique constraint on `hn_id` for automatic deduplication
- ✅ **Every 2 hours** polling (per spec.md)
- ✅ **Parallel fetching** with asyncio.gather (batch of 100 IDs at a time)
- ✅ **Vercel Cron** for serverless execution

**Migration Path**
1. **Phase 1** (Current): Algolia + JSONL (MVP working)
2. **Phase 1.5** (Recommended): Add PostgreSQL schema
3. **Phase 2**: Switch to Firebase API with incremental scanning
4. **Phase 3**: Deploy to Vercel Cron for production

**Known Limitations of Current Implementation**
- No deduplication at collection time
- Cannot detect newly updated posts (score/comment changes)
- Limited to front page posts only (misses new posts not yet on front page)
- Requires manual run or long-running process for APScheduler

**Benefits of Firebase + PostgreSQL Approach**
- Captures ALL new posts (not just front page)
- Efficient incremental scanning (only fetch new IDs)
- Automatic deduplication via database constraint
- Can update existing posts when they're re-fetched
- Scales better for high-frequency polling
