# Epic 2: Summarization & LLM Integration

**Epic ID:** EPIC-002
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 2 weeks (Sprint 2)
**Status:** In Progress ⏳
**Version:** 2.0 (Updated for HN Pal)

---

## Epic Goal

Build an AI-powered summarization system using OpenAI Agents SDK that generates high-quality 2-3 sentence summaries for HN posts, with observability via Langfuse and token tracking for cost management.

---

## Epic Description

### Product Vision Context

This epic delivers the core value proposition of HN Pal: transforming lengthy HN posts into concise, digestible summaries that users can read in seconds. The summarization system must:
- Generate consistent, high-quality summaries (≥80% pass rate on LLM-as-judge evaluation)
- Use OpenAI Agents SDK for structured, observable LLM interactions
- Track token usage and costs per user for billing/monitoring
- Process 200 posts/day in < 10 minutes
- Store summaries in PostgreSQL for fast retrieval

### What We're Building

A production-grade summarization pipeline that:
- **OpenAI Agents SDK** integration with Langfuse observability
- **SummarizationAgent** with structured outputs (Pydantic models)
- **Prompt engineering** with 5 variants (basic, technical, business, concise, personalized)
- **LLM-as-judge evaluation** to ensure ≥80% quality threshold
- **Token tracking** per-user in `user_token_usage` and `agent_calls` tables
- **Cost monitoring** with budget alerts (~$0.03/day for 200 posts with GPT-4o-mini)
- **Sequential processing** (optimize later if needed)

### Success Criteria

**Summary Quality:**
- LLM-as-judge evaluation: ≥80% pass rate (5 quality dimensions)
- User satisfaction: 4/5+ rating (beta feedback)
- Factual accuracy: No hallucinations or incorrect information
- Conciseness: 2-3 sentences (30-60 words)
- Information density: Captures key points without fluff

**Technical Performance:**
- Processing time: < 10 minutes for 200 posts (sequential)
- Summary generation: < 3 seconds per post average
- Token usage: ~500 tokens per summary (150 input + 350 output)
- Cost: ~$0.03/day for 200 posts with GPT-4o-mini
- Error rate: < 1% (handle LLM API failures gracefully)

**Observability:**
- All LLM calls tracked in Langfuse (traces, latency, costs)
- Token usage per-user aggregated daily (`user_token_usage` table)
- Agent call logs for debugging (`agent_calls` table)

---

## User Stories

### Story 2.1: OpenAI Agents SDK Integration ⏳

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-2.5-llm-client-integration.md`

**As a** developer
**I need** to integrate OpenAI Agents SDK with Langfuse observability
**So that** we can build reliable, traceable LLM-powered features

**Acceptance Criteria:**
- [ ] OpenAI Agents SDK installed and configured
- [ ] Langfuse integration working (public key, secret key, host)
- [ ] SummarizationAgent created with structured outputs (Pydantic)
- [ ] Token tracking per-user (`user_token_usage` table)
- [ ] Agent call logging (`agent_calls` table)
- [ ] Cost calculation logic (GPT-4o-mini pricing: $0.15/$0.60 per 1M tokens)
- [ ] Error handling for LLM API failures (retry 3x, log error)
- [ ] Basic usage example (summarize test post)

**Technical Notes:**
- **OpenAI Agents SDK:** Use `openai-agents` Python package
- **Langfuse:** Cloud-hosted observability (https://cloud.langfuse.com)
- **Pydantic Models:**
  ```python
  class Summary(BaseModel):
      summary_text: str  # 2-3 sentences
      key_points: List[str]  # 3-5 bullet points (optional)
      confidence: float  # 0.0-1.0 (model confidence)
  ```
- **Token Tracking:**
  - Per-call: `agent_calls` table (detailed logs)
  - Per-user daily: `user_token_usage` table (aggregated)
- **Cost Formula:**
  ```python
  cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending
- 🔄 Database tables defined in data-models.md

---

### Story 2.2: Summarization Prompt Engineering ⏳

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-2.3-summarization-prompt-engineering.md`

**As a** ML/data engineer
**I need** to design and test prompt variants for summarization
**So that** we generate high-quality, consistent summaries

**Acceptance Criteria:**
- [ ] 5 prompt variants designed:
  1. **basic** - General-purpose, 2-3 sentences with key insights
  2. **technical** - Deep technical details, architecture decisions
  3. **business** - Market impact, strategic insights
  4. **concise** - Ultra-brief, single sentence (30 words max)
  5. **personalized** - Tailored to user topics/style (future)
- [ ] Prompts stored in markdown files (`backend/app/infrastructure/prompts/`)
- [ ] LLM-as-judge evaluation implemented (5 quality dimensions)
- [ ] Test dataset created (5 diverse HN posts)
- [ ] Automated evaluation script (`scripts/evaluate_prompts.py`)
- [ ] ≥80% pass rate achieved (4/5 posts must score ≥80% per variant)
- [ ] Winning prompt(s) selected for production
- [ ] Git-based versioning for prompt history

**Technical Notes:**
- **LLM-as-Judge Evaluation:**
  - **Dimensions:** Factual accuracy (30%), info density (25%), clarity (15%), relevance (10%), length (20%)
  - **Scoring:** 0-100% per summary
  - **Pass Threshold:** ≥80% score per summary
  - **Approval:** ≥80% of summaries must pass (4/5 posts)
- **Test Dataset:**
  - 5 diverse HN posts: technical article, Show HN, Ask HN, research paper, blog post
  - Manual selection for variety
  - Store in `data/test_posts.json`
- **Prompt Storage:**
  ```
  backend/app/infrastructure/prompts/
  ├── summarizer.md          # Default (basic)
  ├── summarizer_technical.md
  ├── summarizer_business.md
  ├── summarizer_concise.md
  └── summarizer_personalized.md
  ```
- **Versioning:** Git history tracks prompt iterations

**Current State:**
- 📝 Activity document complete
- ✅ Initial prompt exists (`backend/app/infrastructure/services/prompts/summarizer.md`)
- 🔄 LLM-as-judge evaluation needs implementation
- 🔄 5 variants need design and testing

---

### Story 2.3: Basic Summarization Pipeline

**Status:** TO IMPLEMENT

**As a** system
**I need** to generate summaries for all crawled posts daily
**So that** users receive digestible content in Telegram digests

**Acceptance Criteria:**
- [ ] Read markdown content from RocksDB (or filesystem fallback)
- [ ] Generate 2-3 sentence summaries using SummarizationAgent
- [ ] Store summaries to PostgreSQL (`posts.summary`, `posts.summarized_at`)
- [ ] Handle different post types (story, Ask HN, Show HN)
- [ ] Sequential processing (one post at a time)
- [ ] Error handling:
  - LLM API failures → retry 3x, log error, skip post
  - Timeout → 30 seconds max per post
  - Rate limits → exponential backoff
- [ ] Skip already-summarized posts (`posts.summarized_at IS NOT NULL`)
- [ ] Integrate into pipeline orchestrator (Step 3: Summarize)
- [ ] Logging: posts processed, summaries generated, errors, timing

**Technical Notes:**
- **Input:** Read from RocksDB `markdown` column family (or filesystem)
- **Processing Logic:**
  ```python
  for post in posts_without_summary:
      markdown = rocksdb.get(f"{post.hn_id}", column_family="markdown")
      summary = summarization_agent.summarize(markdown)
      db.execute("UPDATE posts SET summary = ?, summarized_at = ? WHERE hn_id = ?",
                 summary, now(), post.hn_id)
  ```
- **Post Type Handling:**
  - **Story:** Standard summarization
  - **Ask HN:** Summarize question + top comments (if available)
  - **Show HN:** Summarize project description + purpose
- **Performance:** Sequential = ~3 sec/post × 200 posts = 10 minutes (acceptable)
- **Optimization (Future):** Parallel processing with asyncio (Sprint 2+ enhancement)

**Current State:**
- ✅ Standalone script exists (`scripts/run_summarization.py`)
- 🔄 Needs integration with OpenAI Agents SDK
- 🔄 Needs pipeline orchestrator integration

---

## Technical Stack

**LLM Integration:**
- `openai-agents` - Agent orchestration framework
- `langfuse` - LLM observability and tracing
- `tiktoken` - Token counting (OpenAI)
- `pydantic` - Structured outputs (data validation)

**Backend:**
- Python 3.11+ (async/await support)
- PostgreSQL (summary storage, token tracking)
- RocksDB or filesystem (markdown content input)
- APScheduler (pipeline integration)

**Models:**
- **Default:** GPT-4o-mini ($0.15 input / $0.60 output per 1M tokens)
- **Future:** GPT-4o (higher quality, 10x cost), Anthropic Claude (prompt caching)

**Deployment:**
- Local development: Direct API calls
- Production: Same (Vercel serverless or VM)

---

## Risks & Mitigation

### Risk 1: LLM API Costs Exceed Budget
**Risk:** Unexpected token usage spikes increase costs beyond $2-5/day
**Mitigation:**
- Use GPT-4o-mini by default (~$0.03/day for 200 posts)
- Daily cost tracking with alerts (if > $5/day, notify)
- Hard limits in code (max 500 summaries/day)
- Monitor Langfuse dashboard for cost trends
- Optimize prompts to reduce output tokens

### Risk 2: Prompt Quality Issues
**Risk:** Summaries are inaccurate, verbose, or miss key points
**Mitigation:**
- LLM-as-judge automated testing (≥80% pass rate required)
- Iterate on prompts until quality threshold met
- Beta user feedback loop (manual review of 20 summaries/week)
- A/B testing different prompt variants (track user engagement)

### Risk 3: Processing Time Too Slow
**Risk:** Sequential processing takes > 10 minutes (blocks pipeline)
**Mitigation:**
- Start with sequential (simple, works for 200 posts)
- Optimize later with parallel processing if needed (asyncio, batch 10 posts)
- Use faster model (GPT-4o-mini vs GPT-4o)
- Set timeout per post (30 seconds max)

### Risk 4: LLM API Reliability
**Risk:** OpenAI API downtime or rate limits
**Mitigation:**
- Retry logic (3 attempts with exponential backoff)
- Fallback: Skip post, log error, continue pipeline
- Consider multi-provider setup (OpenAI + Anthropic fallback)
- Monitor API status page (https://status.openai.com)

### Risk 5: Token Tracking Accuracy
**Risk:** Token counts incorrect → cost estimates wrong
**Mitigation:**
- Use `tiktoken` library for accurate counting
- Validate against OpenAI API response (compare estimated vs actual)
- Daily reconciliation (sum `agent_calls` tokens vs `user_token_usage`)
- Langfuse provides secondary validation (independent tracking)

---

## Dependencies

**External:**
- OpenAI API (GPT-4o-mini access)
- Langfuse Cloud (observability SaaS)
- PostgreSQL (for summary storage)
- RocksDB or filesystem (for markdown input)

**Internal:**
- Epic 1 (Ingest Pipeline) must be complete
- Markdown content must be available (RocksDB or filesystem)
- `posts` table must exist (`summary`, `summarized_at` columns)
- `user_token_usage` and `agent_calls` tables must exist

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] OpenAI Agents SDK integrated with Langfuse
- [ ] Token tracking operational (per-user usage)
- [ ] 5 prompt variants designed and tested
- [ ] LLM-as-judge evaluation passing (≥80%)
- [ ] Basic summarization pipeline working
- [ ] Summaries stored to PostgreSQL
- [ ] Cost monitoring functional (manual Langfuse check)
- [ ] Processing time < 10 minutes for 200 posts
- [ ] Error handling tested (API failures, timeouts)
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Summaries generated daily! 🎉

---

## Success Metrics (Post-Launch)

**Quality:**
- LLM-as-judge score: ≥80% pass rate (automated)
- User satisfaction: 4/5+ rating (manual survey)
- Factual accuracy: No hallucinations reported (manual review)
- Summary length: 30-60 words (2-3 sentences)

**Performance:**
- Processing time: < 10 minutes for 200 posts
- Summary generation: < 3 seconds per post average
- Error rate: < 1% (LLM API failures handled gracefully)

**Cost:**
- Daily cost: ~$0.03 for 200 posts (GPT-4o-mini)
- Monthly cost: ~$1 (very affordable)
- Token usage: ~500 tokens per summary (150 input + 350 output)

**Observability:**
- Langfuse dashboard shows all LLM calls with traces
- Token usage per-user tracked daily
- Agent call logs available for debugging

---

## Notes

- **Priority:** High-quality summaries are critical for user engagement
- **Prompt Engineering:** Invest time in iteration (quality > speed)
- **Cost Optimization:** GPT-4o-mini sufficient for MVP, upgrade to GPT-4o if quality issues
- **Observability:** Langfuse essential for debugging and cost tracking
- **Future Enhancement:** Parallel processing (asyncio) if sequential too slow
- **User Feedback:** Collect manual reviews of summaries (20/week) for quality validation

---

**Next Epic:** Epic 3 - Telegram Bot Foundation & Delivery
**Depends On:** Epic 1 (Ingest Pipeline), Epic 2 (Summarization)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
