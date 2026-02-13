# Epic 3: Telegram Bot Foundation & Delivery

**Epic ID:** EPIC-003
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 2 weeks (Sprint 3)
**Status:** Documented 📝
**Version:** 2.0 (HN Pal)

---

## Epic Goal

Launch the Telegram bot with digest delivery system, basic commands, state machine, and inline buttons - establishing the user-facing interface that delivers AI-summarized HN posts directly to users' Telegram DMs.

---

## Epic Description

### Product Vision Context

This epic transforms HN Pal from a backend data pipeline into a user-facing product. The Telegram bot delivers daily digests in a conversational format, replacing traditional email/web interfaces with a mobile-first, chat-based experience. The bot must:
- Deliver digests in "flat scroll" format (one message per post)
- Support basic commands (/start, /pause, /help, /saved)
- Implement state machine (IDLE ↔ DISCUSSION states)
- Display inline buttons (Discuss, Read, Save, 👍👎)
- Track deliveries in database for analytics

### What We're Building

A production-ready Telegram bot that:
- **aiogram 3.x** framework with async support
- **FSM state management** using Redis (IDLE, DISCUSSION, ONBOARDING states)
- **Flat scroll digest delivery** (one message per post with summary)
- **Inline button grid** on each post (💬 Discuss, 🔗 Read, ⭐ Save, 👍 👎)
- **User registration** (create user in PostgreSQL on /start)
- **Command routing** (/start, /pause, /help, /saved)
- **Delivery tracking** (deliveries table with batch_id, message_id)
- **Error handling** (graceful failures, retry logic)

### Success Criteria

**User Experience:**
- Users receive daily digest via Telegram DM
- Digest is readable and well-formatted (flat scroll style)
- Commands respond instantly (< 1 second)
- Buttons render correctly on mobile
- No broken links or formatting issues

**Technical Performance:**
- Digest delivery: < 2 minutes for 10 users
- Message delivery success rate: > 95%
- Bot uptime: > 99%
- State transitions: < 100ms
- Redis connection stable (fallback to in-memory if needed)

**Engagement:**
- Beta users engage with digest (open rate assumed 100% via Telegram)
- Click-through on inline buttons: > 20%
- Command usage: /start (100%), /pause (< 10%), /saved (> 30%)

---

## User Stories

### Story 3.1: Bot Initialization & Basic Commands 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-3.0-telegram-bot-foundation.md` (Sub-activity 3.1)

**As a** user
**I want** to start the bot and access basic commands
**So that** I can register, configure preferences, and get help

**Acceptance Criteria:**
- [ ] aiogram 3.x project structure set up
- [ ] Bot token configured (TELEGRAM_BOT_TOKEN env var)
- [ ] `/start` command implemented:
  - Welcome message with bot description
  - User registration (create user in PostgreSQL)
  - Simple onboarding (optional: pick 3 interests)
  - Set default preferences (digest delivery enabled)
- [ ] `/pause` command implemented:
  - Toggle `users.status` between 'active' and 'paused'
  - Confirmation message ("Digests paused. Use /pause again to resume.")
- [ ] `/help` command implemented:
  - List all available commands with descriptions
  - Link to documentation (if available)
- [ ] `/saved` command implemented (placeholder for Sprint 4):
  - Show bookmarked posts count
  - Message: "You have 5 saved posts. (Full list coming soon!)"
- [ ] Bot polling mode for development (long polling)
- [ ] Error handling (invalid commands, API failures)
- [ ] Logging (command usage, user registration, errors)

**Technical Notes:**
- **aiogram Structure:**
  ```
  backend/app/presentation/bot/
  ├── __init__.py
  ├── main.py              # Bot entry point
  ├── handlers/
  │   ├── commands.py      # /start, /pause, /help, /saved
  │   ├── callbacks.py     # Inline button handlers (Sprint 4)
  │   └── messages.py      # Discussion messages (Sprint 5)
  ├── middleware/
  │   ├── auth.py          # User registration/loading
  │   └── logging.py       # Request logging
  └── utils/
      ├── keyboards.py     # Inline button layouts
      └── formatters.py    # Message formatting
  ```
- **User Registration Flow:**
  ```python
  @router.message(Command("start"))
  async def start_handler(message: Message):
      user = get_or_create_user(message.from_user.id)
      await message.answer("Welcome to HN Pal! ...")
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 3.2: State Machine & Routing 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-3.0-telegram-bot-foundation.md` (Sub-activity 3.2)

**As a** developer
**I need** a state machine to manage bot conversation flow
**So that** users can transition between IDLE and DISCUSSION states

**Acceptance Criteria:**
- [ ] FSM configured with 3 states:
  - **IDLE:** Default state (waiting for digest or command)
  - **DISCUSSION:** Active discussion about a post
  - **ONBOARDING:** First-time setup (optional)
- [ ] Redis storage for FSM state:
  - Key pattern: `fsm:{telegram_id}:state`
  - TTL: 60 minutes (auto-cleanup inactive sessions)
- [ ] State-based message routing:
  - IDLE: Route commands, ignore freeform messages
  - DISCUSSION: Route all messages to DiscussionAgent (Sprint 5)
  - ONBOARDING: Route to onboarding flow
- [ ] Priority router:
  1. Commands (highest priority)
  2. Callback queries (inline buttons)
  3. Messages (lowest priority, state-dependent)
- [ ] State transition logic:
  - `/start` → ONBOARDING (if new user) or IDLE
  - Tap "Discuss" button → DISCUSSION
  - 30 min timeout → IDLE (Sprint 5)
- [ ] Session management:
  - Store active_discussion_post_id in `users` table
  - Clear on state transition to IDLE
- [ ] Graceful degradation (Redis unavailable → in-memory state)

**Technical Notes:**
- **aiogram FSM:**
  ```python
  from aiogram.fsm.storage.redis import RedisStorage
  from aiogram.fsm.state import State, StatesGroup

  class BotStates(StatesGroup):
      IDLE = State()
      DISCUSSION = State()
      ONBOARDING = State()

  storage = RedisStorage.from_url("redis://localhost:6379/0")
  dp = Dispatcher(storage=storage)
  ```
- **State Data:**
  ```json
  {
    "state": "DISCUSSION",
    "data": {
      "active_post_id": 38543210,
      "discussion_started_at": "2026-02-13T10:00:00Z",
      "last_message_at": "2026-02-13T10:15:22Z"
    }
  }
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 3.3: Flat Scroll Digest Delivery 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-3.0-telegram-bot-foundation.md` (Sub-activity 3.3)

**As a** user
**I want** to receive daily HN digest via Telegram
**So that** I can read summaries without leaving my messaging app

**Acceptance Criteria:**
- [ ] Query top posts from PostgreSQL:
  - Filters: `score > 100`, `summary IS NOT NULL`, `type IN ('story')`
  - Order by: `score DESC`
  - Limit: 10 posts (configurable per user, future)
- [ ] Rank posts by score (MVP: simple sorting)
- [ ] Format digest messages (Style 2: flat scroll):
  ```
  🔶 1/10 · PostgreSQL 18 Released
  postgresql.org

  Major performance gains across OLTP workloads
  with up to 2x throughput. New JSON path
  indexing and async I/O.

  ⬆️ 452 · 💬 230

  [💬 Discuss] [🔗 Read] [⭐ Save]
  [👍] [👎]
  ```
- [ ] Send one message per post (avoid Telegram flood limits with delays)
- [ ] Track deliveries in `deliveries` table:
  - Fields: user_id, post_id, message_id, batch_id, delivered_at
  - batch_id format: `YYYY-MM-DD-morning` (e.g., `2026-02-13-morning`)
- [ ] Integrate into pipeline orchestrator (Step 5: Deliver)
- [ ] Handle delivery failures:
  - Telegram rate limits: throttle with delays (aiogram built-in)
  - User blocked bot: log, skip, set status to 'blocked'
  - Network errors: retry once, log error
- [ ] Logging: users delivered, posts sent, errors

**Technical Notes:**
- **Message Formatting:**
  ```python
  def format_post_message(post: Post, index: int, total: int) -> str:
      return f"""🔶 {index}/{total} · {post.title}
  {post.domain}

  {post.summary}

  ⬆️ {post.score} · 💬 {post.comment_count}"""
  ```
- **Delivery Flow:**
  ```python
  async def deliver_digest(user_id: int):
      posts = get_top_posts(limit=10)
      batch_id = f"{date.today()}-morning"

      for idx, post in enumerate(posts, 1):
          message_text = format_post_message(post, idx, len(posts))
          keyboard = get_post_buttons(post.hn_id)

          msg = await bot.send_message(user_id, message_text, reply_markup=keyboard)

          save_delivery(user_id, post.id, msg.message_id, batch_id)
          await asyncio.sleep(0.5)  # Avoid flood limits
  ```
- **Telegram Rate Limits:**
  - 30 messages/second per bot
  - aiogram handles throttling automatically
  - Add 0.5s delay between messages for safety

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending
- 🔄 Pipeline integration needed (Step 5)

---

### Story 3.4: Inline Buttons (Basic) 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-3.0-telegram-bot-foundation.md` (Sub-activity 3.4)

**As a** user
**I want** to see interactive buttons on each post
**So that** I can discuss, read, save, or react to posts

**Acceptance Criteria:**
- [ ] Design inline button layout (2 rows):
  - Row 1: [💬 Discuss] [🔗 Read] [⭐ Save]
  - Row 2: [👍] [👎]
- [ ] Implement button grid using aiogram InlineKeyboardMarkup:
  ```python
  keyboard = InlineKeyboardMarkup(inline_keyboard=[
      [
          InlineKeyboardButton(text="💬 Discuss", callback_data=f"discuss:{hn_id}"),
          InlineKeyboardButton(text="🔗 Read", url=f"https://news.ycombinator.com/item?id={hn_id}"),
          InlineKeyboardButton(text="⭐ Save", callback_data=f"save:{hn_id}")
      ],
      [
          InlineKeyboardButton(text="👍", callback_data=f"react:up:{hn_id}"),
          InlineKeyboardButton(text="👎", callback_data=f"react:down:{hn_id}")
      ]
  ])
  ```
- [ ] Placeholder callback handlers (full implementation in Sprint 4):
  - `discuss:{hn_id}` → "Discussion feature coming soon!"
  - `save:{hn_id}` → "Bookmark feature coming soon!"
  - `react:up:{hn_id}` → "Thanks for your feedback!"
  - `react:down:{hn_id}` → "Thanks for your feedback!"
- [ ] 🔗 Read button (external URL):
  - Direct link to HN post (works immediately, no callback)
- [ ] Test button rendering on mobile (iOS + Android)
- [ ] Ensure buttons fit on one screen (no horizontal scroll)

**Technical Notes:**
- **Callback Data Format:** `action:param1:param2:...`
- **External URL Button:** Telegram handles automatically (opens browser)
- **Button Design:**
  - Keep text short (emojis + 1-2 words)
  - Use semantic colors (future: green for Save, red for unsave)
- **Future (Sprint 4):** Full callback implementation

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

## Technical Stack

**Bot Framework:**
- **aiogram 3.x** - Async Telegram bot framework
- **Redis** - FSM state storage
- **PostgreSQL** - User data, deliveries tracking
- **Python 3.11+** - Async/await support

**Deployment:**
- **Development:** Polling mode (long polling)
- **Production (Sprint 6):** Webhook mode on Vercel serverless

**Key Libraries:**
- `aiogram>=3.0.0` - Bot framework
- `redis>=5.0.0` - State management
- `sqlalchemy>=2.0.0` - Database ORM
- `pydantic>=2.0.0` - Data validation

---

## Risks & Mitigation

### Risk 1: Telegram Rate Limits
**Risk:** Sending 10+ messages rapidly triggers flood limits (30 msg/sec)
**Mitigation:**
- aiogram built-in throttling (automatic)
- Add 0.5s delay between digest messages (asyncio.sleep)
- Batch deliveries (max 20 users at a time)
- Monitor Telegram API errors, backoff if rate-limited

### Risk 2: Bot Deployment Complexity
**Risk:** Webhook mode on Vercel requires HTTPS, certificate, domain setup
**Mitigation:**
- Start with polling mode (simple, works everywhere)
- Defer webhook migration to Sprint 6 (production deployment)
- Test webhook locally with ngrok first
- Document deployment steps thoroughly

### Risk 3: Redis Connection Failures
**Risk:** Redis unavailable → FSM state lost
**Mitigation:**
- Graceful degradation: fallback to in-memory state (aiogram MemoryStorage)
- Rebuild state from PostgreSQL (`users.active_discussion_post_id`)
- Monitor Redis connection health
- Alert on Redis downtime

### Risk 4: Message Delivery Failures
**Risk:** User blocks bot, network errors, invalid chat_id
**Mitigation:**
- Catch exceptions per user (don't fail entire batch)
- Update `users.status = 'blocked'` if bot blocked
- Retry once on network errors
- Log all delivery failures with context

### Risk 5: State Management Bugs
**Risk:** FSM transitions incorrect, users stuck in wrong state
**Mitigation:**
- Thorough testing of state transitions
- Logging all state changes with timestamps
- Manual state reset tool (admin command)
- /start command always resets to IDLE (escape hatch)

---

## Dependencies

**External:**
- Telegram Bot API (bot token required)
- Redis instance (local or managed)
- PostgreSQL database (users, posts, deliveries tables)

**Internal:**
- Epic 1 (Ingest Pipeline) - needs posts data
- Epic 2 (Summarization) - needs summaries in `posts.summary`
- Database migrations (users, deliveries tables)

---

## Definition of Done

- [ ] All 4 stories completed with acceptance criteria met
- [ ] Telegram bot operational (aiogram 3.x)
- [ ] Basic commands working (/start, /pause, /help, /saved)
- [ ] FSM state machine with Redis storage
- [ ] Flat scroll digest delivery working
- [ ] Users receive daily digest via Telegram
- [ ] Deliveries tracked in database
- [ ] Inline buttons displayed (placeholder callbacks)
- [ ] Bot deployed (polling mode for dev)
- [ ] Error handling and logging in place
- [ ] Tested with 5 internal users (beta)
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** First Telegram digest delivered! 🚀

---

## Success Metrics (Post-Launch)

**User Engagement:**
- Digest open rate: 100% (Telegram DM, always visible)
- Button click rate: > 20% (at least one button per digest)
- Command usage: /start (100%), /pause (< 10%), /saved (> 30%)
- User retention: > 80% after 1 week

**Technical Performance:**
- Digest delivery time: < 2 minutes for 10 users
- Message delivery success rate: > 95%
- Bot uptime: > 99%
- State transitions: < 100ms
- Redis connection uptime: > 99%

**Quality:**
- Zero formatting errors (messages render correctly)
- Zero broken links (🔗 Read button works)
- User satisfaction: 4/5+ (beta feedback)

---

## Notes

- **Priority:** Get basic digest delivery working first, polish later
- **Polling vs Webhook:** Start with polling (simpler), migrate to webhook in Sprint 6
- **Inline Buttons:** Placeholder callbacks OK for Sprint 3, full implementation in Sprint 4
- **Message Formatting:** Test on both iOS and Android devices
- **Error Handling:** Log everything, fail gracefully, never crash bot
- **Future Enhancement:** Personalized post ranking based on user interests (Sprint 6)

---

**Next Epic:** Epic 4 - Interactive Elements
**Depends On:** Epic 1 (Ingest), Epic 2 (Summarization), Epic 3 (Bot Foundation)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
