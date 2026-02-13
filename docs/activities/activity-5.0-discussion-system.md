# Activity 5.0: Discussion System & Agent Integration

## Overview

Implement the core conversational capability of HN Pal. This phase focuses on the "Discussion State," where the bot shifts from a broadcast medium to an interactive AI agent. When a user taps "💬 Discuss," the bot loads the full article context, the user's past memories, and past related conversations to provide a multi-turn, context-aware discussion experience.

---

## Prerequisites

- [Activity 3.0: Telegram Bot Foundation](activity-3.0-telegram-bot-foundation.md) (States and transitions) ✅
- [Activity 4.0: Interactive Elements](activity-4.0-interactive-elements.md) (Discuss button trigger) ✅
- [Activity 2.5: LLM Client Integration](activity-2.5-llm-client-integration.md) (OpenAI Agents SDK) ⏳
- S3/RocksDB storage with markdown content ready.

---

## Objectives

1. **Context Loading**: Efficiently retrieve markdown content and user memory for the active post.
2. **Multi-turn Conversation**: Implement the loop where user messages are routed to the `DiscussionAgent`.
3. **Session Management**: Handle the 30-minute inactivity timeout and explicit discussion switching.
4. **Agent Prompting**: Design the system prompt for the `DiscussionAgent` to act as a knowledgeable HN peer.
5. **Conversation Persistence**: Save logs to the `conversations` table for history and memory extraction.

---

## Technical Architecture

### The Discussion Loop

When a message is received in `State.DISCUSSION`:

1.  **Identify Post**: Retrieve `active_post_id` from FSM data.
2.  **Fetch Context**:
    - **Article**: Load `.md` from storage (RocksDB/S3).
    - **Memory**: Query `memory` table for user-specific facts/interests.
    - **History**: Load the last N messages of the *current* conversation.
3.  **Agent Invocation**: Wrap context and user message into the `DiscussionAgent` call.
4.  **Reply & Log**: Send the agent response to Telegram and append both messages to the database.

### State Transition Logic

```python
async def switch_discussion(user_id, new_post_id):
    # 1. Close current discussion
    await finalize_discussion(user_id)
    
    # 2. Update FSM
    await state.update_data(active_post_id=new_post_id)
    
    # 3. Initialize new session
    # ... send header "📖 Discussing: [Title]" ...
```

---

## Implementation Details

### 1. Discussion Header

When entering a discussion, send a pinned-style message (or distinct formatting) to clearly signal the state change:

```text
📖 Discussing: [Post Title]
───────────────────
Article context loaded. Ask me anything!
Tap "Discuss" on another post to switch.
```

### 2. Inactivity Timeout (30 min)

- Use a background task or a timestamp check on incoming messages.
- If `now - last_message_time > 30m`:
  - Call `finalize_discussion`.
  - Notify user: "Discussion timed out. Moving back to IDLE."
  - Reset FSM state.

### 3. Agent System Prompt

The `DiscussionAgent` should:

- Use the provided markdown as the primary source of truth.
- Reference the user's specific interests (e.g., "Since you're interested in Rust...").
- Mantain a "knowledgeable pier" persona—curious, critical, and objective.

---

## Database Integration

**Table: `conversations`**
- `user_id`: Reference to users.
- `post_id`: Reference to posts.
- `messages`: JSONB array of `{role, content, timestamp}`.
- `token_usage`: Tracked for billing/analytics.

---

## Acceptance Criteria

- [ ] Successful routing of messages to LLM when in `DISCUSSION` state.
- [ ] Agent correctly answers questions about the specific markdown content.
- [ ] Tapping "Discuss" on Post B while discussing Post A saves A and starts B.
- [ ] Conversations are persisted correctly in PostgreSQL.
- [ ] 30-minute timeout resets the state to `IDLE`.
- [ ] Header message is sent upon starting any new discussion.

---

## Sub-Activities

- **5.1: Context Retrieval Engine (Storage + Memory)**
- **5.2: DiscussionAgent System Prompt & Configuration**
- **5.3: Session Persistent Storage (DB Integration)**
- **5.4: State Transition & Switch Logic**
- **5.5: Inactivity Timeout Background Worker**
- **5.6: Error Handling (Large context, API rate limits)**
- **5.7: Conversation UI Polish (Markdown rendering, streaming responses)**
