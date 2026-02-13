# Architecture Documentation Index

**Project:** HN Pal - Intelligent HackerNews Telegram Bot
**Version:** 2.0 (Multi-Phase Implementation)
**Last Updated:** 2026-02-13

---

## Architecture Overview

This directory contains the technical architecture documentation for HN Pal, a Telegram bot that delivers curated HackerNews digests and enables AI-powered discussions about posts. These documents guide development through a phased implementation approach, from MVP data collection to advanced memory-based personalization.

---

## Core Architecture Documents

### 1. **[Tech Stack](./tech-stack.md)** 📚

**Purpose:** Technology choices and infrastructure

**Contents:**
- Core technologies: Python 3.11+, aiogram 3.x, PostgreSQL, RocksDB, Redis
- Development tools: uv package manager, Ruff linting, pytest
- External APIs: HN Firebase API, OpenAI Agents SDK, Telegram Bot API
- Deployment: Local dev → Vercel serverless (future)
- Phase-specific tech requirements

**Read this first to understand:**
- What libraries we're using and why
- How components fit together
- Development toolchain setup

---

### 2. **[Data Models](./data-models.md)** 🗄️

**Purpose:** Database schemas and data structures

**Contents:**
- **PostgreSQL Schema:** 7 tables (users, posts, deliveries, conversations, memory, token_usage, agent_calls)
- **RocksDB Storage:** Content blobs with column families (html, text, markdown)
- **Redis State:** Bot FSM state and session caching
- **Pydantic Models:** Type-safe data validation
- **Migration Strategy:** JSONL → PostgreSQL + RocksDB

**Read this when:**
- Implementing any data access layer
- Writing database migrations
- Designing new features that need persistence
- Understanding storage architecture

---

### 3. **[Source Tree](./source-tree.md)** 📁

**Purpose:** Project structure and file organization

**Contents:**
- Directory organization (backend/, scripts/, data/, docs/)
- Clean architecture layers (domain, application, infrastructure, presentation)
- File naming conventions
- Import patterns (absolute vs relative)
- Module responsibilities

**Read this when:**
- Starting new development work
- Adding new modules or services
- Refactoring code structure
- Onboarding to the project

---

### 4. **[Coding Standards](./coding-standards.md)** ✨

**Purpose:** Code quality and style guidelines

**Contents:**
- Python style guide (PEP 8 + Ruff formatting)
- Naming conventions (snake_case, PascalCase, UPPER_SNAKE_CASE)
- Type hints and docstrings (Google-style)
- Error handling patterns
- Async/await best practices
- Testing standards (pytest, AAA pattern)

**Read this when:**
- Writing new code
- Reviewing pull requests
- Setting up IDE/linter configuration

---

### 5. **[API Design](./api-design.md)** 🔌 *(To be created)*

**Purpose:** Telegram bot command and callback routing

**Contents:**
- Bot commands (/start, /pause, /memory, /saved, /token)
- Inline button callbacks (Discuss, Read, Save, reactions)
- State machine design (IDLE ↔ DISCUSSION ↔ ONBOARDING)
- Message templates and formatting
- Error handling and user feedback

**Status:** To be documented in Phase 3 (Bot Foundation)

---

## Implementation Phases

### Phase 1: Ingest Pipeline ✅ (Mostly Complete)

**Goal:** Collect and store HN posts with article content

**Architecture Focus:**
- HN API polling (Firebase API recommended)
- Content extraction (trafilatura + markitdown)
- PostgreSQL + RocksDB storage
- Pipeline orchestration (APScheduler)

**Key Documents:**
- [Tech Stack](./tech-stack.md) - Storage technologies
- [Data Models](./data-models.md) - `posts` table schema, RocksDB structure
- [Source Tree](./source-tree.md) - Pipeline module organization

**Activities:**
- ✅ Activity 1.1: HN API polling
- ✅ Activity 1.3: Content crawling
- 🔄 Activity 1.5: RocksDB storage
- 🔄 Activity 1.7: Pipeline orchestration

---

### Phase 2: Summarization ⏳ (In Progress)

**Goal:** Generate AI-powered summaries of articles

**Architecture Focus:**
- OpenAI Agents SDK integration
- Langfuse observability
- Prompt engineering and evaluation
- Token tracking for cost management

**Key Documents:**
- [Tech Stack](./tech-stack.md) - LLM integration
- [Data Models](./data-models.md) - `agent_calls`, `user_token_usage` tables
- [Coding Standards](./coding-standards.md) - Agent design patterns

**Activities:**
- ⏳ Activity 2.3: Prompt engineering
- ⏳ Activity 2.5: LLM client with Agents SDK

---

### Phase 3: Bot Foundation 📝 (Documented)

**Goal:** Telegram bot with digest delivery

**Architecture Focus:**
- aiogram 3.x bot framework
- FSM state management (Redis)
- Message routing and commands
- Inline button system
- Digest delivery (flat scroll format)

**Key Documents:**
- [Tech Stack](./tech-stack.md) - Bot framework
- [Data Models](./data-models.md) - `users`, `deliveries` tables
- [API Design](./api-design.md) - Bot commands and callbacks *(to be created)*

**Activities:**
- 📝 Activity 3.0: Telegram bot foundation (7 sub-activities)

---

### Phase 4: Interactive Elements 📝 (Documented)

**Goal:** User interaction via inline buttons

**Architecture Focus:**
- Callback routing (Discuss, Read, Save, 👍👎)
- State transitions (IDLE → DISCUSSION)
- Bookmark system
- Interest tracking via reactions
- UI feedback and polish

**Key Documents:**
- [Data Models](./data-models.md) - `deliveries.reaction`, `deliveries.is_saved`
- [API Design](./api-design.md) - Callback handlers

**Activities:**
- 📝 Activity 4.0: Interactive elements (6 sub-activities)

---

### Phase 5: Discussion System 📝 (Documented)

**Goal:** AI-powered conversations about posts

**Architecture Focus:**
- DiscussionAgent with OpenAI Agents SDK
- Context loading (article + memory)
- Multi-turn conversation management
- Auto-switch and 30-min timeout
- Conversation persistence

**Key Documents:**
- [Data Models](./data-models.md) - `conversations` table
- [Tech Stack](./tech-stack.md) - Agent architecture
- [Coding Standards](./coding-standards.md) - Async conversation loops

**Activities:**
- 📝 Activity 5.0: Discussion system (7 sub-activities)

---

### Phase 6: Memory System ⏳ (Documented)

**Goal:** Personalized interactions with user memory

**Architecture Focus:**
- Two-tier memory (MEMORY.md + daily notes)
- Daily batch extraction (implicit)
- Real-time capture (explicit)
- BM25 full-text search
- Memory context injection into agents

**Key Documents:**
- [Data Models](./data-models.md) - `memory` table
- [Tech Stack](./tech-stack.md) - Memory extraction agents

**Activities:**
- ⏳ Activity 6.0: Memory system (6 sub-activities)

---

## Reading Order by Role

### For Backend Developers (Python)

**Getting Started:**
1. [Tech Stack](./tech-stack.md) → Understand technologies
2. [Source Tree](./source-tree.md) → Know where files go
3. [Coding Standards](./coding-standards.md) → Follow conventions
4. [Data Models](./data-models.md) → Understand schemas

**When Implementing:**
- **Phase 1 (Ingest):** Data Models → Source Tree → Tech Stack
- **Phase 2 (Summarization):** Tech Stack (Agents SDK) → Data Models (agent_calls)
- **Phase 3 (Bot):** Tech Stack (aiogram) → API Design → Data Models (users)
- **Phase 5 (Discussion):** Data Models (conversations) → Tech Stack (Agents)
- **Phase 6 (Memory):** Data Models (memory) → Tech Stack (BM25)

---

### For AI/ML Developers

**Getting Started:**
1. [Tech Stack](./tech-stack.md) → OpenAI Agents SDK, Langfuse
2. [Data Models](./data-models.md) → Token tracking, agent calls
3. `docs/activities/activity-2.3-summarization-prompt-engineering.md` → Prompt design

**When Implementing:**
- **Summarization:** Prompt engineering → LLM-as-judge evaluation → Token tracking
- **Discussion Agent:** Context loading → Multi-turn conversations → Memory injection
- **Memory Extraction:** Post-discussion extraction → Daily batch jobs → Confidence scoring

---

### For DevOps/Infrastructure

**Getting Started:**
1. [Tech Stack](./tech-stack.md) → Infrastructure requirements
2. [Data Models](./data-models.md) → Database setup (PostgreSQL, RocksDB, Redis)
3. `docs/activities/activity-1.7-scheduled-pipeline-orchestration.md` → Pipeline deployment

**When Deploying:**
- **Local Dev:** Docker Compose (PostgreSQL + Redis)
- **Production (Future):** Vercel serverless + Supabase + Upstash Redis

---

## Quick Reference

### Key File Locations

**Backend Code:**
```
backend/
├── app/
│   ├── domain/          # Business logic, models
│   ├── application/     # Use cases, orchestration
│   ├── infrastructure/  # External services, database, LLM clients
│   └── presentation/    # Telegram bot handlers (future)
├── scripts/             # CLI scripts (pipeline, migration)
└── tests/               # pytest test suite
```

**Data Storage:**
```
data/
├── content.rocksdb/     # HTML, text, markdown (compressed)
├── raw/                 # Legacy JSONL files (to be migrated)
└── processed/           # Summaries, synthesis (JSONL)
```

**Documentation:**
```
docs/
├── architecture/        # This directory
├── activities/          # Detailed activity documents
├── design/              # Design decisions
└── spec.md              # Product specification
```

---

### Essential Commands

**Setup (uv package manager):**
```bash
cd backend
uv sync                   # Install dependencies
```

**Database Migrations:**
```bash
uv run alembic upgrade head      # Apply migrations
uv run alembic revision --autogenerate -m "message"  # Create migration
```

**Run Pipeline:**
```bash
uv run python scripts/run_pipeline.py       # Full pipeline
uv run python scripts/crawl_content.py      # Crawl only
uv run python scripts/run_summarization.py  # Summarize only
```

**Run Tests:**
```bash
uv run pytest                    # All tests
uv run pytest tests/unit/        # Unit tests only
uv run pytest -v -s              # Verbose with print output
```

**Code Quality:**
```bash
uv run ruff check .              # Lint code
uv run ruff format .             # Format code
uv run mypy backend/app          # Type checking
```

**Future (Telegram Bot):**
```bash
uv run python -m app.presentation.bot  # Start bot (polling)
```

---

## Architecture Principles

### 1. Clean Architecture

**Layered Design:**
- **Domain:** Business logic, entities (posts, users, conversations)
- **Application:** Use cases, orchestration (pipelines, agents)
- **Infrastructure:** External services (DB, LLM APIs, Telegram)
- **Presentation:** User interfaces (Telegram bot handlers)

**Benefits:**
- Testable (mock external dependencies)
- Maintainable (clear separation of concerns)
- Flexible (swap implementations without changing business logic)

---

### 2. Storage Optimization

**PostgreSQL for Structure:**
- Relational data (users ↔ conversations ↔ memory)
- ACID transactions
- Complex queries

**RocksDB for Blobs:**
- High-performance content storage
- Built-in compression (Zstandard)
- No filesystem overhead (730K files → ~20 SST files)

**Redis for Ephemeral State:**
- Bot FSM state (IDLE, DISCUSSION)
- Session caching (30-min TTL)
- No persistence needed

---

### 3. Agent-First LLM Integration

**OpenAI Agents SDK:**
- Multi-agent architecture (SummarizationAgent, DiscussionAgent, MemoryAgent)
- Structured outputs (Pydantic validation)
- Tool calling (database queries, web search)
- Built-in observability (Langfuse integration)

**Benefits:**
- Native conversation management
- Type-safe agent responses
- Easy to add new agents
- Full LLM call tracing

---

### 4. Cost-Conscious Design

**Token Tracking:**
- Per-user daily aggregates (`user_token_usage` table)
- Per-call logging (`agent_calls` table)
- Cost calculation built-in

**Optimization Strategies:**
- Use GPT-4o-mini by default (~$0.03/day for 200 posts)
- Prompt caching (future - Anthropic API)
- Batch API for overnight runs (future - 50% cost savings)

---

### 5. Progressive Enhancement

**MVP First:**
- File-based MVP (JSONL) → works immediately
- Simple sequential processing → good enough for 200 posts/day
- Manual testing → fast iteration

**Production When Needed:**
- PostgreSQL + RocksDB → when scale requires it
- Parallel processing → when speed matters
- Automated testing → when features stabilize

---

## Migration Path

### Current State (Phase 1)

**Storage:** JSONL files + filesystem
**Pipeline:** Standalone scripts (collect, crawl, summarize)
**Status:** MVP working, ready for optimization

---

### Phase 1.5 (In Progress)

**Storage Migration:**
- ✅ PostgreSQL schema designed (`data-models.md`)
- 🔄 RocksDB implementation (`activity-1.5-rocksdb-content-storage.md`)
- 🔄 Migration script (`backend/scripts/migrate_jsonl_to_db.py`)

**Pipeline Unification:**
- 🔄 Unified orchestrator (`activity-1.7-scheduled-pipeline-orchestration.md`)
- 🔄 Step-level error isolation
- 🔄 Run reporting and metrics

---

### Phase 2-6 (Planned)

**Phase 2:** Summarization with Agents SDK + Langfuse
**Phase 3:** Telegram bot foundation (aiogram)
**Phase 4:** Interactive buttons (callbacks)
**Phase 5:** Discussion agent (conversations)
**Phase 6:** Memory system (personalization)

---

## Data Flow Diagrams

### Current: Ingest Pipeline

```
HN API → Collect Posts → Crawl URLs → Extract Content → Store (JSONL/Files)
                ↓              ↓              ↓
         PostgreSQL*     RocksDB*      Filesystem (current)

* Future migration targets
```

---

### Future: Full Pipeline (All Phases)

```
┌─────────────────────────────────────────────────────────────┐
│                     Daily Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Collect    → HN API → PostgreSQL                  │
│  Step 2: Crawl      → URLs → RocksDB                       │
│  Step 3: Summarize  → RocksDB → SummarizationAgent         │
│  Step 4: Synthesize → Summaries → Cross-article themes     │
│  Step 5: Deliver    → Telegram Bot → Users                 │
│  Step 6: Memory     → Reactions → MemoryExtractionAgent    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

User Interaction Flow:

1. User receives digest (Step 5)
2. User taps "Discuss" → DISCUSSION state
3. DiscussionAgent loads context (article + memory)
4. Multi-turn conversation
5. On end → MemoryExtractionAgent extracts insights
6. Memory updated → influences future discussions
```

---

## Document Status

| Document | Status | Last Updated | Phase |
|----------|--------|--------------|-------|
| index.md | ✅ Updated | 2026-02-13 | All |
| tech-stack.md | ✅ Updated | 2026-02-13 | All |
| data-models.md | ✅ Updated | 2026-02-13 | All |
| source-tree.md | ⏳ Needs Update | 2025-10-21 | 1-3 |
| coding-standards.md | ✅ Current | 2025-10-21 | All |
| api-design.md | 📝 To Create | - | 3-4 |
| testing-strategy.md | ⏳ Needs Update | 2025-10-21 | All |

---

## Contributing to Architecture Docs

### When to Update

**During Development:**
- Document design decisions in activity files
- Note deviations from planned architecture
- Update TODOs and implementation notes

**After Feature Complete:**
- Update architecture docs to reflect reality
- Add new sections for new components
- Update diagrams and data flows
- Increment document versions

---

### Update Process

1. **Identify Changes:** What architectural decisions changed?
2. **Update Relevant Docs:** Which architecture docs need updates?
3. **Review:** Cross-reference with related documents
4. **Version:** Update "Last Updated" date
5. **Communicate:** Notify team of significant changes

---

## Questions or Updates?

**For architecture questions:**
- Check existing docs first (this index)
- Review relevant activity documents in `docs/activities/`
- Check `docs/spec.md` for product requirements

**For architecture updates:**
- Small changes: Update docs directly
- Large changes: Discuss with team first, document decision

**Document Owner:** Development Team
**Maintained By:** Developers implementing each phase

---

## Next Steps

### Immediate (Phase 1.5)
- [ ] Complete RocksDB migration (Activity 1.5)
- [ ] Unified pipeline orchestrator (Activity 1.7)
- [ ] Update `source-tree.md` with clean architecture

### Short-term (Phase 2)
- [ ] Implement OpenAI Agents SDK client (Activity 2.5)
- [ ] Prompt engineering with LLM-as-judge (Activity 2.3)
- [ ] Add observability with Langfuse

### Medium-term (Phase 3-4)
- [ ] Create `api-design.md` for bot commands
- [ ] Implement Telegram bot foundation (Activity 3.0)
- [ ] Add interactive elements (Activity 4.0)

### Long-term (Phase 5-6)
- [ ] Discussion system with context loading (Activity 5.0)
- [ ] Memory extraction and personalization (Activity 6.0)
- [ ] Production deployment on Vercel

---

**Architecture Status:** Phase 1 MVP Complete ✅ | Phase 1.5 In Progress 🔄

**Current Focus:** RocksDB storage migration + Pipeline orchestration

**Last Review:** 2026-02-13
