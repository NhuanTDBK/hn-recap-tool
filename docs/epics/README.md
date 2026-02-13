# HN Pal - Epic Backlog

**Project:** HN Pal - Intelligent HackerNews Telegram Bot
**Version:** 2.0 (Updated for Telegram Bot Architecture)
**Last Updated:** 2026-02-13

---

## Epic Overview

This directory contains the epic-level planning documents for HN Pal. Each epic represents a major feature area or product milestone, broken down into user stories aligned with specific sprints.

---

## Active Epics

### Epic 1: Ingest Pipeline ✅
**Status:** Mostly Complete
**Priority:** P0 - Critical (MVP Core)
**Timeline:** Sprint 1 (2 weeks)
**File:** [epic-1-ingest-pipeline.md](./epic-1-ingest-pipeline.md)

**Goal:** Build the foundational data collection infrastructure that fetches HackerNews posts daily, extracts article content, and stores everything efficiently in PostgreSQL + RocksDB.

**Stories:**
- 1.1: HackerNews API Polling System ✅
- 1.2: URL Crawler and Content Extraction ✅
- 1.3: RocksDB Content Storage 🔄
- 1.4: Pipeline Orchestration 🔄

**Key Deliverables:**
- HN API polling (Firebase API)
- Content extraction (trafilatura + markitdown)
- RocksDB storage with Zstandard compression
- Unified pipeline orchestrator (APScheduler)

---

### Epic 2: Summarization & LLM Integration ⏳
**Status:** In Progress
**Priority:** P0 - Critical (MVP Core)
**Timeline:** Sprint 2 (2 weeks)
**File:** [epic-2-summarization-llm-integration.md](./epic-2-summarization-llm-integration.md)

**Goal:** Build an AI-powered summarization system using OpenAI Agents SDK that generates high-quality 2-3 sentence summaries for HN posts, with observability via Langfuse and token tracking.

**Stories:**
- 2.1: OpenAI Agents SDK Integration ⏳
- 2.2: Summarization Prompt Engineering ⏳
- 2.3: Basic Summarization Pipeline

**Key Deliverables:**
- OpenAI Agents SDK + Langfuse integration
- 5 prompt variants with LLM-as-judge evaluation (≥80% pass rate)
- Token tracking per-user
- Sequential summarization (200 posts/day in < 10 min)

---

### Epic 3: Telegram Bot Foundation & Delivery 📝
**Status:** Documented (Ready for Implementation)
**Priority:** P0 - Critical (MVP Core)
**Timeline:** Sprint 3 (2 weeks)
**File:** [epic-3-telegram-bot-foundation.md](./epic-3-telegram-bot-foundation.md)

**Goal:** Launch the Telegram bot with digest delivery system, basic commands, state machine, and inline buttons - establishing the user-facing interface.

**Stories:**
- 3.1: Bot Initialization & Basic Commands 📝
- 3.2: State Machine & Routing 📝
- 3.3: Flat Scroll Digest Delivery 📝
- 3.4: Inline Buttons (Basic) 📝

**Key Deliverables:**
- aiogram 3.x bot with FSM (Redis state management)
- Basic commands (/start, /pause, /help, /saved)
- Flat scroll digest delivery (one message per post)
- Inline button grid (💬 Discuss, 🔗 Read, ⭐ Save, 👍 👎)
- Delivery tracking (deliveries table)

---

### Epic 4: Interactive Elements 📝
**Status:** Documented (Ready for Implementation)
**Priority:** P0 - Critical (MVP Core)
**Timeline:** Sprint 4 (2 weeks)
**File:** [epic-4-interactive-elements.md](./epic-4-interactive-elements.md)

**Goal:** Implement fully functional inline button callbacks for user interactions - enabling discussions, bookmarks, reactions, and external links.

**Stories:**
- 4.1: Discussion Trigger & State Transition 📝
- 4.2: Bookmark & Reaction System 📝
- 4.3: External Link Handler ✅ (Already working)

**Key Deliverables:**
- 💬 Discuss button → IDLE ↔ DISCUSSION state transition
- ⭐ Save button → Bookmark toggle (deliveries.is_saved)
- 👍👎 Reactions → Interest tracking (deliveries.reaction)
- /saved command → List bookmarked posts
- Auto-switch logic (save current → start new discussion)

---

### Epic 5: Discussion System 📝
**Status:** Documented (Ready for Implementation)
**Priority:** P1 - High Priority (MVP Enhancement)
**Timeline:** Sprint 5 (2 weeks)
**File:** [epic-5-discussion-system.md](./epic-5-discussion-system.md)

**Goal:** Enable AI-powered conversations about HN posts using DiscussionAgent - transforming the bot into an interactive learning companion.

**Stories:**
- 5.1: Context Retrieval Engine 📝
- 5.2: DiscussionAgent Configuration 📝
- 5.3: Conversation Persistence 📝
- 5.4: 30-Minute Timeout Handler 📝

**Key Deliverables:**
- DiscussionAgent (OpenAI Agents SDK)
- Context loading (article + user memory)
- Multi-turn conversations (JSONB message history)
- Auto-switch between discussions
- 30-minute timeout (APScheduler background worker)
- Conversation persistence (conversations table)

---

### Epic 6: Memory System & MVP Polish 📝
**Status:** Documented (Ready for Implementation)
**Priority:** P1 - Nice-to-have (MVP Enhancement)
**Timeline:** Sprint 6 (2 weeks)
**File:** [epic-6-memory-system-mvp-polish.md](./epic-6-memory-system-mvp-polish.md)

**Goal:** Implement memory extraction for personalization and polish the MVP for beta launch - adding intelligence that learns user preferences over time.

**Stories:**
- 6.1: Post-Discussion Memory Extraction ⏳
- 6.2: Daily Batch Memory Extraction ⏳
- 6.3: Memory Management Commands ⏳
- 6.4: Token Usage Command ⏳
- 6.5: MVP Polish & Bug Fixes

**Key Deliverables:**
- MemoryExtractionAgent (post-discussion insights)
- Daily batch extraction (interests from reactions)
- Memory management (/memory, /memory pause, /memory forget, /memory clear)
- Token usage command (/token)
- MVP polish (bug fixes, performance, UX, documentation)
- Production deployment (Vercel webhook mode)
- Beta launch (10-20 external users)

---

## Epic Status Legend

- ✅ **Complete** - All stories implemented and tested
- 🔄 **In Progress** - Some stories complete, some in progress
- ⏳ **In Progress** - All stories in progress
- 📝 **Documented** - Activity documents complete, ready for implementation
- 🔴 **Blocked** - Cannot proceed due to dependencies

---

## Epic Dependencies

```
Epic 1 (Ingest Pipeline)
  ↓
Epic 2 (Summarization) ← depends on Epic 1
  ↓
Epic 3 (Bot Foundation) ← depends on Epic 1 & 2
  ↓
Epic 4 (Interactive Elements) ← depends on Epic 3
  ↓
Epic 5 (Discussion System) ← depends on Epic 3 & 4
  ↓
Epic 6 (Memory & Polish) ← depends on Epic 5
```

**Critical Path:** Epic 1 → Epic 2 → Epic 3 → Epic 4 (MVP launch possible here)
**Enhancement Path:** Epic 5 → Epic 6 (Advanced features)

---

## Archived Epics (Old Architecture)

The following epics were designed for the old "Knowledge Graph Builder" web app architecture and have been archived:

- **Epic 1 (Old):** Topic-Clustered Digest - [archived/epic-1-topic-clustered-digest.md](./archived/epic-1-topic-clustered-digest.md)
- **Epic 2 (Old):** Personalization System - [archived/epic-2-personalization-system.md](./archived/epic-2-personalization-system.md)
- **Epic 3 (Old):** Comment Integration - [archived/epic-3-comment-integration.md](./archived/epic-3-comment-integration.md)

These epics focused on email delivery, web UI, topic clustering (2-3 topics), and preference-based personalization - features replaced by Telegram bot, discussions, and memory-based personalization in the new architecture.

---

## How to Use This Directory

### For Product Owners / Stakeholders
- Read epic descriptions to understand feature scope
- Review success criteria to understand goals
- Check dependencies to understand timeline constraints

### For Developers
- Read full epic document for technical details
- Reference activity documents (docs/activities/) for implementation steps
- Check acceptance criteria for story completion

### For Scrum Masters
- Track epic progress (story completion %)
- Identify blockers and dependencies
- Update sprint plan based on epic status

---

## Epic Template Structure

Each epic follows this template:

1. **Header** - ID, priority, timeline, status
2. **Epic Goal** - One-sentence summary
3. **Epic Description** - Product vision, what we're building, success criteria
4. **User Stories** - Detailed stories with acceptance criteria
5. **Technical Stack** - Technologies used
6. **Risks & Mitigation** - Potential issues and solutions
7. **Dependencies** - External/internal dependencies
8. **Definition of Done** - Checklist for epic completion
9. **Success Metrics** - Post-launch measurements
10. **Notes** - Additional context

---

## Current Sprint Focus

**Sprint 1 (Week 1-2):** Epic 1 - Ingest Pipeline
**Sprint 2 (Week 3-4):** Epic 2 - Summarization
**Sprint 3 (Week 5-6):** Epic 3 - Bot Foundation
**Sprint 4 (Week 7-8):** Epic 4 - Interactive Elements
**Sprint 5 (Week 9-10):** Epic 5 - Discussion System
**Sprint 6 (Week 11-12):** Epic 6 - Memory & MVP Polish

**MVP Launch Target:** End of Sprint 6 (Week 12)

---

## Future Epics (Post-MVP)

After Sprint 6 MVP launch, potential epics for Sprint 7+:

- **Epic 7:** Advanced Personalization (BM25 memory search, personalized ranking)
- **Epic 8:** Advanced Features (HN comment integration, cross-article synthesis)
- **Epic 9:** Scale & Monetization (webhook deployment, batch API, premium tiers)
- **Epic 10:** Platform Expansion (MCP integration, multi-source support, web dashboard)

See `docs/sprint-plan.md` for detailed future enhancement roadmap.

---

**Document Owner:** Bob (Scrum Master) 🏃
**Last Updated:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot Architecture
