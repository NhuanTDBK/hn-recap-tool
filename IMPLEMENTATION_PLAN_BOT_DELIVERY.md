# Implementation Plan: Bot API for Delivery to Users
## HN Pal Phase 2.5 - Deliver Digest to Users via Telegram

**Status:** Planning Phase
**Date:** 2026-02-14
**Scope:** Ingest → Summarize → **Deliver** pipeline completion
**Priority:** High (MVP requires user delivery)

---

## 🎯 Overview

This plan outlines the implementation of the **Delivery Pipeline**, which is the **final step of the ingest phase** (Phase 1.7 in the build order). After posts are collected and summarized, they must be delivered to users' Telegram DMs.

### Key Principle
**"No channels, no groups. Just you and the bot."** — Deliver to individual users via DM, not broadcast channels.

---

## 📊 Current Architecture Gap

The ingest pipeline is currently **80% complete**:

```
Ingest (1.1-1.6) ✅  →  Summarize (2.1-2.3) ✅  →  Deliver (???) ❌
                                                       └─ NOT IMPLEMENTED
```

### What Exists Now:
- ✅ HN polling
- ✅ Content crawling
- ✅ HTML → Markdown conversion
- ✅ Summary generation via OpenAI Agents
- ✅ RocksDB content storage
- ✅ PostgreSQL data models

### What's Missing:
- ❌ Delivery database models (Delivery table, last_delivered_at on User)
- ❌ User delivery logic (per-user, per-interest)
- ❌ Telegram bot integration
- ❌ Message formatting (Style 2: Flat Scroll)
- ❌ Inline buttons (Discuss, Read, Save, 👍👎)

---

## 🏗️ Implementation Scope

This plan covers building **one complete end-to-end feature**:
- **Trigger:** End of summarization pipeline
- **Input:** Posts with summaries, users with interests, last delivery time
- **Process:** Select posts per user, format messages, send via Telegram
- **Output:** Delivery records in DB, messages in user's Telegram DM

**NOT in scope (defer to Phase 3+):**
- Interactive buttons (Phase 4)
- Discussion state management (Phase 5)
- Memory extraction (Phase 6)
- Commands: /start, /pause, /memory, /token (Phase 7)

---

## 📋 Tasks & Components

### Task 1: Database Schema Updates
**Files to Create/Modify:**

#### 1.1 Create Delivery & Conversation Models
- **File:** `backend/app/infrastructure/database/models.py`
- **Action:** Add two new models:

```
Delivery (tracks which posts were sent to which users)
├── id (UUID, primary key)
├── user_id (FK → users)
├── post_id (FK → posts)
├── message_id (BIGINT) - Telegram message ID
├── batch_id (TEXT) - Group posts in same digest batch
├── reaction (TEXT) - "up" | "down" | null (from user interaction)
├── delivered_at (TIMESTAMPTZ)

Conversation (stores discussion threads per user per post)
├── id (UUID, primary key)
├── user_id (FK → users)
├── post_id (FK → posts)
├── messages (JSONB) - [{role, content, timestamp}, ...]
├── token_usage (JSONB) - {input_tokens, output_tokens}
├── started_at (TIMESTAMPTZ)
├── ended_at (TIMESTAMPTZ)
```

#### 1.2 Add Delivery Timestamp to User
- **File:** `backend/app/infrastructure/database/models.py`
- **Action:** Add to User model:
  - `last_delivered_at` (TIMESTAMPTZ, nullable) - When this user last received a digest
  - `delivery_style` (VARCHAR, default="flat_scroll") - Message style preference

#### 1.3 Create Alembic Migration
- **File:** `backend/alembic/versions/{timestamp}_add_delivery_models.py`
- **Action:** Auto-generate migration from SQLAlchemy models

---

### Task 2: Repository Layer for Delivery Tracking
**Files to Create:**

#### 2.1 Create DeliveryRepository Interface
- **File:** `backend/app/application/interfaces/repositories.py`
- **Action:** Add interface:

```
DeliveryRepository
├── save_delivery(user_id, post_id, message_id, batch_id) → Delivery
├── find_deliveries_for_user(user_id, limit=10) → List[Delivery]
├── find_deliveries_for_batch(batch_id) → List[Delivery]
├── update_reaction(delivery_id, reaction) → Delivery
└── get_user_delivery_count(user_id, days=7) → int
```

#### 2.2 Implement PostgresDeliveryRepository
- **File:** `backend/app/infrastructure/repositories/postgres/delivery_repo.py`
- **Action:** Implement all interface methods using SQLAlchemy

#### 2.3 Create ConversationRepository
- **File:** `backend/app/infrastructure/repositories/postgres/conversation_repo.py`
- **Action:** Save/retrieve conversation threads for discussion feature (defer full usage to Phase 5)

---

### Task 3: Delivery Selection & Filtering Use Case
**Files to Create:**

#### 3.1 Create SelectPostsForDeliveryUseCase
- **File:** `backend/app/application/use_cases/delivery_selection.py`
- **Action:** Implement logic to select posts for each user:

```
For each user:
  1. Get user.interests (tags like ["rust", "databases"])
  2. Get user.last_delivered_at (when they last received posts)
  3. Select posts where:
     - created_at > user.last_delivered_at (OR latest if none)
     - type == "story" (skip ask_hn, show_hn)
     - summary IS NOT NULL (must be summarized)
     - is_dead = false
  4. Rank by: score DESC (most relevant first)
  5. Filter by interest match (optional personalization)
  6. Return: List[Post] to deliver
```

**Return Type:**
```python
@dataclass
class UserDeliveryPlan:
    user_id: int
    posts: List[Post]  # Posts selected for this user
    batch_id: str      # Unique ID for this delivery batch
    delivery_count: int
```

---

### Task 4: Message Formatting (Style 2: Flat Scroll)
**Files to Create:**

#### 4.1 Create MessageFormatter Service
- **File:** `backend/app/presentation/bot/formatters/digest_formatter.py`
- **Action:** Format message per spec:

```
Style 2 format for each post:

┌─────────────────────────────────────────┐
│  🔶 1/8 · PostgreSQL 18 Released        │
│  postgresql.org                         │
│                                         │
│  [2-3 sentence summary from DB]         │
│                                         │
│  ⬆️ 452 · 💬 230                        │
│                                         │
│  ┌──────────┬────────┬────────┐         │
│  │ 💬 Discuss│ 🔗 Read │ ⭐ Save │       │
│  └──────────┴────────┴────────┘         │
│  👍  👎                                 │
└─────────────────────────────────────────┘
```

**Components:**
- Header: `🔶 {position}/{total} · {title}`
- Domain: Extract from post.url
- Summary: post.summary (2-3 sentences)
- Stats: `⬆️ {score} · 💬 {comment_count}`
- Buttons: Discuss, Read, Save
- Reactions: 👍 👎

#### 4.2 Create InlineKeyboard Builder
- **File:** `backend/app/presentation/bot/keyboards/inline.py`
- **Action:** Build inline button rows:

```
Row 1: [Discuss Button] [Read Button] [Save Button]
Row 2: [👍] [👎]
```

**Button Callbacks:**
- `discuss_{post_id}` - Trigger discussion state
- `read_{post_id}` - Open URL (or show expanded text)
- `save_{post_id}` - Bookmark post
- `react_up_{post_id}` - Upvote reaction
- `react_down_{post_id}` - Downvote reaction

---

### Task 5: Telegram Bot Integration (Aiogram)
**Files to Create:**

#### 5.1 Create Bot Instance & Dispatcher
- **File:** `backend/app/presentation/bot/bot.py`
- **Action:**

```python
# Load from environment
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
bot = Bot(token=TELEGRAM_BOT_TOKEN)
router = Router()
```

#### 5.2 Create Delivery Handler
- **File:** `backend/app/presentation/bot/handlers/delivery.py`
- **Action:**

```python
async def send_digest_to_user(
    user: User,
    posts: List[Post],
    batch_id: str
) -> dict:
    """Send formatted digest messages to user's Telegram DM.

    Args:
        user: User to deliver to
        posts: Posts selected for delivery
        batch_id: Unique ID for this batch

    Returns:
        {
            "user_id": int,
            "messages_sent": int,
            "failures": List[error],
            "message_ids": List[int],
        }
    """
    # For each post:
    #   1. Format message (Style 2)
    #   2. Create inline keyboard
    #   3. Send to user.telegram_id (DM)
    #   4. Record message_id
    #   5. Create Delivery record in DB
    # Return summary
```

**Key Points:**
- Send to `user.telegram_id` (direct DM, not group/channel)
- Rate limiting: 1 message per second (Telegram API limit)
- Error handling: Log failures, continue with next post
- Store `message_id` in Delivery table for future button callbacks

#### 5.3 Create Callback Router (Phase 4, minimal setup)
- **File:** `backend/app/presentation/bot/handlers/callbacks.py`
- **Action:** Create empty handlers for future button callbacks:

```python
@router.callback_query(F.data.startswith("discuss_"))
async def handle_discuss(callback: CallbackQuery):
    """Placeholder - implemented in Phase 5."""
    await callback.answer("Discussion coming soon!")

@router.callback_query(F.data.startswith("save_"))
async def handle_save(callback: CallbackQuery):
    """Placeholder - implemented in Phase 4."""
    await callback.answer("Bookmark coming soon!")

# Similar placeholders for read_, react_up_, react_down_
```

---

### Task 6: Delivery Pipeline Orchestrator
**Files to Create/Modify:**

#### 6.1 Create DeliveryPipeline Use Case
- **File:** `backend/app/application/use_cases/delivery_pipeline.py`
- **Action:** Orchestrate the entire delivery flow:

```python
async def run_delivery_pipeline(
    batch_id: str = None,  # Optional, generates if not provided
    max_posts_per_user: int = 10,
    skip_users: List[int] = None,
) -> dict:
    """Execute the delivery pipeline end-to-end.

    Flow:
    1. Load all active users
    2. For each user:
       a. Select posts (via SelectPostsForDeliveryUseCase)
       b. Format messages (via MessageFormatter)
       c. Send to Telegram (via bot.send_message)
       d. Record deliveries in DB
       e. Update user.last_delivered_at
    3. Return summary stats

    Returns:
        {
            "batch_id": str,
            "total_users": int,
            "users_delivered": int,
            "users_skipped": int,
            "total_messages_sent": int,
            "total_posts_delivered": int,
            "errors": List[error_details],
            "duration_seconds": float,
        }
    """
```

#### 6.2 Update Pipeline Orchestrator
- **File:** `backend/app/application/use_cases/pipeline.py`
- **Action:** Add delivery step after summarization:

```
Current:
  Collect → Crawl → Summarize → [END]

Updated:
  Collect → Crawl → Summarize → Deliver → [END]
                                  ↓
                            Track in Delivery table
```

---

### Task 7: API Endpoint to Trigger Delivery (Manual Testing)
**Files to Create:**

#### 7.1 Create Delivery API Router
- **File:** `backend/app/presentation/api/delivery.py`
- **Action:** Create FastAPI router:

```python
@router.post("/api/deliveries/run")
async def trigger_delivery(
    force: bool = False,  # Bypass time checks
    dry_run: bool = False,  # Don't actually send
) -> dict:
    """Manually trigger delivery pipeline.

    For testing and admin use.

    Returns:
        Pipeline execution results
    """
```

#### 7.2 Add Route to Main App
- **File:** `backend/app/main.py`
- **Action:** Register delivery router

---

### Task 8: Configuration & Environment Setup
**Files to Update:**

#### 8.1 Update AgentSettings
- **File:** `backend/app/infrastructure/agents/config.py`
- **Action:** Add bot configuration:

```python
class AgentSettings(BaseSettings):
    # ... existing fields ...

    # Telegram Bot
    telegram_bot_token: Optional[str] = None
    telegram_delivery_rate_limit: float = 1.0  # seconds between messages
    telegram_max_messages_per_user: int = 20  # per delivery batch
```

#### 8.2 Update .env
- **File:** `.env`
- **Action:** Ensure these are present:

```
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=8245860948:AAFBLK8efxUvN18Q_...  # Already in .env
POSTGRES_URL=postgresql+asyncpg://...  # For async access
DELIVERY_ENABLED=true
DELIVERY_RATE_LIMIT=1.0  # seconds between Telegram messages
```

#### 8.3 Update pyproject.toml
- **File:** `backend/pyproject.toml`
- **Action:** Ensure dependencies:

```toml
dependencies = [
    # ... existing ...
    "aiogram>=3.0.0",        # Telegram bot framework
    "python-telegram-bot>=20.0",  # Alternative/backup
]
```

---

### Task 9: Testing & Validation
**Files to Create:**

#### 9.1 Unit Tests for Delivery Selection
- **File:** `backend/tests/application/use_cases/test_delivery_selection.py`
- **Tests:**
  - Select posts newer than last_delivered_at
  - Fallback to latest post if none found
  - Filter out Ask HN / Show HN
  - Sort by score descending
  - Respect max_posts_per_user limit

#### 9.2 Unit Tests for Message Formatting
- **File:** `backend/tests/presentation/bot/test_digest_formatter.py`
- **Tests:**
  - Format message per Style 2 spec
  - Include position counter (1/N)
  - Extract domain from URL
  - Render inline keyboard
  - Handle long titles/summaries

#### 9.3 Integration Tests
- **File:** `backend/tests/integration/test_delivery_pipeline.py`
- **Tests:**
  - Create test user, posts, summaries
  - Run delivery pipeline
  - Verify Delivery records created
  - Verify user.last_delivered_at updated
  - Mock Telegram API calls (don't actually send)

#### 9.4 Manual E2E Test Script
- **File:** `backend/scripts/test_delivery_e2e.py`
- **Action:** Script to:
  1. Load real user & posts
  2. Format messages
  3. Optionally send to test user's Telegram
  4. Verify delivery tracking

---

## 🗂️ File Structure Summary

```
backend/
├── app/
│   ├── domain/
│   │   └── entities.py (no changes - Delivery entity exists as value object)
│   │
│   ├── application/
│   │   ├── interfaces/
│   │   │   ├── repositories.py (ADD: DeliveryRepository)
│   │   │   └── services.py
│   │   └── use_cases/
│   │       ├── delivery_selection.py (NEW)
│   │       ├── delivery_pipeline.py (NEW)
│   │       └── pipeline.py (MODIFY: add delivery step)
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   │   └── models.py (ADD: Delivery, Conversation; MODIFY: User)
│   │   ├── repositories/
│   │   │   └── postgres/
│   │   │       ├── delivery_repo.py (NEW)
│   │   │       └── conversation_repo.py (NEW)
│   │   ├── agents/
│   │   │   └── config.py (ADD: telegram settings)
│   │   └── services/
│   │       └── telegram_bot_service.py (NEW - wrapper around aiogram)
│   │
│   └── presentation/
│       ├── api/
│       │   ├── __init__.py
│       │   └── delivery.py (NEW - manual trigger endpoint)
│       └── bot/
│           ├── __init__.py
│           ├── bot.py (NEW - bot instance & setup)
│           ├── handlers/
│           │   ├── __init__.py
│           │   ├── delivery.py (NEW - send_digest_to_user)
│           │   └── callbacks.py (NEW - placeholder handlers)
│           ├── keyboards/
│           │   ├── __init__.py
│           │   └── inline.py (NEW - button builders)
│           └── formatters/
│               ├── __init__.py
│               └── digest_formatter.py (NEW - message formatting)
│
├── alembic/
│   └── versions/
│       └── {timestamp}_add_delivery_models.py (NEW)
│
├── tests/
│   ├── application/
│   │   └── use_cases/
│   │       └── test_delivery_selection.py (NEW)
│   ├── presentation/
│   │   └── bot/
│   │       └── test_digest_formatter.py (NEW)
│   └── integration/
│       └── test_delivery_pipeline.py (NEW)
│
└── scripts/
    └── test_delivery_e2e.py (NEW)
```

---

## 🔄 Execution Flow (Detailed)

### Trigger Point
**When:** After summarization pipeline completes (end of ingest phase)
**How:** Scheduled job or manual API call

### Step-by-Step Flow

```
START: run_delivery_pipeline()
│
├─ 1. Generate batch_id (UUID)
├─ 2. Load all User where status='active'
│
└─ For each user:
   │
   ├─ 3a. SELECT posts WHERE
   │      · created_at > user.last_delivered_at OR created_at IS MAX
   │      · type = 'story'
   │      · summary IS NOT NULL
   │      · is_dead = false
   │
   ├─ 3b. Sort by score DESC, limit to max_posts_per_user
   │
   ├─ 4. For each selected post:
   │    │
   │    ├─ 4a. Format message (Style 2)
   │    │      → "🔶 1/N · Title"
   │    │      → Domain
   │    │      → Summary
   │    │      → Score & comments
   │    │
   │    ├─ 4b. Create inline keyboard
   │    │      → [💬 Discuss] [🔗 Read] [⭐ Save]
   │    │      → [👍] [👎]
   │    │
   │    ├─ 4c. Send message to user.telegram_id
   │    │      → Capture message_id from response
   │    │      → Rate limit: 1 msg/sec
   │    │
   │    └─ 4d. Create Delivery record
   │           INSERT INTO deliveries (
   │             user_id, post_id, message_id,
   │             batch_id, delivered_at
   │           )
   │
   ├─ 5. Update user.last_delivered_at = now()
   │
   └─ 6. Log stats for this user

END: Return aggregated stats
     {
       batch_id: UUID,
       total_users: int,
       users_delivered: int,
       total_messages_sent: int,
       errors: List[str],
       duration: float
     }
```

---

## 🔌 API Contracts

### Endpoint: POST /api/deliveries/run

**Request:**
```json
{
  "force": false,          // Skip time checks, deliver to everyone
  "dry_run": false,        // Don't actually send Telegram messages
  "max_posts_per_user": 10, // Limit posts per user
  "skip_users": []         // Skip specific user IDs
}
```

**Response (200 OK):**
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_users": 42,
  "users_delivered": 38,
  "users_skipped": 4,
  "total_messages_sent": 278,
  "total_posts_delivered": 278,
  "errors": [
    {
      "user_id": 5,
      "reason": "Invalid telegram_id"
    }
  ],
  "duration_seconds": 45.3,
  "timestamp": "2026-02-14T15:30:00Z"
}
```

---

## 🧪 Testing Strategy

### Unit Tests (Isolated)
- **Delivery Selection:** Mock repo, test filtering logic
- **Message Formatting:** Test Style 2 format per spec
- **Keyboard Builder:** Test button creation
- **User Updates:** Test last_delivered_at timestamp

### Integration Tests (DB + Code)
- Create test users/posts
- Run delivery pipeline
- Verify DB records created
- **Mock Telegram API** (don't actually send)

### Manual E2E Test
- Use test user with real Telegram ID
- Run delivery pipeline
- Verify message in Telegram
- Check delivery records in DB
- Test button interactions (Phase 4)

---

## ⚠️ Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Telegram API rate limits | Implement 1 msg/sec delay |
| Invalid user telegram_id | Skip gracefully, log error |
| Bot token invalid | Fail fast with clear error |
| Message send timeout | Retry 3x with backoff |
| Long summaries overflow message | Truncate to fit Telegram limits |
| Duplicate deliveries | Track last_delivered_at per user |
| Users opt-out | Check status='paused' before sending |

---

## 📅 Implementation Order

### Phase A: Database & Repos (Foundation)
1. ✅ Create Delivery & Conversation models
2. ✅ Add User.last_delivered_at
3. ✅ Create Alembic migration
4. ✅ Implement DeliveryRepository
5. ✅ Update config with bot settings

### Phase B: Selection & Formatting (Logic)
6. ✅ Implement SelectPostsForDeliveryUseCase
7. ✅ Implement MessageFormatter (Style 2)
8. ✅ Implement InlineKeyboardBuilder

### Phase C: Bot Integration (Transport)
9. ✅ Create Bot instance & dispatcher
10. ✅ Implement send_digest_to_user handler
11. ✅ Create placeholder callback handlers
12. ✅ Implement rate limiting & error handling

### Phase D: Orchestration (Pipeline)
13. ✅ Implement DeliveryPipeline use case
14. ✅ Integrate into main Pipeline orchestrator
15. ✅ Create API endpoint /api/deliveries/run

### Phase E: Testing (Validation)
16. ✅ Unit tests for selection logic
17. ✅ Unit tests for message formatting
18. ✅ Integration tests with mock Telegram
19. ✅ Manual E2E test script

---

## ✅ Definition of Done

- [ ] All 9 tasks completed
- [ ] All database models created & migrated
- [ ] All use cases implemented with error handling
- [ ] All message formatting matches spec (Style 2)
- [ ] All inline buttons working (Phase 4 placeholders for some)
- [ ] Telegram integration functional
- [ ] Unit tests: 30+ passing
- [ ] Integration tests: 10+ passing
- [ ] Manual E2E test: successful
- [ ] Rate limiting: 1 msg/sec verified
- [ ] Error handling: tested (invalid token, timeout, etc.)
- [ ] Documentation: updated
- [ ] Code review: passed
- [ ] Ready for Phase 4 (interactive buttons)

---

## 🚀 Next Phase (Phase 4)

After delivery is complete, Phase 4 will implement:
- Discuss button callback handling
- Save/bookmark functionality
- Reaction button handling (👍 👎)
- Discussion state machine

---

**Plan Prepared By:** James (Full Stack Developer)
**Date:** 2026-02-14
**Status:** Ready for Implementation
**Estimated Effort:** 40-50 hours
**Target Completion:** 2 weeks
