# Updated Project Structure

**Status:** Brainstormed based on requirements analysis  
**Date:** February 13, 2026  
**Context:** Aligning current MVP structure with [spec.md](../spec.md) and [activity documents](../activities/README.md)

---

## Gap Analysis: Current vs. Target

| Area | Current | Target (Spec) | Gap |
|------|---------|---------------|-----|
| **User model** | Email/password (web app) | Telegram-first (`telegram_id`, `interests`, `memory_enabled`) | Complete rewrite |
| **Storage** | JSONL files on disk | PostgreSQL + RocksDB | New layer needed |
| **Bot** | None | aiogram 3.x with FSM states | Entire new subsystem |
| **Domain entities** | User, Post, Comment, Digest | + Delivery, Conversation, Memory | 3 new entities |
| **Agents** | Summarizer, Reducer, Synthesizer | + Discussion, Memory Extraction | 2 new agents |
| **Pipeline** | Separate CLI scripts | APScheduler orchestrator | Orchestration layer |
| **Interfaces** | Monolithic 529-line file | Split by concern + new repos | Refactor + expansion |
| **Content storage** | Filesystem (`data/content/`) | RocksDB with column families | New adapter |
| **Presentation** | FastAPI REST API | FastAPI + Telegram bot handlers | Bot handlers layer |
| **Database** | None (JSONL) | SQLAlchemy + Alembic | Full ORM layer |

---

## Proposed Directory Structure

```
hackernews_digest/
├── backend/
│   ├── alembic/                          # 🆕 Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI entry point
│   │   │
│   │   ├── domain/                       # ── DOMAIN LAYER ──
│   │   │   ├── __init__.py
│   │   │   ├── entities.py               # 🔄 Expand: + Delivery, Conversation, MemoryEntry
│   │   │   │                              #    Rewrite User for Telegram (telegram_id, interests)
│   │   │   ├── value_objects.py          # PostType, ReactionType, DiscussionState, MemoryCategory
│   │   │   └── exceptions.py
│   │   │
│   │   ├── application/                  # ── APPLICATION LAYER ──
│   │   │   ├── __init__.py
│   │   │   ├── interfaces/               # 🔄 Split 529-line interfaces.py → per-concern files
│   │   │   │   ├── __init__.py
│   │   │   │   ├── repositories.py       #   UserRepo, PostRepo, DigestRepo, CommentRepo,
│   │   │   │   │                          #   DeliveryRepo 🆕, ConversationRepo 🆕, MemoryRepo 🆕
│   │   │   │   ├── content_storage.py    #   ContentRepository (text/html/markdown)
│   │   │   │   ├── services.py           #   HNService, ContentExtractor, CacheService,
│   │   │   │   │                          #   SummarizationService, SynthesisService
│   │   │   │   ├── agents.py             # 🆕 DiscussionService, MemoryExtractionService
│   │   │   │   └── security.py           #   PasswordHasher, TokenService
│   │   │   │
│   │   │   └── use_cases/
│   │   │       ├── __init__.py
│   │   │       ├── collection.py          # Fetch HN posts (existing)
│   │   │       ├── crawl_content.py       # Crawl article URLs (existing)
│   │   │       ├── summarization.py       # Generate summaries (existing)
│   │   │       ├── synthesis.py           # 🔄 Extract from scripts → use case
│   │   │       ├── delivery.py           # 🆕 Digest delivery to users
│   │   │       ├── discussion.py         # 🆕 Start/switch/end discussions
│   │   │       ├── memory.py             # 🆕 Extract/search/manage memory
│   │   │       ├── auth.py               # (existing, may deprecate for Telegram-only)
│   │   │       └── digests.py            # (existing)
│   │   │
│   │   ├── infrastructure/              # ── INFRASTRUCTURE LAYER ──
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   └── settings.py           # 🔄 Add: database_url, redis_url, telegram_bot_token
│   │   │   │
│   │   │   ├── database/                 # 🆕 SQLAlchemy + Alembic
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py               #   Base, engine, metadata
│   │   │   │   ├── models.py             #   ORM models (mirrors domain entities)
│   │   │   │   └── session.py            #   AsyncSession factory
│   │   │   │
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── jsonl/                # 🔄 Namespace existing JSONL repos (keep for local dev)
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── helpers.py
│   │   │   │   │   ├── post_repo.py
│   │   │   │   │   ├── content_repo.py
│   │   │   │   │   ├── digest_repo.py
│   │   │   │   │   └── user_repo.py
│   │   │   │   ├── postgres/             # 🆕 PostgreSQL implementations (production)
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── post_repo.py
│   │   │   │   │   ├── user_repo.py
│   │   │   │   │   ├── delivery_repo.py
│   │   │   │   │   ├── conversation_repo.py
│   │   │   │   │   └── memory_repo.py
│   │   │   │   └── rocksdb/              # 🆕 RocksDB content storage (replaces filesystem)
│   │   │   │       ├── __init__.py
│   │   │   │       └── content_store.py  #   Column families: html, text, markdown
│   │   │   │
│   │   │   ├── services/                 # External service integrations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── hn_client.py
│   │   │   │   ├── enhanced_content_extractor.py
│   │   │   │   ├── crawl_status_tracker.py
│   │   │   │   ├── redis_cache.py
│   │   │   │   ├── telegram_notifier.py
│   │   │   │   └── content_extractor.py
│   │   │   │
│   │   │   ├── agents/                   # 🔄 Rename from services (AI/LLM-specific)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── summarization_agent.py    # OpenAI summarizer + reducer
│   │   │   │   ├── synthesis_agent.py        # OpenAI general + topic synthesis
│   │   │   │   ├── discussion_agent.py       # 🆕 Multi-turn conversation agent
│   │   │   │   ├── memory_extraction_agent.py # 🆕 Extract insights from interactions
│   │   │   │   └── prompts/
│   │   │   │       ├── summarizer.md
│   │   │   │       ├── reducer.md
│   │   │   │       ├── general_synthesis.md
│   │   │   │       ├── synthesis_topic.md
│   │   │   │       ├── discussion.md         # 🆕
│   │   │   │       └── memory_extraction.md  # 🆕
│   │   │   │
│   │   │   ├── pipeline/                 # 🆕 Pipeline orchestration (Activity 1.7)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py       #   PipelineOrchestrator (APScheduler)
│   │   │   │   ├── steps.py              #   Step definitions (collect, crawl, summarize, etc.)
│   │   │   │   └── reporting.py          #   Run reports, timing, metrics
│   │   │   │
│   │   │   ├── security/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── jwt_handler.py        # (may deprecate if Telegram-only)
│   │   │   │   └── password_hasher.py    # (may deprecate if Telegram-only)
│   │   │   │
│   │   │   └── jobs/                     # 🔄 Thin wrappers → delegate to pipeline
│   │   │       ├── __init__.py
│   │   │       └── data_collector.py
│   │   │
│   │   └── presentation/               # ── PRESENTATION LAYER ──
│   │       ├── __init__.py
│   │       ├── api/                      # FastAPI REST API (existing)
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── digests.py
│   │       │   └── dependencies.py
│   │       ├── schemas/                  # API request/response schemas
│   │       │   ├── __init__.py
│   │       │   ├── user.py
│   │       │   └── digest.py
│   │       └── bot/                     # 🆕 Telegram bot (aiogram 3.x) - Phase 3-7
│   │           ├── __init__.py
│   │           ├── bot.py               #   Bot instance, dispatcher setup
│   │           ├── states.py            #   FSM states (IDLE, DISCUSSION, ONBOARDING)
│   │           ├── handlers/
│   │           │   ├── __init__.py
│   │           │   ├── commands.py      #   /start, /pause, /saved, /memory, /token
│   │           │   ├── callbacks.py     #   Inline button callbacks (discuss, save, react)
│   │           │   ├── discussion.py    #   Discussion message routing
│   │           │   └── onboarding.py    #   Interest selection flow
│   │           ├── keyboards/
│   │           │   ├── __init__.py
│   │           │   └── inline.py        #   Button layouts (Discuss, Read, Save, 👍👎)
│   │           ├── middlewares/
│   │           │   ├── __init__.py
│   │           │   └── auth.py          #   User registration/lookup middleware
│   │           └── formatters/
│   │               ├── __init__.py
│   │               └── digest.py        #   Message formatting (Style 1 & 2)
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── domain/                   # Entity validation tests
│   │   │   ├── use_cases/                # Business logic tests (mocked deps)
│   │   │   └── agents/                   # Agent prompt/behavior tests
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   ├── repositories/             # JSONL + Postgres repo tests
│   │   │   ├── services/                 # HN client, content extractor tests
│   │   │   └── bot/                      # 🆕 Bot handler tests (aiogram test utils)
│   │   ├── e2e/                          # 🆕 Full pipeline tests
│   │   │   └── test_pipeline.py
│   │   ├── fixtures/                     # 🆕 Shared test data
│   │   │   ├── posts.py
│   │   │   └── users.py
│   │   └── conftest.py
│   │
│   ├── alembic.ini                       # 🆕
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── data/                                 # 🔄 MINIMAL - only RocksDB + memory files
│   ├── content.rocksdb/                  # Content blobs (3 column families: html, text, markdown)
│   └── memory/                           # 🆕 Phase 6 — per-user memory files
│       └── {user_id}/
│           ├── MEMORY.md                 # Durable facts (< 2000 words)
│           ├── memory/
│           │   └── YYYY-MM-DD.md         # Daily notes
│           └── index/                    # BM25 search index
│
├── scripts/
│   ├── fetch_hn_posts.py
│   ├── crawl_content.py
│   ├── run_summarization.py
│   ├── run_synthesis.py
│   ├── run_synthesis_topic.py
│   ├── push_to_telegram.py
│   ├── run_pipeline.py                   # 🆕 Unified pipeline CLI
│   ├── run_bot.py                        # 🆕 Start Telegram bot (polling mode)
│   └── run_full_flow.py
│
├── docs/
│   ├── activities/
│   ├── architecture/
│   ├── epics/
│   ├── spec.md
│   └── ...
│
├── docker-compose.yml                    # 🔄 Add postgres + redis + pgadmin
├── pyproject.toml
├── AGENTS.md
└── README.md
```

---

## Key Structural Decisions

### 1. **Split `interfaces.py` (529 lines) → `interfaces/` package**

The monolithic interfaces file is hard to navigate. Split by concern:

| File | Interfaces |
|------|-----------|
| `repositories.py` | UserRepo, PostRepo, DigestRepo, CommentRepo, **DeliveryRepo**, **ConversationRepo**, **MemoryRepo** |
| `content_storage.py` | ContentRepository (html/text/markdown) |
| `services.py` | HNService, ContentExtractor, CacheService, SummarizationService, SynthesisService |
| `agents.py` | **DiscussionService**, **MemoryExtractionService** |
| `security.py` | PasswordHasher, TokenService |

**Migration strategy:** Re-export all interfaces from `interfaces/__init__.py` for backward compatibility.

---

### 2. **Separate `agents/` from `services/`**

Current: agents (summarization, synthesis) live in `services/` alongside non-AI services (HN client, Redis, Telegram). These have fundamentally different concerns:

- **services/**: HTTP clients, caches, notifiers — deterministic, infrastructure
- **agents/**: LLM-powered, prompt-driven, stochastic — AI orchestration

**Benefit:** Clear separation of AI vs. traditional services, easier to swap LLM providers.

---

### 3. **New `pipeline/` package (Activity 1.7)**

Replace ad-hoc `jobs/data_collector.py` with a proper orchestration layer:

- `orchestrator.py` — APScheduler setup, step chaining, error isolation
- `steps.py` — Each pipeline step as a callable with clear input/output
- `reporting.py` — Run timing, success/failure metrics, per-step stats

**Pipeline Steps:**
1. Collect (fetch HN posts)
2. Crawl (extract content from URLs)
3. Summarize (generate AI summaries)
4. Synthesize (cross-article themes)
5. Deliver (send to Telegram)
6. Extract Memory (daily batch - Phase 6)

---

### 4. **New `presentation/bot/` package (Phase 3-7)**

The Telegram bot is a separate presentation concern from the REST API:

- `handlers/` — Message and callback routing (like API routes)
- `keyboards/` — Inline button definitions (like API schemas)
- `states.py` — FSM state definitions (IDLE, DISCUSSION, ONBOARDING)
- `middlewares/` — User auth/registration per message
- `formatters/` — Message formatting (Style 1 brief, Style 2 flat scroll)

**Key files:**
- `bot.py` — Bot instance, dispatcher, FSM storage
- `handlers/callbacks.py` — Inline button callbacks (💬 Discuss, ⭐ Save, 👍👎)
- `handlers/discussion.py` — Route messages during DISCUSSION state to agent
- `formatters/digest.py` — Format digest messages (Style 1 vs. 2)

---

### 5. **Dual repository implementations**

Keep JSONL repos working (MVP) while adding Postgres repos (production):

```
repositories/
├── jsonl/          # Current — keep working for local dev
└── postgres/       # New — SQLAlchemy async ORM
```

**Switch via config:** `STORAGE_BACKEND=jsonl|postgres`

**Why keep JSONL:**
- No database setup needed for first-time contributors
- Fast iteration during development
- Easy debugging (cat files vs. SQL queries)
- Postgres for production only

---

### 6. **RocksDB replaces filesystem for content**

**Before:**
```
data/content/
├── html/{hn_id}.html
├── text/{hn_id}.txt
└── markdown/{hn_id}.md
```

**After:**
```
data/content.rocksdb/  (single database with column families)
```

**Benefits:**
- 70% space savings (built-in Zstandard compression)
- No filesystem overhead (inodes, blocks, metadata per file)
- O(1) key-value access by HN ID
- Single-writer optimized (LSM tree architecture)
- Simple backup (copy one directory)

**See:** [Activity 1.5 - RocksDB Content Storage](../activities/activity-1.5-rocksdb-content-storage.md)

---

### 7. **Domain entity expansion**

**New entities needed** (from [spec.md](../spec.md) data model):

```python
class Delivery(BaseModel):
    """Track which posts were delivered to which users."""
    user_id: str
    post_id: str
    message_id: int              # Telegram message ID
    batch_id: str                # Groups posts in same digest
    reaction: Optional[str]      # "up" | "down" | None
    delivered_at: datetime

class Conversation(BaseModel):
    """Store discussion history between user and bot."""
    user_id: str
    post_id: str
    messages: list[dict]         # [{role, content, timestamp}, ...]
    token_usage: dict            # {input_tokens, output_tokens}
    started_at: datetime
    ended_at: Optional[datetime]

class MemoryEntry(BaseModel):
    """Store extracted user knowledge and preferences."""
    user_id: str
    type: str                    # "interest" | "fact" | "discussion_note"
    content: str
    source_post_id: Optional[str]
    active: bool = True
    created_at: datetime
```

**User entity needs rewrite** for Telegram-first:

```python
class User(BaseModel):
    telegram_id: int             # Primary identifier (not email)
    username: Optional[str]
    interests: list[str]         # ["distributed systems", "rust"]
    active_discussion_post_id: Optional[str]
    memory_enabled: bool = True
    status: str = "active"       # "active" | "paused"
    created_at: datetime
    # Remove: email, hashed_password (no web auth needed)
```

---

### 8. **New use cases**

| Use Case | Purpose | Phase | Activity |
|----------|---------|-------|----------|
| `delivery.py` | Rank posts × user interests, send digest via Telegram | 3 | 3.0 |
| `discussion.py` | Start/switch/end discussions, load context, save convo | 5 | 5.0 |
| `memory.py` | Extract memory from interactions, search, manage | 6 | 6.0 |
| `synthesis.py` | Extract from `scripts/run_synthesis.py` → use case | 2 | Current |

---

### 9. **Minimal `data/` folder**

With RocksDB + PostgreSQL, the `data/` folder shrinks to almost nothing:

| Current `data/` path | New home |
|---|---|
| `raw/*.jsonl` (post metadata) | PostgreSQL `posts` table |
| `content/html/`, `text/`, `markdown/` | RocksDB column families |
| `processed/summaries/` | PostgreSQL `posts.summary` column |
| `processed/synthesis/` | PostgreSQL `synthesis` table |
| `users/` | PostgreSQL `users` table |
| `crawl_status.jsonl` | PostgreSQL `posts.is_crawl_success` |

**What remains:**
- `content.rocksdb/` — Content blobs with compression
- `memory/` — Per-user memory files (Phase 6, could move to PostgreSQL later)

---

## Migration Roadmap

Recommended order to avoid breaking existing functionality:

### Phase 0: Refactor (No Breaking Changes)

1. **Split interfaces** → `interfaces/` package (re-export from `__init__.py`, zero breakage)
2. **Move agents** → `infrastructure/agents/` (rename imports in use cases)
3. **Add synthesis use case** (extract from `scripts/run_synthesis.py`)

### Phase 1: Database Layer

4. **Add database ORM** (`infrastructure/database/`)
5. **Create Alembic migrations** (initial schema: users, posts, deliveries, conversations, memory)
6. **Add Postgres repos** alongside JSONL repos (dual backend support)

### Phase 2: Content Storage

7. **Implement RocksDB adapter** (`repositories/rocksdb/content_store.py`)
8. **Migrate existing content** (one-time script: filesystem → RocksDB)
9. **Update crawl pipeline** to use RocksDB

### Phase 3: Pipeline Orchestration

10. **Create pipeline package** (`infrastructure/pipeline/`)
11. **Extract steps** from existing scripts
12. **Test orchestrator** (manual runs before scheduling)

### Phase 4: Telegram Bot (Phased)

13. **Bot foundation** (Activity 3.0): `/start`, basic commands, FSM setup
14. **Digest delivery** (Activity 3.0): Send formatted messages to users
15. **Inline buttons** (Activity 4.0): Discuss, Read, Save, 👍👎
16. **Discussion agent** (Activity 5.0): Multi-turn conversations
17. **Memory system** (Activity 6.0): Extract, store, surface user knowledge

---

## File Count Comparison

| Layer | Current Files | Proposed Files | Change |
|-------|---------------|----------------|--------|
| Domain | 3 | 3 | Same (but expanded entities) |
| Interfaces | 1 (529 lines) | 5 (~100 lines each) | Split for clarity |
| Use Cases | 5 | 8 | +3 (delivery, discussion, memory) |
| Repositories | 5 (JSONL only) | 11 (5 JSONL + 5 Postgres + 1 RocksDB) | +6 |
| Services | 7 | 7 | Same |
| Agents | 2 (in services/) | 4 (separate package) | +2 (discussion, memory), moved |
| Pipeline | 1 (jobs/) | 3 (orchestrator, steps, reporting) | +2 |
| Presentation | 6 (API only) | 14 (API + Bot) | +8 (bot handlers, keyboards, formatters) |
| **Total** | ~30 files | ~55 files | +25 files (+83%) |

**Analysis:** File count nearly doubles, but each file is more focused and easier to maintain. Total LOC may increase only 30-40% due to:
- Splitting interfaces doesn't add code
- Bot handlers are thin routing layers
- Pipeline orchestrator replaces bash scripts

---

## Configuration Changes

### Current `.env`:
```bash
SECRET_KEY=...
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=...
```

### Proposed `.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/hn_pal
REDIS_URL=redis://localhost:6379/0

# Storage backend (jsonl | postgres)
STORAGE_BACKEND=postgres
CONTENT_STORAGE=rocksdb  # or: filesystem

# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_CHANNEL_ID=@your_channel  # (may deprecate for DM-only bot)

# Pipeline
PIPELINE_SCHEDULE=0 7 * * *  # Daily at 7:00 AM UTC

# Optional: Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

---

## Docker Compose Updates

Add PostgreSQL, Redis, and optional admin tools:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: hn_pal
      POSTGRES_PASSWORD: hn_pal_dev
      POSTGRES_DB: hn_pal
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Optional: PostgreSQL admin
  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@hnpal.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin

  # Optional: Redis admin
  redis-commander:
    image: rediscommander/redis-commander:latest
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:
```

---

## Next Steps

1. **Review this document** with the team
2. **Prioritize phases** based on roadmap
3. **Create implementation issues** for each phase
4. **Start with Phase 0** (refactor without breaking changes)
5. **Test dual backend support** (JSONL + Postgres) before full migration

---

## Related Documents

- [spec.md](../spec.md) — Product requirements (Telegram bot vision)
- [activities/README.md](../activities/README.md) — Implementation activities
- [activities/activity-1.5-rocksdb-content-storage.md](../activities/activity-1.5-rocksdb-content-storage.md) — RocksDB design
- [activities/activity-3.0-telegram-bot-foundation.md](../activities/activity-3.0-telegram-bot-foundation.md) — Bot architecture
- [AGENTS.md](../../AGENTS.md) — Agent system documentation
