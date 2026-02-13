# Epic 5: Discussion System

**Epic ID:** EPIC-005
**Priority:** P1 - High Priority (MVP Enhancement)
**Timeline:** 2 weeks (Sprint 5)
**Status:** Documented 📝
**Version:** 2.0 (HN Pal)

---

## Epic Goal

Enable AI-powered conversations about HN posts using DiscussionAgent - transforming the bot from a digest delivery tool into an interactive learning companion that can discuss, explain, and explore topics with users.

---

## Epic Description

### Product Vision Context

This epic delivers the core differentiator of HN Pal: conversational discussions about posts. Unlike traditional digest tools, users can now ask questions, request explanations, explore related topics, and have natural conversations about content. The discussion system must:
- Load full article context and user memory for rich conversations
- Handle multi-turn dialogues with coherent context
- Auto-switch between posts without losing conversation history
- Timeout inactive discussions after 30 minutes
- Persist all conversations for memory extraction (Sprint 6)

### What We're Building

A production-grade discussion system that:
- **DiscussionAgent** using OpenAI Agents SDK (GPT-4o-mini)
- **Context retrieval engine** (article + user memory from database)
- **Multi-turn conversation loop** with message history management
- **Auto-switch logic** (save current discussion → start new when tapping Discuss on another post)
- **30-minute timeout** with background worker (APScheduler job)
- **Conversation persistence** in PostgreSQL (`conversations` table with JSONB messages)
- **Token tracking** per conversation (cost monitoring)
- **Error handling** (LLM API failures, timeout, context loading errors)

### Success Criteria

**User Experience:**
- Conversations feel natural and coherent
- Agent responses relevant to article context
- Memory integration personalizes discussions (Sprint 6)
- Auto-switch seamless (no confusion)
- Timeout notifications clear

**Technical Performance:**
- Context loading: < 2 seconds
- Agent response time: < 10 seconds (LLM latency)
- Multi-turn coherence: 100% (no context loss)
- Conversation persistence: 100% (no data loss)
- Timeout accuracy: ±1 minute (30 min ±1 min acceptable)

**Engagement:**
- Average conversation length: > 3 turns
- Discussion completion rate: > 70% (not ended by timeout)
- User satisfaction: 4/5+ (beta feedback)

---

## User Stories

### Story 5.1: Context Retrieval Engine 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-5.0-discussion-system.md` (Sub-activity 5.1)

**As a** developer
**I need** to load article content and user memory when discussion starts
**So that** DiscussionAgent has full context for intelligent conversations

**Acceptance Criteria:**
- [ ] Load article markdown from RocksDB:
  - Key: `{hn_id}` from `markdown` column family
  - Fallback: Read from filesystem (`data/content/markdown/{hn_id}.md`)
  - Error handling: If not found → use post title + summary only
- [ ] Load user memory from PostgreSQL:
  - Query: `SELECT * FROM memory WHERE user_id = ? AND active = true ORDER BY created_at DESC LIMIT 50`
  - Filter by relevance (future: BM25 search, Sprint 6)
  - For MVP: Load all active memory (limit 50 entries)
- [ ] Load related past conversations (optional for MVP):
  - Query: `SELECT * FROM conversations WHERE user_id = ? AND post_id IN (SELECT id FROM posts WHERE title ILIKE '%{keyword}%') LIMIT 3`
  - Extract keywords from current post title
  - For MVP: Skip this (implement in Sprint 6 if time permits)
- [ ] Assemble context payload:
  ```python
  context = {
      "article": {
          "title": post.title,
          "url": post.url,
          "markdown": article_markdown,
          "summary": post.summary,
          "hn_id": post.hn_id
      },
      "user_memory": [
          {"type": "interest", "content": "Distributed systems"},
          {"type": "work_context", "content": "Building search engine with PostgreSQL"}
      ],
      "related_conversations": []  # Future
  }
  ```
- [ ] Cache context in Redis:
  - Key: `context:{telegram_id}:{post_id}`
  - Value: JSON-serialized context
  - TTL: 30 minutes (matches discussion timeout)
  - Invalidate on discussion end
- [ ] Handle errors:
  - Article not found → Fallback to title + summary
  - Memory query failure → Continue with empty memory
  - Redis cache miss → Reload from database
- [ ] Performance optimization:
  - Redis cache hit → < 100ms
  - Full load from DB + RocksDB → < 2 seconds

**Technical Notes:**
- **Context Assembly:**
  ```python
  async def load_discussion_context(user_id: int, hn_id: int) -> dict:
      # Check Redis cache first
      cached = await redis.get(f"context:{user_id}:{hn_id}")
      if cached:
          return json.loads(cached)

      # Load from sources
      post = db.query(Post).filter_by(hn_id=hn_id).first()
      markdown = rocksdb.get(f"{hn_id}", column_family="markdown")
      memory = db.query(Memory).filter_by(user_id=user_id, active=True).limit(50).all()

      context = {
          "article": {...},
          "user_memory": [{"type": m.type, "content": m.content} for m in memory],
          "related_conversations": []
      }

      # Cache in Redis
      await redis.setex(f"context:{user_id}:{hn_id}", 1800, json.dumps(context))
      return context
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 5.2: DiscussionAgent Configuration 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-5.0-discussion-system.md` (Sub-activity 5.2)

**As a** user
**I want** to have natural conversations about posts with AI
**So that** I can explore topics, ask questions, and learn deeply

**Acceptance Criteria:**
- [ ] Create DiscussionAgent using OpenAI Agents SDK:
  - Model: GPT-4o-mini (cost-effective, fast)
  - System prompt includes article context
  - Structured outputs: Text response (Pydantic model)
- [ ] Configure system prompt:
  ```
  You are discussing the following HackerNews post with a user:

  Title: {article.title}
  URL: {article.url}

  Article Content:
  {article.markdown}

  Summary: {article.summary}

  User Context (Memory):
  {user_memory}

  Engage in a helpful, informative discussion about this post. Answer questions, provide insights, and explore related topics. Be concise (2-3 paragraphs max).
  ```
- [ ] Implement multi-turn conversation loop:
  - Load conversation history from `conversations.messages` (JSONB array)
  - Append new user message to history
  - Send full history to agent (maintain context)
  - Receive agent response
  - Append agent response to history
  - Save updated history to database
- [ ] Message history management:
  - Format: `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`
  - Max history: 20 messages (trim older messages if exceeded)
  - System message always first (article context)
- [ ] Token tracking per turn:
  - Count input tokens (tiktoken)
  - Count output tokens (OpenAI API response)
  - Update `conversations.total_input_tokens += input_tokens`
  - Update `conversations.total_output_tokens += output_tokens`
  - Calculate cost: `cost = (input_tokens / 1M * $0.15) + (output_tokens / 1M * $0.60)`
- [ ] Error handling:
  - LLM API failure → Retry 3x, then: "Sorry, I'm having trouble responding. Try again?"
  - Timeout (30 sec) → "Response took too long. Try again?"
  - Invalid response → "Unexpected error. Try again?"
- [ ] Test with different scenarios:
  - Single-turn (one question)
  - Multi-turn (5+ back-and-forth)
  - Follow-up questions (context preservation)
  - Edge cases (very long articles, no article content)

**Technical Notes:**
- **Agent Configuration:**
  ```python
  from openai_agents import Agent
  from pydantic import BaseModel

  class DiscussionResponse(BaseModel):
      response: str

  discussion_agent = Agent(
      model="gpt-4o-mini",
      system_prompt=system_prompt_template,
      response_model=DiscussionResponse,
      langfuse=langfuse_client
  )
  ```
- **Conversation Loop:**
  ```python
  @router.message(StateFilter(BotStates.DISCUSSION))
  async def discussion_message_handler(message: Message, state: FSMContext):
      state_data = await state.get_data()
      hn_id = state_data["active_post_id"]

      # Load conversation from DB
      conversation = get_or_create_conversation(message.from_user.id, hn_id)

      # Append user message
      conversation.messages.append({"role": "user", "content": message.text, "timestamp": now()})

      # Get agent response
      response = await discussion_agent.respond(conversation.messages)

      # Append agent response
      conversation.messages.append({"role": "assistant", "content": response.response, "timestamp": now()})

      # Update tokens and cost
      conversation.total_input_tokens += response.input_tokens
      conversation.total_output_tokens += response.output_tokens
      conversation.total_cost_usd += calculate_cost(response.input_tokens, response.output_tokens)

      # Save to DB
      db.commit()

      # Send to user
      await message.answer(response.response)
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 5.3: Conversation Persistence 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-5.0-discussion-system.md` (Sub-activity 5.3)

**As a** developer
**I need** to persist all conversations to the database
**So that** we can extract memory and provide conversation history

**Acceptance Criteria:**
- [ ] Create conversation on discussion start:
  - Table: `conversations`
  - Fields: `user_id`, `post_id`, `messages` (JSONB array), `started_at`, `agent_model`
  - Initial messages: System prompt only
- [ ] Append messages after each turn:
  - Update `conversations.messages` JSONB array
  - `messages.append({"role": "user", "content": "...", "timestamp": "..."})`
  - `messages.append({"role": "assistant", "content": "...", "timestamp": "..."})`
- [ ] Update token usage and cost:
  - `conversations.total_input_tokens += input_tokens`
  - `conversations.total_output_tokens += output_tokens`
  - `conversations.total_cost_usd += cost`
  - `conversations.last_message_at = now()`
- [ ] End conversation (on auto-switch or timeout):
  - Set `conversations.ended_at = now()`
  - Clear `users.active_discussion_post_id = NULL`
  - Transition state to IDLE
  - Clear Redis context cache
- [ ] Context loading (for memory extraction, Sprint 6):
  - Store `conversations.context_loaded` JSONB:
    ```json
    {
      "article": true,
      "memory": true,
      "memory_count": 12,
      "related_posts": 0
    }
    ```
- [ ] Database indexes:
  - `idx_user_conversations (user_id, started_at DESC)`
  - `idx_active_conversations (user_id, ended_at) WHERE ended_at IS NULL`
  - `idx_post_conversations (post_id)`
- [ ] Error handling:
  - DB write failure → Retry 3x, log error, continue (conversation lost but bot functional)
  - JSONB append failure → Reinitialize messages array

**Technical Notes:**
- **Conversation Creation:**
  ```python
  def get_or_create_conversation(user_id: int, hn_id: int) -> Conversation:
      post = db.query(Post).filter_by(hn_id=hn_id).first()
      conversation = db.query(Conversation).filter_by(
          user_id=user_id,
          post_id=post.id,
          ended_at=None
      ).first()

      if not conversation:
          context = load_discussion_context(user_id, hn_id)
          conversation = Conversation(
              user_id=user_id,
              post_id=post.id,
              messages=[{"role": "system", "content": build_system_prompt(context)}],
              agent_model="gpt-4o-mini",
              context_loaded={"article": True, "memory": len(context["user_memory"])}
          )
          db.add(conversation)
          db.commit()

      return conversation
  ```
- **JSONB Operations:**
  ```python
  # SQLAlchemy JSONB append
  conversation.messages = conversation.messages + [new_message]
  db.commit()
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending
- ✅ Database schema defined in data-models.md

---

### Story 5.4: 30-Minute Timeout Handler 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-5.0-discussion-system.md` (Sub-activity 5.5)

**As a** user
**I want** inactive discussions to auto-close after 30 minutes
**So that** I don't stay stuck in discussion state indefinitely

**Acceptance Criteria:**
- [ ] Track last message timestamp in FSM state:
  - `state_data["last_message_at"] = now()`
  - Update on every user message
- [ ] Background worker checks for inactive discussions:
  - APScheduler job running every 5 minutes
  - Query FSM state for all users in DISCUSSION state
  - Calculate inactivity: `now() - last_message_at`
  - If inactivity > 30 minutes → trigger timeout
- [ ] Timeout actions:
  - End conversation:
    - Set `conversations.ended_at = now()`
    - Clear `users.active_discussion_post_id = NULL`
  - Send notification to user:
    ```
    ⏱️ Discussion timed out due to inactivity.

    Your conversation has been saved. Tap 💬 Discuss on any post to start a new discussion!
    ```
  - Transition state to IDLE
  - Clear Redis context cache
  - Log timeout event (user_id, post_id, duration)
- [ ] Graceful handling:
  - If user sends message during timeout processing → Cancel timeout, continue discussion
  - If timeout notification fails (user blocked bot) → Log, skip notification
- [ ] Configuration:
  - Timeout duration: 30 minutes (configurable via settings)
  - Worker frequency: 5 minutes (APScheduler cron)
- [ ] Monitoring:
  - Track timeout rate (should be < 30% of discussions)
  - Alert if timeout rate > 50% (indicates UX issue)

**Technical Notes:**
- **APScheduler Job:**
  ```python
  from apscheduler.schedulers.asyncio import AsyncIOScheduler

  scheduler = AsyncIOScheduler()

  @scheduler.scheduled_job('interval', minutes=5)
  async def check_discussion_timeouts():
      # Get all users in DISCUSSION state from Redis
      fsm_keys = await redis.keys("fsm:*:state")
      for key in fsm_keys:
          state_data = await redis.hgetall(key)
          if state_data.get("state") == "DISCUSSION":
              last_message_at = datetime.fromisoformat(state_data["last_message_at"])
              inactivity = now() - last_message_at
              if inactivity > timedelta(minutes=30):
                  telegram_id = extract_telegram_id_from_key(key)
                  await timeout_discussion(telegram_id)
  ```
- **Timeout Function:**
  ```python
  async def timeout_discussion(telegram_id: int):
      user = get_user_by_telegram_id(telegram_id)
      if user.active_discussion_post_id:
          # End conversation
          conversation = get_active_conversation(user.id)
          conversation.ended_at = now()
          user.active_discussion_post_id = None
          db.commit()

          # Send notification
          await bot.send_message(telegram_id, "⏱️ Discussion timed out...")

          # Transition to IDLE
          await state.set_state(BotStates.IDLE)
          await state.clear()
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

## Technical Stack

**LLM Integration:**
- **OpenAI Agents SDK** - DiscussionAgent
- **Langfuse** - Observability
- **tiktoken** - Token counting

**Backend:**
- **PostgreSQL** - Conversations, messages (JSONB)
- **RocksDB** - Article markdown
- **Redis** - Context caching, FSM state

**Scheduler:**
- **APScheduler** - Background timeout worker

---

## Risks & Mitigation

### Risk 1: LLM Response Latency Too High (> 10 sec)
**Risk:** Slow agent responses frustrate users
**Mitigation:**
- Use GPT-4o-mini (faster than GPT-4o)
- Optimize context size (trim long articles to 4000 tokens max)
- Show typing indicator while waiting (`await bot.send_chat_action(chat_id, "typing")`)
- Set timeout (30 sec), return error if exceeded
- Monitor latency (alert if p95 > 15 seconds)

### Risk 2: Context Loading Performance
**Risk:** Loading article + memory takes > 2 seconds
**Mitigation:**
- Redis caching (< 100ms on cache hit)
- Lazy load memory (only when needed, not for every message)
- Limit memory query (50 entries max)
- Index database queries (see data-models.md)
- Monitor loading time (alert if p95 > 3 seconds)

### Risk 3: Timeout Background Worker Reliability
**Risk:** Worker crashes, timeouts never trigger
**Mitigation:**
- APScheduler with exception handling
- Log all timeout events
- Monitor worker health (heartbeat every 5 min)
- Manual timeout command: `/end_discussion` (escape hatch)
- Alert if no timeouts for 24 hours (indicates worker dead)

### Risk 4: Conversation Data Loss
**Risk:** DB write failure loses conversation history
**Mitigation:**
- Transactional writes (all-or-nothing)
- Retry logic (3 attempts)
- Log all DB errors
- Backup conversations daily
- Graceful degradation (continue bot, log error)

### Risk 5: Token Usage Explosion
**Risk:** Long conversations consume excessive tokens/costs
**Mitigation:**
- Trim message history (max 20 messages)
- Summarize older context (future enhancement)
- Hard limit: Max 50 turns per conversation
- Budget alerts (if daily cost > $5)
- Monitor token usage per conversation (p95, p99)

---

## Dependencies

**External:**
- OpenAI API (GPT-4o-mini)
- Langfuse (observability)
- PostgreSQL (conversations table)
- RocksDB (article markdown)
- Redis (context cache, FSM)

**Internal:**
- Epic 3 (Bot Foundation) - needs FSM, state management
- Epic 4 (Interactive Elements) - needs Discuss button callback
- Database migration (conversations, memory tables)

---

## Definition of Done

- [ ] All 4 stories completed with acceptance criteria met
- [ ] Context retrieval working (article + memory)
- [ ] DiscussionAgent responding to messages
- [ ] Multi-turn conversations functional
- [ ] Conversations persisted to database (JSONB messages)
- [ ] 30-minute timeout implemented (background worker)
- [ ] Auto-switch between discussions working
- [ ] Token usage tracked per conversation
- [ ] Error handling tested (LLM failures, timeouts, DB errors)
- [ ] Tested with 5+ turn conversations
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Discussion system working! 🎉

---

## Success Metrics (Post-Launch)

**User Engagement:**
- Average conversation length: > 3 turns
- Discussion completion rate: > 70% (not ended by timeout)
- Timeout rate: < 30%
- User satisfaction: 4/5+ (beta feedback)

**Technical Performance:**
- Context loading: < 2 seconds (p95)
- Agent response time: < 10 seconds (p95)
- Conversation persistence: 100% (no data loss)
- Timeout accuracy: ±1 minute
- Token usage: ~2000 tokens per conversation (5 turns)

**Quality:**
- Multi-turn coherence: 100% (no context loss)
- Factual accuracy: No hallucinations (manual review)
- Relevance: Agent responses on-topic (user feedback)

---

## Notes

- **Priority:** Context coherence is critical (users expect continuity)
- **Performance:** Show typing indicator to manage latency expectations
- **Token Optimization:** Trim message history to balance context vs cost
- **Error Handling:** Always graceful (never crash discussion)
- **Future Enhancement:** Memory extraction after discussions (Sprint 6)
- **Monitoring:** Track conversation metrics (length, completion rate, timeouts)

---

**Next Epic:** Epic 6 - Memory System & MVP Polish
**Depends On:** Epic 3 (Bot), Epic 4 (Interactive Elements), Epic 5 (Discussion System)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
