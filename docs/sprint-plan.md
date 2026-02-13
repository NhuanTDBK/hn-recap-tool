# HN Pal - Sprint Plan

**Project:** HN Pal - Intelligent HackerNews Telegram Bot
**Timeline:** 12 weeks (6 × 2-week sprints)
**Goal:** Launch MVP Telegram bot with 10-20 beta users
**Prepared by:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 (Updated for Telegram Bot Architecture)

---

## Sprint Overview

| Sprint | Duration | Focus | Activities | MVP Critical |
|--------|----------|-------|------------|--------------|
| Sprint 1 | Week 1-2 | **Foundation: Ingest Pipeline** | 1.1-1.7 (HN polling, crawling, RocksDB, orchestration) | ✅ Critical |
| Sprint 2 | Week 3-4 | **Summarization & LLM Integration** | 2.1-2.5 (Basic summarization, OpenAI Agents SDK, prompts) | ✅ Critical |
| Sprint 3 | Week 5-6 | **Bot Foundation & Delivery** | 3.0 (Telegram bot, commands, digest delivery) | ✅ Critical |
| Sprint 4 | Week 7-8 | **Interactive Elements** | 4.0 (Inline buttons, callbacks, state management) | ✅ Critical |
| Sprint 5 | Week 9-10 | **Discussion System** | 5.0 (DiscussionAgent, context loading, conversations) | ⚠️ High Priority |
| Sprint 6 | Week 11-12 | **Memory System & Polish** | 6.0 (Memory extraction, personalization) + MVP Polish | ⚠️ Nice-to-have |

**Key Dependencies:**
- Sprint 2 depends on Sprint 1 (needs data collection + storage working)
- Sprint 3 depends on Sprint 2 (needs summaries for digest delivery)
- Sprint 4 depends on Sprint 3 (needs bot foundation for buttons)
- Sprint 5 depends on Sprint 3 & 4 (needs bot + buttons for discussions)
- Sprint 6 depends on Sprint 5 (needs conversations for memory extraction)

---

## Sprint 1: Foundation - Ingest Pipeline (Week 1-2)

**Goal:** Establish data collection and storage infrastructure for HN posts with content extraction

**Reference:** See `docs/activities/README.md` - Phase 1 activities

### Stories

#### Story 1.1: HackerNews API Polling System ✅
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** COMPLETED
**Activity:** activity-1.1-hn-api-polling.md

**Key Tasks:**
1. Implement Firebase API client (`/v0/maxitem` + `/v0/item/{id}`)
2. Incremental scanning with last processed ID tracking
3. Store posts metadata to PostgreSQL (Alembic migrations)
4. Filter posts (score > 100, skip Ask/Show HN)
5. APScheduler for scheduled execution
6. Error handling and retry logic

**Acceptance:** HN posts fetched daily, stored to PostgreSQL with deduplication

---

#### Story 1.2: URL Crawler and Content Extraction ✅
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** COMPLETED
**Activity:** activity-1.3-url-crawler-and-conversion.md

**Key Tasks:**
1. Implement HTTP fetching with user-agent rotation
2. trafilatura for clean text extraction
3. markitdown for HTML → Markdown conversion
4. Concurrent crawling (semaphore-limited, 3 workers)
5. Store HTML, text, markdown to filesystem
6. Database crawl tracking (`is_crawl_success`, retry logic)

**Acceptance:** Article content extracted and stored in 3 formats (HTML, text, markdown)

---

#### Story 1.3: RocksDB Content Storage 🔄
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** IN PROGRESS
**Activity:** activity-1.5-rocksdb-content-storage.md

**Key Tasks:**
1. Set up RocksDB with column families (html, text, markdown)
2. Configure Zstandard compression (~70% savings)
3. Migrate filesystem content to RocksDB
4. Update crawl pipeline to write to RocksDB
5. Add content retrieval layer (ContentRepository)
6. Performance testing and validation

**Acceptance:** Content stored in RocksDB with compression, filesystem migration complete

---

#### Story 1.4: Pipeline Orchestration 🔄
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** IN PROGRESS
**Activity:** activity-1.7-scheduled-pipeline-orchestration.md

**Key Tasks:**
1. Create PipelineOrchestrator with 5 steps (Collect → Crawl → Summarize → Synthesize → Deliver)
2. APScheduler integration with cron triggers
3. Step-level error isolation (failed step doesn't kill pipeline)
4. Pipeline run reporting (timing, metrics per step)
5. CLI script for manual execution (`scripts/run_pipeline.py`)
6. Logging and monitoring

**Acceptance:** Unified pipeline runs daily, generates reports, handles failures gracefully

---

### Sprint 1 Definition of Done
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

### Sprint 1 Risks
- **Risk:** RocksDB migration complexity
  **Mitigation:** Start simple with single column family, add more incrementally

- **Risk:** Crawl failures for paywalled content
  **Mitigation:** Log failures, retry logic, skip after 3 attempts

- **Risk:** Pipeline orchestration bugs
  **Mitigation:** Test each step independently first, add step isolation

---

## Sprint 2: Summarization & LLM Integration (Week 3-4)

**Goal:** Generate AI-powered summaries using OpenAI Agents SDK with observability

**Reference:** See `docs/activities/README.md` - Phase 2 activities

### Stories

#### Story 2.1: OpenAI Agents SDK Integration ⏳
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-2.5-llm-client-integration.md

**Key Tasks:**
1. Set up OpenAI Agents SDK client
2. Configure Langfuse observability integration
3. Create SummarizationAgent with structured outputs (Pydantic)
4. Implement token tracking per-user (`user_token_usage` table)
5. Log all agent calls (`agent_calls` table)
6. Cost calculation and budget monitoring
7. Error handling for LLM API failures

**Acceptance:** LLM client working with Langfuse tracing and token tracking

---

#### Story 2.2: Summarization Prompt Engineering ⏳
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-2.3-summarization-prompt-engineering.md

**Key Tasks:**
1. Design 5 prompt variants (basic, technical, business, concise, personalized)
2. Store prompts in markdown files (`backend/app/infrastructure/prompts/`)
3. Implement LLM-as-judge evaluation (5 quality dimensions)
4. Create test dataset (5 diverse HN posts)
5. Run automated evaluation (≥80% pass rate required)
6. Iterate on prompts until quality threshold met
7. Git-based versioning for prompts

**Acceptance:** Prompt variants tested, ≥80% pass rate on LLM-as-judge evaluation

---

#### Story 2.3: Basic Summarization Pipeline
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** TO IMPLEMENT

**Key Tasks:**
1. Read markdown content from RocksDB
2. Generate 2-3 sentence summaries using SummarizationAgent
3. Store summaries to PostgreSQL (`posts.summary`)
4. Handle different post types (story, Ask HN, Show HN)
5. Sequential processing (optimize later in Phase 2.4)
6. Error handling (API failures, timeouts, retries)
7. Integrate into pipeline orchestrator (Step 3)

**Acceptance:** 200 posts/day summarized, stored to database, < 10 min processing time

---

### Sprint 2 Definition of Done
- [ ] OpenAI Agents SDK integrated with Langfuse
- [ ] Token tracking operational (per-user usage)
- [ ] 5 prompt variants designed and tested
- [ ] LLM-as-judge evaluation passing (≥80%)
- [ ] Basic summarization pipeline working
- [ ] Summaries stored to PostgreSQL
- [ ] Cost monitoring dashboard (manual check)
- [ ] Processing time < 10 minutes for 200 posts
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Summaries generated daily! 🎉

### Sprint 2 Risks
- **Risk:** LLM API costs exceed budget
  **Mitigation:** Use GPT-4o-mini (~$0.03/day), monitor daily, set hard limits

- **Risk:** Prompt quality issues
  **Mitigation:** LLM-as-judge automated testing, iterate until passing

- **Risk:** Processing time too slow
  **Mitigation:** Start sequential (simple), optimize in future sprint if needed

---

## Sprint 3: Bot Foundation & Delivery (Week 5-6)

**Goal:** Launch Telegram bot with digest delivery and basic commands

**Reference:** See `docs/activities/README.md` - Phase 3 activities (Activity 3.0)

### Stories

#### Story 3.1: Bot Initialization & Basic Commands 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-3.0-telegram-bot-foundation.md (Sub-activity 3.1)

**Key Tasks:**
1. Set up aiogram 3.x project structure
2. Implement `/start` command (welcome message + onboarding)
3. Implement `/pause` command (toggle deliveries)
4. Implement `/help` command (show available commands)
5. User registration (create user in PostgreSQL on /start)
6. Bot polling mode for development
7. Error handling and logging

**Acceptance:** Bot responds to basic commands, creates users in database

---

#### Story 3.2: State Machine & Routing 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-3.0-telegram-bot-foundation.md (Sub-activity 3.2)

**Key Tasks:**
1. Set up FSM with 3 states (IDLE, DISCUSSION, ONBOARDING)
2. Configure Redis storage for FSM state
3. Implement state-based message routing
4. Create priority router (commands > callbacks > messages)
5. State transition logic (IDLE ↔ DISCUSSION)
6. Session management with timeouts

**Acceptance:** FSM working with Redis, messages routed based on state

---

#### Story 3.3: Flat Scroll Digest Delivery 📝
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-3.0-telegram-bot-foundation.md (Sub-activity 3.3)

**Key Tasks:**
1. Query top posts from PostgreSQL (score > 100, has_summary = true)
2. Rank posts by score × interest match (basic: just score for MVP)
3. Format digest messages (Style 2: flat scroll)
4. Send one message per post (title, domain, summary, score, comments)
5. Track deliveries in `deliveries` table (user_id, post_id, message_id, batch_id)
6. Integrate into pipeline orchestrator (Step 5: Deliver)
7. Handle delivery failures (log, retry once)

**Acceptance:** Users receive daily digest via Telegram DM (flat scroll format)

---

#### Story 3.4: Inline Buttons (Basic) 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-3.0-telegram-bot-foundation.md (Sub-activity 3.4)

**Key Tasks:**
1. Add inline button layout to digest messages
2. Implement button grid: [💬 Discuss] [🔗 Read] [⭐ Save]
3. Add reaction buttons: [👍] [👎]
4. Placeholder callbacks (implement full logic in Sprint 4)
5. Test button rendering and basic callbacks

**Acceptance:** Digest messages display inline buttons (full functionality in Sprint 4)

---

### Sprint 3 Definition of Done
- [ ] Telegram bot operational (aiogram 3.x)
- [ ] Basic commands working (/start, /pause, /help)
- [ ] FSM state machine with Redis storage
- [ ] Flat scroll digest delivery working
- [ ] Users receive daily digest via Telegram
- [ ] Deliveries tracked in database
- [ ] Inline buttons displayed (placeholder callbacks)
- [ ] Bot deployed (polling mode for dev)
- [ ] Error handling and logging in place
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** First Telegram digest delivered! 🚀

### Sprint 3 Risks
- **Risk:** Telegram rate limits (30 msg/sec)
  **Mitigation:** aiogram built-in throttling, send digests in batches

- **Risk:** Bot deployment complexity
  **Mitigation:** Start with polling (simple), migrate to webhooks later

- **Risk:** Redis connection failures
  **Mitigation:** Graceful degradation (in-memory state fallback)

---

## Sprint 4: Interactive Elements (Week 7-8)

**Goal:** Implement inline button callbacks and user interactions

**Reference:** See `docs/activities/README.md` - Phase 4 activities (Activity 4.0)

### Stories

#### Story 4.1: Discussion Trigger & State Transition 📝
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-4.0-interactive-elements.md (Sub-activities 4.1-4.2)

**Key Tasks:**
1. Implement `💬 Discuss` button callback handler
2. Transition state: IDLE → DISCUSSION
3. Load post context (update `users.active_discussion_post_id`)
4. Send discussion header message ("📖 Discussing: {title}")
5. Handle auto-switch (if already in DISCUSSION, save previous → start new)
6. Update FSM state in Redis
7. Test state transitions

**Acceptance:** Tapping `💬 Discuss` starts discussion, auto-switches if already active

---

#### Story 4.2: Bookmark & Reaction System 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-4.0-interactive-elements.md (Sub-activities 4.3-4.5)

**Key Tasks:**
1. Implement `⭐ Save` button callback (toggle bookmark)
2. Update `deliveries.is_saved` in database
3. Implement `👍 👎` reaction callbacks
4. Update `deliveries.reaction` in database
5. Track interest signals for future personalization
6. Provide instant UI feedback (callback query answers)
7. Implement `/saved` command (list bookmarked posts)

**Acceptance:** Users can save posts, react with 👍👎, view saved list

---

#### Story 4.3: External Link Handler 📝
**Priority:** P0 - Critical
**Estimate:** 2 story points
**Status:** DOCUMENTED
**Activity:** activity-4.0-interactive-elements.md (Sub-activity 4.3)

**Key Tasks:**
1. Implement `🔗 Read` button callback
2. Generate HN link: `https://news.ycombinator.com/item?id={hn_id}`
3. Send inline keyboard with link (Telegram URL button)
4. Track click events (optional analytics)

**Acceptance:** Tapping `🔗 Read` opens HN post in browser

---

### Sprint 4 Definition of Done
- [ ] All inline buttons functional (Discuss, Read, Save, 👍👎)
- [ ] State transitions working (IDLE ↔ DISCUSSION)
- [ ] Bookmark system operational
- [ ] Reaction tracking in database
- [ ] `/saved` command lists bookmarked posts
- [ ] UI feedback instant (callback query answers)
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Interactive bot working! 🎉

### Sprint 4 Risks
- **Risk:** State management bugs (FSM transitions)
  **Mitigation:** Thorough testing, logs for state changes

- **Risk:** Database consistency (concurrent button presses)
  **Mitigation:** Use transactions, handle race conditions

---

## Sprint 5: Discussion System (Week 9-10)

**Goal:** Enable AI-powered conversations about posts using DiscussionAgent

**Reference:** See `docs/activities/README.md` - Phase 5 activities (Activity 5.0)

### Stories

#### Story 5.1: Context Retrieval Engine 📝
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-5.0-discussion-system.md (Sub-activity 5.1)

**Key Tasks:**
1. Load article markdown from RocksDB (by hn_id)
2. Load user memory from PostgreSQL (`memory` table, active = true)
3. Load related past conversations (same topic keywords)
4. Assemble context payload (article + memory + related convos)
5. Cache context in Redis (key: `context:{telegram_id}:{post_id}`, TTL: 30 min)
6. Handle context loading errors (fallback to article only)

**Acceptance:** Context loaded when discussion starts (article + memory)

---

#### Story 5.2: DiscussionAgent Configuration 📝
**Priority:** P0 - Critical
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-5.0-discussion-system.md (Sub-activity 5.2)

**Key Tasks:**
1. Create DiscussionAgent using OpenAI Agents SDK
2. Configure system prompt with article context
3. Implement multi-turn conversation loop
4. Add message history management (append to `conversations.messages`)
5. Track token usage per conversation
6. Handle LLM API errors and timeouts
7. Test with different discussion scenarios

**Acceptance:** DiscussionAgent responds to user messages with article context

---

#### Story 5.3: Conversation Persistence 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-5.0-discussion-system.md (Sub-activity 5.3)

**Key Tasks:**
1. Create conversation on discussion start (`conversations` table)
2. Append messages to JSONB array (`conversations.messages`)
3. Update token usage and cost after each turn
4. Save conversation on end (auto-switch or timeout)
5. Set `conversations.ended_at` timestamp
6. Clear `users.active_discussion_post_id`

**Acceptance:** Conversations saved to database with full message history

---

#### Story 5.4: 30-Minute Timeout Handler 📝
**Priority:** P0 - Critical
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-5.0-discussion-system.md (Sub-activity 5.5)

**Key Tasks:**
1. Track last message timestamp in FSM state
2. Background worker checks for inactive discussions (every 5 min)
3. Auto-close discussions after 30 min inactivity
4. Send timeout notification to user ("Discussion ended due to inactivity")
5. Save conversation and transition to IDLE
6. Clean up Redis state

**Acceptance:** Discussions auto-close after 30 min inactivity

---

### Sprint 5 Definition of Done
- [ ] Context retrieval working (article + memory)
- [ ] DiscussionAgent responding to messages
- [ ] Multi-turn conversations functional
- [ ] Conversations persisted to database
- [ ] 30-minute timeout implemented
- [ ] Auto-switch between discussions working
- [ ] Token usage tracked per conversation
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Discussion system working! 🎉

### Sprint 5 Risks
- **Risk:** LLM response latency too high (> 10 sec)
  **Mitigation:** Optimize context size, use faster model (GPT-4o-mini)

- **Risk:** Context loading performance
  **Mitigation:** Redis caching, load only recent memory (last 30 days)

- **Risk:** Timeout background worker reliability
  **Mitigation:** APScheduler job, logs for all auto-closes

---

## Sprint 6: Memory System & MVP Polish (Week 11-12)

**Goal:** Implement memory extraction for personalization and polish MVP for beta launch

**Reference:** See `docs/activities/README.md` - Phase 6 activities (Activity 6.0)

### Stories

#### Story 6.1: Post-Discussion Memory Extraction ⏳
**Priority:** P1 - Nice-to-have
**Estimate:** 5 story points
**Status:** DOCUMENTED
**Activity:** activity-6.0-memory-system.md (Sub-activities 6.2-6.3)

**Key Tasks:**
1. Create MemoryExtractionAgent using OpenAI Agents SDK
2. Extract insights when discussion ends (topics, opinions, connections)
3. Structured output using Pydantic (MemoryCreate model)
4. Store memory entries to `memory` table
5. Confidence scoring (0.0-1.0) for implicit extractions
6. Handle explicit capture ("remember this" triggers)

**Acceptance:** Memory extracted and stored after each discussion

---

#### Story 6.2: Daily Batch Memory Extraction ⏳
**Priority:** P1 - Nice-to-have
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-6.0-memory-system.md (Sub-activity 6.2)

**Key Tasks:**
1. Daily pipeline step (Step 6: Memory)
2. Read user interactions (reactions, saves, skips) from past 24h
3. Extract implicit interests and preferences via LLM
4. Store to `memory` table with `source_type = "daily_batch"`
5. Aggregate duplicate entries (merge similar interests)
6. Run at 23:00 UTC after delivery

**Acceptance:** Daily batch job extracts memory from user interactions

---

#### Story 6.3: Memory Management Commands ⏳
**Priority:** P1 - Nice-to-have
**Estimate:** 3 story points
**Status:** DOCUMENTED
**Activity:** activity-6.0-memory-system.md (Sub-activity 6.6)

**Key Tasks:**
1. Implement `/memory` command (view active memory)
2. Implement `/memory pause` (toggle memory on/off)
3. Implement `/memory forget` (interactive selection to delete entries)
4. Implement `/memory clear` (full memory reset with confirmation)
5. Display memory in categorized format (interests, work context, etc.)
6. Update `users.memory_enabled` flag

**Acceptance:** Users can view and manage their memory via commands

---

#### Story 6.4: Token Usage Command ⏳
**Priority:** P1 - Nice-to-have
**Estimate:** 2 story points
**Status:** DOCUMENTED

**Key Tasks:**
1. Implement `/token` command
2. Query `user_token_usage` table for current user
3. Display daily and total usage (input/output tokens, cost)
4. Show breakdown by operation (summarization, discussion, memory)
5. Format nicely for Telegram display

**Acceptance:** `/token` command shows user's LLM usage and costs

---

#### Story 6.5: MVP Polish & Bug Fixes
**Priority:** P0 - Critical
**Estimate:** 8 story points
**Assignee:** Full Team

**Key Tasks:**
1. **Testing:** End-to-end testing with 5 internal beta users
2. **Bug Fixes:** Address all critical and high-priority bugs
3. **Performance:** Optimize slow operations (context loading, LLM calls)
4. **UX Polish:** Improve message formatting, error messages
5. **Documentation:** User guide, bot commands reference
6. **Monitoring:** Set up error tracking (Langfuse, logs)
7. **Deployment:** Deploy to production (webhook mode on Vercel)
8. **Beta Launch:** Onboard 10-20 external beta users
9. **Feedback Collection:** Set up feedback form (/feedback command)
10. **Metrics:** Track engagement, conversation length, satisfaction

**Acceptance:** MVP ready for beta launch, no critical bugs, smooth UX

---

### Sprint 6 Definition of Done
- [ ] Post-discussion memory extraction working
- [ ] Daily batch memory extraction implemented
- [ ] Memory management commands operational
- [ ] `/token` command shows usage stats
- [ ] All critical bugs fixed
- [ ] Performance optimized (response times < 10s)
- [ ] User documentation complete
- [ ] Monitoring and alerting set up
- [ ] Deployed to production (webhook mode)
- [ ] 10-20 beta users onboarded
- [ ] Feedback collection active
- [ ] **MILESTONE:** MVP LAUNCH! 🚀

### Sprint 6 Risks
- **Risk:** Memory extraction quality issues
  **Mitigation:** LLM-as-judge evaluation, confidence thresholds, user feedback

- **Risk:** Critical bugs found late
  **Mitigation:** Start internal testing early (Week 11), buffer time for fixes

- **Risk:** Production deployment issues
  **Mitigation:** Test webhook mode in staging first, rollback plan ready

---

## Success Criteria - MVP Launch (End of Week 12)

### Product Success
- ✅ Daily HN digest delivered via Telegram (flat scroll format)
- ✅ 2-3 sentence AI summaries for each post
- ✅ Interactive buttons (Discuss, Read, Save, reactions)
- ✅ Conversational discussions about posts
- ✅ Memory extraction for personalization
- ✅ 10-20 beta users actively engaged

### Quality Success
- ✅ Summary quality: 4/5+ rating (LLM-as-judge ≥80%)
- ✅ Discussion responsiveness: < 10 sec response time
- ✅ Bot uptime: > 99%
- ✅ User satisfaction: 4/5+ (beta feedback survey)

### Technical Success
- ✅ Pipeline runs daily without manual intervention
- ✅ Digest delivery success rate > 95%
- ✅ Processing time < 10 minutes per digest
- ✅ LLM costs within budget (~$2-5/day for 200 posts + conversations)
- ✅ Database performance: < 1s query times
- ✅ RocksDB storage: < 5 GB for 6 months data

---

## Sprint Ceremonies

### Daily Standups (15 min)
- Time: 9:00 AM daily
- Format: What did you do? What will you do? Any blockers?

### Sprint Planning (2 hours)
- Start of each sprint
- Review stories, assign tasks, estimate effort
- Identify dependencies and risks

### Sprint Review (1 hour)
- End of each sprint
- Demo completed stories to stakeholders
- Gather feedback

### Sprint Retrospective (1 hour)
- End of each sprint
- What went well? What can improve? Action items?

---

## Team Roles

| Role | Responsibilities | Sprint Load |
|------|------------------|-------------|
| Backend Developer | Pipeline, database, bot handlers, LLM integration | 13-16 story points/sprint |
| ML/Data Engineer | Summarization, prompts, memory extraction, agent design | 8-10 story points/sprint |
| DevOps/Infrastructure | PostgreSQL, RocksDB, Redis, Vercel deployment | 5-8 story points/sprint |
| Scrum Master (Bob) | Sprint planning, standups, unblock team | N/A |
| Product Owner (John) | Prioritization, acceptance, stakeholder comms | N/A |

**Note:** Team may need to be cross-functional depending on available resources.

---

## Risk Management

### High Risks
1. **LLM API costs exceed budget**
   - **Mitigation:** Use GPT-4o-mini ($0.15/$0.60 per 1M tokens), daily cost tracking, hard limits

2. **Bot deployment complexity (Vercel webhooks)**
   - **Mitigation:** Start with polling (simple), migrate to webhooks in Sprint 6

3. **Memory extraction quality issues**
   - **Mitigation:** Confidence scoring, LLM-as-judge evaluation, user feedback loop

### Medium Risks
1. **HN API rate limits or downtime**
   - **Mitigation:** Incremental scanning, retry logic, fallback to cached data

2. **RocksDB migration complexity**
   - **Mitigation:** Migrate incrementally, keep filesystem fallback initially

3. **Telegram rate limits (30 msg/sec)**
   - **Mitigation:** aiogram built-in throttling, batch digest delivery

### Low Risks
1. **Redis connection failures**
   - **Mitigation:** Graceful degradation (in-memory FSM state)

2. **Database query performance**
   - **Mitigation:** Proper indexing, query optimization, connection pooling

---

## Post-Sprint 6: Future Enhancements (Week 13+)

After MVP launch, potential next sprints:

**Sprint 7-8: Advanced Personalization**
- BM25 memory search for better context retrieval
- Personalized digest ranking (based on interests + reactions)
- Onboarding flow optimization (3 questions)
- Interest management UI (inline keyboards)

**Sprint 9-10: Advanced Features**
- HN comment integration (quality filtering, insight extraction)
- Cross-article synthesis (theme detection across posts)
- Conversation templates (e.g., "Explain like I'm 5", "Technical deep dive")
- Multi-turn conversation improvements (better context management)

**Sprint 11-12: Scale & Monetization**
- Webhook deployment on Vercel (serverless)
- Batch API for cost optimization (50% savings)
- Premium tiers (longer conversations, more memory, priority delivery)
- Multi-language support (summary translation)

**Sprint 13+: Platform Expansion**
- MCP integration (Model Context Protocol)
- Multi-source support (Reddit, Lobste.rs, etc.)
- Team knowledge graphs (shared memory)
- Web dashboard for conversation history

---

## Migration Notes

### Old vs New Architecture

**What Changed:**
- ❌ **Removed:** Web app, email delivery, topic clustering, Next.js frontend
- ✅ **New:** Telegram bot, inline buttons, conversational discussions, memory system
- ✅ **Enhanced:** RocksDB storage (vs filesystem), OpenAI Agents SDK (vs basic LLM calls), Redis FSM (vs stateless)

**What Stayed:**
- ✅ HN API polling and content crawling
- ✅ AI-powered summarization (simplified to 2-3 sentences)
- ✅ PostgreSQL for metadata
- ✅ APScheduler for pipeline orchestration
- ✅ Daily digest delivery (now via Telegram)

**Migration Path:**
- Phase 1 mostly complete (polling, crawling)
- Phase 2 in progress (summarization)
- Phases 3-6 new development (bot, discussions, memory)

---

**Sprint Plan Status:** Ready for Sprint 2 Kickoff (Summarization)
**Current Phase:** Sprint 1 completed (Ingest Pipeline), Sprint 2 in progress
**Next Action:** Complete RocksDB migration + Pipeline orchestrator (Sprint 1 cleanup)
**Prepared by:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - Telegram Bot Architecture
