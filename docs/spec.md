# HN Pal — Product Spec v2

## Overview

A Telegram bot that delivers curated Hacker News summaries to your DM and lets you have conversations about them. No channels, no groups. Just you and the bot.

---

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                          HN Pal                                 │
│                                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │  Ingest    │  │ Summarize  │  │  Memory    │  │   Bot    │ │
│  │            │  │            │  │            │  │          │ │
│  │ Poll HN    │  │ Generate   │  │ Track      │  │ Deliver  │ │
│  │ Crawl URLs │  │ summaries  │  │ interests  │  │ digests  │ │
│  │ HTML → MD  │  │ via LLM    │  │ Store      │  │ Handle   │ │
│  │ Store      │  │ Skip Ask/  │  │ convos     │  │ commands │ │
│  │ metadata   │  │ Show HN    │  │ Extract    │  │ Manage   │ │
│  │            │  │            │  │ insights   │  │ discuss  │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘ │
│        │               │               │               │       │
│        └───────────┬───┴───────────┬───┘               │       │
│                    ▼               ▼                    │       │
│             ┌────────────┐  ┌────────────┐             │       │
│             │ PostgreSQL │  │    S3      │             │       │
│             │ (Supabase) │  │            │             │       │
│             │            │  │ HTML files │             │       │
│             │ users      │  │ MD files   │             │       │
│             │ posts      │  │            │             │       │
│             │ deliveries │  └────────────┘             │       │
│             │ convos     │                             │       │
│             │ memory     │◀────────────────────────────┘       │
│             └────────────┘                                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Infrastructure                                          │  │
│  │  Vercel ── bot server + cron jobs                        │  │
│  │  Supabase ── PostgreSQL                                  │  │
│  │  S3 ── file storage (HTML + Markdown)                    │  │
│  │  Claude API ── summarization + chat                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Ingest**

- Poll HN API (`/topstories`, `/beststories`) on schedule via Vercel cron
- Skip `Ask HN` and `Show HN` posts
- For each qualifying post: fetch the linked URL, crawl HTML content
- Convert HTML → clean Markdown (via trafilatura or similar)
- Save metadata (title, url, score, comment_count, hn_id, type) to PostgreSQL
- Save raw HTML and converted Markdown to S3, store file references in DB

**Summarize**

- Runs after ingest (or as part of same pipeline)
- Reads Markdown content from S3
- Calls Claude API to generate 2-3 sentence summary
- Stores summary back in PostgreSQL
- Only processes posts that have not been summarized yet

**Memory**

- Tracks user interests (implicit from reactions + discussions, explicit from onboarding)
- Stores conversation history per post per user
- After discussion ends: LLM extracts key insights, opinions, connections
- Serves memory context when discussions start
- Handles memory commands (view, pause, forget, clear)

**Bot**

- Telegram bot server running on Vercel
- Delivers digest messages on schedule
- Handles inline button callbacks (discuss, reactions)
- Manages discussion state (active post per user, auto-switch)
- Routes commands
- **Note**: Read and Save buttons removed (links now embedded in messages)

---

## Data Model (PostgreSQL on Supabase)

```sql
users (
  id UUID PRIMARY KEY,
  telegram_id BIGINT UNIQUE,
  username TEXT,
  interests JSONB,               -- ["distributed systems", "rust", ...]
  active_discussion_post_id UUID,
  memory_enabled BOOLEAN DEFAULT true,
  status TEXT DEFAULT 'active',  -- active | paused
  created_at TIMESTAMPTZ
)

posts (
  id UUID PRIMARY KEY,
  hn_id INT UNIQUE,
  type TEXT,                     -- story | ask_hn | show_hn
  title TEXT,
  url TEXT,
  domain TEXT,
  score INT,
  comment_count INT,
  html_s3_key TEXT,              -- s3://hn-pal/html/{hn_id}.html
  markdown_s3_key TEXT,          -- s3://hn-pal/md/{hn_id}.md
  summary TEXT,
  summarized_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ,
  hn_published_at TIMESTAMPTZ
)

deliveries (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users,
  post_id UUID REFERENCES posts,
  message_id BIGINT,             -- telegram message id
  batch_id TEXT,                  -- groups posts in same digest
  reaction TEXT,                  -- up | down | null
  delivered_at TIMESTAMPTZ
)

conversations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users,
  post_id UUID REFERENCES posts,
  messages JSONB,                -- [{role, content, timestamp}, ...]
  token_usage JSONB,             -- {input_tokens, output_tokens}
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ
)

memory (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users,
  type TEXT,                     -- interest | fact | discussion_note
  content TEXT,
  source_post_id UUID,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ
)
```

**S3 structure:**

```
hn-pal/
  html/{hn_id}.html     -- raw crawled HTML
  md/{hn_id}.md          -- converted markdown
```

---

## Message Templates

### Style 1: Brief Digest (default)

Compact. One message. Tap to expand.

```
┌─────────────────────────────────────────┐
│                                         │
│  🔶 HN Brief — Feb 8 morning           │
│                                         │
│  1 · PostgreSQL 18 Released             │
│  2 · Why We Left Kubernetes             │
│  3 · Local-First Sync Engine in Rust    │
│  4 · The Death of SaaS Pricing          │
│  5 · Understanding CRDTs               │
│                                         │
│  ┌─────┬─────┬─────┬─────┬─────┐       │
│  │  1  │  2  │  3  │  4  │  5  │       │
│  └─────┴─────┴─────┴─────┴─────┘       │
│                                         │
└─────────────────────────────────────────┘
```

Small message. Under Telegram limits. User taps a number to expand.

### Style 2: Flat Scroll (preferred) — Updated Format

Each post is its own message. User scrolls through at their own pace.
Links are now clickable in the message text using Markdown formatting.

```
┌─────────────────────────────────────────┐
│  PostgreSQL 18 Released                 │
│  HN Discussion                          │
│                                         │
│  Major performance gains across OLTP    │
│  workloads with up to 2x throughput.    │
│  New JSON path indexing and async I/O.  │
│                                         │
│  Read Article on postgresql.org         │
│                                         │
│  ⬆️ 452 · 💬 230 · 1/8                  │
│                                         │
│  ┌──────────┬─────┬─────┐              │
│  │ 💬 Discuss│ 👍  │ 👎  │              │
│  └──────────┴─────┴─────┘              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Why We Left Kubernetes                 │
│  HN Discussion                          │
│                                         │
│  A 15-person startup shares why they    │
│  moved back to bare metal after 2       │
│  years on K8s. Cost and complexity.     │
│                                         │
│  Read Article on blog.startup.io        │
│                                         │
│  ⬆️ 389 · 💬 187 · 2/8                  │
│                                         │
│  ┌──────────┬─────┬─────┐              │
│  │ 💬 Discuss│ 👍  │ 👎  │              │
│  └──────────┴─────┴─────┘              │
└─────────────────────────────────────────┘

         ... continues scrolling ...
```

**Format Changes (2026-02-15)**:
- **Bold title** using Markdown (asterisks removed from display)
- **Clickable "HN Discussion" link** to HackerNews comments
- **Clickable "Read Article" link** with domain name
- **Position indicator** moved to stats line (e.g., "1/8")
- **Simplified buttons**: Removed Read and Save (redundant with inline links)
- **Parse mode**: Changed from HTML to Markdown for better reliability

### Expanded Post (from Style 1 tap) — Updated Format

```
┌─────────────────────────────────────────┐
│                                         │
│  PostgreSQL 18 Released                 │
│  HN Discussion                          │
│                                         │
│  PostgreSQL 18 brings significant       │
│  performance improvements to OLTP       │
│  workloads with up to 2x throughput     │
│  on high-connection counts. Key         │
│  additions include native JSON path     │
│  indexing, async I/O for vacuum, and    │
│  improved logical replication.          │
│                                         │
│  Read Article on postgresql.org         │
│                                         │
│  ⬆️ 452 · 💬 230 · 1/8                  │
│                                         │
│  ┌──────────┬─────┬─────┐              │
│  │ 💬 Discuss│ 👍  │ 👎  │              │
│  └──────────┴─────┴─────┘              │
│                                         │
└─────────────────────────────────────────┘
```

### Active Discussion

```
┌─────────────────────────────────────────┐
│                                         │
│  📖 Discussing: PostgreSQL 18 Released  │
│  ─────────────────────────────────      │
│  Article + top comments loaded.         │
│  Ask me anything. Tap Discuss on        │
│  another post to switch.               │
│                                         │
└─────────────────────────────────────────┘

  User: What are people saying in
        the comments?

┌─────────────────────────────────────────┐
│  The top comments focus on three        │
│  themes: the async vacuum being a       │
│  game-changer for large tables,         │
│  skepticism about the 2x claim, and     │
│  excitement about JSON path indexing    │
│  catching up to MongoDB.               │
└─────────────────────────────────────────┘

  User: How does this relate to that
        CockroachDB post we discussed?

┌─────────────────────────────────────────┐
│  Good connection. Last week you read    │
│  about CockroachDB dropping their       │
│  free tier. One argument was that       │
│  Postgres is "good enough." PG 18's    │
│  improvements strengthen that case.     │
└─────────────────────────────────────────┘
```

Discussion ends by:

- Tapping `💬 Discuss` on another post → auto-switch
- 30 min inactivity → auto-close

No explicit end button.

### Memory View (`/memory`)

```
┌─────────────────────────────────────────┐
│                                         │
│  🧠 What I Remember                     │
│                                         │
│  Interests:                             │
│  · Distributed systems                  │
│  · Rust, PostgreSQL                     │
│  · ML infrastructure                    │
│                                         │
│  Recent discussions:                    │
│  · CockroachDB pricing (Feb 5)         │
│  · Raft consensus deep dive (Feb 3)    │
│  · Rust async comparison (Jan 28)      │
│                                         │
│  Notes:                                 │
│  · Prefers practical over theoretical   │
│  · Building a search system with        │
│    embeddings                           │
│                                         │
│  Memory is ON                           │
│                                         │
└─────────────────────────────────────────┘
```

---

## Bot Flow

```
                        ┌───────────┐
                        │  /start   │
                        └─────┬─────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Welcome msg    │
                     │  "I'm HN Pal.  │
                     │  I send you HN  │
                     │  digests and    │
                     │  chat about     │
                     │  posts."        │
                     │                 │
                     │  Pick interests │
                     │  (inline btns   │
                     │   or skip)      │
                     └────────┬────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │         IDLE STATE            │
              │    (no active discussion)     │
              └──┬──────────┬──────────┬──────┘
                 │          │          │
      ┌──────────┘          │          └──────────┐
      ▼                     ▼                     ▼
┌───────────┐       ┌─────────────┐       ┌────────────┐
│ Digest    │       │  Command    │       │ Freeform   │
│ arrives   │       │  received   │       │ message    │
│           │       │             │       │            │
│ Style 1:  │       │ /start      │       │ General    │
│ tap [N]   │       │ /pause      │       │ chat, no   │
│ to expand │       │ /saved      │       │ post       │
│           │       │ /memory     │       │ context    │
│ Style 2:  │       │ /memory     │       │            │
│ already   │       │   pause     │       │            │
│ expanded, │       │ /memory     │       │            │
│ scroll    │       │   forget    │       │            │
│           │       │ /memory     │       │            │
│           │       │   clear     │       │            │
│           │       │ /token      │       │            │
└─────┬─────┘       └─────────────┘       └────────────┘
      │
      │ User taps [💬 Discuss]
      │ on any post
      ▼
┌──────────────────────────┐
│    DISCUSSION STATE      │
│                          │
│  active_post = X         │
│  Load from S3:           │
│  · article markdown      │
│  Load from DB:           │
│  · user memory           │
│  · past related convos   │
│                          │
│  All user messages       │◀─── user types freely
│  routed to this context  │
│                          │
│  LLM receives:           │
│  · article content       │
│  · user memory           │
│  · convo history         │
│                          │
│  Exit:                   │
│  ├─ [Discuss] on another │
│  │  post → save + switch │
│  └─ 30 min timeout       │
│     → save + idle        │
│                          │
│  On exit:                │
│  · Save conversation     │
│  · Extract memory via    │
│    LLM (topics, opinions,│
│    connections)           │
│  · Update token usage    │
│  · Clear active_post     │
└──────────────────────────┘
```

---

## Ingest Pipeline Flow

```
┌───────────────┐
│  Vercel Cron  │
│  (every 2h)   │
└───────┬───────┘
        │
        ▼
┌─────────────────┐
│  Poll HN API    │
│  /topstories    │
│  /beststories   │
└────────┬────────┘
        │
        ▼
┌─────────────────┐
│  Filter         │
│                 │
│  ✗ Skip Ask HN  │
│  ✗ Skip Show HN │
│  ✗ Skip if      │
│    already in DB│
│  ✓ Score > 100  │
└────────┬────────┘
         │ new posts only
         ▼
┌─────────────────┐
│  For each post: │
│                 │
│  1. Fetch URL   │
│     (HTTP GET)  │
│                 │
│  2. Get raw     │
│     HTML        │
│                 │
│  3. Upload HTML │
│     to S3       │
│     html/{id}   │
│                 │
│  4. HTML → MD   │
│     (trafilat-  │
│      ura)       │
│                 │
│  5. Upload MD   │
│     to S3       │
│     md/{id}     │
│                 │
│  6. Insert post │
│     metadata    │
│     to DB       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summarize      │
│                 │
│  Read MD from   │
│  S3 → Claude    │
│  API → 2-3 line │
│  summary → save │
│  to DB          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deliver        │
│                 │
│  For each       │
│  active user:   │
│  · Check if     │
│    digest time  │
│  · Collect un-  │
│    delivered    │
│    posts        │
│  · Rank by      │
│    score ×      │
│    interest     │
│  · Send via     │
│    bot (style   │
│    1 or 2)      │
│  · Log to       │
│    deliveries   │
└─────────────────┘
```

---

## Discussion Flow (Detail)

```
User taps [💬 Discuss]
         │
         ▼
┌──────────────────┐
│ Has active       │
│ discussion?      │
└──┬───────────┬───┘
   │ yes       │ no
   ▼           ▼
┌────────┐  ┌─────────────┐
│ Save   │  │ Set active  │
│ prev   │  │ post = this │
│ convo  │  └──────┬──────┘
│ Extract│         │
│ memory │         │
└───┬────┘         │
    └──────┬───────┘
           ▼
┌──────────────────┐
│ Load context     │
│                  │
│ From S3:         │
│ · article.md     │
│                  │
│ From DB:         │
│ · user memory    │
│ · past convos    │
│   on related     │
│   topics         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Send header:     │
│ "📖 Discussing:  │
│  [title]"        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ CONVERSATION     │
│ LOOP             │◀────┐
│                  │     │
│ User message     │     │
│       │          │     │
│       ▼          │     │
│ Claude API:      │     │
│ · system: article│     │
│   + memory +     │     │
│   convo history  │     │
│ · user: message  │     │
│       │          │     │
│       ▼          │     │
│ Response → user  │     │
│ Track tokens     │─────┘
│                  │
└────────┬─────────┘
         │
  Exit trigger:
  ├─ [Discuss] another post
  └─ 30 min no message
         │
         ▼
┌──────────────────┐
│ End discussion   │
│                  │
│ · Save convo     │
│   to DB          │
│ · LLM extract:   │
│   topics,        │
│   opinions,      │
│   connections    │
│ · Store in       │
│   memory table   │
│ · Sum token      │
│   usage          │
│ · Clear active   │
│   post           │
└──────────────────┘
```

---

## Commands

```
/start          Onboarding + pick interests
/pause          Pause / resume deliveries (toggle)
/saved          Show bookmarked posts
/memory         View what bot remembers
/memory pause   Toggle memory on/off
/memory forget  Forget a specific topic (interactive)
/memory clear   Full memory reset
/token          Show token usage stats
```

That's it. Everything else happens through inline buttons on messages.

---

## Tech Stack

| Component       | Choice                    |
| --------------- | ------------------------- |
| Language        | Python                    |
| Bot framework   | aiogram 3.x               |
| Database        | PostgreSQL (Supabase)     |
| File storage    | S3                        |
| Cron            | Vercel Cron               |
| Bot hosting     | Vercel (serverless)       |
| LLM             | Claude API                |
| HTML extraction | trafilatura               |
| HTML → Markdown | trafilatura / markdownify |

---

## Build Order

| Phase | Scope                                                |
| ----- | ---------------------------------------------------- |
| 1     | Ingest: HN poll → crawl → HTML → MD → S3 + DB        |
| 2     | Summarize: read MD from S3 → Claude → store summary  |
| 3     | Bot: /start + deliver flat scroll digests to your DM |
| 4     | Inline buttons: Discuss, 👍👎 (Read/Save removed)   |
| 5     | Discussion flow with article context                 |
| 6     | Memory: track + extract + surface in discussions     |
| 7     | Commands: /memory, /saved, /token, /pause            |

**Status (2026-02-15)**: Phases 1-4 complete. Format updated with clickable Markdown links.
