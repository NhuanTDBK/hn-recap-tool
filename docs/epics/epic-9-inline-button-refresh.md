# Epic 9: Inline Button Refresh

**Epic ID:** EPIC-009
**Priority:** P1 - High
**Timeline:** 1 sprint
**Status:** Draft
**Version:** 1.0

---

## Epic Goal

Simplify and refresh the inline button layout on digest messages — replacing the current two-row keyboard with a compact, menu-swappable design that prioritises content expansion and quick feedback, while deferring the Discuss feature to a future release.

---

## Epic Description

### Product Vision Context

User feedback and usage data show that the **Discuss** button sees low engagement relative to reactions and saves. Meanwhile, users frequently want to read the full summary without leaving Telegram. This epic:

1. **Adds a "Show More" button** — expands the truncated summary inline via `callback_query` + `edit_message_text`, logged as a `show_more` event.
2. **Keeps Save** — same logic, same callback, no regression.
3. **Groups Thumb-up / Thumb-down behind an "Actions" button** — tapping Actions swaps the keyboard to a reaction menu with a Back button to return.
4. **Removes Discuss from the UI** — the `handle_discuss` handler and its FSM logic are **preserved in code** (no deletion) but the button is no longer rendered. Discuss will return in a future version.

### Keyboard Interaction

**Default menu (rendered on every delivered post):**

```
[ 📖 More ]  [ 🔖 Save ]  [ ⚡ Actions ]
```

**After tapping ⚡ Actions → keyboard swaps to:**

```
[ 👍 Good Response ]  [ 👎 Bad Response ]  [ « Back ]
```

**After tapping « Back → returns to default menu.**

This replaces the current two-row layout:

```
Row 1: [ 💬 Discuss ]  [ 👍 ]  [ 👎 ]
Row 2: [ 🔖 Save for later ]
```

### What We're Building

| Button | Menu | Behaviour | Event logged |
|--------|------|-----------|-------------|
| 📖 More | Default | `edit_message_text` to show full summary | `show_more` in `user_activity_log` |
| 🔖 Save | Default | Same as today | `save` in `user_activity_log` |
| ⚡ Actions | Default | Swap keyboard to reactions menu | — |
| 👍 Good Response | Reactions | Same as today | `rate_up` in `user_activity_log` |
| 👎 Bad Response | Reactions | Same as today | `rate_down` in `user_activity_log` |
| « Back | Reactions | Swap keyboard back to default menu | — |

### Success Criteria

**User Experience:**
- Clean three-button row renders correctly on mobile and desktop Telegram clients
- "Show More" expands summary in-place without sending a new message
- Menu swap between Default ↔ Reactions is instant (< 500 ms)
- Discuss handler still works if called programmatically (no code deleted)

**Technical:**
- `user_activity_log` records `show_more` events correctly
- No regressions on existing `save`, `rate_up`, `rate_down` flows
- No regressions on Discuss FSM (handler preserved, just not triggered from UI)

---

## User Stories

### Story 9.1: Inline Button Redesign — Show More, Actions Menu, Remove Discuss UI

Single story covering the full keyboard redesign. See `docs/stories/9.1.story.md`.

---

## Dependencies

**Internal:**
- Epic 4 (Interactive Elements) — existing callback infrastructure
- Story 8.4 — `user_activity_log` table and `PostgresActivityLogRepository` (must be deployed)

**External:**
- Telegram Bot API (`callback_query`, `edit_message_text`, `edit_message_reply_markup`)

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing Discuss button confuses existing users | Low | Low | Discuss was low-engagement; button simply disappears, no error state |
| Full summary exceeds Telegram 4096-char limit after expansion | Medium | Medium | Truncate expanded text at 4000 chars with "..." if needed |
| `edit_message_text` fails on old messages (Telegram 48-hour edit window) | Low | Low | Catch `MessageNotModified` / `MessageCantBeEdited` errors gracefully |
| Menu swap feels sluggish on slow connections | Low | Low | Answer callback immediately, then edit keyboard; both are lightweight API calls |

---

## Definition of Done

- [ ] Story 9.1 completed with all acceptance criteria met
- [ ] Default three-button keyboard renders on iOS, Android, and desktop Telegram
- [ ] "Show More" expands summary inline; `show_more` event logged
- [ ] Actions → Reactions → Back menu swap works correctly
- [ ] Save, Thumb-up, Thumb-down work exactly as before
- [ ] Discuss button removed from UI; handler code preserved
- [ ] All existing callback tests pass (no regressions)
- [ ] Code reviewed and merged

---

## Notes

- **Discuss deferral rationale:** The discussion feature requires full article context loading, FSM state management, and LLM integration (Epic 5). Current usage does not justify the UX cost of the button. It will return in a future version with a different interaction pattern.
- **Future:** When Discuss returns, it may use a `/discuss` command or a long-press interaction rather than an inline button.

---

**Prepared By:** BMad Master
**Date:** 2026-02-27
