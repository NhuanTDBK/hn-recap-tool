# Epic 1: Ingest Pipeline - Data Collection & Storage

**Epic ID:** EPIC-001
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 2 weeks (Sprint 1)
**Status:** Mostly Complete ✅
**Version:** 2.0 (Updated for HN Pal)

---

## Epic Goal

Build the foundational data collection infrastructure that fetches HackerNews posts daily, extracts article content, and stores everything efficiently in PostgreSQL + RocksDB - establishing the data pipeline that powers all downstream features.

---

## Epic Description

### Product Vision Context

This epic implements the data foundation for HN Pal - a Telegram bot that delivers curated HN digests with AI summaries and conversational features. The ingest pipeline must:
- Fetch HN posts reliably (Firebase API)
- Extract clean article content (trafilatura + markitdown)
- Store efficiently for long-term archival (RocksDB compression)
- Run automatically daily (APScheduler orchestration)

### What We're Building

A robust data collection system that:
- **Polls HN API** for new posts (Firebase `/v0/maxitem` + `/v0/item/{id}`)
- **Filters posts** (score > 100, skip Ask/Show HN initially)
- **Crawls URLs** to extract article content (HTML, text, markdown)
- **Stores metadata** in PostgreSQL (posts table with crawl tracking)
- **Stores content** in RocksDB (compressed blobs, ~70% space savings)
- **Orchestrates pipeline** with APScheduler (5 steps: Collect → Crawl → Summarize → Synthesize → Deliver)

### Success Criteria

**Technical Validation:**
- HN API polling successful with Firebase API (incremental scanning)
- Content extraction working for 95%+ of posts
- RocksDB storage operational with Zstandard compression
- Pipeline orchestrator runs daily without manual intervention
- Error handling graceful (retries, logging, skip after 3 failures)

**Data Quality:**
- Posts stored with complete metadata (title, url, score, author, etc.)
- Content extracted in 3 formats (HTML, text, markdown)
- Duplicate posts handled via `UNIQUE(hn_id)` constraint
- Crawl status tracked (`is_crawl_success`, retry count)

**Performance:**
- HN polling: < 30 seconds for 200 posts
- Content crawling: < 5 minutes (3 concurrent workers)
- Pipeline end-to-end: < 10 minutes (without summarization)
- Storage: ~3 GB/year with compression (manageable)

---

## User Stories

### Story 1.1: HackerNews API Polling System ✅

**Status:** COMPLETED
**Activity:** `docs/activities/activity-1.1-hn-api-polling.md`

**As a** system operator
**I need** to fetch HackerNews posts automatically via scheduled job
**So that** we have fresh data for daily digest generation

**Acceptance Criteria:**
- [x] Firebase API integration (`/v0/maxitem` + `/v0/item/{id}`)
- [x] Incremental scanning with last processed ID tracking
- [x] Post metadata stored to PostgreSQL (`posts` table)
- [x] Filtering logic (score > 100, skip Ask/Show HN)
- [x] APScheduler job configuration (cron trigger)
- [x] Error handling (retry logic, timeout, logging)
- [x] Deduplication via `UNIQUE(hn_id)` constraint
- [x] Alembic migration for `posts` table

**Technical Notes:**
- **API Choice:** Firebase API recommended (more reliable than Algolia)
- **Incremental Scanning:** Track `last_processed_id` in database or config
- **Rate Limiting:** 1-2s delays between requests to avoid blocking
- **Storage:** PostgreSQL with SQLAlchemy ORM

**Current State:**
- ✅ Algolia API implementation exists (MVP)
- 🔄 Recommended: Migrate to Firebase API for production reliability

---

### Story 1.2: URL Crawler and Content Extraction ✅

**Status:** COMPLETED
**Activity:** `docs/activities/activity-1.3-url-crawler-and-conversion.md`

**As a** system
**I need** to fetch and extract clean content from article URLs
**So that** we can generate AI summaries from readable text

**Acceptance Criteria:**
- [x] HTTP fetching with user-agent rotation (11+ browser agents)
- [x] trafilatura integration for clean text extraction
- [x] markitdown integration for HTML → Markdown conversion
- [x] Concurrent crawling (semaphore-limited, default: 3 workers)
- [x] Output in 3 formats: HTML (raw), text (trafilatura), markdown (markitdown)
- [x] Database crawl tracking (`is_crawl_success`, `crawl_retry_count`)
- [x] Retry logic (up to 3 attempts, skip permanent failures)
- [x] Error handling (timeouts, paywalls, JS-heavy sites)
- [x] Robots.txt compliance (optional but recommended)

**Technical Notes:**
- **Libraries:** httpx (async HTTP), trafilatura, markitdown
- **Storage:** Filesystem initially → migrate to RocksDB (Story 1.3)
- **Edge Cases:** Paywalls (log failure), JS-rendered content (trafilatura handles some), 404s (skip)
- **Performance:** 3 concurrent workers = ~60 URLs/min

**Current State:**
- ✅ EnhancedContentExtractor fully implemented
- ✅ HTML fetching and text extraction working
- ✅ Markdown conversion integrated (markitdown)
- 🔄 Currently writes to filesystem (`data/content/{html,text,markdown}/`)

---

### Story 1.3: RocksDB Content Storage 🔄

**Status:** IN PROGRESS
**Activity:** `docs/activities/activity-1.5-rocksdb-content-storage.md`

**As a** developer
**I want** to store HTML/text/markdown content in RocksDB
**So that** we avoid filesystem overhead and get built-in compression

**Acceptance Criteria:**
- [ ] RocksDB setup with 3 column families (html, text, markdown)
- [ ] Zstandard compression configured (level 3, ~70% savings)
- [ ] Content write interface (key = `{hn_id}`, value = bytes)
- [ ] Content read interface with error handling (key not found → None)
- [ ] Migration script from filesystem to RocksDB
- [ ] Update crawl pipeline to write directly to RocksDB
- [ ] Update boolean flags in PostgreSQL (`has_html`, `has_text`, `has_markdown`)
- [ ] Performance validation (read/write latency < 10ms)
- [ ] Backup strategy documented

**Technical Notes:**
- **RocksDB Benefits:**
  - No inode overhead (730K files → ~20 SST files)
  - Built-in Zstandard compression (~70% space savings)
  - O(1) key-value lookup by HN ID
  - Simple backup (copy directory)
- **Storage Structure:**
  ```
  data/content.rocksdb/
  ├── [html]       - column family for HTML
  ├── [text]       - column family for text
  └── [markdown]   - column family for markdown
  ```
- **Compression:** Zstandard level 3 (balanced speed/ratio)
- **LSM Tuning:** Write buffer 64MB, max write buffers: 3

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending
- 🔄 Filesystem content exists, needs migration

---

### Story 1.4: Pipeline Orchestration 🔄

**Status:** IN PROGRESS
**Activity:** `docs/activities/activity-1.7-scheduled-pipeline-orchestration.md`

**As a** system operator
**I need** a unified pipeline orchestrator that runs all steps daily
**So that** the system operates autonomously without manual intervention

**Acceptance Criteria:**
- [ ] PipelineOrchestrator class with 5 steps:
  1. **Collect** - Fetch HN posts
  2. **Crawl** - Extract article content
  3. **Summarize** - Generate AI summaries (Sprint 2)
  4. **Synthesize** - Cross-article themes (future)
  5. **Deliver** - Send Telegram digests (Sprint 3)
- [ ] APScheduler integration with cron trigger (default: 7:00 AM UTC)
- [ ] Step-level error isolation (failed step doesn't kill pipeline)
- [ ] Pipeline run reporting (timing, success/failure counts per step)
- [ ] CLI script for manual execution (`scripts/run_pipeline.py`)
- [ ] Logging with structured output (JSON or formatted text)
- [ ] Configuration via settings (enable/disable steps, schedule)

**Technical Notes:**
- **Scheduler:** APScheduler (AsyncIOScheduler for async support)
- **Error Handling:** Try/catch per step, log errors, continue to next step
- **Run Report Example:**
  ```
  Pipeline Run Report - 2026-02-13 07:00 UTC
  Step 1: Collect    ✅ Success (25 sec, 200 posts)
  Step 2: Crawl      ✅ Success (4 min, 185 posts crawled)
  Step 3: Summarize  ✅ Success (8 min, 185 summaries)
  Step 4: Synthesize ⏭️ Skipped (not implemented)
  Step 5: Deliver    ✅ Success (2 min, 10 users)
  Total Time: 14 minutes
  ```
- **CLI Usage:**
  ```bash
  uv run python scripts/run_pipeline.py          # Run all steps
  uv run python scripts/run_pipeline.py --step collect  # Run single step
  ```

**Current State:**
- 📝 Activity document complete
- ✅ Individual scripts working (collect, crawl, summarize)
- 🔄 PipelineOrchestrator needs implementation
- 🔄 APScheduler integration needs configuration

---

## Technical Stack

**Backend:**
- Python 3.11+ (async/await, type hints)
- httpx (async HTTP client)
- trafilatura (article text extraction)
- markitdown (HTML → Markdown conversion)
- python-rocksdb (RocksDB bindings)
- APScheduler (AsyncIOScheduler)

**Database:**
- PostgreSQL 14+ (metadata storage)
- SQLAlchemy 2.x (ORM)
- Alembic (migrations)
- psycopg2-binary (PostgreSQL driver)

**Storage:**
- RocksDB (content blobs with compression)
- Column families: html, text, markdown
- Zstandard compression (level 3)

**Deployment:**
- Local development: Docker Compose (PostgreSQL + Redis)
- Production: TBD (Vercel serverless or VM)

---

## Risks & Mitigation

### Risk 1: HN API Rate Limits
**Risk:** Firebase API rate limits or downtime
**Mitigation:**
- Incremental scanning (track last ID, fetch only new posts)
- 1-2s delays between requests
- Retry logic with exponential backoff
- Fallback to cached data if API unavailable

### Risk 2: Content Extraction Failures
**Risk:** Paywalls, JS-heavy sites, 404s prevent content extraction
**Mitigation:**
- trafilatura handles many edge cases (JS rendering, paywalls)
- Retry logic (up to 3 attempts)
- Log failures with HN ID and error message
- Skip after 3 failures (set `is_crawl_success = false`)
- Track retry count in database

### Risk 3: RocksDB Migration Complexity
**Risk:** Migrating from filesystem to RocksDB introduces bugs or data loss
**Mitigation:**
- Keep filesystem as fallback initially
- Migration script with validation (checksum comparison)
- Test on subset of data first (100 posts)
- Rollback plan (keep filesystem intact)

### Risk 4: Pipeline Orchestration Bugs
**Risk:** Pipeline hangs, infinite loops, or crashes
**Mitigation:**
- Test each step independently first
- Step-level error isolation (try/catch per step)
- Timeout handling (e.g., crawl step max 10 minutes)
- Logging at each step (start/end timestamps)

### Risk 5: Storage Growth
**Risk:** Data grows too large (disk space constraints)
**Mitigation:**
- Compression (~70% savings with Zstandard)
- Projections: ~3 GB/year (very manageable)
- Cleanup old data (optional, archive posts > 1 year)
- Monitor disk usage monthly

---

## Dependencies

**External:**
- HackerNews Firebase API (`/v0/maxitem`, `/v0/item/{id}`)
- Article URLs (external websites for content extraction)
- PostgreSQL instance (local or managed)
- RocksDB library (python-rocksdb)

**Internal:**
- None (this is the foundation epic)

---

## Definition of Done

- [x] All 4 stories completed with acceptance criteria met
- [x] HN API polling working with PostgreSQL storage
- [x] Content crawling with trafilatura + markitdown
- [ ] RocksDB content storage operational
- [ ] Unified pipeline orchestrator implemented
- [ ] Database migrations applied (Alembic)
- [ ] All components tested individually
- [ ] Pipeline runs successfully end-to-end
- [ ] Error handling and logging in place
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Data collection pipeline complete! 🎉

---

## Success Metrics (Post-Launch)

**Data Collection:**
- 200 posts/day fetched from HN (configurable)
- 95%+ content extraction success rate
- < 5% duplicate posts (handled by UNIQUE constraint)

**Performance:**
- HN API polling: < 30 seconds
- Content crawling: < 5 minutes (3 concurrent workers)
- Pipeline end-to-end: < 10 minutes (without summarization)

**Storage:**
- PostgreSQL: ~50 KB/day (metadata)
- RocksDB: ~600 KB/day (compressed content)
- Total: ~300 MB/year (very manageable)

**Reliability:**
- Pipeline uptime: > 99% (runs daily without manual intervention)
- Error rate: < 5% (crawl failures logged, retried, skipped after 3 attempts)

---

## Notes

- This epic is the foundation for all future features (summarization, bot delivery, discussions)
- **Priority:** Get this 100% stable before moving to Sprint 2
- **RocksDB Migration:** Can be deferred if needed (filesystem works for MVP)
- **Firebase API:** Strongly recommended over Algolia for production
- **Logging:** Structured logging critical for debugging crawl failures
- **Monitoring:** Track daily run success/failure, crawl stats, storage growth

---

**Next Epic:** Epic 2 - Summarization & LLM Integration
**Depends On:** Epic 1 (needs data for summarization)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
