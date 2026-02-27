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
│  │ Store      │  │ 5 variants │  │ convos     │  │ commands │ │
│  │ metadata   │  │ + caching  │  │ Extract    │  │ Manage   │ │
│  │            │  │ + tracking │  │ insights   │  │ discuss  │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └────┬─────┘ │
│        │               │               │               │       │
│        └───────────┬───┴───────────┬───┘               │       │
│                    ▼               ▼                    │       │
│             ┌────────────┐  ┌────────────┐             │       │
│             │ PostgreSQL │  │  RocksDB   │             │       │
│             │   (RDS)    │  │            │             │       │
│             │            │  │ HTML files │             │       │
│             │ users      │  │ MD files   │             │       │
│             │ posts      │  │ (local FS) │             │       │
│             │ summaries  │  │            │             │       │
│             │ deliveries │  └────────────┘             │       │
│             │ convos     │                             │       │
│             └────────────┘◀─────────────────────────────┘       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Infrastructure                                          │  │
│  │  AWS EC2 ── app servers + background jobs               │  │
│  │  AWS RDS ── PostgreSQL (managed database)               │  │
│  │  AWS S3 ── backups, logs, exports                       │  │
│  │  OpenAI API ── gpt-4o-mini for summarization           │  │
│  │  Langfuse ── LLM observability & token tracking         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Ingest**

- Poll HN API (`/topstories`, `/beststories`) via APScheduler (hourly)
- Skip `Ask HN` and `Show HN` posts
- For each qualifying post: fetch the linked URL, crawl HTML content
- Convert HTML → clean Markdown (via trafilatura + markitdown)
- Save metadata (title, url, score, comment_count, hn_id, type) to PostgreSQL
- Save HTML, text, and Markdown to RocksDB (local filesystem with Zstandard compression)

**Summarize**

- Runs after ingest via APScheduler (every 30 minutes)
- Reads Markdown content from RocksDB
- Uses OpenAI Agents SDK (gpt-4o-mini model) to generate summaries
- 5 prompt variants: basic, technical, business, concise, personalized
- User can choose preferred summary style (stored in `users.summary_preferences`)
- Each summary tracked with token usage in `agent_calls` and aggregated in `user_token_usage`
- Stores summaries in PostgreSQL for fast retrieval
- Only processes posts that have not been summarized yet

**Memory**

- Tracks user interests (implicit from reactions + discussions, explicit from onboarding)
- Stores conversation history per post per user
- After discussion ends: LLM extracts key insights, opinions, connections
- Serves memory context when discussions start
- Handles memory commands (view, pause, forget, clear)

**Bot**

- Telegram bot server running on AWS EC2
- Delivers digest messages on schedule
- Handles inline button callbacks (discuss, reactions)
- Manages discussion state (active post per user, auto-switch)
- Routes commands
- Read and Save button links now embedded directly in message text (Markdown format)

---

## Data Model (PostgreSQL)

### Core Tables

```python
# posts — HackerNews posts with crawled content metadata
posts {
  id UUID PRIMARY KEY,
  hn_id INT UNIQUE,              -- HackerNews post ID
  type TEXT,                     -- story | ask | show | job
  title TEXT,
  author TEXT,
  url TEXT,
  domain TEXT,                   -- extracted from URL
  score INT,
  comment_count INT,
  
  # Content storage (tracks what's in RocksDB)
  has_html BOOLEAN,              -- raw HTML in RocksDB
  has_text BOOLEAN,              -- extracted plain text
  has_markdown BOOLEAN,          -- converted markdown
  
  # Crawl tracking
  is_crawl_success BOOLEAN,
  crawl_retry_count INT,
  crawl_error TEXT,
  crawled_at TIMESTAMPTZ,
  content_length INT,
  
  # HN metadata
  is_dead BOOLEAN,
  is_deleted BOOLEAN,
  
  # Summary (basic summary for quick access, full summaries in summaries table)
  summary TEXT,                  -- fallback basic summary
  summarized_at TIMESTAMPTZ,
  
  # Timestamps
  created_at TIMESTAMPTZ,        -- HN post creation time
  collected_at TIMESTAMPTZ,      -- when we collected it
  updated_at TIMESTAMPTZ
}

# users — Telegram users with preferences and subscription state
users {
  id INT PRIMARY KEY,
  telegram_id BIGINT UNIQUE,
  username TEXT(255),
  
  # Preferences
  interests JSON,                -- ["distributed systems", "rust", ...]
  memory_enabled BOOLEAN DEFAULT true,
  status TEXT(50),               -- active | paused | blocked
  delivery_style TEXT(50),       -- flat_scroll | brief
  summary_preferences JSON,      -- {style: "basic", detail_level: "medium", ...}
  
  # Tracking
  last_delivered_at TIMESTAMPTZ,
  
  # Timestamps
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  
  # Relationships
  - summaries (1:N) cascade
  - token_usage (1:N) cascade
  - agent_calls (1:N) cascade
  - deliveries (1:N) cascade
  - conversations (1:N) cascade
}

# summaries — Personalized summaries per user/post/style
summaries {
  id INT PRIMARY KEY,
  post_id UUID FOREIGN KEY,
  user_id INT FOREIGN KEY,
  
  # Summary data
  prompt_type TEXT(50),          -- basic | technical | business | concise | personalized
  summary_text TEXT,             -- the actual summary (2-3 sentences)
  key_points JSON,               -- extracted key points if structured output
  technical_level TEXT(50),      -- beginner | intermediate | advanced
  
  # Cost tracking
  token_count INT,
  cost_usd DECIMAL(10, 6),
  
  # User feedback
  rating INT,                    -- 1-5 stars
  user_feedback TEXT,
  
  # Timestamps
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  
  # Unique constraint: one summary per (user_id, post_id, prompt_type)
}

# deliveries — Tracks which posts were sent to which users
deliveries {
  id UUID PRIMARY KEY,
  user_id INT FOREIGN KEY,
  post_id UUID FOREIGN KEY,
  
  # Delivery metadata
  message_id INT,                -- Telegram message ID
  batch_id TEXT,                 -- groups posts in same digest
  reaction TEXT,                 -- "up" | "down" | null (user interaction)
  
  # Timestamps
  delivered_at TIMESTAMPTZ
}

# conversations — Discussion threads per user per post
conversations {
  id UUID PRIMARY KEY,
  user_id INT FOREIGN KEY,
  post_id UUID FOREIGN KEY,
  
  # Conversation data
  messages JSON,                 -- [{role, content, timestamp}, ...]
  token_usage JSON,              -- {input_tokens, output_tokens, model}
  
  # Timestamps
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ          -- null if still active
}

# user_token_usage — Daily aggregated token tracking per user
user_token_usage {
  id INT PRIMARY KEY,
  user_id INT FOREIGN KEY,
  date DATE,
  model TEXT(50),                -- gpt-4o-mini | gpt-4o | etc
  
  # Token counts
  input_tokens INT,
  output_tokens INT,
  total_tokens INT,
  
  # Cost
  cost_usd DECIMAL(10, 6),
  request_count INT,
  
  # Timestamps
  created_at TIMESTAMPTZ,
  
  # Unique constraint: one per (user_id, date, model)
}

# agent_calls — Individual agent call tracking for debugging/observability
agent_calls {
  id INT PRIMARY KEY,
  user_id INT FOREIGN KEY,
  
  # Call details
  trace_id TEXT,                 -- Langfuse trace ID
  agent_name TEXT(100),          -- SummarizationAgent | DiscussionAgent | etc
  operation TEXT(100),           -- summarize_post | answer_question | etc
  model TEXT(50),                -- gpt-4o-mini | gpt-4o | etc
  
  # Token usage
  input_tokens INT,
  output_tokens INT,
  total_tokens INT,
  cost_usd DECIMAL(10, 6),
  
  # Performance
  latency_ms INT,                -- Response time in milliseconds
  status TEXT(20),               -- success | error
  
  # Error tracking
  error_message TEXT,
  
  # Timestamps
  created_at TIMESTAMPTZ
}

# user_activity_log — Append-only log of user interactions
user_activity_log {
  id UUID PRIMARY KEY,
  user_id INT FOREIGN KEY,
  post_id UUID FOREIGN KEY,
  
  # Action details
  action_type TEXT(20),          -- rate_up | rate_down | save
  
  # Timestamps
  created_at TIMESTAMPTZ
}
```

### Content Storage (RocksDB)

Content is stored in **RocksDB** (local filesystem, not S3) for performance:

```
rocksdb_data/
  html/{post_id}        -- raw crawled HTML (~200KB per post)
  text/{post_id}        -- extracted plain text (~50KB per post)
  md/{post_id}          -- converted markdown (~30KB per post)
```

**Why RocksDB?**

- High throughput for write-heavy ingest pipelines (~100 posts/hour)
- Zstandard compression reduces disk usage by ~70%
- Local filesystem access (faster than S3 GET requests)
- Self-contained in Docker volume (no external dependencies)
- Read-only access from summarizer (safe concurrent access)

---

## Summary Styles & Personalization

HN Pal supports **5 summary variants** tailored to different users' preferences and technical backgrounds:

### Summary Style Variants

| Style | Audience | Example | Characteristics |
| ----- | -------- | ------- | --------------- |
| **basic** | General developers | 2–3 sentences, 50–80 words | Balanced depth, clear for non-specialists, highlights practical impact |
| **technical** | Senior engineers | Implementation details, algorithms, trade-offs | Deep technical terminology, protocols, benchmarks, architectural decisions |
| **business** | CTOs, managers | Non-technical language, cost & ROI | Strategic business value, competitive positioning, market impact |
| **concise** | Busy developers | 1 sentence, ≤30 words | Ultra-brief headline-style summary |
| **personalized** | Individual users | Interest-aware, contextual | Tailored to user's past interests and discussion history |

### User Summary Preferences

The `users` table stores each user's preferred style in the `summary_preferences` JSON field:

```json
{
  "style": "basic",
  "detail_level": "medium",
  "technical_depth": "intermediate"
}
```

Users can configure their preference via `/preferences` command during onboarding or at any time.

### Cost & Token Tracking

**Per-call tracking** (`agent_calls` table):

- Trace ID (Langfuse)
- Input/output tokens
- Cost in USD (calculated from OpenAI pricing)
- Latency in milliseconds

**Per-user daily aggregation** (`user_token_usage` table):

- Daily totals grouped by model (gpt-4o-mini, gpt-4o, etc.)
- Cost in USD
- Request count

**Pricing** (as of 2026-02):

- gpt-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- Realistic cost per summary: ~$0.00015 per input + $0.0003 per output = ~$0.0005 total
- Daily cost for 200 posts: ~$0.10 per day

**Langfuse integration**:

- All agent calls automatically traced
- Dashboard shows per-user usage trends
- Budget alerts for cost anomalies

---

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
┌─────────────────┐
│  APScheduler    │
│  (every hour)   │
└───────┬─────────┘
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
│  ✓ Score > 50   │
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
│  3. Store HTML  │
│     to RocksDB  │
│     html/{id}   │
│                 │
│  4. HTML → Text │
│     → MD        │
│     (trafilat-  │
│      ura)       │
│                 │
│  5. Store Text  │
│     & MD to     │
│     RocksDB     │
│     text/{id}   │
│     md/{id}     │
│                 │
│  6. Insert post │
│     metadata    │
│     to DB       │
│                 │
│  7. Mark flags: │
│     is_crawl_   │
│     success=T   │
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│  Summarize       │
│  (every 30 min)  │
│                  │
│  Read unsumm.    │
│  posts from DB   │
│                  │
│  Get MD content  │
│  from RocksDB    │
│  ↓              │
│  OpenAI Agent    │
│  (gpt-4o-mini)   │
│  ↓              │
│  Store summary   │
│  to DB + track   │
│  tokens in       │
│  agent_calls &   │
│  user_token_     │
│  usage tables    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Deliver         │
│  (every hour)    │
│                  │
│  For each       │
│  active user:   │
│  · Check if     │
│    delivery time│
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
└──────────────────┘
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
│ From RocksDB:    │
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
│ OpenAI API:      │     │
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
/preferences    Set summary style (basic, technical, business, concise, personalized)
/pause          Pause / resume deliveries (toggle)
/saved          Show bookmarked posts
/memory         View what bot remembers
/memory pause   Toggle memory on/off
/memory forget  Forget a specific topic (interactive)
/memory clear   Full memory reset
/token          Show token usage stats + cost
```

Everything else happens through inline buttons on messages.

---

## Tech Stack

| Component | Choice |
| --------- | ------ |
| Language | Python 3.10+ |
| Bot framework | aiogram 3.x |
| Database | PostgreSQL + asyncpg |
| Content storage | RocksDB + Zstandard compression |
| LLM API | OpenAI Agents SDK (gpt-4o-mini) |
| Observability | Langfuse |
| Package manager | uv |
| Migrations | Alembic |
| Compute | AWS EC2 |
| Infrastructure | Terraform + AWS |
| Content extraction | trafilatura + markitdown |
| Task scheduling | APScheduler |

---

## Build Order & Implementation Status

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | Ingest: HN poll → crawl → HTML → MD → RocksDB + DB | ✅ Complete |
| 2 | Summarize: OpenAI Agents, 5 variants, tokens | 🔄 80% In Progress |
| 3 | Bot: /start + deliver flat scroll digests | ✅ Complete |
| 4 | Inline buttons: Discuss, 👍👎 reactions | ✅ Complete |
| 5 | Discussion flow with article context | 📝 Planned |
| 6 | Memory: track + extract + surface | 📝 Planned |
| 7 | Commands: /memory, /saved, /token, /pause | 🔄 In Progress |
| 8 | Improvements: watermark fix, crawler daemon | 🔄 In Progress |
| 9 | AWS deployment: Terraform IaC | ✅ Complete |

**Current Status (2026-02-26)**:

- **Core functionality**: Ingest → Summarize → Deliver loop working
- **Phase 2 progress**: LLM integration complete; 5-variant prompt framework; summary preferences in User model; cost tracking via Langfuse  
- **Phase 8 improvements**: Fixed summarizer watermark (collected_at rolling window); added crawler daemon to docker-compose
- **Production ready**: AWS infrastructure (VPC, RDS, S3, EC2, IAM) provisioned via Terraform
