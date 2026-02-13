# Activity 4.0: Interactive Elements & Callback System

## Overview

Implement the interactive UI elements for Hacker News posts delivered via Telegram. This phase focuses on the inline button grid that accompanies every post in the digest, and the callback routing system that handles user interactions for discussing, reading, saving, and reacting to posts.

---

## Prerequisites

- [Activity 3.0: Telegram Bot Foundation](activity-3.0-telegram-bot-foundation.md) (Bot initialized, FSM ready) ✅
- PostgreSQL schema with `deliveries` and `user_saved_posts` tables 🔄
- Activity 2.5: LLM Client integration (for discussion context) ⏳

---

## Objectives

1. **Standardized Button Grid**: Implement a consistent layout for all post deliveries.
2. **Callback Routing**: Set up a dedicated `callback_router` for clean interaction handling.
3. **Discussion Trigger**: Connect the "Discuss" button to the FSM state transition.
4. **Link Handling**: Direct users to source URLs and HN discussion pages.
5. **Bookmark System**: Implement "Save" functionality with persistent storage.
6. **Reaction Logging**: Capture 👍/👎 feedback for the future Memory System.

---

## Technical Details

### Inline Keyboard Layout

Every post message will have an attached `InlineKeyboardMarkup` with the following structure:

| Row | Button | Callback Data | Description |
| :--- | :--- | :--- | :--- |
| **1** | 💬 Discuss | `discuss:{post_id}` | Starts/switches to conversation mode |
| **1** | 🔗 Read | `N/A (URL Button)` | Direct link to the source article |
| **1** | ⭐ Save | `save:{post_id}` | Toggles bookmark for the user |
| **2** | 👍 | `react:up:{post_id}` | Positive interest feedback |
| **2** | 👎 | `react:down:{post_id}` | Negative interest feedback |

### Callback Data Factory

Using `aiogram.filters.callback_data.CallbackData` for type-safe callback handling:

```python
from aiogram.filters.callback_data import CallbackData

class PostAction(CallbackData, prefix="post"):
    action: str  # "discuss", "save", "react_up", "react_down"
    post_id: int
```

---

## Implementation Flow

### 1. General Handler Pattern

Each callback handler should follow this pattern:

1. **Extract post_id**: From callback data.
2. **Validate**: Ensure user and post exist.
3. **Action**: Update database or FSM state.
4. **Feedback**: Always call `callback_query.answer()` (with text if needed).
5. **UI Update**: Optionally update the message (e.g., change ⭐ to 🌟).

### 2. Activity 4.2: Discussion Trigger (`discuss:{post_id}`)

- If user is in `IDLE`:
  1. Set state to `DISCUSSION`.
  2. Store `current_post_id` in FSM data.
  3. Send "Entering discussion for..." greeting.
- If user is in `DISCUSSION` with *another* post:
  1. Save current conversation.
  2. Switch `current_post_id`.
  3. Update user.

### 3. Activity 4.4: Bookmark System (`save:{post_id}`)

- Toggle logic:
  - Check if `(user_id, post_id)` exists in `user_saved_posts`.
  - If exists: Remove (Unsave).
  - If not: Add (Save).
- Feedback: `callback_query.answer("Saved to /saved list", show_alert=False)`.

---

## UI/UX Considerations

- **Latency**: User should get immediate feedback via `answer_callback_query` (the spinning icon stops).
- **Visual State**: When a post is saved, the button label should ideally toggle (e.g., "⭐ Save" → "🌟 Saved").
- **Clarity**: Use clear emojis to distinguish actions from links.

---

## Acceptance Criteria

- [ ] `callback_router` registered in the main bot dispatcher.
- [ ] Posts are delivered with the correct 2-row button grid.
- [ ] "Discuss" button successfully triggers `DISCUSSION` state.
- [ ] Source links open correctly in external browser or Telegram In-App browser.
- [ ] "Save" button updates the `user_saved_posts` table.
- [ ] Reactions (👍/👎) are logged in the `deliveries` table.
- [ ] All buttons provide feedback via `answer_callback_query`.

---

## Sub-Activities

- **4.1: Inline Button Layout Implementation**
- **4.2: Discussion State Transition Handler**
- **4.3: External Link Logic**
- **4.4: Bookmark Database Integration**
- **4.5: Reaction & Sentiment Tracking**
- **4.6: Comprehensive UI Polish & Feedback**
