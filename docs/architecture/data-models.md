# Data Models - PostgreSQL Schema & RocksDB Storage

**Project:** HN Pal - Intelligent HackerNews Telegram Bot
**Version:** 2.0 (Multi-Phase Implementation)
**Last Updated:** 2026-02-13

---

## Overview

This document defines the complete data architecture for HN Pal:

1. **PostgreSQL Schema** - Relational data (users, posts, conversations, memory)
2. **RocksDB Storage** - Content blobs (HTML, text, markdown)
3. **Redis State** - Bot FSM state and session data
4. **Pydantic Models** - Type-safe data validation

---

## Storage Architecture

```
┌──────────────────────────────────────────────────┐
│                 HN Pal Storage                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  PostgreSQL (Supabase)    RocksDB (Local)       │
│  ┌─────────────────┐      ┌─────────────────┐   │
│  │ users           │      │ Column Families │   │
│  │ posts           │      │ ├── html        │   │
│  │ deliveries      │      │ ├── text        │   │
│  │ conversations   │      │ └── markdown    │   │
│  │ memory          │      │                 │   │
│  │ user_token_usage│      │ Zstd Compressed │   │
│  │ agent_calls     │      │ ~70% savings    │   │
│  └─────────────────┘      └─────────────────┘   │
│                                                  │
│  Redis (State Management)                       │
│  ┌─────────────────────────────────────────┐    │
│  │ FSM State (IDLE, DISCUSSION)            │    │
│  │ User Sessions                            │    │
│  │ Bot Context Cache                        │    │
│  └─────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

**Why This Architecture:**

- **PostgreSQL** → Structured queries, ACID transactions, relationships
- **RocksDB** → High-performance content blobs, built-in compression, no filesystem overhead
- **Redis** → Fast ephemeral state for bot FSM and caching

---

## PostgreSQL Schema

### `users` Table

**Purpose:** Telegram user accounts and preferences

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),

    -- Bot state
    active_discussion_post_id INTEGER REFERENCES posts(hn_id),
    memory_enabled BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused')),

    -- Personalization
    interests JSONB DEFAULT '[]'::jsonb,  -- ["distributed systems", "rust", ...]
    digest_preferences JSONB DEFAULT '{
        "style": "flat_scroll",
        "frequency": "daily",
        "time": "07:00",
        "max_posts": 10
    }'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_telegram_id (telegram_id),
    INDEX idx_status (status),
    INDEX idx_active_discussion (active_discussion_post_id)
);
```

**Key Fields:**

- `telegram_id` - Unique Telegram user ID (from bot API)
- `active_discussion_post_id` - Currently active discussion post (NULL if IDLE)
- `memory_enabled` - Toggle for memory extraction
- `interests` - User-declared topics (from onboarding or /memory)
- `digest_preferences` - Delivery schedule and format

---

### `posts` Table

**Purpose:** HN posts with metadata and crawl status

```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    hn_id INTEGER UNIQUE NOT NULL,

    -- HN metadata
    type VARCHAR(20) NOT NULL CHECK (type IN ('story', 'ask_hn', 'show_hn', 'poll', 'job')),
    title TEXT NOT NULL,
    url TEXT,
    domain VARCHAR(255),
    author VARCHAR(255),
    score INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    hn_published_at TIMESTAMPTZ,

    -- Content storage references (RocksDB keys)
    has_html BOOLEAN DEFAULT false,
    has_text BOOLEAN DEFAULT false,
    has_markdown BOOLEAN DEFAULT false,

    -- Crawl tracking
    is_crawl_success BOOLEAN DEFAULT false,
    crawl_retry_count INTEGER DEFAULT 0,
    crawl_error TEXT,
    crawled_at TIMESTAMPTZ,

    -- Summarization
    summary TEXT,
    summarized_at TIMESTAMPTZ,
    summary_model VARCHAR(50),  -- e.g., "gpt-4o-mini"
    summary_tokens INTEGER,
    summary_prompt_type VARCHAR(50),  -- "basic", "technical", etc.

    -- Timestamps
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_hn_id (hn_id),
    INDEX idx_type (type),
    INDEX idx_crawl_status (is_crawl_success, crawl_retry_count),
    INDEX idx_summarized (summarized_at),
    INDEX idx_published (hn_published_at DESC),
    INDEX idx_score (score DESC)
);
```

**Content Storage Logic:**

- **HTML/Text/Markdown** stored in **RocksDB** with key = `{hn_id}`
- Boolean flags (`has_html`, `has_text`, `has_markdown`) track presence
- No S3 keys needed - direct RocksDB lookup

**Crawl Retry Logic:**

```python
if is_crawl_success:
    skip()  # Already crawled successfully
elif crawl_retry_count >= 3:
    skip()  # Permanent failure
else:
    retry()  # Retry up to 3 times
```

---

### `deliveries` Table

**Purpose:** Track digest messages sent to users

```sql
CREATE TABLE deliveries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,

    -- Telegram message tracking
    message_id BIGINT NOT NULL,  -- Telegram message ID
    batch_id VARCHAR(50),  -- Groups posts in same digest (e.g., "2026-02-13-morning")

    -- User engagement
    reaction VARCHAR(10) CHECK (reaction IN ('up', 'down', NULL)),
    is_saved BOOLEAN DEFAULT false,
    is_read BOOLEAN DEFAULT false,

    -- Timestamps
    delivered_at TIMESTAMPTZ DEFAULT NOW(),
    reacted_at TIMESTAMPTZ,
    saved_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_user_batch (user_id, batch_id),
    INDEX idx_post_deliveries (post_id),
    INDEX idx_saved (user_id, is_saved) WHERE is_saved = true,
    INDEX idx_reaction (user_id, reaction) WHERE reaction IS NOT NULL,

    UNIQUE(user_id, post_id)  -- One delivery per user per post
);
```

**Batch ID Format:** `YYYY-MM-DD-{morning|evening}` (e.g., `2026-02-13-morning`)

---

### `conversations` Table

**Purpose:** Store multi-turn discussion sessions

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,

    -- Conversation data
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Format: [{"role": "user", "content": "...", "timestamp": "..."}, ...]

    -- Token tracking
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10, 6) DEFAULT 0.0,

    -- Session metadata
    agent_model VARCHAR(50),  -- "gpt-4o-mini", "gpt-4o"
    context_loaded JSONB,  -- {"article": true, "memory": true, "related_posts": 2}

    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_user_conversations (user_id, started_at DESC),
    INDEX idx_post_conversations (post_id),
    INDEX idx_active_conversations (user_id, ended_at) WHERE ended_at IS NULL
);
```

**Message Format (JSONB):**

```json
[
  {
    "role": "system",
    "content": "You are discussing: PostgreSQL 18 Released\n\nArticle: ...",
    "timestamp": "2026-02-13T10:00:00Z"
  },
  {
    "role": "user",
    "content": "What are people saying in the comments?",
    "timestamp": "2026-02-13T10:01:15Z"
  },
  {
    "role": "assistant",
    "content": "The top comments focus on...",
    "timestamp": "2026-02-13T10:01:18Z"
  }
]
```

---

### `memory` Table

**Purpose:** User memory for personalized interactions

```sql
CREATE TABLE memory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Memory metadata
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'interest', 'preference', 'work_context', 'personal_context',
        'discussion_note', 'fact', 'opinion', 'connection'
    )),

    -- Memory content
    content TEXT NOT NULL,
    source_type VARCHAR(50),  -- "onboarding", "discussion", "reaction", "explicit"
    source_post_id INTEGER REFERENCES posts(id),
    source_conversation_id INTEGER REFERENCES conversations(id),

    -- Lifecycle
    active BOOLEAN DEFAULT true,
    confidence DECIMAL(3, 2) DEFAULT 1.0,  -- 0.0-1.0 (for implicit extraction)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,

    -- Indexes
    INDEX idx_user_active_memory (user_id, active) WHERE active = true,
    INDEX idx_memory_type (user_id, type),
    INDEX idx_source_post (source_post_id),
    INDEX idx_created_date (created_at DESC)
);
```

**Memory Types:**

| Type | Example | Source |
|------|---------|--------|
| `interest` | "Distributed systems" | Onboarding, reactions |
| `preference` | "Prefers concise summaries" | Explicit command |
| `work_context` | "Building search with embeddings" | Discussion |
| `personal_context` | "Learning Rust" | Discussion |
| `discussion_note` | "Discussed CockroachDB pricing on 2026-02-10" | Post-discussion extraction |
| `fact` | "Uses PostgreSQL in production" | Discussion |
| `opinion` | "Skeptical of microservices hype" | Discussion |
| `connection` | "Related to previous Raft consensus discussion" | LLM extraction |

---

### `user_token_usage` Table

**Purpose:** Track LLM API costs per user

```sql
CREATE TABLE user_token_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Daily aggregates
    date DATE NOT NULL,

    -- Token counts
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,

    -- Cost tracking
    total_cost_usd DECIMAL(10, 6) DEFAULT 0.0,

    -- Breakdown by operation
    summarization_tokens INTEGER DEFAULT 0,
    discussion_tokens INTEGER DEFAULT 0,
    memory_extraction_tokens INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_user_date (user_id, date DESC),
    UNIQUE(user_id, date)
);
```

**Cost Calculation:**

```python
# GPT-4o-mini pricing (as of 2026-02-13)
INPUT_COST_PER_1M = 0.15   # $0.15 / 1M tokens
OUTPUT_COST_PER_1M = 0.60  # $0.60 / 1M tokens

cost = (input_tokens / 1_000_000 * INPUT_COST_PER_1M) + \
       (output_tokens / 1_000_000 * OUTPUT_COST_PER_1M)
```

---

### `agent_calls` Table

**Purpose:** Detailed LLM agent call logs for observability

```sql
CREATE TABLE agent_calls (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    -- Agent metadata
    agent_type VARCHAR(50) NOT NULL,  -- "SummarizationAgent", "DiscussionAgent", etc.
    model VARCHAR(50) NOT NULL,  -- "gpt-4o-mini", "gpt-4o"

    -- Call details
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER,

    -- Tracing
    langfuse_trace_id VARCHAR(255),  -- For Langfuse integration
    conversation_id INTEGER REFERENCES conversations(id),

    -- Status
    success BOOLEAN DEFAULT true,
    error_message TEXT,

    -- Timestamps
    called_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    INDEX idx_agent_type (agent_type, called_at DESC),
    INDEX idx_user_calls (user_id, called_at DESC),
    INDEX idx_langfuse_trace (langfuse_trace_id)
);
```

---

## RocksDB Storage

### Structure

```
data/content.rocksdb/
├── [default]    - metadata (not used)
├── [html]       - raw HTML content
├── [text]       - extracted text (trafilatura)
└── [markdown]   - converted markdown (markitdown)
```

### Column Family Schema

**Key Format:** `{hn_id}` (integer as string, e.g., `"38543210"`)

**Value:** Raw bytes (compressed with Zstandard)

**Python Interface:**

```python
import rocksdb

# Open database with column families
opts = rocksdb.Options(create_if_missing=True)
opts.compression = rocksdb.CompressionType.zstd_compression

db = rocksdb.DB(
    "data/content.rocksdb",
    opts,
    column_families={
        "html": rocksdb.ColumnFamilyOptions(),
        "text": rocksdb.ColumnFamilyOptions(),
        "markdown": rocksdb.ColumnFamilyOptions()
    }
)

# Write content
html_cf = db.column_family_handle(b"html")
db.put(b"38543210", html_content.encode("utf-8"), html_cf)

# Read content
content = db.get(b"38543210", html_cf)
if content:
    html = content.decode("utf-8")
```

### Storage Projections

**Assumptions:**
- 200 posts/day
- Average HTML: 100 KB → 30 KB compressed (70% savings)
- Average text: 15 KB → 5 KB compressed
- Average markdown: 20 KB → 7 KB compressed
- Total per post: ~42 KB compressed

**Yearly Projection:**

| Year | Posts | Raw Size | Compressed | Total DB Size |
|------|-------|----------|------------|---------------|
| 1    | 73K   | 10 GB    | 3 GB       | 3 GB          |
| 5    | 365K  | 50 GB    | 15 GB      | 15 GB         |
| 10   | 730K  | 100 GB   | 30 GB      | 30 GB         |

**Benefits vs Filesystem:**

- No inode overhead (730K files → ~20 SST files)
- Built-in compression (Zstandard)
- O(1) lookup by HN ID
- Simple backup (single directory)
- No filesystem fragmentation

---

## Redis State Schema

### Bot FSM State

**Key Pattern:** `fsm:{telegram_id}:state`

**Value:** JSON string

```json
{
  "state": "DISCUSSION",  // "IDLE" | "DISCUSSION" | "ONBOARDING"
  "data": {
    "active_post_id": 38543210,
    "discussion_started_at": "2026-02-13T10:00:00Z",
    "last_message_at": "2026-02-13T10:15:22Z"
  }
}
```

**TTL:** 60 minutes (auto-cleanup inactive sessions)

---

### User Session Cache

**Key Pattern:** `session:{telegram_id}`

**Value:** JSON string (user object)

```json
{
  "id": 42,
  "telegram_id": 123456789,
  "username": "john_doe",
  "memory_enabled": true,
  "interests": ["rust", "databases"]
}
```

**TTL:** 30 minutes

---

### Bot Context Cache

**Key Pattern:** `context:{telegram_id}:{post_id}`

**Value:** JSON string (loaded context for discussion)

```json
{
  "article_markdown": "...",
  "user_memory": ["Interest in distributed systems", "Building search engine"],
  "related_conversations": [12, 45],
  "loaded_at": "2026-02-13T10:00:00Z"
}
```

**TTL:** 30 minutes (duration of typical discussion)

---

## Pydantic Models

### User Models (`backend/app/domain/models/user.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    interests: List[str] = Field(default_factory=list)

class UserInDB(UserBase):
    id: int
    active_discussion_post_id: Optional[int] = None
    memory_enabled: bool = True
    status: str = "active"
    interests: List[str] = Field(default_factory=list)
    digest_preferences: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_interaction_at: Optional[datetime] = None

class User(UserBase):
    """Public user representation"""
    id: int
    status: str
    interests: List[str]
    created_at: datetime
```

---

### Post Models (`backend/app/domain/models/post.py`)

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class PostBase(BaseModel):
    hn_id: int
    type: str
    title: str
    url: Optional[HttpUrl] = None
    domain: Optional[str] = None
    author: Optional[str] = None
    score: int = 0
    comment_count: int = 0

class PostCreate(PostBase):
    hn_published_at: Optional[datetime] = None

class PostInDB(PostBase):
    id: int
    has_html: bool = False
    has_text: bool = False
    has_markdown: bool = False
    is_crawl_success: bool = False
    crawl_retry_count: int = 0
    summary: Optional[str] = None
    summarized_at: Optional[datetime] = None
    fetched_at: datetime
    created_at: datetime

class PostWithContent(PostInDB):
    """Post with loaded content from RocksDB"""
    markdown_content: Optional[str] = None
    text_content: Optional[str] = None

class PostSummary(BaseModel):
    """Minimal post for digest delivery"""
    hn_id: int
    title: str
    url: Optional[HttpUrl] = None
    domain: Optional[str] = None
    score: int
    comment_count: int
    summary: Optional[str] = None
```

---

### Conversation Models (`backend/app/domain/models/conversation.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Message(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str
    timestamp: datetime

class ConversationCreate(BaseModel):
    user_id: int
    post_id: int
    agent_model: str = "gpt-4o-mini"

class ConversationInDB(BaseModel):
    id: int
    user_id: int
    post_id: int
    messages: List[Message] = Field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    agent_model: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    last_message_at: datetime

class ConversationUpdate(BaseModel):
    """Append new message to conversation"""
    message: Message
    input_tokens: int
    output_tokens: int
    cost_usd: float
```

---

### Memory Models (`backend/app/domain/models/memory.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MemoryCreate(BaseModel):
    user_id: int
    type: str  # "interest", "preference", "work_context", etc.
    content: str
    source_type: str  # "onboarding", "discussion", "reaction", "explicit"
    source_post_id: Optional[int] = None
    source_conversation_id: Optional[int] = None
    confidence: float = 1.0

class MemoryInDB(MemoryCreate):
    id: int
    active: bool = True
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None

class MemoryUpdate(BaseModel):
    active: Optional[bool] = None
    content: Optional[str] = None
    confidence: Optional[float] = None
```

---

### Agent Models (`backend/app/domain/models/agent.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AgentCallCreate(BaseModel):
    user_id: Optional[int] = None
    agent_type: str  # "SummarizationAgent", "DiscussionAgent", etc.
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    langfuse_trace_id: Optional[str] = None
    conversation_id: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None

class AgentCallInDB(AgentCallCreate):
    id: int
    called_at: datetime

class TokenUsageSummary(BaseModel):
    """Daily token usage summary"""
    date: str  # YYYY-MM-DD
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    summarization_tokens: int
    discussion_tokens: int
    memory_extraction_tokens: int
```

---

## Data Validation Rules

### User Validation

- `telegram_id` must be positive integer (Telegram IDs are always positive)
- `username` max length: 255 characters
- `interests` max items: 50
- `status` must be one of: "active", "paused"

### Post Validation

- `hn_id` must be positive integer
- `title` max length: 500 characters
- `type` must be one of: "story", "ask_hn", "show_hn", "poll", "job"
- `score` must be >= 0
- `comment_count` must be >= 0

### Conversation Validation

- `messages` array max size: 1000 (prevent runaway conversations)
- Each message `content` max length: 10,000 characters
- `role` must be one of: "system", "user", "assistant"

### Memory Validation

- `content` max length: 5,000 characters
- `confidence` must be 0.0 - 1.0
- `type` must be valid memory type (see enum in schema)

---

## Database Migration Strategy

### Phase 1: JSONL → PostgreSQL + RocksDB

**Current State:** JSONL files in `data/` directory

**Migration Steps:**

1. Set up PostgreSQL schema (Alembic migrations)
2. Set up RocksDB column families
3. Write migration script:
   - Read JSONL posts → INSERT INTO posts
   - Read filesystem HTML/text/markdown → RocksDB
   - Update `has_html`, `has_text`, `has_markdown` flags
4. Validate data integrity
5. Switch application to new storage
6. Archive JSONL files

**Migration Script Location:** `backend/scripts/migrate_jsonl_to_db.py`

---

### Phase 2: Add Telegram User Tables

**When:** Before Phase 3 (Bot Foundation)

**New Tables:**
- `users`
- `deliveries`

**Migration:** Create tables with Alembic, no data migration needed

---

### Phase 3: Add Conversation Tables

**When:** Before Phase 5 (Discussion System)

**New Tables:**
- `conversations`
- `memory`
- `user_token_usage`
- `agent_calls`

**Migration:** Create tables with Alembic, no data migration needed

---

## Alembic Migrations

### Migration File Naming

```
backend/alembic/versions/
├── 001_initial_posts_schema.py
├── 002_add_crawl_tracking.py
├── 003_add_summarization_fields.py
├── 004_create_users_table.py
├── 005_create_deliveries_table.py
├── 006_create_conversations_table.py
├── 007_create_memory_table.py
└── 008_create_agent_tracking_tables.py
```

### Example Migration (001_initial_posts_schema.py)

```python
"""Initial posts schema

Revision ID: 001
Revises:
Create Date: 2026-02-13 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hn_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        # ... rest of schema
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hn_id')
    )

    op.create_index('idx_hn_id', 'posts', ['hn_id'])
    op.create_index('idx_type', 'posts', ['type'])

def downgrade():
    op.drop_table('posts')
```

---

## Error Handling

### PostgreSQL Operations

**Connection Failure:**
- Retry with exponential backoff (3 attempts)
- Log error with context
- Raise exception if all retries fail

**Constraint Violation:**
- `UNIQUE(hn_id)` → Skip insert, log duplicate
- `FOREIGN KEY` → Log error, skip operation
- `CHECK` → Validate data before insert

**Transaction Rollback:**
- Use context managers for atomic operations
- Log rollback reason
- Re-raise exception

---

### RocksDB Operations

**Database Corruption:**
- Log error with stack trace
- Return None for reads
- Skip writes, continue execution

**Key Not Found:**
- Return None (expected behavior)
- Don't log as error

**Write Failure:**
- Log error with HN ID
- Continue processing other posts
- Track failed writes for retry

---

### Redis Operations

**Connection Failure:**
- Degrade gracefully (no FSM state persistence)
- Log warning
- Continue bot operation (in-memory state only)

**Key Not Found:**
- Expected behavior for expired sessions
- Don't log as error
- Reconstruct state from PostgreSQL

---

## Performance Considerations

### PostgreSQL Optimizations

**Indexes:**
- All foreign keys indexed
- Query-heavy columns indexed (see schema)
- Partial indexes for filtered queries

**Query Patterns:**
- Use `SELECT` with specific columns (avoid `SELECT *`)
- Limit result sets with `LIMIT`
- Use `EXISTS` for boolean checks (faster than `COUNT`)

**Connection Pooling:**
- SQLAlchemy pool size: 5-10 connections
- Pool recycle: 3600 seconds (1 hour)

---

### RocksDB Optimizations

**Compression:**
- Zstandard level 3 (balanced compression/speed)
- 70% space savings on average

**LSM Tree Tuning:**
- Write buffer size: 64 MB (default)
- Max write buffer number: 3
- Background compaction threads: 2

**Read Performance:**
- Block cache: 256 MB (hot data in memory)
- Bloom filters enabled (reduce disk seeks)

---

### Redis Optimizations

**Memory Management:**
- Max memory: 256 MB
- Eviction policy: `allkeys-lru` (least recently used)
- Persist: AOF disabled (ephemeral data only)

**Key Expiration:**
- Set TTL on all keys
- Use Redis `SCAN` for bulk operations (not `KEYS`)

---

## Backup & Recovery

### PostgreSQL Backups

**Frequency:** Daily (automated via Supabase)

**Retention:** 7 days

**Recovery:** Point-in-time recovery (PITR) available

---

### RocksDB Backups

**Frequency:** Weekly

**Strategy:**
1. Stop writes (graceful shutdown)
2. Create snapshot: `cp -r data/content.rocksdb data/backups/content-{date}.rocksdb`
3. Upload to S3 (optional)
4. Resume writes

**Recovery:**
1. Stop application
2. Replace `data/content.rocksdb` with backup
3. Restart application

---

### Redis Backups

**Strategy:** No backups (ephemeral state only)

**Recovery:** Rebuild FSM state from PostgreSQL on restart

---

## Data Privacy & Security

### Sensitive Data

**Stored:**
- Telegram user IDs (public identifiers)
- Usernames (public)
- Conversation history (private)
- User memory (private)

**NOT Stored:**
- Phone numbers
- Email addresses
- Payment information

---

### Encryption

**At Rest:**
- PostgreSQL: Supabase encryption enabled
- RocksDB: Filesystem-level encryption (optional)
- Redis: No encryption (ephemeral data)

**In Transit:**
- PostgreSQL: SSL/TLS required
- Redis: Local connection only (no network exposure)

---

### Data Retention

**User Data:**
- Active users: Indefinite
- Deleted accounts: 30 days grace period, then hard delete

**Conversation Data:**
- Active conversations: Indefinite
- User can delete via `/memory clear`

**Post Data:**
- Posts: Indefinite (archival)
- Content (RocksDB): Indefinite

---

**Data Models Owner:** Development Team
**Last Review:** 2026-02-13
**Next Review:** Monthly during active development
