# Epic 6: Memory System & MVP Polish

**Epic ID:** EPIC-006
**Priority:** P1 - Nice-to-have (MVP Enhancement)
**Timeline:** 2 weeks (Sprint 6)
**Status:** Documented 📝
**Version:** 2.0 (HN Pal)

---

## Epic Goal

Implement memory extraction for personalization and polish the MVP for beta launch - adding intelligence that learns user preferences over time while ensuring a smooth, bug-free experience for external users.

---

## Epic Description

### Product Vision Context

This epic adds the "intelligence" layer to HN Pal: a memory system that learns from user interactions (discussions, reactions, saves) to personalize future conversations and digests. Additionally, this sprint focuses on polishing the entire product for beta launch - fixing bugs, optimizing performance, and creating documentation. The memory system must:
- Extract insights from discussions automatically (post-discussion)
- Batch extract interests from daily reactions (implicit signals)
- Allow users to manage their memory (/memory commands)
- Surface memory in future discussions (context injection)
- Track and display token usage (/token command)

### What We're Building

**Memory System:**
- **MemoryExtractionAgent** using OpenAI Agents SDK
- **Post-discussion extraction** (topics, opinions, connections)
- **Daily batch extraction** (interests from reactions, saves, skips)
- **Memory management commands** (/memory, /memory pause, /memory forget, /memory clear)
- **Token usage command** (/token shows daily/total costs)
- **Confidence scoring** (0.0-1.0 for implicit extractions)

**MVP Polish:**
- End-to-end testing with 5 internal users
- Bug fixes (all critical, high-priority)
- Performance optimization (context loading, LLM calls)
- UX improvements (message formatting, error messages)
- Documentation (user guide, bot commands reference)
- Monitoring setup (Langfuse, error tracking)
- Production deployment (webhook mode on Vercel)
- Beta launch (10-20 external users)

### Success Criteria

**Memory Quality:**
- Extraction accuracy: > 80% (manual review)
- Confidence scoring: Correlates with quality (high confidence → accurate)
- User satisfaction: 4/5+ (memory feels helpful, not creepy)

**Memory Usage:**
- Memory surfaced in discussions: > 50% of conversations reference user context
- /memory command usage: > 30% of users
- Memory opt-out rate: < 10%

**MVP Quality:**
- Zero critical bugs at launch
- Performance targets met (see sprint-plan.md)
- User onboarding smooth (< 2 minutes)
- Documentation complete and clear
- Beta users satisfied: 4/5+ rating

---

## User Stories

### Story 6.1: Post-Discussion Memory Extraction ⏳

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-6.0-memory-system.md` (Sub-activities 6.2-6.3)

**As a** system
**I need** to extract insights from discussions automatically
**So that** future conversations are personalized to user interests and context

**Acceptance Criteria:**
- [ ] Create MemoryExtractionAgent using OpenAI Agents SDK:
  - Model: GPT-4o-mini
  - Structured output: `List[MemoryCreate]` (Pydantic model)
  - Prompt: Extract topics, opinions, connections, work context
- [ ] Trigger extraction when discussion ends:
  - On auto-switch (user taps Discuss on another post)
  - On timeout (30 min inactivity)
  - On manual end (future: /end_discussion command)
- [ ] Extract memory categories:
  - **interest** - Topics user engaged with (e.g., "Distributed systems")
  - **opinion** - User's stance on topics (e.g., "Skeptical of microservices hype")
  - **work_context** - Professional info (e.g., "Building search with PostgreSQL")
  - **personal_context** - Hobbies, side projects (e.g., "Learning Rust")
  - **connection** - Links to past discussions (e.g., "Related to previous Raft consensus discussion")
- [ ] Store memory to `memory` table:
  - Fields: `user_id`, `type`, `content`, `source_type = "discussion"`, `source_conversation_id`, `confidence = 1.0` (explicit)
- [ ] Handle explicit capture:
  - Detect "remember this" triggers in user messages
  - Extract immediately (don't wait for discussion end)
  - Store with `source_type = "explicit"`, `confidence = 1.0`
- [ ] Confidence scoring (for future implicit extraction):
  - 1.0 = Explicit statement from user
  - 0.8-0.9 = Strong inference from discussion
  - 0.6-0.7 = Weak inference from reactions
  - < 0.6 = Don't store (too uncertain)
- [ ] Deduplication:
  - Check if similar memory exists (fuzzy match on content)
  - If exists → update confidence, don't create duplicate
  - If new → create new entry
- [ ] Error handling:
  - Extraction failure → Log error, skip (non-blocking)
  - DB write failure → Retry 3x, log error
- [ ] Logging: memories extracted, types, confidence scores

**Technical Notes:**
- **MemoryExtractionAgent:**
  ```python
  from openai_agents import Agent
  from pydantic import BaseModel

  class MemoryCreate(BaseModel):
      type: str  # "interest", "opinion", "work_context", etc.
      content: str
      confidence: float

  class MemoryExtraction(BaseModel):
      memories: List[MemoryCreate]

  memory_agent = Agent(
      model="gpt-4o-mini",
      system_prompt="""Extract user insights from this conversation.
      Identify interests, opinions, work context, and connections to other topics.
      Only extract confident insights (confidence > 0.8).""",
      response_model=MemoryExtraction
  )
  ```
- **Extraction Trigger:**
  ```python
  async def end_discussion(user_id: int, conversation_id: int):
      conversation = get_conversation(conversation_id)

      # Extract memory
      extraction = await memory_agent.extract(conversation.messages)

      # Store to DB
      for mem in extraction.memories:
          create_memory(
              user_id=user_id,
              type=mem.type,
              content=mem.content,
              source_type="discussion",
              source_conversation_id=conversation_id,
              confidence=mem.confidence
          )

      # Mark conversation ended
      conversation.ended_at = now()
      db.commit()
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 6.2: Daily Batch Memory Extraction ⏳

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-6.0-memory-system.md` (Sub-activity 6.2)

**As a** system
**I need** to extract interests from daily user interactions
**So that** implicit signals (reactions, saves) inform personalization

**Acceptance Criteria:**
- [ ] Daily pipeline step (Step 6: Memory):
  - Run at 23:00 UTC (after digest delivery)
  - Process all users with `memory_enabled = true`
- [ ] Read user interactions from past 24 hours:
  - Query `deliveries` table: `WHERE user_id = ? AND delivered_at > now() - interval '24 hours'`
  - Extract signals:
    - **Upvotes** (`reaction = 'up'`) → Positive interest
    - **Downvotes** (`reaction = 'down'`) → Negative signal (skip or low confidence)
    - **Saves** (`is_saved = true`) → Strong interest
    - **Skips** (no reaction, no save, no discuss) → Weak negative signal
- [ ] Extract implicit interests via LLM:
  - Prompt: "Based on these posts the user engaged with, what are their interests?"
  - Input: Post titles + domains + upvotes/saves
  - Output: `List[MemoryCreate]` with interests
- [ ] Store to `memory` table:
  - `source_type = "daily_batch"`
  - `confidence = 0.6-0.8` (implicit extraction)
  - `created_at = now()`
- [ ] Aggregate duplicate entries:
  - If interest already exists → Increase confidence (max 1.0)
  - If new → Create new entry
- [ ] Run for all active users:
  - Batch process (10 users at a time)
  - Total processing time: < 30 minutes for 100 users
- [ ] Logging: users processed, memories extracted, errors

**Technical Notes:**
- **Batch Processing:**
  ```python
  async def daily_batch_memory_extraction():
      users = get_users(memory_enabled=True, status='active')

      for user in users:
          # Get interactions from past 24 hours
          deliveries = get_deliveries(user.id, since=now() - timedelta(days=1))

          upvoted_posts = [d.post for d in deliveries if d.reaction == 'up']
          saved_posts = [d.post for d in deliveries if d.is_saved]

          # Extract interests
          interests = await memory_agent.extract_interests(upvoted_posts + saved_posts)

          # Store to DB
          for interest in interests:
              create_or_update_memory(
                  user_id=user.id,
                  type="interest",
                  content=interest.content,
                  source_type="daily_batch",
                  confidence=interest.confidence
              )
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 6.3: Memory Management Commands ⏳

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-6.0-memory-system.md` (Sub-activity 6.6)

**As a** user
**I want** to view and manage my memory
**So that** I have control over what the bot remembers about me

**Acceptance Criteria:**
- [ ] Implement `/memory` command:
  - Query `memory` table: `WHERE user_id = ? AND active = true ORDER BY type, created_at DESC`
  - Display in categorized format:
    ```
    🧠 Your Memory (12 entries)

    📚 Interests (5)
    • Distributed systems
    • PostgreSQL performance
    • Rust programming

    💼 Work Context (3)
    • Building search engine with PostgreSQL
    • Team of 5 engineers
    • Startup environment

    💭 Opinions (2)
    • Skeptical of microservices hype
    • Prefers simple solutions

    🔗 Connections (2)
    • Related to previous Raft consensus discussion
    • Related to previous CockroachDB pricing discussion

    Manage: /memory pause | /memory forget | /memory clear
    ```
  - Pagination if > 20 entries (inline buttons: « Previous | Next »)
- [ ] Implement `/memory pause` command:
  - Toggle `users.memory_enabled` flag
  - If paused → Show: "Memory paused. Extraction disabled. Use /memory pause again to resume."
  - If resumed → Show: "Memory resumed. Learning from your interactions again!"
- [ ] Implement `/memory forget` command:
  - Interactive selection (inline buttons for each memory entry)
  - Tap entry → Set `memory.active = false` (soft delete)
  - Confirmation: "Forgot: {content}"
- [ ] Implement `/memory clear` command:
  - Confirmation dialog (inline buttons: Confirm | Cancel)
  - If confirmed → Set `active = false` for all user memories
  - Message: "All memory cleared. Starting fresh!"
- [ ] Display memory in categorized format (group by type)
- [ ] Handle empty memory:
  - "You don't have any memory yet. Chat with me about posts and I'll learn your interests!"
- [ ] Error handling:
  - DB query failure → "Error loading memory. Try again?"
  - No permission → (Not applicable, all users can manage own memory)

**Technical Notes:**
- **Command Handlers:**
  ```python
  @router.message(Command("memory"))
  async def memory_handler(message: Message):
      memories = get_active_memories(message.from_user.id)

      if not memories:
          await message.answer("You don't have any memory yet...")
          return

      # Group by type
      grouped = group_by_type(memories)

      # Format message
      text = "🧠 Your Memory ({} entries)\n\n".format(len(memories))
      for type, items in grouped.items():
          text += f"{type_emoji(type)} {type.title()} ({len(items)})\n"
          for item in items[:3]:  # Show first 3
              text += f"• {item.content}\n"
          text += "\n"

      text += "Manage: /memory pause | /memory forget | /memory clear"

      await message.answer(text)
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 6.4: Token Usage Command ⏳

**Status:** DOCUMENTED

**As a** user
**I want** to see my LLM usage and costs
**So that** I understand how much I'm using the AI features

**Acceptance Criteria:**
- [ ] Implement `/token` command
- [ ] Query `user_token_usage` table:
  - Today's usage: `WHERE user_id = ? AND date = current_date`
  - Total usage: `SUM(total_input_tokens), SUM(total_output_tokens), SUM(total_cost_usd) WHERE user_id = ?`
- [ ] Display usage stats:
  ```
  📊 Your Token Usage

  Today (2026-02-13):
  • Input: 12,450 tokens
  • Output: 8,320 tokens
  • Cost: $0.07

  All Time:
  • Input: 145,320 tokens
  • Output: 98,540 tokens
  • Total Cost: $0.81

  Breakdown:
  💬 Discussions: 85%
  📝 Summaries: 10%
  🧠 Memory: 5%

  Powered by GPT-4o-mini ($0.15/$0.60 per 1M tokens)
  ```
- [ ] Show breakdown by operation:
  - Summarization: `summarization_tokens`
  - Discussion: `discussion_tokens`
  - Memory: `memory_extraction_tokens`
- [ ] Format nicely for Telegram (monospace code block for numbers)
- [ ] Handle no usage:
  - "You haven't used any AI features yet. Start a discussion to try!"
- [ ] Error handling:
  - DB query failure → "Error loading usage stats. Try again?"

**Technical Notes:**
- **Command Handler:**
  ```python
  @router.message(Command("token"))
  async def token_handler(message: Message):
      user_id = get_user_id(message.from_user.id)

      # Today's usage
      today = get_usage(user_id, date=current_date())

      # All-time usage
      total = get_total_usage(user_id)

      text = f"""📊 Your Token Usage

  Today ({current_date()}):
  • Input: {today.total_input_tokens:,} tokens
  • Output: {today.total_output_tokens:,} tokens
  • Cost: ${today.total_cost_usd:.2f}

  All Time:
  • Input: {total.input_tokens:,} tokens
  • Output: {total.output_tokens:,} tokens
  • Total Cost: ${total.cost_usd:.2f}

  Powered by GPT-4o-mini ($0.15/$0.60 per 1M tokens)"""

      await message.answer(text)
  ```

**Current State:**
- 🔄 Implementation pending
- ✅ Database schema defined (user_token_usage table)

---

### Story 6.5: MVP Polish & Bug Fixes

**Priority:** P0 - Critical
**Estimate:** 8 story points
**Assignee:** Full Team

**As a** product owner
**I need** a polished, bug-free MVP ready for beta launch
**So that** external users have a smooth onboarding experience

**Acceptance Criteria:**

**Testing:**
- [ ] End-to-end testing with 5 internal beta users (1 week)
- [ ] Test all user flows:
  - Onboarding (/start)
  - Daily digest delivery
  - Button interactions (Discuss, Save, reactions)
  - Discussions (multi-turn, auto-switch, timeout)
  - Memory commands
  - Token usage
- [ ] Collect feedback via survey (Google Form)
- [ ] Prioritize bugs: Critical (P0) → High (P1) → Medium (P2) → Low (P3)

**Bug Fixes:**
- [ ] Fix all P0 (critical) bugs before launch
- [ ] Fix all P1 (high-priority) bugs if time permits
- [ ] Document P2/P3 bugs for future sprints

**Performance Optimization:**
- [ ] Context loading: < 2 seconds (p95)
- [ ] LLM response time: < 10 seconds (p95)
- [ ] Button callbacks: < 500ms (p95)
- [ ] Digest delivery: < 2 minutes for 10 users
- [ ] Database queries: < 200ms (p95)

**UX Improvements:**
- [ ] Message formatting polish (use markdown, bold, emojis appropriately)
- [ ] Error messages clear and actionable (no technical jargon)
- [ ] Button labels concise (emojis + 1-2 words)
- [ ] Help text comprehensive (/help command)
- [ ] Onboarding smooth (< 2 minutes, 3 steps max)

**Documentation:**
- [ ] User guide (how to use HN Pal)
- [ ] Bot commands reference (all commands documented)
- [ ] FAQ (common questions)
- [ ] Privacy policy (what data we store)
- [ ] Terms of service (optional for beta)

**Monitoring:**
- [ ] Langfuse dashboard configured (LLM call tracing)
- [ ] Error tracking (log critical errors with context)
- [ ] Performance monitoring (latency, uptime)
- [ ] User analytics (command usage, engagement rates)

**Production Deployment:**
- [ ] Deploy to Vercel (webhook mode)
- [ ] Configure webhook endpoint (`/api/telegram-webhook`)
- [ ] HTTPS certificate (Vercel automatic)
- [ ] Environment variables (secrets management)
- [ ] Database backup strategy (daily backups)
- [ ] Rollback plan (if critical bug found)

**Beta Launch:**
- [ ] Onboard 10-20 external beta users
- [ ] Invite via personal networks (quality over quantity)
- [ ] Set expectations (beta = bugs expected, feedback welcome)
- [ ] Feedback collection active (/feedback command or Google Form)
- [ ] Monitor first 3 days closely (daily check-ins)

**Metrics Tracking:**
- [ ] User retention (7-day, 30-day)
- [ ] Engagement (digest open rate, button clicks, discussions)
- [ ] Satisfaction (NPS or 1-5 rating)
- [ ] Costs (daily LLM usage, infrastructure)

**Acceptance:** MVP ready for beta launch, no critical bugs, smooth UX, documentation complete

---

## Technical Stack

**Memory System:**
- **OpenAI Agents SDK** - MemoryExtractionAgent
- **PostgreSQL** - `memory` table
- **Pydantic** - Structured extraction outputs

**Deployment:**
- **Vercel** - Serverless functions (webhook mode)
- **Supabase or managed PostgreSQL** - Database
- **Upstash or Redis Cloud** - Managed Redis
- **Langfuse** - Observability

---

## Risks & Mitigation

### Risk 1: Memory Extraction Quality Issues
**Risk:** Agent extracts incorrect or low-quality insights
**Mitigation:**
- Confidence thresholds (only store > 0.8 confidence)
- Manual review of 20 extractions/week
- User feedback loop (/memory forget for bad extractions)
- LLM-as-judge evaluation (test on 10 sample conversations)

### Risk 2: Critical Bugs Found Late
**Risk:** Bug discovered after beta launch
**Mitigation:**
- Start internal testing early (Week 11, not Week 12)
- Buffer time for fixes (2-3 days)
- Prioritize ruthlessly (P0 only)
- Rollback plan ready (revert to pre-launch version)

### Risk 3: Production Deployment Issues
**Risk:** Webhook mode fails, bot goes offline
**Mitigation:**
- Test webhook mode in staging first (ngrok)
- Vercel deployment guide followed carefully
- Monitor bot health (heartbeat every 5 min)
- Fallback to polling mode if webhook fails
- On-call person ready for first 3 days

### Risk 4: Beta User Churn
**Risk:** Users try once, never return
**Mitigation:**
- Set expectations (beta, feedback welcome)
- Daily digest delivery (passive re-engagement)
- Follow-up messages (Day 3, Day 7 check-ins)
- Easy opt-out (/pause, not just block)
- Collect exit feedback (why did you stop using?)

### Risk 5: LLM Costs Exceed Budget
**Risk:** More conversations → higher costs
**Mitigation:**
- Hard limits (max 50 turns per conversation)
- Budget alerts (if daily cost > $10)
- Monitor token usage per user (identify outliers)
- Trim message history aggressively (max 20 messages)

---

## Dependencies

**External:**
- OpenAI API (MemoryExtractionAgent)
- Vercel (production deployment)
- PostgreSQL (managed instance)
- Redis (managed instance)

**Internal:**
- All previous epics (1-5) must be complete
- Database migrations (memory, user_token_usage tables)
- Beta user list (10-20 people)

---

## Definition of Done

- [ ] All 5 stories completed with acceptance criteria met
- [ ] Post-discussion memory extraction working
- [ ] Daily batch memory extraction implemented
- [ ] Memory management commands operational (/memory, /memory pause, /memory forget, /memory clear)
- [ ] Token usage command working (/token)
- [ ] All critical bugs fixed
- [ ] Performance optimized (response times < targets)
- [ ] User documentation complete
- [ ] Monitoring and alerting set up
- [ ] Deployed to production (webhook mode on Vercel)
- [ ] 10-20 beta users onboarded
- [ ] Feedback collection active
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** MVP LAUNCH! 🚀🎉

---

## Success Metrics (Post-Launch)

**Memory Quality:**
- Extraction accuracy: > 80% (manual review of 20 samples)
- Confidence correlation: High confidence → accurate (manual validation)
- User satisfaction: 4/5+ ("Memory feels helpful")

**Memory Usage:**
- Memory surfaced in discussions: > 50% of conversations
- /memory command usage: > 30% of users
- Memory opt-out rate: < 10%

**MVP Quality:**
- Zero critical bugs at launch
- User onboarding time: < 2 minutes
- User satisfaction: 4/5+ (beta survey)
- 7-day retention: > 70%
- 30-day retention: > 50%

**Engagement:**
- Average conversation length: > 3 turns
- Daily digest engagement: > 80% (at least 1 button click)
- /saved usage: > 50% of users

**Costs:**
- Daily LLM cost: < $5 (for 20 users)
- Infrastructure cost: < $20/month (Vercel + Supabase + Redis)

---

## Notes

- **Priority:** Memory extraction nice-to-have, MVP polish critical
- **Testing:** Start early (Week 11), not last minute
- **Documentation:** Clear, concise, user-friendly (not technical)
- **Deployment:** Test webhook mode thoroughly before switching
- **Beta Launch:** Quality users > quantity (target early adopters, tech-savvy)
- **Feedback:** Actively solicit, respond quickly, iterate fast
- **Future Enhancements:** BM25 memory search, personalized digest ranking, advanced prompts

---

**Project Complete!** 🎉
**Next Steps:** Post-launch monitoring, user feedback iteration, advanced features (Sprint 7+)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
