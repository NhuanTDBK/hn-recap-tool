# Story 9.1 Implementation Checklist
## Inline Button Redesign — Show More, Actions Menu, Remove Discuss UI

**Story ID:** 9.1
**Epic:** Epic 9 — Inline Button Refresh
**Status:** Ready for Implementation
**Implementation Phase:** Sprint TBD

---

## Pre-Implementation Verification

- [ ] Story 9.1 approved and ready (`docs/stories/9.1.story.md`)
- [ ] Epic 9 design finalized (`docs/epics/epic-9-inline-button-refresh.md`)
- [ ] HTML mockup reviewed (`docs/mockups/telegram-buttons-demo.html`)
- [ ] All 9 Acceptance Criteria understood
- [ ] All 8 Tasks identified and mapped
- [ ] Current button implementation reviewed in code (`presentation/bot/formatters/digest_formatter.py`, `presentation/bot/handlers/callbacks.py`)
- [ ] Existing tests identified for regression verification

---

## Task 1: Keyboard Builder Methods
**AC: 1, 4, 6 | Files: digest_formatter.py | Complexity: Low | Est. Time: 1-2 hours**

### Subtasks

- [ ] **1.1 Understand current implementation**
  - [ ] Read `InlineKeyboardBuilder.build_post_keyboard()` (current two-row layout)
  - [ ] Read `InlineKeyboardBuilder.build_batch_keyboard()` (unchanged, verify)
  - [ ] Understand callback_data format used

- [ ] **1.2 Rewrite `build_post_keyboard()` for default menu**
  - [ ] Change return value to single-row layout: `[ 📖 More ] [ 🔖 Save ] [ ⚡ Actions ]`
  - [ ] Ensure correct callback_data: `show_more_{post_id}`, `save_post_{post_id}`, `actions_{post_id}`
  - [ ] Remove `💬 Discuss` button completely
  - [ ] Test locally: button renders correctly

- [ ] **1.3 Add `build_post_keyboard_without_more()` method**
  - [ ] Returns two-button layout: `[ 🔖 Save ] [ ⚡ Actions ]`
  - [ ] Use when summary already expanded (AC-2)
  - [ ] Same callback_data as default menu (minus show_more)

- [ ] **1.4 Add `build_reactions_keyboard()` method**
  - [ ] Returns three-button layout: `[ 👍 Good Response ] [ 👎 Bad Response ] [ « Back ]`
  - [ ] Callback_data: `react_up_{post_id}`, `react_down_{post_id}`, `back_{post_id}`
  - [ ] Test locally: renders correctly on mobile and desktop

- [ ] **1.5 Verify `build_batch_keyboard()` unchanged**
  - [ ] Confirm "📖 View Posts" button still present
  - [ ] No modifications to batch header

- [ ] **1.6 Code review checkpoint**
  - [ ] All three methods follow existing code patterns
  - [ ] Button labels match design spec exactly
  - [ ] Callback data patterns consistent
  - [ ] Type hints and docstrings added

---

## Task 2: DigestMessageFormatter — Full Summary Method
**AC: 2 | Files: digest_formatter.py | Complexity: Low | Est. Time: 30 mins - 1 hour**

### Subtasks

- [ ] **2.1 Understand current `format_post_message()` implementation**
  - [ ] Identify where summary is truncated (SUMMARY_TRUNCATE_LENGTH = 500)
  - [ ] Understand message structure (title, links, summary, stats)

- [ ] **2.2 Add `format_post_message_full()` method**
  - [ ] Copy structure from `format_post_message()`
  - [ ] **Remove the truncation logic** — no `SUMMARY_TRUNCATE_LENGTH` limit
  - [ ] Apply 4000-char safety limit (Telegram message limit)
  - [ ] Truncate with "..." if exceeding 4000 chars
  - [ ] Return fully formatted message text

- [ ] **2.3 Test the new method**
  - [ ] Test with short summary (< 500 chars)
  - [ ] Test with long summary (> 1000 chars)
  - [ ] Test with very long summary (> 4000 chars) — verify truncation with "..."
  - [ ] Verify message formatting matches `format_post_message()`

- [ ] **2.4 Code review checkpoint**
  - [ ] Method follows existing patterns
  - [ ] Docstring clearly explains full vs truncated
  - [ ] Safety limit explanation in comments

---

## Task 3: Show More Handler
**AC: 2, 8 | Files: callbacks.py | Complexity: Medium | Est. Time: 2-3 hours**

### Subtasks

- [ ] **3.1 Understand existing callback handler patterns**
  - [ ] Study `handle_save_post` (simple pattern)
  - [ ] Study `handle_react_up` (with DB transaction pattern)
  - [ ] Understand error handling approach

- [ ] **3.2 Register `handle_show_more` handler**
  - [ ] Add decorator: `@callback_router.callback_query(F.data.startswith("show_more_"))`
  - [ ] Extract post_id from callback_data (`callback.data.replace("show_more_", "")`)
  - [ ] Extract telegram_id from callback.from_user.id

- [ ] **3.3 Implement core logic**
  - [ ] Load post from database (same pattern as `handle_discuss`)
  - [ ] Call `formatter.format_post_message_full(post, position, total)` to get full text
  - [ ] Call `callback.message.edit_message_text(text=full_text, reply_markup=keyboard_without_more)`
  - [ ] Handle `MessageNotModified` and `MessageCantBeEdited` errors gracefully (AC-8)

- [ ] **3.4 Implement activity log insertion**
  - [ ] Use `PostgresActivityLogRepository(session)`
  - [ ] Call `log_activity(user_id, post_id, "show_more")`
  - [ ] Wrap in try/except to avoid failing user experience (AC-8)
  - [ ] Log warning if insertion fails

- [ ] **3.5 Implement callback alert**
  - [ ] Call `callback.answer("📖 Full summary loaded", show_alert=False)`
  - [ ] This provides instant UI feedback

- [ ] **3.6 Test the handler**
  - [ ] Send a digest, tap 📖 More button
  - [ ] Verify message text expands to full summary
  - [ ] Verify "More" button is removed from keyboard
  - [ ] Verify `user_activity_log` has new row with `action_type = "show_more"`
  - [ ] Test error cases (message too old, DB error)

- [ ] **3.7 Code review checkpoint**
  - [ ] Error handling matches existing handlers
  - [ ] Logging level appropriate
  - [ ] No race conditions or edge cases missed

---

## Task 4: Actions Menu Swap Handler
**AC: 4 | Files: callbacks.py | Complexity: Low | Est. Time: 1-1.5 hours**

### Subtasks

- [ ] **4.1 Register `handle_actions_menu` handler**
  - [ ] Add decorator: `@callback_router.callback_query(F.data.startswith("actions_"))`
  - [ ] Extract post_id from callback_data

- [ ] **4.2 Implement menu swap logic**
  - [ ] Build reactions keyboard: `builder.build_reactions_keyboard(post_id)`
  - [ ] Call `callback.message.edit_message_reply_markup(reply_markup=keyboard_dict)`
  - [ ] Handle `MessageNotModified` / `MessageCantBeEdited` errors (best-effort)

- [ ] **4.3 Implement callback alert**
  - [ ] Call `callback.answer("Choose a reaction", show_alert=False)`

- [ ] **4.4 Test the handler**
  - [ ] Tap ⚡ Actions button
  - [ ] Verify keyboard swaps to reactions menu
  - [ ] Verify only three buttons shown: 👍 Good Response, 👎 Bad Response, « Back

---

## Task 5: Back Button Handler
**AC: 6 | Files: callbacks.py | Complexity: Low-Medium | Est. Time: 1-2 hours**

### Subtasks

- [ ] **5.1 Register `handle_back_to_default` handler**
  - [ ] Add decorator: `@callback_router.callback_query(F.data.startswith("back_"))`
  - [ ] Extract post_id from callback_data

- [ ] **5.2 Determine if summary was expanded**
  - [ ] Check message text length: `len(callback.message.text) > SUMMARY_TRUNCATE_LENGTH + 50`
  - [ ] If true → use `build_post_keyboard_without_more()`
  - [ ] If false → use `build_post_keyboard()`

- [ ] **5.3 Implement menu swap logic**
  - [ ] Build appropriate default keyboard based on expansion state
  - [ ] Call `callback.message.edit_message_reply_markup(reply_markup=keyboard_dict)`

- [ ] **5.4 Implement callback alert**
  - [ ] Call `callback.answer(show_alert=False)` — silent, no alert shown

- [ ] **5.5 Test the handler**
  - [ ] From default menu, tap ⚡ Actions
  - [ ] Verify reactions menu shown
  - [ ] Tap « Back
  - [ ] Verify returns to default menu silently
  - [ ] Test from expanded state (More already tapped)
  - [ ] Verify « Back returns to menu without More button

---

## Task 6: Modify React Handlers to Swap Back
**AC: 5 | Files: callbacks.py | Complexity: Medium | Est. Time: 1.5-2 hours**

### Subtasks

- [ ] **6.1 Review `handle_react_up` implementation**
  - [ ] Understand existing logic (DB update, activity log, callback alert)
  - [ ] Identify where to add keyboard swap

- [ ] **6.2 Add swap-back logic to `handle_react_up`**
  - [ ] After existing reaction logic completes successfully
  - [ ] Determine if summary was expanded (same check as Task 5)
  - [ ] Build appropriate default keyboard
  - [ ] Call `callback.message.edit_message_reply_markup()` in try/except (best-effort, don't fail UX)

- [ ] **6.3 Add swap-back logic to `handle_react_down`**
  - [ ] Same pattern as `handle_react_up`

- [ ] **6.4 Verify existing behavior preserved**
  - [ ] `deliveries.reaction` still updated (no regression)
  - [ ] `user_activity_log` still inserted with `"rate_up"` / `"rate_down"` (no regression)
  - [ ] Callback alerts unchanged ("👍 Summary rated helpful..." / "👎 Noted...")

- [ ] **6.5 Test the handlers**
  - [ ] From reactions menu, tap 👍 Good Response
  - [ ] Verify reaction recorded in `deliveries.reaction`
  - [ ] Verify activity logged
  - [ ] Verify keyboard swaps back to default menu
  - [ ] Test from expanded state (More already tapped)
  - [ ] Verify menu returned without More button
  - [ ] Repeat for 👎 Bad Response

---

## Task 7: Verify Discuss Handler Preserved
**AC: 7 | Files: callbacks.py | Complexity: Low | Est. Time: 30 mins**

### Subtasks

- [ ] **7.1 Confirm `handle_discuss` still registered**
  - [ ] Decorator `@callback_router.callback_query(F.data.startswith("discuss_"))` present
  - [ ] Handler implementation unchanged

- [ ] **7.2 Confirm `BotStates.DISCUSSION` FSM state still defined**
  - [ ] Check `presentation/bot/states.py` (or wherever defined)
  - [ ] No deletion or modification

- [ ] **7.3 Verify discuss handler can still be called**
  - [ ] Manually craft a `discuss_{post_id}` callback (e.g., via Telegram message edit)
  - [ ] Verify handler responds and transitions to DISCUSSION state
  - [ ] Verify no errors or broken code paths

- [ ] **7.4 Code review checkpoint**
  - [ ] No accidental deletions in callbacks.py
  - [ ] Imports still include all necessary FSM state classes

---

## Task 8: Regression Testing
**AC: 3, 5, 7, 9 | Files: test suite | Complexity: Medium | Est. Time: 2-3 hours**

### Subtasks

- [ ] **8.1 Run existing callback tests**
  - [ ] Execute all tests in `tests/unit/presentation/bot/handlers/test_callbacks.py`
  - [ ] All tests must PASS (no regressions)
  - [ ] Note: `handle_discuss`, `handle_react_up`, `handle_react_down` tests may need updates for keyboard swap logic

- [ ] **8.2 Test 🔖 Save flow end-to-end**
  - [ ] Deliver a digest post
  - [ ] Tap 🔖 Save button
  - [ ] Verify callback alert shown
  - [ ] Verify `user_activity_log` row with `action_type = "save"` created
  - [ ] Verify keyboard unchanged

- [ ] **8.3 Test 👍/👎 flow end-to-end (via Actions menu)**
  - [ ] Deliver digest post
  - [ ] Tap ⚡ Actions
  - [ ] Verify reactions menu shown
  - [ ] Tap 👍 Good Response
  - [ ] Verify callback alert shown
  - [ ] Verify `deliveries.reaction = "up"` updated
  - [ ] Verify `user_activity_log` row with `action_type = "rate_up"` created
  - [ ] Verify keyboard swaps back to default menu
  - [ ] Repeat for 👎 Bad Response

- [ ] **8.4 Test 📖 More flow end-to-end**
  - [ ] Deliver digest post with truncated summary
  - [ ] Tap 📖 More
  - [ ] Verify message text expands to full summary
  - [ ] Verify More button removed from keyboard
  - [ ] Verify `user_activity_log` row with `action_type = "show_more"` created
  - [ ] Verify other buttons still functional (Save, Actions)

- [ ] **8.5 Test Discuss handler still works**
  - [ ] Manually trigger `discuss_{post_id}` callback (old cached message or manual test)
  - [ ] Verify handler responds correctly
  - [ ] Verify FSM transitions to DISCUSSION state

- [ ] **8.6 Test batch header keyboard unchanged**
  - [ ] Verify "📖 View Posts" button still present
  - [ ] No modifications to batch message

- [ ] **8.7 Test edge cases**
  - [ ] Rapid button clicking (multiple taps within 500ms)
  - [ ] Very old messages (> 48 hours) — `edit_message_text` should fail gracefully
  - [ ] Network failures / DB errors during callback handling
  - [ ] Very long summaries (> 4000 chars) — verify truncation with "..."

- [ ] **8.8 Verify no console errors**
  - [ ] Check application logs for any warnings / errors
  - [ ] Ensure no unhandled exceptions

---

## Post-Implementation Verification

- [ ] All 8 tasks completed and verified
- [ ] All 9 Acceptance Criteria met
- [ ] Existing tests all passing (no regressions)
- [ ] New test coverage added for: `handle_show_more`, `handle_actions_menu`, `handle_back_to_default`
- [ ] Code review completed
- [ ] All files committed with clear commit message

---

## Files Touched

- `backend/app/presentation/bot/formatters/digest_formatter.py` — keyboard builders, message formatter
- `backend/app/presentation/bot/handlers/callbacks.py` — three new handlers, two modified handlers
- `tests/unit/presentation/bot/handlers/test_callbacks.py` — new tests (optional but recommended)

---

## Rollback Steps (if needed)

1. Revert `build_post_keyboard()` to two-row layout
2. Remove new handlers: `handle_show_more`, `handle_actions_menu`, `handle_back_to_default`
3. Revert react handler modifications (remove swap-back logic)
4. Verify `handle_discuss` still functional
5. All data tables unchanged — safe rollback

---

## Sign-Off

- **Assigned to:** [Developer Name]
- **Start Date:** [Date]
- **Target Completion:** [Date]
- **Reviewed by:** [Code Reviewer]
- **QA Verified by:** [QA Tester]

---

**Status: READY FOR IMPLEMENTATION** ✅
