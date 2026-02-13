# Epic 4: Interactive Elements

**Epic ID:** EPIC-004
**Priority:** P0 - Critical (MVP Core)
**Timeline:** 2 weeks (Sprint 4)
**Status:** Documented 📝
**Version:** 2.0 (HN Pal)

---

## Epic Goal

Implement fully functional inline button callbacks for user interactions - enabling discussions, bookmarks, reactions, and external links - transforming the bot from a broadcast tool into an interactive experience.

---

## Epic Description

### Product Vision Context

This epic brings HN Pal to life by making the digest interactive. Users can now tap buttons to start discussions, save posts for later, react to content, and open HN links. This is where the bot transitions from passive content delivery to active user engagement. The interactive system must:
- Handle button callbacks instantly (< 500ms)
- Trigger state transitions (IDLE → DISCUSSION)
- Persist user actions (bookmarks, reactions) to database
- Provide instant UI feedback (callback answers)
- Track engagement signals for future personalization

### What We're Building

A complete inline button system that:
- **💬 Discuss button** → Starts discussion, transitions to DISCUSSION state
- **⭐ Save button** → Toggle bookmark (save/unsave), updates `deliveries.is_saved`
- **👍👎 Reaction buttons** → Track interest signals, updates `deliveries.reaction`
- **🔗 Read button** → Opens HN post in browser (already working via URL button)
- **Auto-switch logic** → If already in DISCUSSION, save current → start new
- **Callback routing** → Type-safe handlers using aiogram CallbackData
- **UI feedback** → Instant visual confirmation (callback query answers)
- **/saved command** → List bookmarked posts with links

### Success Criteria

**User Experience:**
- Button taps respond instantly (< 500ms)
- State transitions seamless (no confusion)
- Bookmarks persist across sessions
- Reactions recorded accurately
- /saved command shows correct list

**Technical Performance:**
- Callback handling: < 500ms
- Database updates: < 200ms
- State transitions: < 100ms
- Concurrent button presses handled (no race conditions)
- Error rate: < 0.1%

**Engagement:**
- Discussion button click rate: > 15%
- Save button click rate: > 30%
- Reaction button click rate: > 40%
- /saved command usage: > 50% of users

---

## User Stories

### Story 4.1: Discussion Trigger & State Transition 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-4.0-interactive-elements.md` (Sub-activities 4.1-4.2)

**As a** user
**I want** to tap "💬 Discuss" button to start a conversation about a post
**So that** I can ask questions and explore the topic with AI assistance

**Acceptance Criteria:**
- [ ] Implement callback handler for `discuss:{hn_id}` callback data
- [ ] State transition logic:
  - **If IDLE:** Transition to DISCUSSION state
  - **If already in DISCUSSION:** Save current conversation → Start new discussion (auto-switch)
- [ ] Load post context:
  - Update `users.active_discussion_post_id = hn_id`
  - Store `discussion_started_at` in FSM state data
- [ ] Send discussion header message:
  ```
  📖 Discussing: PostgreSQL 18 Released
  ─────────────────────────────────
  Article loaded. Ask me anything!
  Tap 💬 Discuss on another post to switch.
  ```
- [ ] Auto-switch behavior (if already discussing):
  - End current conversation (save to `conversations` table)
  - Extract memory (Sprint 6 feature, placeholder for now)
  - Clear FSM state data for old post
  - Start new discussion with new post
  - Send: "Switched to discussing: {new_title}"
- [ ] Update FSM state in Redis:
  - State: `DISCUSSION`
  - Data: `{"active_post_id": hn_id, "discussion_started_at": "...", "last_message_at": "..."}`
- [ ] Handle errors:
  - Post not found → "Sorry, this post is unavailable."
  - Context loading failure → "Error starting discussion. Try again."
- [ ] Callback query answer (instant UI feedback):
  - Success: "Discussion started! 💬"
  - Auto-switch: "Switched discussion to: {title}"
  - Error: "Error: {message}"

**Technical Notes:**
- **Callback Data Format:** `discuss:{hn_id}` (e.g., `discuss:38543210`)
- **aiogram CallbackData:**
  ```python
  class DiscussCallback(CallbackData, prefix="discuss"):
      hn_id: int

  @router.callback_query(DiscussCallback.filter())
  async def discuss_handler(query: CallbackQuery, callback_data: DiscussCallback, state: FSMContext):
      hn_id = callback_data.hn_id
      # Transition to DISCUSSION state
      await state.set_state(BotStates.DISCUSSION)
      await state.update_data(active_post_id=hn_id, discussion_started_at=...)
      # Update database
      update_user(query.from_user.id, active_discussion_post_id=hn_id)
      # Send header message
      await query.message.answer("📖 Discussing: ...")
      await query.answer("Discussion started! 💬")
  ```
- **Auto-Switch Logic:**
  ```python
  current_state = await state.get_state()
  if current_state == BotStates.DISCUSSION:
      # Save current conversation
      await save_conversation(...)
      # Start new discussion
      await start_discussion(hn_id)
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 4.2: Bookmark & Reaction System 📝

**Status:** DOCUMENTED
**Activity:** `docs/activities/activity-4.0-interactive-elements.md` (Sub-activities 4.3-4.5)

**As a** user
**I want** to save posts for later and react with 👍👎
**So that** I can build a reading list and signal my interests

**Acceptance Criteria:**
- [ ] Implement **⭐ Save** button callback:
  - Callback data format: `save:{hn_id}` or `unsave:{hn_id}`
  - Toggle bookmark state in `deliveries.is_saved`
  - If saved → unsave (set `is_saved = false`, callback: "Removed from saved ✓")
  - If not saved → save (set `is_saved = true`, `saved_at = now()`, callback: "Saved! ⭐")
  - Update button text: `⭐ Save` ↔ `✓ Saved`
  - Handle race conditions (concurrent taps → last write wins)
- [ ] Implement **👍 Upvote** callback:
  - Callback data: `react:up:{hn_id}`
  - Update `deliveries.reaction = 'up'`, `reacted_at = now()`
  - If already upvoted → remove reaction (`reaction = NULL`)
  - Callback answer: "Upvoted! 👍" or "Reaction removed"
  - Track as interest signal (future personalization)
- [ ] Implement **👎 Downvote** callback:
  - Callback data: `react:down:{hn_id}`
  - Update `deliveries.reaction = 'down'`, `reacted_at = now()`
  - If already downvoted → remove reaction (`reaction = NULL`)
  - Callback answer: "Downvoted 👎" or "Reaction removed"
- [ ] Instant UI feedback:
  - Update button appearance (highlight selected reaction)
  - Callback query answer (toast notification)
- [ ] Implement **/saved** command:
  - Query `deliveries` table: `WHERE user_id = ? AND is_saved = true`
  - Format list:
    ```
    📚 Your Saved Posts (5)

    1. PostgreSQL 18 Released
       news.ycombinator.com/item?id=38543210

    2. Why We Left Kubernetes
       news.ycombinator.com/item?id=38542105

    ...

    Tap 💬 Discuss to start a conversation!
    ```
  - If no saved posts: "You haven't saved any posts yet. Tap ⭐ Save on posts you want to read later!"
  - Pagination if > 10 saved posts (future enhancement)
- [ ] Database transactions (avoid race conditions)
- [ ] Error handling (DB failures, invalid hn_id)

**Technical Notes:**
- **Callback Data:**
  ```python
  class SaveCallback(CallbackData, prefix="save"):
      hn_id: int

  class ReactCallback(CallbackData, prefix="react"):
      direction: str  # "up" or "down"
      hn_id: int
  ```
- **Toggle Logic:**
  ```python
  delivery = get_delivery(user_id, hn_id)
  if delivery.is_saved:
      delivery.is_saved = False
      message = "Removed from saved ✓"
  else:
      delivery.is_saved = True
      delivery.saved_at = now()
      message = "Saved! ⭐"
  db.commit()
  await query.answer(message)
  ```
- **Button Update (Dynamic):**
  ```python
  # Update button text after save/unsave
  keyboard = InlineKeyboardMarkup(...)
  await query.message.edit_reply_markup(reply_markup=keyboard)
  ```

**Current State:**
- 📝 Activity document complete
- 🔄 Implementation pending

---

### Story 4.3: External Link Handler 📝

**Status:** ALREADY WORKING ✅
**Activity:** `docs/activities/activity-4.0-interactive-elements.md` (Sub-activity 4.3)

**As a** user
**I want** to tap "🔗 Read" to open the HN post in my browser
**So that** I can view the full discussion and comments

**Acceptance Criteria:**
- [x] 🔗 Read button implemented as **URL button** (Telegram native)
- [x] Link format: `https://news.ycombinator.com/item?id={hn_id}`
- [x] Opens in browser automatically (no callback needed)
- [ ] Optional: Track click events (analytics)
  - Callback data: `track:read:{hn_id}` (invisible to user)
  - Log to database or analytics service
  - Don't block user action (async logging)

**Technical Notes:**
- **URL Button (Telegram Native):**
  ```python
  InlineKeyboardButton(
      text="🔗 Read",
      url=f"https://news.ycombinator.com/item?id={hn_id}"
  )
  ```
- **No callback needed** - Telegram handles automatically
- **Click Tracking (Optional):**
  - Use Telegram Bot API `getUpdates` to detect link clicks (not reliable)
  - Alternative: Add UTM parameters to URL, track on HN side (not possible)
  - **Recommendation:** Skip click tracking for MVP, add in future if needed

**Current State:**
- ✅ Already implemented in Sprint 3
- ⏳ Click tracking optional (future enhancement)

---

## Technical Stack

**Bot Framework:**
- **aiogram 3.x** - Callback query handlers
- **aiogram.filters.callback_data** - Type-safe callback routing

**Database:**
- **PostgreSQL** - `deliveries` table (bookmarks, reactions)
- **SQLAlchemy** - ORM with transactions

**State Management:**
- **Redis** - FSM state storage
- **aiogram FSM** - State transitions

---

## Risks & Mitigation

### Risk 1: State Management Bugs
**Risk:** FSM transitions incorrect, users stuck in wrong state
**Mitigation:**
- Thorough testing of all state transitions
- Logging all state changes with timestamps
- Manual reset tool (admin command: `/reset_state`)
- /start command always resets to IDLE (escape hatch)
- Monitor FSM state distribution (alert if > 10% in unexpected state)

### Risk 2: Database Consistency (Concurrent Clicks)
**Risk:** User taps button multiple times → race condition
**Mitigation:**
- Use database transactions (SQLAlchemy `with session.begin()`)
- Last write wins (acceptable for bookmarks/reactions)
- Add unique constraint: `UNIQUE(user_id, post_id)` on deliveries
- Test with rapid button clicking (manual QA)

### Risk 3: Callback Query Timeout
**Risk:** Slow callback handling → Telegram shows "processing" spinner forever
**Mitigation:**
- Always call `await query.answer()` within 5 seconds (Telegram limit)
- Answer immediately, then process async if needed
- Handle exceptions gracefully (answer with error message)
- Monitor callback latency (alert if > 1 second average)

### Risk 4: Button State Desync
**Risk:** Button text shows "Saved" but database shows not saved
**Mitigation:**
- Always update button after database write (edit_reply_markup)
- Use transactions (atomic update + button change)
- Refresh button state on error (reload from DB)
- Test edge cases (rapid clicks, network failures)

### Risk 5: /saved Command Performance
**Risk:** Loading saved posts slow if user has 1000+ bookmarks
**Mitigation:**
- Limit query: `LIMIT 100` (show first 100)
- Add pagination (inline buttons: « Previous | Next »)
- Index on `deliveries (user_id, is_saved) WHERE is_saved = true`
- Cache saved post count in Redis (invalidate on save/unsave)

---

## Dependencies

**External:**
- Telegram Bot API (callback query handling)
- PostgreSQL (deliveries table)
- Redis (FSM state)

**Internal:**
- Epic 3 (Bot Foundation) - needs bot running, inline buttons displayed
- Database migration (deliveries table with is_saved, reaction columns)

---

## Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] All inline buttons functional (Discuss, Save, 👍👎, Read)
- [ ] State transitions working (IDLE ↔ DISCUSSION)
- [ ] Auto-switch logic implemented (save previous → start new)
- [ ] Bookmark system operational (save/unsave toggle)
- [ ] Reaction tracking in database (up/down)
- [ ] /saved command lists bookmarked posts
- [ ] UI feedback instant (callback query answers)
- [ ] Tested with concurrent button presses (no race conditions)
- [ ] Error handling tested (DB failures, invalid data)
- [ ] Code reviewed and merged
- [ ] **MILESTONE:** Interactive bot working! 🎉

---

## Success Metrics (Post-Launch)

**User Engagement:**
- Discussion button click rate: > 15%
- Save button click rate: > 30%
- Reaction button click rate: > 40%
- /saved command usage: > 50% of users

**Technical Performance:**
- Callback handling latency: < 500ms average
- Database update latency: < 200ms
- State transition latency: < 100ms
- Error rate: < 0.1%

**Quality:**
- Button state accuracy: 100% (no desyncs)
- Zero race condition bugs reported
- User satisfaction: 4/5+ (beta feedback)

---

## Notes

- **Priority:** Callback handling must be fast (< 500ms) for good UX
- **State Transitions:** Test edge cases thoroughly (concurrent clicks, rapid state changes)
- **Database Transactions:** Critical for data consistency
- **Button Updates:** Always refresh UI after database write
- **Error Handling:** Always answer callback query (even on error)
- **Future Enhancement:** Personalized digest ranking based on reactions (Sprint 6)

---

**Next Epic:** Epic 5 - Discussion System
**Depends On:** Epic 3 (Bot Foundation), Epic 4 (Interactive Elements)
**Prepared By:** Bob (Scrum Master) 🏃
**Date:** 2026-02-13
**Version:** 2.0 - HN Pal Telegram Bot
