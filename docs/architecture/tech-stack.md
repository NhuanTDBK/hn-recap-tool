# Tech Stack

**Project:** HN Pal - Intelligent HackerNews Telegram Bot
**Version:** 2.0 (Multi-Phase Implementation)
**Last Updated:** 2026-02-13

---

## Core Technologies

### Backend

**Language & Runtime:**
- **Python 3.11+** - Primary language
- **Reason:** Modern async support, type hints, excellent library ecosystem, strong LLM integration

**Bot Framework:**
- **aiogram 3.x** - Async Telegram bot framework  
- **Reason:** Native async/await, built-in FSM for state management, clean middleware, active development

**Task Scheduling:**
- **APScheduler 3.10+** - Background job scheduling
- **Reason:** Simple, Pythonic, supports cron-like scheduling, async support

### Data Storage

**Metadata Storage:**
- **PostgreSQL 14+** - Relational database
- **Use Cases:** Posts, users, conversations, summaries, token tracking 
- **ORM:** SQLAlchemy 2.x with Alembic migrations
- **Reason:** ACID transactions, structured queries, production-ready

**Content Storage:**
- **RocksDB** - Embedded key-value database
- **Use Cases:** HTML, text, and markdown content (large blobs)
- **Compression:** Zstandard built-in (~70% space savings)
- **Reason:** LSM tree optimized for write-heavy workloads, no filesystem overhead

**State Management:**
- **Redis 7.0+** - In-memory data store
- **Use Cases:** Telegram bot FSM state, user sessions, caching
- **Reason:** Fast key-value access, supports TTL, FSM storage for aiogram

### External APIs

**HackerNews:**
- **Current:** HN Algolia API - `http://hn.algolia.com/api/v1`
- **Recommended:** Firebase API - `/v0/maxitem` + `/v0/item/{id}`
- **Migration:** Incremental ID scanning for efficient polling
- **Rate Limit:** No documented limits for Firebase API

**Content Extraction:**
- **trafilatura 1.6+** - Article text extraction  
- **markitdown** - HTML to Markdown conversion
- **User-Agent Rotation** - 11+ browser agents to avoid blocking
- **Reason:** Best-in-class extraction, handles paywalls/JS sites

**LLM Provider:**
- **OpenAI Agents SDK** - Agent orchestration framework
- **Models:** GPT-4o-mini (cost-effective), GPT-4o (advanced)
- **Observability:** Langfuse integration for tracing
- **Cost Budget:** ~$2-5/day for 200 posts + conversations

**Telegram Bot:**
- **Telegram Bot API** - Official bot platform
- **Deployment:** Polling (dev) → Webhook (prod on Vercel)
- **Rate Limits:** 30 messages/second, managed by aiogram

### AI Agents

**Agent Framework:**
- **OpenAI Agents SDK** - Multi-agent orchestration
- **Structured Outputs:** Pydantic models for type safety
- **Tool Calling:** Database queries, web search, memory access
- **Reason:** Native agent abstractions, multi-turn conversations, context management

**Agent Types:**
- **SummarizationAgent:** Generate article summaries (Phase 2)
- **DiscussionAgent:** Facilitate conversations about posts (Phase 5) 
- **MemoryAgent:** Personalized interactions with user context (Phase 6)
- **QAAgent:** Answer questions with database tools (Phase 3+)

**Observability:**
- **Langfuse** - LLM call tracing and analytics
- **Token Tracking:** Per-user usage for cost monitoring
- **Performance Metrics:** Agent response times, success rates

---

## Development Tools

### Package Management

**Backend:**
- **uv** - Fast Python package manager
- **pyproject.toml** - Configuration file  
- **uv.lock** - Lockfile for reproducible builds
- **Reason:** Faster than pip/poetry, excellent dependency resolution

### Code Quality

**Linting & Formatting:**
- **Ruff** - Fast Python linter and formatter
- **Reason:** Combines linting + formatting in one fast tool, replacing Black

**Type Checking:**
- **mypy** - Static type checker
- **Reason:** Catch type errors early, improve code reliability

### Testing

**Backend:**
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support  
- **httpx** - HTTP client for API testing
- **Bot Testing:** aiogram test utilities for bot handlers

### Version Control

**Repository:**
- **Git + GitHub**
- **Branching:** Simple feature branches for MVP

---

## Infrastructure & Deployment

### Local Development

**Database Services:**
- **Docker Compose** - PostgreSQL + Redis containers
- **Port Mapping:** PostgreSQL:5432, Redis:6379 
- **Data Volumes:** Persistent storage across restarts

**Bot Development:**
- **Polling Mode** - Long-polling for local testing
- **Environment:** `.env` files with API keys
- **Hot Reload:** File watching for development

### Production Deployment (Future)

**Platform:**
- **Vercel** - Serverless functions for webhooks
- **Webhook Endpoint:** `/api/telegram-webhook`
- **Reason:** Zero-config deployment, automatic scaling

**Database:**
- **Supabase** - Managed PostgreSQL with APIs
- **Redis:** Upstash or Redis Cloud (managed)
- **RocksDB:** Local storage on Vercel filesystem

**Monitoring:**
- **Vercel Analytics** - Function performance
- **Langfuse** - LLM observability
- **Bot Logs:** Structured logging to stdout

---

## Library Dependencies (Current Implementation)

### Core Backend

```toml
# pyproject.toml (uv)
[project]
name = "hn-pal"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    # Core Framework
    "aiogram>=3.0.0",           # Telegram bot framework
    "pydantic>=2.0.0",          # Data validation
    "pydantic-settings>=2.0.0", # Settings management
    
    # Database & Storage
    "sqlalchemy>=2.0.0",        # Database ORM
    "alembic>=1.13.0",          # Database migrations
    "psycopg2-binary>=2.9.0",   # PostgreSQL driver
    "python-rocksdb>=0.8.0",    # Content storage
    "redis>=5.0.0",             # State management
    
    # HTTP & Content Processing
    "httpx>=0.24.0",            # Async HTTP client
    "trafilatura>=1.6.0",       # Article extraction
    "markitdown>=0.1.0",        # HTML to Markdown
    
    # AI & LLM
    "openai-agents",             # Agent framework
    "langfuse>=2.0.0",          # LLM observability
    "tiktoken>=0.5.0",          # Token counting
    
    # Task Scheduling
    "apscheduler>=3.10.0",      # Background jobs
    
    # Utilities
    "python-dotenv>=1.0.0",     # Environment variables
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0", 
    "ruff>=0.1.0",              # Linting + formatting
    "mypy>=1.8.0",              # Type checking
]
```
---

## API Keys & Configuration

**Required Environment Variables:**

```bash
# Backend (.env)

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/hn_pal
REDIS_URL=redis://localhost:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=123456789:ABC...

# LLM API
OPENAI_API_KEY=sk-proj-...
# Alternative: ANTHROPIC_API_KEY=sk-ant-...

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Application
ENVIRONMENT=development  # or production
DEBUG=true
LOG_LEVEL=INFO
```

---

## Data Storage & Performance

**Storage Estimates (with RocksDB compression):**

- Raw posts metadata: ~50 KB/day (200 posts × ~250 bytes)
- Compressed content (RocksDB): ~600 KB/day (200 posts × ~3 KB compressed)
- Summaries: ~100 KB/day (200 posts × ~500 bytes)
- User data & conversations: ~50 KB/day
- **Daily Total:** ~800 KB/day = ~300 MB/year
- **10-year projection:** ~3 GB (very manageable)

**Performance Targets:**

- HN API polling: < 30 seconds for 200 posts
- Content crawling: < 5 minutes (3 concurrent workers)
- Summarization: < 10 minutes (sequential processing)
- Bot response time: < 3 seconds for simple queries
- Discussion agent: < 10 seconds for context loading

**RocksDB Benefits:**

- 70% space savings vs uncompressed files
- No filesystem inode overhead (730K inodes → ~20 SST files)
- O(1) key-value access by HN ID
- Built-in compression and compaction

---

## Architecture Phases

### Phase 1: Ingest Pipeline (✅ Completed)

**Technologies:**
- HN API polling with APScheduler
- Content extraction with trafilatura + markitdown
- RocksDB for content storage
- PostgreSQL for metadata
- Pipeline orchestration

### Phase 2: Summarization (⏳ In Progress)

**Technologies:**
- OpenAI Agents SDK for summarization
- Prompt engineering with LLM-as-judge evaluation
- Langfuse observability integration
- Batch processing optimization

### Phase 3: Bot Foundation (📝 Ready)

**Technologies:**
- aiogram 3.x Telegram bot framework
- FSM state management (IDLE ↔ DISCUSSION)
- Redis for bot state persistence
- Inline buttons for user interactions

### Phase 4: Interactive Elements (📝 Ready)

**Technologies:**
- Callback routing for button actions
- Bookmark system integration
- Interest tracking via reactions
- UI feedback and polish

### Phase 5: Discussion System (📝 Ready)

**Technologies:**
- DiscussionAgent with context loading
- Multi-turn conversation management
- 30-minute timeout handling
- Conversation persistence

### Phase 6: Memory System (📝 Ready)

**Technologies:**
- Memory extraction agents
- Two-tier storage (MEMORY.md + daily notes)
- BM25 full-text search
- Personalized context injection

**Legend:** ✅ Completed, ⏳ In Progress, 📝 Documented

---

## Security & Privacy

**Bot Security:**

- Telegram webhook validation
- Rate limiting per user (aiogram middleware)
- Input validation via Pydantic
- Environment variable separation

**Data Privacy:**

- User data stored locally (PostgreSQL + RocksDB)
- No third-party analytics or tracking
- User memory can be cleared on request
- Conversation data encrypted at rest

**API Security:**

- HTTPS required in production
- API keys in environment variables only
- LLM API call logging for audit trails

---

## Migration Strategy

### From MVP to Production

**Current (File-based MVP):**

- JSONL files for posts
- Filesystem for content
- APScheduler in-process

**Target (Database-backed Production):**

- PostgreSQL for structured data
- RocksDB for content blobs
- Vercel serverless for bot hosting

**Migration Steps:**

1. Add PostgreSQL schema (Activity 1.1)
2. Implement RocksDB storage (Activity 1.5) 
3. Unified pipeline orchestrator (Activity 1.7)
4. Deploy Telegram bot (Activity 3.0)
5. Add conversation features (Activities 4.0-6.0)

**Timeline:** Phases can be implemented incrementally without breaking changes.

---

**Tech Stack Owner:** Development Team  
**Last Review:** 2026-02-13  
**Next Review:** Monthly during active development
