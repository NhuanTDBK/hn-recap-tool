# HN Pal - Activity Documents

This directory contains detailed activity documents for implementing HN Pal features based on `docs/spec.md`.

## Document Structure

Each activity document follows this template:
- **Overview**: What the activity accomplishes
- **Prerequisites**: Dependencies and required infrastructure
- **Objectives**: Specific, measurable goals
- **Technical Details**: Architecture decisions and flow diagrams
- **Implementation Flow**: Data flow and component interactions
- **Testing & Validation**: How to verify the implementation
- **Acceptance Criteria**: Checkboxes for completion
- **Related Activities**: Upstream/downstream dependencies
- **Notes & Assumptions**: Design decisions and future enhancements

---

## Phase 1: Ingest Pipeline

### Activity 1.1: Set up HN API polling system ✅
**Status**: Completed
**File**: `activity-1.1-hn-api-polling.md`

**Summary:**
Polls HackerNews API to fetch new posts on a scheduled basis. Uses Firebase API (`/v0/maxitem` + `/v0/item/{id}`) for incremental scanning, tracks last processed ID in database, and stores posts in PostgreSQL.

**Key Features:**
- Firebase API incremental scanning (tracks max ID)
- PostgreSQL storage with Alembic migrations
- Deduplication via unique constraint on `hn_id`
- Scheduled execution (APScheduler → migrate to Vercel Cron)
- Automatic filtering (Firebase API excludes Ask/Show HN via `/v0/topstories`)

**Current State:**
- ✅ Algolia API implementation exists (MVP)
- 🔄 Recommended: Migrate to Firebase API for production
- 🔄 Recommended: Add PostgreSQL storage (currently JSONL)

---

### Activity 1.2: Implement content filtering logic ⏭️
**Status**: Skipped (simple query-based filtering)
**File**: N/A

**Summary:**
Filtering handled by:
1. Using Firebase `/v0/topstories` endpoint (pre-filters Ask/Show HN)
2. SQL query: `WHERE score > 100 AND url IS NOT NULL`
3. Checking `is_crawl_success` to skip already-crawled posts

No separate activity document needed - integrated into polling and crawling activities.

---

### Activity 1.3: URL crawler and Markdown conversion ✅
**Status**: Completed (Crawler) / To Implement (Markdown)
**File**: `activity-1.3-url-crawler-and-conversion.md`

**Summary:**
Fetches HTML content from post URLs, extracts clean text with trafilatura, converts HTML to Markdown with markitdown library, and stores all formats in filesystem. Tracks crawl status in PostgreSQL with retry logic.

**Key Features:**
- Robust HTTP fetching (user-agent rotation, retry logic, robots.txt compliance)
- Concurrent crawling (semaphore-limited, default: 3)
- Three output formats:
  - HTML: `data/content/html/{hn_id}.html` (raw source)
  - Text: `data/content/text/{hn_id}.txt` (trafilatura extraction)
  - Markdown: `data/content/markdown/{hn_id}.md` (markitdown conversion)
- Database tracking with `is_crawl_success` and `crawl_retry_count`
- Smart skip logic to prevent recursive crawling loops

**Current State:**
- ✅ EnhancedContentExtractor fully implemented
- ✅ HTML fetching and text extraction working
- 🔄 Need to integrate markitdown for Markdown conversion
- 🔄 Need to add database tracking (currently uses JSONL)

**Retry Logic:**
- `is_crawl_success = true` → Skip (already successful)
- `is_crawl_success = false AND retry_count < 3` → Retry
- `retry_count >= 3` → Skip (permanent failure)

---

### Activity 1.4: HTML to Markdown conversion ✅
**Status**: Merged into Activity 1.3
**File**: See `activity-1.3-url-crawler-and-conversion.md`

**Summary:**
Markdown conversion is part of the crawling pipeline (Activity 1.3) using markitdown library.

---

### Activity 1.5: RocksDB content storage 🔄
**Status**: In Progress
**File**: `activity-1.5-rocksdb-content-storage.md`

**Summary:**
Implement RocksDB-based storage for HTML, text, and Markdown content. Eliminates filesystem fragmentation and overhead by using embedded key-value database with built-in compression, optimized for single-writer architecture.

**Key Features:**
- RocksDB with column families (html, text, markdown)
- Built-in Zstandard compression (~70% space savings)
- Single-writer optimized (LSM tree architecture)
- O(1) key-value access by HN ID
- No filesystem overhead (inodes, blocks, metadata per file)
- Simple backup and archival strategies

**Storage Structure:**
```
data/content.rocksdb/
├── [html]       - column family for HTML
├── [text]       - column family for text
└── [markdown]   - column family for markdown
```

**Storage Projections (compressed):**
- 1 year: ~3 GB (vs ~10 GB uncompressed)
- 5 years: ~15 GB
- 10 years: ~30 GB

**Priority:** High (eliminates filesystem overhead from day 1)

---

### Activity 1.6: Database schema setup ✅
**Status**: Documented in Activity 1.1
**File**: `activity-1.1-hn-api-polling.md`

**Summary:**
PostgreSQL schema with Alembic migrations. Includes posts table with crawl tracking fields.

**Tables:**
- `posts` - HN posts with metadata and crawl status
- `crawl_logs` (optional) - Separate crawl tracking table

---

### Activity 1.7: Scheduled Pipeline Orchestration 🔄
**Status**: In Progress
**File**: `activity-1.7-scheduled-pipeline-orchestration.md`

**Summary:**
Unify the separate CLI scripts into a single, scheduled pipeline orchestrator using APScheduler. Chains all ingest steps — HN polling, content crawling, summarization, synthesis, and Telegram delivery — into a reliable, automated daily job.

**Key Features:**
- APScheduler-based scheduling (configurable cron triggers)
- 5-step sequential pipeline: Collect → Crawl → Summarize → Synthesize → Deliver
- Step-level error isolation (failed step doesn't kill pipeline)
- Pipeline run reports with per-step timing and metrics
- CLI script for manual execution (`scripts/run_pipeline.py`)
- Configurable schedule and step toggles via settings

**Pipeline Steps:**
```
Step 1: Collect    — Fetch HN front page posts (critical, aborts on failure)
Step 2: Crawl      — Extract content from post URLs
Step 3: Summarize  — Generate AI summaries via OpenAI
Step 4: Synthesize — Cross-article theme synthesis
Step 5: Deliver    — Push summaries to Telegram
```

**Typical Run Time:** 3-6 minutes
**Schedule:** Daily at 7:00 AM UTC (configurable)

**Current State:**
- ✅ APScheduler integrated in DataCollectorJob (basic version)
- ✅ All standalone scripts working
- 🔄 Need to create PipelineOrchestrator with step isolation
- 🔄 Need to add run logging and reporting
- 🔄 Need unified CLI script

---

## Phase 2: Summarization

### Activity 2.1: Basic summarization (Option 1)
**Status**: To Document
**File**: TBD

**Summary:**
Implement basic AI-powered summarization that reads markdown content and generates 2-3 sentence summaries. Stores all summaries in a single database table for tracking and retrieval.

**Key Features:**
- Read markdown from storage (RocksDB or filesystem)
- Generate summaries using LLM API (OpenAI/Claude)
- Store summaries with metadata (hn_id, summary, generated_at, model, tokens)
- Handle API errors, rate limiting, and retries
- Support batch processing for multiple posts

**Database Schema:**
```sql
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    hn_id INTEGER NOT NULL REFERENCES posts(hn_id),
    summary TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW(),
    model VARCHAR(50),  -- e.g., "gpt-4o-mini", "claude-3-haiku"
    tokens_used INTEGER,
    version INTEGER DEFAULT 1,
    -- Optional: store prompt variant used
    prompt_type VARCHAR(50),  -- "basic", "technical", "business"
    UNIQUE(hn_id, version)  -- Allow multiple versions per post
);
```

---

### Activity 2.2: Memory-enhanced summarization (Option 2)
**Status**: Future Enhancement
**File**: TBD

**Summary:**
Enhance summarization with user feedback and memory layer. Uses user preferences (stored in users table) to personalize summaries over time.

**Key Features:**
- Read user config from users table (summarization preferences)
- Include user context in prompts (preferred topics, style)
- Generate personalized summaries based on user history
- Store user feedback in summaries table (ratings, feedback)
- Regenerate improved summaries based on feedback

**Prerequisites:**
- Activity 2.1: Basic summarization
- Phase 6: Memory System (users table with config)

**User Config Schema (in users table):**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    -- Summarization preferences stored as JSONB config
    config JSONB DEFAULT '{
        "summarization": {
            "style": "concise",           -- "concise", "detailed", "technical"
            "preferred_topics": [],       -- ["ai", "startups", "crypto"]
            "language": "en",
            "enable_memory": false        -- Option 1 vs Option 2
        }
    }'::jsonb
);

-- Add feedback columns to summaries table
ALTER TABLE summaries ADD COLUMN user_feedback JSONB;
-- Example: {"rating": 4, "feedback_text": "Too technical", "user_id": 123}
```

---

### Activity 2.3: Summarization prompt engineering ⏳
**Status**: Documented
**File**: `activity-2.3-summarization-prompt-engineering.md`

**Summary:**
Design and test prompt templates for generating high-quality summaries. Uses LLM-as-judge for automated quality evaluation with ≥80% pass rate requirement.

**Key Features:**
- 5 prompt variants (basic, technical, business, concise, personalized)
- Simple markdown file storage (no database complexity)
- **LLM-as-judge evaluation** with 5 quality dimensions
- **80% pass rate threshold** (quality gate)
- Automated testing script with detailed reporting
- User preference integration for personalization
- Git-based versioning

**Quality Evaluation:**
- **Dimensions:** Factual accuracy (30%), info density (25%), clarity (15%), relevance (10%), length (20%)
- **Test dataset:** 5 diverse HN posts (small for quick iteration)
- **Scoring:** 0-100% per summary, must achieve ≥80% to pass
- **Approval:** Variant passes if ≥80% of summaries score ≥80% (4/5 posts must pass)

**Prompt Variants:**
- **Basic:** General-purpose, 2-3 sentences with key insights
- **Technical:** Deep technical details, architecture decisions
- **Business:** Market impact, strategic insights
- **Concise:** Ultra-brief, single sentence (30 words max)
- **Personalized:** Tailored to user topics and style preferences

**Storage:**
- Prompts: Markdown files in `backend/app/infrastructure/prompts/`
- Tracking: `summaries.prompt_type` column stores which prompt was used
- Versioning: Git history (simple and effective)

---

### Activity 2.4: Batch summarization optimization ⏳
**Status**: Future Release (Low Priority)
**File**: TBD

**Summary:**
Optimize batch processing for cost and performance. Includes parallel processing, prompt caching, and advanced rate limiting strategies.

**Why Future Release:**
- Current sequential processing is fast enough for MVP
- Cost is not a concern at current scale (~$1/month)
- Complexity not justified for 200 posts/day
- Can add optimization when scaling up

**Key Features (Future):**
- Parallel processing with asyncio (reduce processing time)
- Prompt caching to save tokens (Anthropic API)
- Batch API for overnight runs (50% cost savings)
- Smart batching (prioritize high-score posts)
- Advanced rate limiting with token bucket
- Cost tracking and optimization alerts

**Current Approach (Sufficient for MVP):**
- Simple sequential processing in Activity 2.1
- Basic rate limiting (sleep between requests)
- Process all posts in 2-3 minutes daily
- ~$0.03/day cost (negligible)

---

### Activity 2.5: LLM Client with OpenAI Agents SDK ⏳
**Status**: Documented
**File**: `activity-2.5-llm-client-integration.md`

**Summary:**
Implement unified LLM client using OpenAI Agents Python SDK with Langfuse observability and per-user token tracking. Designed for both summarization and future conversational bot interactions.

**Key Features:**
- OpenAI Agents SDK for agent-based architecture
- Langfuse integration for observability and tracing
- Per-user token tracking for pricing/billing
- Summarization agent (current)
- Q&A agent architecture (future - Telegram bot)
- Tool calling support for database queries
- Structured outputs with Pydantic

**Agent Types:**
- **SummarizationAgent:** Generate summaries from markdown (Phase 2)
- **QAAgent:** Answer user questions with tools (Phase 3 - Telegram)
- **DiscussionAgent:** Facilitate conversations (Phase 5)
- **MemoryAgent:** Personalized interactions (Phase 6)

**Token Tracking:**
- Database tables: `user_token_usage`, `agent_calls`
- Per-user daily aggregates
- Cost calculation with pricing table
- Usage queries for billing/limits

**Tech Stack:**
- `openai-agents` - Agent framework
- `langfuse` - Observability platform
- `pydantic` - Structured outputs

---

## Phase 3: Bot Foundation & Delivery

### Activity 3.0: Telegram Bot Foundation & Flow Design 📝
**Status**: Documented (Ready for Implementation)
**File**: `activity-3.0-telegram-bot-foundation.md`

**Summary:**
Comprehensive design and implementation guide for the Telegram bot using aiogram 3.x. Covers bot state machine (IDLE ↔ DISCUSSION), message routing, inline buttons, commands, digest delivery, and discussion management with 30-min auto-timeout.

**Key Features:**
- **Bot Framework:** aiogram 3.x (async Python)
- **State Machine:** IDLE, DISCUSSION, ONBOARDING states with FSM
- **Message Routing:** State-based routing with priority routers
- **Inline Buttons:** Discuss, Read, Save, 👍👎 reactions
- **Commands:** /start, /pause, /saved, /memory, /token
- **Digest Delivery:** Style 2 (flat scroll) - one message per post
- **Discussion Management:** Auto-switch posts, 30-min timeout, context loading
- **Memory Integration:** Extract insights on discussion end

**Bot States:**
```
/start → ONBOARDING → IDLE ⇄ DISCUSSION
                       ↑        ↓
                       └────────┘
                    (auto-switch, 30min timeout)
```

**Inline Buttons Per Post:**
- 💬 Discuss - Start/switch discussion
- 🔗 Read - Open HN link
- ⭐ Save - Toggle saved status
- 👍 👎 - React (track preferences)

**Sub-Activities (7 Steps):**
- 3.1: Bot initialization & basic commands
- 3.2: State machine & routing
- 3.3: Digest delivery (Style 2)
- 3.4: Inline buttons & callbacks
- 3.5: Discussion management
- 3.6: Memory commands
- 3.7: Advanced commands (/saved, /token)

**Tech Stack:**
- aiogram 3.x (bot framework)
- FSM Storage: Memory (dev) → Redis (prod)
- Deployment: Polling (dev) → Webhook (prod on Vercel)
- Database: PostgreSQL (users, deliveries, conversations, memory)

**Estimated Time:** 2-3 weeks for full Phase 3

---

## Phase 4: Interactive Elements

### Activity 4.0: Inline buttons & Callback System 📝

**Status**: Documented (Ready for Implementation)
**File**: `activity-4.0-interactive-elements.md`

**Summary:**
Implement the interactive UI elements for HN posts using Telegram inline buttons. Includes a standardized 2-row button grid for every post, callback routing for actions, and seamless integration with the FSM for starting discussions.

**Key Features:**

- Standardized Button Grid: (Discuss, Read, Save) + (👍, 👎)
- Type-safe callback handling with `aiogram` CallbackData
- "Discuss" trigger for state transition (IDLE ↔ DISCUSSION)
- Persistent bookmark system (Save/Unsave)
- Interest tracking via 👍/👎 reactions
- Instant UI feedback via callback query answers

**Sub-Activities:**

- 4.1: Inline Button Layout
- 4.2: Discussion Trigger Handler
- 4.3: External Link Logic
- 4.4: Bookmark Integration
- 4.5: Reaction Tracking
- 4.6: UI Feedback & Polish

---

## Phase 5: Discussion System

### Activity 5.0: Discussion System & Agent Integration 📝

**Status**: Documented (Ready for Implementation)
**File**: `activity-5.0-discussion-system.md`

**Summary:**
Implement the core conversational capability of HN Pal. This phase focuses on the "Discussion State," where the bot shifts from a broadcast medium to an interactive AI agent. Loads full article context and user memories for deep, multi-turn discussions.

**Key Features:**

- Automated context loading (Article MD + User Memory)
- Multi-turn conversation loop via `DiscussionAgent` (OpenAI Agents SDK)
- Discussion switching logic (auto-save previous, start new)
- 30-minute inactivity timeout management
- Discussion persistence in PostgreSQL

**Sub-Activities:**

- 5.1: Context Retrieval Engine
- 5.2: DiscussionAgent Configuration
- 5.3: Session Persistent Storage
- 5.4: State Transition & Switch Logic
- 5.5: Inactivity Timeout Background Worker
- 5.6: Error Handling & Rate Limits
- 5.7: Conversation UI Polish

---

## Phase 6: Memory System

### Activity 6.0: Memory System — Extract, Store & Surface User Knowledge ⏳

**Status**: Documented (Ready for Implementation)
**File**: `activity-6.0-memory-system.md`

**Summary:**
Implement a two-tier memory system that extracts, stores, and surfaces user knowledge to personalize discussions and summaries. Combines daily batch extraction (implicit) with real-time capture (explicit) to build a persistent user profile.

**Key Features:**

- Two-tier storage: MEMORY.md (durable facts) + memory/YYYY-MM-DD.md (daily notes)
- Daily batch job reads user interactions (reactions, discussions, saves) and extracts memory via LLM
- Explicit capture: detects "remember this" triggers during conversation and writes immediately
- Post-discussion extraction: topics, opinions, connections saved on discussion end
- BM25 full-text search over memory entries
- Memory context injection into DiscussionAgent and SummarizationAgent prompts (~1500 tokens)
- Memory management: `/memory`, `/memory pause`, `/memory forget`, `/memory clear`, `/memory search`

**Memory Categories:**

| Category | What It Captures |
| --- | --- |
| User Preferences | Communication style, topic interests, digest format |
| Work Context | Role, company, projects, tech stack, professional goals |
| Personal Context | Opinions, hobbies, side projects, learning goals |
| Reading History | Posts read, discussed, saved, reactions |

**When Memory Is Written:**
- **Implicit:** Daily batch job at 23:00 UTC (pipeline Step 6)
- **Explicit:** User says "remember this" → immediate write
- **Post-discussion:** LLM extracts insights when discussion ends/switches

**Storage Structure:**
```
data/memory/{user_id}/
├── MEMORY.md              # Durable facts, preferences, context (< 2000 words)
├── memory/
│   ├── 2026-02-10.md     # Daily notes
│   └── 2026-02-11.md
└── index/                 # BM25 search index
```

**Sub-Activities (6 Steps):**
- 6.1: Memory Schema & Storage Layer
- 6.2: Daily Batch Memory Extraction
- 6.3: Explicit Memory Capture
- 6.4: BM25 Memory Search
- 6.5: Memory Surfacing & Context Injection
- 6.6: Memory Management Commands

**Tech Stack:**
- OpenAI Agents SDK (MemoryExtractionAgent)
- Pydantic (structured extraction output)
- BM25 (full-text search, no external deps)
- PostgreSQL (memory table mirror for queries)
- File storage (MEMORY.md + daily notes)

**Estimated Time:** 2-3 weeks

---

## Phase 7: Command System

### Activity 7.1-7.7: Bot commands

**Status**: To Document
**Files**: TBD

---

## Progress Summary

**Completed Activities:** 3

- Activity 1.1: HN API polling ✅
- Activity 1.3: URL crawler and Markdown conversion ✅
- Activity 1.6: Database schema (merged into 1.1) ✅

**In Progress Activities:** 2

- Activity 1.5: RocksDB content storage 🔄
- Activity 1.7: Scheduled pipeline orchestration 🔄

**Documented (Ready for Implementation):** 7

- Activity 2.3: Summarization prompt engineering ⏳
- Activity 2.5: LLM client integration ⏳
- Activity 3.0: Telegram bot foundation 📝
- Activity 4.0: Interactive elements 📝
- Activity 5.0: Discussion system 📝
- Activity 6.0: Memory system ⏳

**Skipped Activities:** 1

- Activity 1.2: Content filtering (simple query-based)

**Pending Activities:** 15+

- Phase 2: 2 activities (basic summarization, batch optimization)
- Phase 3: 7 sub-activities (within Activity 3.0)
- Phase 4: 6 sub-activities (within Activity 4.0)
- Phase 5: 7 sub-activities (within Activity 5.0)
- Phase 6: 6 sub-activities (within Activity 6.0)
- Phase 7: 7 activities (Command system)

---

## Key Architectural Decisions

### API Choice

- **Recommended**: Firebase API (`/v0/maxitem` + `/v0/item/{id}`)
- **Current**: Algolia API (MVP)
- **Why**: Incremental scanning, captures ALL posts, more efficient

### Storage

- **Phase 1 (MVP)**: JSONL files + filesystem
- **Phase 1.5**: RocksDB for content blobs (Activity 1.5)
- **Future**: PostgreSQL for metadata, RocksDB for content

### Scheduling

- **Current**: APScheduler (in-process, async)
- **Why**: Simple, no infrastructure overhead, good enough for single-machine pipeline
- **Upgrade path**: Celery Beat (if distributed) or platform cron (if serverless)

### Libraries

- **HTTP**: httpx (async)
- **Content Extraction**: trafilatura
- **Markdown Conversion**: markitdown
- **Database**: SQLAlchemy + Alembic
- **Scheduling**: APScheduler (AsyncIOScheduler)
- **LLM**: OpenAI Agents SDK (gpt-4o-mini)
- **Bot**: aiogram 3.x (Phase 3)

### Crawl Strategy

- Concurrent requests (semaphore-limited)
- User-agent rotation
- Robots.txt compliance
- Retry logic with exponential backoff
- Database tracking to prevent recursive loops

---

## Migration Path

1. **Phase 1 (Current)**: File-based MVP
   - JSONL for posts
   - Filesystem for HTML/text/markdown
   - APScheduler for cron
   - Standalone scripts for each step

2. **Phase 1.5 (In Progress)**: Storage + Pipeline
   - RocksDB for content blobs (Activity 1.5)
   - Unified pipeline orchestrator (Activity 1.7)
   - Keep filesystem for pipeline run logs

3. **Phase 2**: Summarization
   - Read markdown from storage
   - Store summaries to disk
   - Integrated into pipeline as step

4. **Phase 3**: Production deployment
   - Telegram bot
   - PostgreSQL for metadata (if needed)
   - Monitor pipeline health

---

## Document Conventions

- ✅ Completed
- 🔄 In Progress
- ⏳ Future/Planned
- ⏭️ Skipped
- 🔴 Blocked

**Last Updated:** 2025-02-13
