# Summarization Scheduler - Brainstorm & Architecture Design

**Goal**: Create an hourly scheduler that incrementally scans new HN posts and generates summaries for all users efficiently.

**Key Requirement**: Don't re-summarize posts already summarized. Only summarize NEW posts incrementally.

---

## 1. System Overview

### Current State (Post Collection)
```
HN API (Hourly)
    ↓
HourlyPostsCollectorJob (runs hourly at :00)
    ↓
PostgreSQL (stores posts)
    ↓
RocksDB (caches metadata)
```

### New State (With Summarization)
```
HN API (Hourly)
    ↓
HourlyPostsCollectorJob (existing - runs hourly at :00)
    ↓
PostgreSQL (stores posts with summary=NULL)
    ↓
HourlySummarizationJob (runs hourly at :15) ← NEW
    ↓
Summarization Agent (batch summarizes new posts)
    ↓
PostgreSQL (updates summary field)
    ↓
DeliveryPipeline (optional: delivers to users)
```

---

## 2. Summarization Scheduler Architecture

### Core Components

#### A. **HourlySummarizationJob** (New Job Class)
Main job that runs hourly and coordinates summarization.

**Responsibilities:**
- Find all unsummarized posts (summary IS NULL)
- Batch posts by content type/length
- Coordinate agent summarization
- Store results back to database
- Track statistics and errors

**Key Methods:**
- `run_summarization()` - Main entry point (called by APScheduler)
- `find_unsummarized_posts()` - Query DB for posts with summary=NULL
- `summarize_batch()` - Summarize a batch of posts
- `update_post_summaries()` - Save summaries back to DB
- `get_stats()` - Return execution statistics

#### B. **Incremental Scanning Strategy**

**Why Incremental?**
- Posts grow continuously (hundreds per day)
- Full re-scan would waste API quota
- Summarization takes time/cost (OpenAI API calls)

**How It Works:**
1. **Track Summarization State** in Post model:
   - `summary`: NULL initially, filled after summarization
   - `summarized_at`: TIMESTAMP when summarization occurred
   - `summarization_status`: ENUM (pending, in_progress, completed, failed)
   - `summarization_error`: TEXT for error messages

2. **Query Strategy**:
   ```sql
   SELECT * FROM posts
   WHERE summary IS NULL
   AND is_dead = false
   AND is_deleted = false
   AND is_crawl_success = true
   ORDER BY created_at DESC
   LIMIT 100
   ```

3. **Batch Windows**:
   - Hour 1 (14:00): Found 150 new posts
   - Hour 2 (15:00): Found 120 new posts
   - Hour 3 (16:00): Found 89 new posts
   - Each hour only processes that hour's new posts

#### C. **User Delivery Coordination**

**Two Delivery Modes:**

**Mode 1: Immediate Individual Delivery**
```
Hour :15 Summarization Completes
    ↓
For each User:
  - Check user.last_delivered_at
  - Find new posts since last delivery with summaries
  - Send to user immediately
  - Update user.last_delivered_at
```

**Mode 2: Batch Hourly Delivery** (Existing)
```
Hour :15 Summarization Completes
    ↓
Hour :30 (or next cycle)
  - DeliveryPipeline runs
  - All users get digest
  - Resets user.last_delivered_at
```

**Decision**: Start with Mode 2 (simpler, fits existing DeliveryPipeline)

---

## 3. Scheduling Strategy

### Timing Design

```
HN Posting Pattern Analysis:
- Peak: 08:00-18:00 UTC (3-5 new posts/minute)
- Off-peak: 18:00-08:00 UTC (0.5-1 post/minute)
- Average: ~100-200 new posts per hour

Scheduler Timeline:
Hour 00:00 - No activity
Hour 00:15 - Summarization Job #1 runs (summarizes 0-20 posts from last hour)
Hour 00:30 - Optional: Delivery #1 (digest to users)
Hour 01:00 - Post Collection Job runs (fetches new posts from HN)
Hour 01:15 - Summarization Job #2 runs
Hour 01:30 - Optional: Delivery #2
Hour 02:00 - Post Collection Job runs
...
```

### Recommended Timing Offsets

```
:00 - HourlyPostsCollectorJob (existing)
      └─ Fetches new posts from HN API
      └─ Takes ~10-30 seconds
      └─ max_instances=1 (prevent overlap)

:15 - HourlySummarizationJob (NEW)
      └─ Summarizes unsummarized posts from last hour
      └─ Takes 2-10 minutes depending on batch size
      └─ max_instances=1 (prevent overlap)
      └─ Rate limited: 1 API call per second to OpenAI

:30 - Optional DeliveryPipeline (existing)
      └─ Send digests to users
      └─ Takes 5-30 minutes depending on user count
      └─ max_instances=1 (prevent overlap)
```

### Why :15 Offset?
- Posts collected at :00
- 15 minutes buffer for post collection to complete
- Summarization can run on posts from previous hour
- Guarantees posts exist before summarization starts

---

## 4. Batch Processing Strategy

### Batch Sizes

**Why Batch?**
- API rate limiting (OpenAI: 60 req/min for gpt-4o-mini)
- Cost optimization (bulk operations cheaper)
- Resource management (memory, CPU)
- Error recovery (fail one batch, retry next hour)

**Recommended Batch Sizes:**
```
Small batch (default): 10-20 posts per batch
- Shorter posts: 20 posts/batch
- Medium posts: 15 posts/batch
- Long posts: 10 posts/batch

Processing Rate: 1 summary/second (with rate limiting)
Example:
- 150 new posts = 15 batches (if 10 posts/batch)
- Processing time = ~2-5 minutes total
```

### Batch Grouping Logic

```python
# Strategy 1: Time-based batching
for post in unsummarized_posts:
    if len(current_batch) < batch_size:
        current_batch.append(post)
    else:
        yield current_batch
        current_batch = [post]

# Strategy 2: Content-length batching (parallel processing)
short_posts = [p for p in unsummarized if len(p.content) < 1000]
medium_posts = [p for p in unsummarized if 1000 <= len(p.content) < 5000]
long_posts = [p for p in unsummarized if len(p.content) >= 5000]

# Process in parallel (3 separate processes)
```

### Batch Error Handling

```
Batch Processing:
1. Start batch of 10 posts
2. Summarize posts 1-5 successfully ✓
3. Post 6 fails (LLM error)
4. Skip post 6, continue 7-10
5. Log failed post for retry
6. Next hour: only retry post 6
7. If still fails after 3 hours: mark as error, skip

Failed Posts Table:
- post_id
- error_message
- retry_count (0-3)
- last_retry_at
```

---

## 5. Database Schema Extensions

### Post Model Updates

```sql
ALTER TABLE posts ADD COLUMN (
    summary TEXT,                    -- The summary text (or NULL)
    summarized_at TIMESTAMP,         -- When summarization occurred
    summarization_status VARCHAR(20) -- pending|in_progress|completed|failed
        DEFAULT 'pending',
    summarization_error TEXT,        -- Error message if failed
    summarization_model VARCHAR(50)  -- Which model generated it (gpt-4o-mini)
        DEFAULT 'gpt-4o-mini',
    summarization_attempts INT DEFAULT 0  -- How many times tried
);

CREATE INDEX idx_posts_needs_summarization
ON posts(summary, is_dead, is_deleted, is_crawl_success, created_at);

CREATE INDEX idx_posts_summarization_status
ON posts(summarization_status, summarization_attempts);
```

### AgentCall Table (Existing - Extended for Summarization)

```sql
-- Already exists, tracks token usage
-- Usage for summarization agent:
INSERT INTO agent_calls (
    user_id,          -- NULL for batch summarization
    agent_name,       -- "SummarizationAgent"
    model,            -- "gpt-4o-mini"
    input_tokens,
    output_tokens,
    latency_ms,
    status,           -- "success" or "error"
    operation,        -- "batch_summarize_posts"
    metadata          -- {"batch_size": 10, "posts_count": 10, "prompt_type": "basic"}
)
```

### Summarization Statistics Table (Optional - New)

```sql
CREATE TABLE summarization_runs (
    id UUID PRIMARY KEY,
    run_at TIMESTAMP DEFAULT now(),
    total_posts_found INT,
    posts_summarized INT,
    posts_failed INT,
    posts_skipped INT,
    batch_count INT,
    total_input_tokens INT,
    total_output_tokens INT,
    total_cost DECIMAL(10, 4),      -- $0.0001 per 1K input tokens, etc
    duration_seconds INT,
    status VARCHAR(20),              -- "completed" or "partial_failure"
    error_message TEXT
);
```

---

## 6. Configuration & Settings

### Environment Variables

```env
# Summarization Job Settings
SUMMARIZATION_ENABLED=true
SUMMARIZATION_BATCH_SIZE=10
SUMMARIZATION_MAX_ATTEMPTS=3
SUMMARIZATION_PROMPT_TYPE=basic

# OpenAI Settings (existing)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_DEFAULT_TEMPERATURE=0.3
OPENAI_DEFAULT_MAX_TOKENS=500

# Rate Limiting
SUMMARIZATION_RATE_LIMIT_RPS=1  # 1 request per second
SUMMARIZATION_REQUEST_TIMEOUT=30  # seconds

# Cost Control
SUMMARIZATION_COST_LIMIT_DAILY=10.0  # Stop if exceeds $10/day
SUMMARIZATION_COST_LIMIT_MONTHLY=100.0

# Logging
SUMMARIZATION_LOG_LEVEL=INFO
SUMMARIZATION_LOG_STATS=true
```

### Configuration Class

```python
class SummarizationConfig:
    enabled: bool = True
    batch_size: int = 10
    max_attempts: int = 3
    prompt_type: str = "basic"  # Can be: basic, technical, business, concise
    rate_limit_rps: float = 1.0
    request_timeout: int = 30
    cost_limit_daily: float = 10.0
    cost_limit_monthly: float = 100.0
    skip_already_failed: bool = False  # Skip posts that failed 3x?
```

---

## 7. Error Handling & Recovery

### Error Categories

**Type 1: API Errors (Retryable)**
- OpenAI API timeout
- Rate limit exceeded
- Temporary connection issues
- Action: Retry in next hour

**Type 2: Content Errors (Non-retryable)**
- Content too long (>100K tokens)
- Unsupported content format
- Action: Mark with status="failed", log error

**Type 3: System Errors (Critical)**
- Database connection lost
- Scheduler crashed
- Action: Alert admin, halt job

### Recovery Strategy

```
Hour 1 (15:00):
  - Summarize 150 posts
  - 10 fail with API timeout
  - Mark 10 with status="pending", attempts=1

Hour 2 (16:00):
  - Find 120 new posts + 10 retry posts
  - Retry the 10 first
  - 2 succeed, 8 still fail
  - Mark 8 with attempts=2

Hour 3 (17:00):
  - Find 100 new posts + 8 retry posts
  - Retry the 8 first
  - 3 succeed, 5 still fail
  - Mark 5 with attempts=3

Hour 4 (18:00):
  - Find 90 new posts + 5 failed posts
  - 5 failed posts exceed max_attempts
  - Mark as status="failed", skip future retries
  - Only summarize 90 new posts
```

---

## 8. Performance Considerations

### Token Usage Estimation

```
Average post content: 2000 characters (~500 tokens input)
Average summary: 100 characters (~25 tokens output)
Cost per post: ~$0.00008 (using gpt-4o-mini pricing)

Daily volume:
- 100-200 posts/hour × 24 hours = 2400-4800 posts/day
- 2400 posts × $0.00008 = $0.192/day (lower bound)
- 4800 posts × $0.00008 = $0.384/day (upper bound)
- Monthly: $5.76 - $11.52

Total Tokens:
- 2400 posts × 525 tokens/post = 1.26M tokens/day
- Input: 1.2M tokens/day (4000 posts × 500 tokens)
- Output: 60K tokens/day (4000 posts × 25 tokens)
```

### Processing Time Estimation

```
Batch size: 10 posts
Rate limit: 1 API call/second
Processing per batch: 10 seconds

150 new posts/hour:
- 15 batches × 10 seconds = 150 seconds (2.5 minutes)
- Plus overhead: +30 seconds (DB queries, parsing) = 3 minutes total

Peak (300 posts/hour):
- 30 batches × 10 seconds = 300 seconds (5 minutes)
- Plus overhead: +30 seconds = 5.5 minutes total
```

### Database Load

```
Query: Find 100-200 unsummarized posts
- Index on (summary, is_dead, is_deleted, is_crawl_success, created_at)
- Expected query time: <100ms

Update: Batch update 150 posts with summaries
- Using parameterized batch update
- Expected update time: <500ms

Index usage:
- Write operations per hour: ~150 updates (minimal)
- Read operations per hour: 1 scan (minimal)
- No transaction locks needed (batch updates separate)
```

---

## 9. Monitoring & Metrics

### Key Metrics to Track

```
Real-time:
- Posts summarized this hour
- API calls made
- Token usage (input/output)
- Processing time
- Error rate
- Cost accumulated

Historical:
- Posts per hour trend
- API failure rate
- Average summarization latency
- Cost per post
- Summary quality score (optional)
```

### Logging Strategy

```
Log Levels:
- INFO: Job started, completed, statistics
- WARNING: Batch failure, retry attempt, cost threshold
- ERROR: Crash, database error, critical failure
- DEBUG: Individual post processing, API calls

Log Format:
{
  "timestamp": "2026-02-14T15:30:45Z",
  "level": "INFO",
  "job": "HourlySummarizationJob",
  "event": "summarization_completed",
  "stats": {
    "posts_found": 150,
    "posts_summarized": 148,
    "posts_failed": 2,
    "duration_seconds": 187,
    "input_tokens": 75000,
    "output_tokens": 3700,
    "cost": 0.018
  }
}
```

---

## 10. Integration with Existing Systems

### With DeliveryPipeline

```
Current DeliveryPipeline:
  1. Load active users
  2. For each user:
     - Select posts created after user.last_delivered_at
     - Format message
     - Send to Telegram

With Summarization:
  1. Load active users
  2. For each user:
     - Select posts created after user.last_delivered_at
     - Filter for posts with summary != NULL ← NEW CHECK
     - Format message using summary
     - Send to Telegram

Change: Only 1 line change - filter for summary field
```

### With SelectPostsForDeliveryUseCase

```python
# Current logic
posts = Post.query.filter(
    Post.created_at > user.last_delivered_at
)

# New logic - add summary check
posts = Post.query.filter(
    Post.created_at > user.last_delivered_at,
    Post.summary.isnot(None)  # NEW: Only posts with summaries
)
```

### With Token Tracking

```python
# Existing AgentCall table tracks OpenAI usage
# For each summarization batch:

AgentCall.insert({
    user_id: NULL,  # Batch operation, not user-specific
    agent_name: "SummarizationAgent",
    model: "gpt-4o-mini",
    input_tokens: 75000,
    output_tokens: 3700,
    operation: "batch_hourly_summarization",
    metadata: {
        "batch_size": 10,
        "total_posts": 150,
        "posts_succeeded": 148,
        "posts_failed": 2,
        "prompt_type": "basic",
        "run_at": "2026-02-14T15:30:00Z"
    }
})
```

---

## 11. Fallback Strategies

### What if Summarization Falls Behind?

```
Scenario: 500 posts accumulated without summaries (2-hour backlog)

Option A: Accelerate (aggressive)
- Increase batch_size from 10 to 25
- Increase rate_limit from 1 to 2 RPS
- Run additional job at :45 minute mark

Option B: Prioritize (selective)
- Only summarize high-score posts (> 200 points)
- Skip low-engagement posts for now
- Catch up next hour with lower scores

Option C: Accept delay (conservative)
- Continue normal schedule
- Posts will be summarized eventually
- Users get older posts without summaries
```

### What if OpenAI API is Down?

```
Hour 1 (15:00):
- OpenAI API unavailable
- Log error, skip job
- No posts summarized

Hour 2 (16:00):
- Check API health first
- If still down: skip job
- Accumulated: 300 unsummarized posts

Hour 3 (17:00):
- API back online
- Run double batch size (20 posts at a time)
- Catch up on 300 posts over next 3 hours
```

---

## 12. Future Enhancements

### Phase 2 (After v1 Working)
- User-specific summarization (technical vs business summaries per user)
- Personalization based on user interests
- Summary quality scoring (LLM evaluates own summaries)
- Caching of summaries (deduplicate same content)
- A/B testing prompt templates

### Phase 3 (Optimization)
- GPU-based summarization (local model)
- Multi-language support
- Summary length preference per user
- Scheduled delivery at user-preferred times
- Analytics dashboard

### Phase 4 (Advanced)
- Incremental updates (update summary as post gets more discussion)
- Conversation threads (summarize comment threads too)
- Real-time delivery (push immediately on hot posts)
- ML-based priority ranking (which posts to summarize first)

---

## 13. Implementation Checklist (Not Doing Yet!)

```
Database Layer:
☐ Add columns to posts table
☐ Create indexes for query optimization
☐ Create summarization_runs tracking table

Business Logic:
☐ Create HourlySummarizationJob class
☐ Implement batch processing strategy
☐ Add retry logic for failed posts
☐ Add cost tracking

Integration:
☐ Register job with APScheduler at :15
☐ Update DeliveryPipeline to check summary field
☐ Add configuration class for settings

Testing:
☐ Unit tests for batch processing
☐ Integration tests with mock OpenAI API
☐ Load testing (simulate 1000+ posts)
☐ Error scenario testing

Monitoring:
☐ Add metrics tracking
☐ Create alerting for failures
☐ Add dashboard for statistics

Documentation:
☐ Update API documentation
☐ Create runbook for operations
☐ Add troubleshooting guide
```

---

## Summary

**Core Architecture:**
1. **HourlySummarizationJob** - Main job class running at :15 UTC
2. **Incremental Scanning** - Only process posts with summary=NULL
3. **Batch Processing** - Groups of 10-20 posts, 1 API call/second
4. **Error Recovery** - Retry failed posts up to 3 times
5. **Cost Tracking** - Monitor OpenAI API spend (~$5-10/month)

**Key Design Decisions:**
- Run at :15 (offset from :00 collection)
- Batch size: 10 posts default
- Rate limit: 1 call/second (respect OpenAI limits)
- Retry: Max 3 attempts per post
- Integration: Minimal changes to existing code

**Timeline:**
- Collected: Hour :00
- Summarized: Hour :15
- Delivered: Hour :30 (or next DeliveryPipeline run)

This design ensures scalable, cost-effective, automated summarization of all HN posts for the entire user base without re-summarizing or duplicating work.
