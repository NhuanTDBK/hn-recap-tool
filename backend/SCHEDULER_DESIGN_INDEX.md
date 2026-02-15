# Summarization Scheduler - Complete Design Documentation

## Overview

This directory contains the complete brainstorm and design for the **Hourly Summarization Scheduler** that will automatically summarize new HackerNews posts for all users.

**Status**: 🧠 **BRAINSTORMING COMPLETE** - Ready for implementation

---

## Key Documents

### 1. **SCHEDULER_SUMMARY.txt** ⭐ START HERE
Quick reference guide with the essential architecture:
- Timing (how the scheduler works)
- Batch processing strategy
- Cost projections
- Integration impact
- How everything flows together

**Read this first** (5-10 min read)

### 2. **SUMMARIZATION_SCHEDULER_BRAINSTORM.md** 📋 DETAILED DESIGN
Comprehensive brainstorming document (2500+ lines):
- 13 detailed sections covering all aspects
- System architecture and data flow
- Database schema design
- Error handling strategies
- Configuration options
- Performance calculations
- Monitoring and metrics
- Implementation checklist

**Read this for deep understanding** (30 min read)

---

## Quick Start Architecture

### Three-Part Job Schedule (APScheduler)

```
:00 - HourlyPostsCollectorJob (existing)
      └─ Collect new posts from HN API
      └─ Store in PostgreSQL
      └─ Time: ~10-30 seconds

:15 - HourlySummarizationJob (NEW)
      └─ Find posts with summary=NULL
      └─ Batch summarize (10-20 posts/batch)
      └─ Rate limited: 1 API call/second
      └─ Time: ~2-5 minutes

:30 - DeliveryPipeline (existing)
      └─ Send digests to users
      └─ Filters for posts WITH summaries
      └─ Time: ~5-15 minutes
```

### How It Works (30-second version)

1. **Posts collected** at :00 (150 new posts/hour typical)
2. **Posts summarized** at :15 (batched, rate-limited)
3. **Users notified** at :30 (via existing DeliveryPipeline)
4. **Repeat hourly** (incremental, never re-summarize)

### Core Innovation: Incremental Scanning

Only process posts where `summary IS NULL` - ensures:
- ✅ No re-summarization (saves $)
- ✅ Efficient queries (fast with index)
- ✅ Simple error recovery (retry next hour)
- ✅ Natural backlog handling (catches up automatically)

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Schedule Offset** | :15 (not :00) | Avoid race condition with collection |
| **Batch Size** | 10 posts | Balance speed vs cost vs API limits |
| **Rate Limit** | 1 call/sec | Respect OpenAI's 60/min limit |
| **Max Retries** | 3 attempts | Balance coverage vs cost |
| **Error Strategy** | Continue on fail | Don't block entire job for one error |
| **Cost Tracking** | Per-batch | Monitor and control spending |
| **State Column** | `summary IS NULL` | Idempotent, no race conditions |

---

## Cost Analysis

### Monthly Budget

```
Typical Volume:    200 posts/hour × 24 = 4,800 posts/day
Pricing:           $0.00008 per post (gpt-4o-mini)
Daily Cost:        ~$0.38
Monthly Cost:      ~$11.52

Peak Volume:       400 posts/hour × 24 = 9,600 posts/day
Peak Cost:         ~$0.77/day = $23/month

Recommendation:    Set daily limit to $10/day (auto-disable if exceeded)
```

---

## Database Changes (Minimal)

### Add to `posts` table

```sql
summary TEXT,                      -- The summary text
summarized_at TIMESTAMP,           -- When summarized
summarization_status VARCHAR(20),  -- pending|completed|failed
summarization_error TEXT,          -- Error message
summarization_attempts INT         -- Retry counter

-- Add index for efficient queries
CREATE INDEX idx_posts_needs_summarization
ON posts(summary, is_dead, is_crawl_success, created_at);
```

### Track in existing `agent_calls` table
- Model: "SummarizationAgent"
- Operation: "batch_hourly_summarization"
- Tokens and costs for monitoring

---

## Implementation Phases (Not Started Yet!)

### Phase 1: Core Job Class (2-3 hours)
- Create `HourlySummarizationJob` class
- Implement batch processing
- Add retry logic

### Phase 2: Database (1 hour)
- Add columns to posts table
- Create indexes
- Add migration

### Phase 3: Integration (1-2 hours)
- Register with APScheduler at :15
- Update DeliveryPipeline filter
- Add configuration

### Phase 4: Testing (2-3 hours)
- Unit tests
- Integration tests
- Load testing

### Phase 5: Operations (1-2 hours)
- Monitoring setup
- Alerting rules
- Documentation

**Total Estimated Time**: 7-11 hours

---

## Example Execution Flow

### Hour 1

**:00** - Collection
```
HN API → 150 new posts
INSERT INTO posts (summary=NULL) × 150
Status: ✅ Complete (20 seconds)
```

**:15** - Summarization
```
SELECT * FROM posts WHERE summary IS NULL
Result: 150 posts found

Batch 1: posts 1-10
├─ Call SummarizationAgent.summarize(batch)
├─ Get back: [SummaryOutput, SummaryOutput, ...]
├─ UPDATE posts SET summary=..., summarization_status='completed'
├─ INSERT INTO agent_calls (tokens, cost)
└─ WAIT 10 seconds (rate limiting)

Batch 2: posts 11-20 (same process)
...
Batch 15: posts 141-150 (same process)

Result: 148 success, 2 failed
Status: ✅ Complete (150 seconds ≈ 2.5 min)
```

**:30** - Delivery
```
DeliveryPipeline.run()
├─ For each user:
│  ├─ Find posts WHERE created_at > user.last_delivered_at
│  ├─ Filter: WHERE summary IS NOT NULL ← NEW!
│  ├─ Format with summaries
│  └─ Send via Telegram
└─ Update user.last_delivered_at

Status: ✅ Complete (5-15 min)
```

### Hour 2

**:00** - Collection
```
Another 120 new posts
INSERT × 120
Status: ✅ Complete
```

**:15** - Summarization
```
SELECT * FROM posts WHERE summary IS NULL
Result: 120 new + 2 failed from hour 1 = 122 total

Process all 122 → 120 succeed, 2 still fail
Status: ✅ Complete
```

---

## Edge Cases & Fallbacks

### OpenAI API Down
- Skip job, retry next hour
- Retry double batch size to catch up
- **Result**: Eventual consistency, no data loss

### Backlog Accumulates
- Continue normal schedule
- Auto-scale batch size if needed
- **Result**: Catches up within 1-3 hours

### Cost Exceeds Budget
- Auto-disable summarization for that day
- Notify admin
- Resume next day
- **Result**: Budget protection

### Failed Posts
- Retry up to 3 times
- Mark as failed after 3 attempts
- Continue with new posts
- **Result**: No blocking, incremental progress

---

## Monitoring Checklist

Track these metrics hourly:
- [ ] Posts summarized count
- [ ] API calls made
- [ ] Input tokens used
- [ ] Output tokens used
- [ ] Cost accumulated
- [ ] Error count
- [ ] Processing time
- [ ] Backlog size

Alert on:
- [ ] Cost exceeds $0.50/hour
- [ ] Processing time > 10 minutes
- [ ] Error rate > 5%
- [ ] Backlog > 500 posts
- [ ] API failure (3+ consecutive)

---

## Integration with Existing Code

### Minimal Changes Required

**File**: `app/application/use_cases/delivery_selection.py`
```python
# Change from:
posts = session.query(Post).filter(Post.created_at > user.last_delivered_at)

# To:
posts = session.query(Post).filter(
    Post.created_at > user.last_delivered_at,
    Post.summary.isnot(None)  # ← Add this line
)
```

That's it! One line change.

---

## Configuration

### Environment Variables

```env
# Summarization Job Settings
SUMMARIZATION_ENABLED=true
SUMMARIZATION_BATCH_SIZE=10
SUMMARIZATION_MAX_ATTEMPTS=3
SUMMARIZATION_PROMPT_TYPE=basic

# Rate Limiting
SUMMARIZATION_RATE_LIMIT_RPS=1

# Cost Control
SUMMARIZATION_COST_LIMIT_DAILY=10.0
SUMMARIZATION_COST_LIMIT_MONTHLY=100.0
```

---

## FAQ

**Q: Why :15 and not :00?**
A: Avoid race condition. Posts collected at :00 need time to be stored. Summarization at :15 ensures posts are in DB.

**Q: What if summarization takes longer than 15 minutes?**
A: APScheduler will skip the next execution (max_instances=1). Next job runs at :30.

**Q: What if a post fails to summarize?**
A: It stays in the database with summary=NULL and status=pending. Retried next hour, up to 3 times.

**Q: Will users see old posts without summaries?**
A: Only if summarization falls behind. They'll see progressively more summarized posts as new hour cycles complete.

**Q: How much will this cost?**
A: ~$11-23/month depending on post volume. Use daily limit to cap at $10/day.

**Q: Can we summarize faster?**
A: Yes, by increasing batch size or rate limit. Trade-off: higher API cost, higher risk of rate limiting.

---

## Next Steps

When ready to implement:

1. Read the **SCHEDULER_SUMMARY.txt** (quick overview)
2. Read the **SUMMARIZATION_SCHEDULER_BRAINSTORM.md** (detailed design)
3. Follow the **Implementation Phases** checklist
4. Implement Phase 1-5 in order
5. Monitor with the metrics checklist

---

## Document Map

```
This Directory:
├── SCHEDULER_SUMMARY.txt (START HERE - 5 min)
├── SUMMARIZATION_SCHEDULER_BRAINSTORM.md (DEEP DIVE - 30 min)
├── SCHEDULER_DESIGN_INDEX.md (YOU ARE HERE)
│
Related Documents:
├── SUMMARIZATION_AGENT_TESTING.md (Testing results)
├── SUMMARIZATION_QUICK_START.md (Agent usage guide)
├── TEST_RESULTS_SUMMARY.txt (Test output)
│
Existing Code:
├── app/infrastructure/jobs/scheduler.py (Main scheduler)
├── app/infrastructure/jobs/hourly_posts_collector.py (Collection job)
├── app/application/use_cases/delivery_pipeline.py (Delivery pipeline)
└── app/infrastructure/agents/summarization_agent.py (Summarization)
```

---

## Summary

The **Summarization Scheduler** is a well-designed, cost-controlled system to automatically summarize HN posts hourly:

✅ **Efficient**: Incremental scanning, no re-work
✅ **Affordable**: ~$11/month typical cost
✅ **Reliable**: Error recovery, retry logic
✅ **Scalable**: Batch processing, rate limiting
✅ **Simple**: Minimal code changes needed
✅ **Monitorable**: Comprehensive metrics tracking

Ready for implementation! 🚀

