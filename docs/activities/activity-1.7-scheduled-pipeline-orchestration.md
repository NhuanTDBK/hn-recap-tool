# Activity 1.7: Scheduled Pipeline Orchestration with APScheduler

**Phase**: 1 - Ingest Pipeline
**Status**: 🔄 In Progress
**Owner**: Engineering Team
**Estimated Effort**: 3-4 hours

---

## Overview

Unify the currently separate CLI scripts into a single, scheduled pipeline orchestrator using APScheduler. The pipeline chains all ingest steps — HN polling, content crawling, summarization, synthesis, and Telegram delivery — into a reliable, automated daily job with proper error handling, step isolation, and observability.

**Current State:**
- ✅ APScheduler already integrated in `DataCollectorJob` (runs at midnight UTC)
- ✅ Individual scripts work standalone (`fetch_hn_posts.py`, `crawl_content.py`, `run_summarization.py`, `run_synthesis.py`, `push_to_telegram.py`)
- ❌ Scripts are disconnected — must be run manually in sequence
- ❌ No unified pipeline orchestration
- ❌ No step-level error isolation (one failure kills entire run)
- ❌ No run logging or observability

---

## Prerequisites

### Upstream Dependencies
- [x] **Activity 1.1**: HN API polling (provides posts)
- [x] **Activity 1.3**: URL crawler (generates content)
- [x] **Activity 1.5**: Content storage (RocksDB or filesystem)

### Required Libraries
- [x] `apscheduler` - Already installed, AsyncIOScheduler
- [x] `httpx` - HTTP client (already used)
- [ ] `structlog` (optional) - Structured logging for pipeline runs

---

## Objectives

1. **Unified Pipeline**: Chain all steps into a single orchestrated job
2. **Step Isolation**: Each step runs independently; failures don't kill the pipeline
3. **Configurable Schedule**: Easy to change timing via settings (not hardcoded)
4. **Run Logging**: Track each pipeline run with step-level status and timing
5. **Manual Trigger**: Keep ability to run pipeline on-demand via CLI
6. **Graceful Degradation**: Pipeline delivers what it can even if some steps fail

---

## Technical Details

### Architecture Decision: Why APScheduler

**Requirements:**
- Run Python async functions on a cron schedule
- Single process, single machine
- ~200 posts/day — trivial volume
- Sequential pipeline steps with error isolation

**APScheduler (Chosen):**
- ✅ Already in the codebase and working
- ✅ Native async/await support (`AsyncIOScheduler`)
- ✅ Cron triggers with timezone support
- ✅ Job persistence (optional, with job stores)
- ✅ Missed job handling (configurable)
- ✅ Zero infrastructure overhead (in-process)
- ✅ Simple API — add job, start, stop

**Alternatives Considered:**

| Option | Why Not |
|--------|---------|
| Airflow | Massive overkill — needs webserver, metadata DB, executor. Designed for data teams with dozens of ETL pipelines |
| Celery Beat | Requires Redis/RabbitMQ broker. Good if you need distributed workers, but this is a single-machine pipeline |
| Prefect/Dagster | Modern DAG runners but still heavyweight for a 5-step sequential pipeline |
| System cron | No Python-native error handling, no async support, harder to test |
| Vercel Cron | Platform lock-in, cold starts, 10s execution limit on hobby tier |

**Bottom Line:** APScheduler is the right tool for a single-process, single-machine pipeline running a few async Python functions on a schedule. Move to Celery Beat only if you later need distributed workers or multi-machine execution.

### Pipeline Design

**Pipeline Steps (Sequential):**

```
┌─────────────────────────────────────────────────────────────┐
│ PIPELINE RUN (triggered by APScheduler or manual CLI)       │
│                                                              │
│  Step 1: COLLECT                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Fetch front page posts from HN Algolia API          │    │
│  │ Save to JSONL: data/raw/{date}-posts.jsonl          │    │
│  │ Output: List[Post] (20-30 posts)                    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ posts                              │
│                         ▼                                    │
│  Step 2: CRAWL                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ For each post with external URL:                    │    │
│  │   • Fetch HTML (rate-limited, concurrent=3)         │    │
│  │   • Extract text with trafilatura                   │    │
│  │   • Save to data/content/{html,text}/               │    │
│  │ Skip already-crawled posts                          │    │
│  │ Output: CrawlStats {successful, failed, skipped}    │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ posts with content                 │
│                         ▼                                    │
│  Step 3: SUMMARIZE                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ For each post with text content:                    │    │
│  │   • Generate 2-4 sentence summary via OpenAI        │    │
│  │   • Map-reduce for long articles (>8K chars)        │    │
│  │   • Save to data/processed/summaries/               │    │
│  │ Output: List[Summary] with JSONL + Markdown files   │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ summaries                          │
│                         ▼                                    │
│  Step 4: SYNTHESIZE                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Generate cross-article synthesis from all summaries │    │
│  │ Identify themes, patterns, connections              │    │
│  │ Save to data/processed/synthesis/                   │    │
│  │ Output: Synthesis markdown file                     │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │ synthesis + summaries               │
│                         ▼                                    │
│  Step 5: DELIVER                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Send individual summaries to Telegram channel       │    │
│  │ Each post = one message (title + summary + links)   │    │
│  │ Rate-limited (0.5s between messages)                │    │
│  │ Output: DeliveryStats {sent, failed}                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  PIPELINE RESULT: PipelineRunReport                         │
│  • Total duration                                           │
│  • Per-step status (success/failed/skipped)                 │
│  • Per-step timing                                          │
│  • Error details for failed steps                           │
│  • Posts collected / crawled / summarized / delivered        │
└─────────────────────────────────────────────────────────────┘
```

**Error Isolation Strategy:**

Each step is wrapped in try/except. A failed step logs the error and the pipeline continues with whatever data is available:

```
Step 1 fails → Pipeline aborts (no data to process)
Step 2 fails → Continue with uncrawled posts (summaries will be shorter)
Step 3 fails → Continue without summaries (deliver titles only)
Step 4 fails → Continue without synthesis (still deliver individual summaries)
Step 5 fails → Log error, summaries still saved to disk for manual push
```

### Data Flow Between Steps

```
Step 1 (Collect) → List[Post]
    ↓ passed in memory + saved to JSONL
Step 2 (Crawl) → CrawlStats + content files on disk
    ↓ posts enriched with content paths
Step 3 (Summarize) → List[Summary] + JSONL file
    ↓ summaries passed in memory + saved to disk
Step 4 (Synthesize) → synthesis markdown string
    ↓ synthesis passed in memory + saved to disk
Step 5 (Deliver) → DeliveryStats
    ↓ messages sent to Telegram
```

### Configuration

Add these settings to `Settings` class:

```python
# Pipeline Schedule
pipeline_schedule_hour: int = 7          # Run at 7 AM
pipeline_schedule_minute: int = 0
pipeline_schedule_timezone: str = "UTC"
pipeline_enabled: bool = True

# Pipeline Steps (toggle individual steps)
pipeline_step_collect: bool = True
pipeline_step_crawl: bool = True
pipeline_step_summarize: bool = True
pipeline_step_synthesize: bool = True
pipeline_step_deliver: bool = True

# Telegram Delivery
telegram_bot_token: Optional[str] = None
telegram_channel_id: Optional[str] = None
telegram_enabled: bool = False
```

---

## Implementation Overview

### Core Components

**1. PipelineOrchestrator Class**
- Location: `backend/app/infrastructure/jobs/pipeline_orchestrator.py`
- Responsibility: Chain pipeline steps with error isolation
- Key Methods:
  - `run()` — Execute full pipeline
  - `run_step(step_name, step_fn)` — Execute single step with timing and error handling
  - `get_last_run_report()` — Return report from most recent run

**2. PipelineRunReport Data Class**
- Location: `backend/app/domain/value_objects.py`
- Fields:
  - `run_id: str` — UUID for this run
  - `started_at: datetime`
  - `completed_at: datetime`
  - `duration_seconds: float`
  - `steps: List[StepResult]` — Per-step results
  - `overall_status: str` — success / partial / failed

**3. StepResult Data Class**
- Fields:
  - `name: str` — Step name (collect, crawl, summarize, synthesize, deliver)
  - `status: str` — success / failed / skipped
  - `started_at: datetime`
  - `duration_seconds: float`
  - `error: Optional[str]`
  - `metrics: Dict` — Step-specific metrics (posts_collected, articles_crawled, etc.)

**4. Updated DataCollectorJob**
- Refactor existing `DataCollectorJob` to use `PipelineOrchestrator`
- Keep APScheduler integration as-is
- Add configurable schedule from settings

### Pipeline Orchestrator Design

```python
class PipelineOrchestrator:
    """Orchestrates the full ingest → summarize → deliver pipeline."""

    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps
        self.last_run_report = None

    async def run(self) -> PipelineRunReport:
        """Execute all pipeline steps sequentially."""
        report = PipelineRunReport(run_id=str(uuid4()))
        context = {}  # Shared data between steps

        for step in self.steps:
            if not step.enabled:
                report.add_step(StepResult(name=step.name, status="skipped"))
                continue

            result = await self._run_step(step, context)
            report.add_step(result)

            # Abort on critical step failure (collect)
            if result.status == "failed" and step.critical:
                logger.error(f"Critical step '{step.name}' failed, aborting pipeline")
                break

        report.complete()
        self.last_run_report = report
        return report

    async def _run_step(self, step, context) -> StepResult:
        """Execute a single step with error isolation and timing."""
        result = StepResult(name=step.name)
        try:
            metrics = await step.execute(context)
            result.succeed(metrics)
        except Exception as e:
            logger.error(f"Step '{step.name}' failed: {e}", exc_info=True)
            result.fail(str(e))
        return result
```

### PipelineStep Interface

```python
class PipelineStep:
    """Base class for pipeline steps."""

    def __init__(self, name: str, enabled: bool = True, critical: bool = False):
        self.name = name
        self.enabled = enabled
        self.critical = critical  # If True, pipeline aborts on failure

    async def execute(self, context: dict) -> dict:
        """Execute the step. Returns metrics dict.

        Args:
            context: Shared dict for passing data between steps.
                     Steps write their output here for downstream steps.
        Returns:
            Metrics dict (e.g., {"posts_collected": 25})
        """
        raise NotImplementedError
```

### Step Implementations

**CollectStep** (critical=True):
```python
class CollectStep(PipelineStep):
    async def execute(self, context):
        posts = await self.collect_use_case.execute(limit=settings.hn_max_posts)
        context["posts"] = posts
        context["date"] = datetime.utcnow().strftime('%Y-%m-%d')
        return {"posts_collected": len(posts)}
```

**CrawlStep** (critical=False):
```python
class CrawlStep(PipelineStep):
    async def execute(self, context):
        posts = context.get("posts", [])
        stats = {"successful": 0, "failed": 0, "skipped": 0}
        for post in posts:
            if post.has_external_url():
                try:
                    await self.crawl_use_case.execute(post)
                    stats["successful"] += 1
                except Exception:
                    stats["failed"] += 1
            else:
                stats["skipped"] += 1
        return stats
```

**SummarizeStep** (critical=False):
```python
class SummarizeStep(PipelineStep):
    async def execute(self, context):
        date = context.get("date")
        summaries = await self.summarize_use_case.execute(date=date)
        context["summaries"] = summaries
        return {"posts_summarized": len(summaries)}
```

**SynthesizeStep** (critical=False):
```python
class SynthesizeStep(PipelineStep):
    async def execute(self, context):
        posts = context.get("posts", [])
        synthesis = await self.synthesis_service.synthesize(posts)
        context["synthesis"] = synthesis
        return {"synthesis_length": len(synthesis)}
```

**DeliverStep** (critical=False):
```python
class DeliverStep(PipelineStep):
    async def execute(self, context):
        summaries = context.get("summaries", [])
        sent = await self.telegram_notifier.send_summary_details(summaries)
        return {"messages_sent": len(summaries) if sent else 0}
```

---

## Schedule Configuration

### Default Schedule

```python
# Run daily at 7:00 AM UTC
trigger = CronTrigger(
    hour=settings.pipeline_schedule_hour,
    minute=settings.pipeline_schedule_minute,
    timezone=settings.pipeline_schedule_timezone,
)
```

### Schedule Options

| Schedule | Cron Expression | Use Case |
|----------|----------------|----------|
| Daily 7 AM UTC | `hour=7, minute=0` | Default — morning digest |
| Every 2 hours | `hour='*/2'` | Frequent updates (higher API cost) |
| Twice daily | `hour='7,19'` | Morning + evening digest |
| Weekdays only | `day_of_week='mon-fri', hour=7` | Work-focused digest |

### Missed Run Handling

```python
scheduler.add_job(
    pipeline.run,
    trigger=trigger,
    id="hn_digest_pipeline",
    name="HN Digest Pipeline",
    replace_existing=True,
    misfire_grace_time=3600,  # Allow 1 hour late execution
    coalesce=True,            # Merge missed runs into one
)
```

---

## CLI Interface

### Unified Pipeline CLI

Create `scripts/run_pipeline.py` for manual execution:

```
Usage:
    python scripts/run_pipeline.py                      # Run full pipeline
    python scripts/run_pipeline.py --steps collect,crawl # Run specific steps
    python scripts/run_pipeline.py --skip-deliver        # Skip Telegram delivery
    python scripts/run_pipeline.py --date 2025-02-10     # Process specific date
    python scripts/run_pipeline.py --dry-run             # Show what would run
```

### CLI Arguments

```
--steps         Comma-separated list of steps to run (default: all)
--skip-deliver  Skip Telegram delivery (useful for testing)
--date          Process a specific date instead of today
--dry-run       Show pipeline plan without executing
--verbose       Enable debug logging
```

---

## Run Logging & Observability

### Pipeline Run Log

Save run reports to `data/pipeline_runs/`:

```
data/pipeline_runs/
├── 2025-02-13-070000-run.json
├── 2025-02-12-070000-run.json
└── ...
```

**Run Report Schema:**
```json
{
  "run_id": "a1b2c3d4",
  "started_at": "2025-02-13T07:00:00Z",
  "completed_at": "2025-02-13T07:04:23Z",
  "duration_seconds": 263,
  "overall_status": "success",
  "steps": [
    {
      "name": "collect",
      "status": "success",
      "duration_seconds": 3.2,
      "metrics": {"posts_collected": 28}
    },
    {
      "name": "crawl",
      "status": "success",
      "duration_seconds": 85.4,
      "metrics": {"successful": 22, "failed": 3, "skipped": 3}
    },
    {
      "name": "summarize",
      "status": "success",
      "duration_seconds": 120.1,
      "metrics": {"posts_summarized": 22}
    },
    {
      "name": "synthesize",
      "status": "success",
      "duration_seconds": 8.7,
      "metrics": {"synthesis_length": 2450}
    },
    {
      "name": "deliver",
      "status": "success",
      "duration_seconds": 45.6,
      "metrics": {"messages_sent": 22}
    }
  ]
}
```

### Console Output

```
2025-02-13 07:00:00 - pipeline - INFO - ══════════════════════════════════════════
2025-02-13 07:00:00 - pipeline - INFO - HN DIGEST PIPELINE STARTED (run: a1b2c3d4)
2025-02-13 07:00:00 - pipeline - INFO - ══════════════════════════════════════════
2025-02-13 07:00:00 - pipeline - INFO - [1/5] collect ── Starting...
2025-02-13 07:00:03 - pipeline - INFO - [1/5] collect ── ✓ Done (3.2s) — 28 posts collected
2025-02-13 07:00:03 - pipeline - INFO - [2/5] crawl ── Starting...
2025-02-13 07:01:28 - pipeline - INFO - [2/5] crawl ── ✓ Done (85.4s) — 22 crawled, 3 failed, 3 skipped
2025-02-13 07:01:28 - pipeline - INFO - [3/5] summarize ── Starting...
2025-02-13 07:03:28 - pipeline - INFO - [3/5] summarize ── ✓ Done (120.1s) — 22 posts summarized
2025-02-13 07:03:28 - pipeline - INFO - [4/5] synthesize ── Starting...
2025-02-13 07:03:37 - pipeline - INFO - [4/5] synthesize ── ✓ Done (8.7s) — synthesis: 2450 chars
2025-02-13 07:03:37 - pipeline - INFO - [5/5] deliver ── Starting...
2025-02-13 07:04:23 - pipeline - INFO - [5/5] deliver ── ✓ Done (45.6s) — 22 messages sent
2025-02-13 07:04:23 - pipeline - INFO - ══════════════════════════════════════════
2025-02-13 07:04:23 - pipeline - INFO - PIPELINE COMPLETE — 4m 23s — status: SUCCESS
2025-02-13 07:04:23 - pipeline - INFO - ══════════════════════════════════════════
```

---

## Integration with FastAPI

### Startup Integration

The pipeline integrates with `main.py` lifespan exactly as the current `DataCollectorJob`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing setup ...

    # Initialize pipeline orchestrator
    pipeline = PipelineOrchestrator(steps=[
        CollectStep("collect", critical=True, ...),
        CrawlStep("crawl", ...),
        SummarizeStep("summarize", ...),
        SynthesizeStep("synthesize", ...),
        DeliverStep("deliver", enabled=settings.telegram_enabled, ...),
    ])

    # Schedule pipeline
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        pipeline.run,
        trigger=CronTrigger(
            hour=settings.pipeline_schedule_hour,
            minute=settings.pipeline_schedule_minute,
            timezone=settings.pipeline_schedule_timezone,
        ),
        id="hn_digest_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown()
```

### API Endpoints (Optional)

```python
# Manual trigger
POST /api/pipeline/run

# Last run status
GET /api/pipeline/status

# Run history
GET /api/pipeline/history?limit=10
```

---

## Testing & Validation

### Manual Testing

**Run Full Pipeline:**
```bash
python scripts/run_pipeline.py
```

**Run Specific Steps:**
```bash
python scripts/run_pipeline.py --steps collect,crawl
```

**Dry Run:**
```bash
python scripts/run_pipeline.py --dry-run
```

### Validation Checklist

- [ ] Pipeline runs all 5 steps in order
- [ ] Failed step does not crash subsequent steps
- [ ] Critical step failure (collect) aborts pipeline
- [ ] Run report saved to `data/pipeline_runs/`
- [ ] Run report includes per-step timing and metrics
- [ ] Schedule works via APScheduler (test with short interval)
- [ ] Manual CLI trigger works
- [ ] `--skip-deliver` flag works
- [ ] Pipeline handles missing env vars gracefully (e.g., no Telegram token)
- [ ] Logs are clear and show step progress

---

## Acceptance Criteria

- [ ] `PipelineOrchestrator` class implemented with step isolation
- [ ] All 5 steps (collect, crawl, summarize, synthesize, deliver) wired up
- [ ] APScheduler triggers pipeline on configurable schedule
- [ ] Pipeline run reports saved as JSON with per-step metrics
- [ ] CLI script `scripts/run_pipeline.py` supports manual execution
- [ ] Failed steps log errors and pipeline continues
- [ ] Critical step (collect) failure aborts pipeline
- [ ] Settings control schedule, step toggles, and Telegram delivery
- [ ] Existing standalone scripts still work independently
- [ ] Console output shows clear step-by-step progress

---

## Migration from Current State

### What Changes

1. **`DataCollectorJob`** — Refactored to use `PipelineOrchestrator` internally
2. **`main.py`** — Updated lifespan to use new pipeline setup
3. **`settings.py`** — Add pipeline schedule and step toggle settings
4. **`value_objects.py`** — Add `PipelineRunReport` and `StepResult`

### What Stays the Same

- All standalone scripts (`fetch_hn_posts.py`, `crawl_content.py`, etc.) remain functional
- APScheduler remains the scheduler
- No new infrastructure dependencies
- Same JSONL/filesystem storage

### Migration Steps

1. Create `PipelineOrchestrator` and step classes
2. Create `PipelineRunReport` value objects
3. Add settings for schedule and step toggles
4. Refactor `DataCollectorJob` to delegate to orchestrator
5. Create `scripts/run_pipeline.py` CLI
6. Update `main.py` lifespan
7. Test full pipeline run
8. Test individual step failures

---

## Performance Characteristics

**Typical Pipeline Run:**

| Step | Duration | Notes |
|------|----------|-------|
| Collect | 2-5s | Single API call to HN Algolia |
| Crawl | 60-120s | 20-25 URLs, 3 concurrent, rate-limited |
| Summarize | 90-180s | 20-25 posts via OpenAI API (concurrent) |
| Synthesize | 5-15s | Single OpenAI API call |
| Deliver | 30-60s | 20-25 Telegram messages, 0.5s delay each |
| **Total** | **3-6 min** | |

**Resource Usage:**
- CPU: Minimal (mostly I/O wait)
- Memory: ~100-200 MB (post data + content in memory)
- Network: ~50-100 API calls (HN + OpenAI + Telegram)
- Cost: ~$0.05-0.10/day for OpenAI API (gpt-4o-mini)

---

## Future Enhancements

**When to upgrade from APScheduler:**
- You need distributed workers across multiple machines → **Celery Beat**
- You need a DAG UI with retries and backfills → **Prefect or Dagster**
- You deploy to serverless → **Platform-native cron** (Vercel, Railway, etc.)

**Potential improvements:**
- Add retry logic per step (e.g., retry crawl 2x before marking failed)
- Add health check endpoint that reports pipeline status
- Add Telegram notification on pipeline failure
- Add pipeline metrics to a dashboard (Grafana, etc.)
- Add backfill mode: process a date range of missed days

---

## Related Activities

**Upstream Dependencies:**
- ✅ Activity 1.1: HN API polling (provides `CollectStep`)
- ✅ Activity 1.3: URL crawler (provides `CrawlStep`)
- ✅ Activity 1.5: Content storage (provides storage backend for crawl)

**Downstream Dependencies:**
- Activity 2.1: Summarization (provides `SummarizeStep`)
- Activity 3.x: Telegram bot (provides `DeliverStep`)

**Related Files:**
- `backend/app/infrastructure/jobs/data_collector.py` — Current scheduler (to refactor)
- `backend/app/infrastructure/jobs/pipeline_orchestrator.py` — New orchestrator
- `backend/app/main.py` — FastAPI lifespan integration
- `backend/app/infrastructure/config/settings.py` — Pipeline settings
- `scripts/run_pipeline.py` — CLI entry point
- `scripts/fetch_hn_posts.py` — Standalone collect script (unchanged)
- `scripts/crawl_content.py` — Standalone crawl script (unchanged)
- `scripts/run_summarization.py` — Standalone summarize script (unchanged)
- `scripts/run_synthesis.py` — Standalone synthesis script (unchanged)
- `scripts/push_to_telegram.py` — Standalone delivery script (unchanged)

---

## Notes & Assumptions

**Design Decisions:**

1. **Why sequential, not parallel steps?**
   Each step depends on the previous step's output. Collect → Crawl → Summarize is inherently sequential. Parallelism happens *within* steps (concurrent crawling, concurrent summarization).

2. **Why keep standalone scripts?**
   They're useful for development, debugging, and ad-hoc runs. The pipeline orchestrator composes the same logic, it doesn't replace it.

3. **Why not a task queue (Celery)?**
   Single machine, single writer, ~5 minute total runtime. A task queue adds infrastructure complexity (broker, worker processes) with no benefit at this scale.

4. **Why save run reports to disk?**
   Simple, no database needed. If you later add PostgreSQL, you can migrate run reports there. For now, JSON files in `data/pipeline_runs/` are easy to inspect and debug.

---

**Last Updated:** 2025-02-13
