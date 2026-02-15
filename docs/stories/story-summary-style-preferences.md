# Story: User Summary Style Preferences

**Story ID:** STORY-2.4
**Epic:** Epic 2 - Summarization & LLM Integration
**Priority:** P1 - High (Before Bot Launch)
**Status:** Draft
**Created:** 2026-02-15
**Estimated Effort:** 1 day (6 hours)

---

## Story

**As a** HN Pal user
**I want** to choose my preferred summary style (basic, technical, business, concise, personalized)
**So that** I receive summaries tailored to my reading preferences and technical level

---

## Problem Statement

Currently, the system generates summaries using only the "basic" prompt variant for all users. While Activity 2.3 defined 5 prompt variants (basic, technical, business, concise, personalized), there is no mechanism for users to:
1. Select their preferred summarization style
2. Store this preference persistently
3. Have the summarization agent use their preference

**Gap Identified:**
- ❌ No `summary_preferences` field in `users` table
- ❌ No bot commands to configure summary style
- ❌ Summarization agent doesn't read user preferences
- ❌ Onboarding flow doesn't ask for summary style preference

**Impact:**
- All users get identical summaries regardless of their background
- Technical users receive oversimplified summaries
- Business users receive unnecessary technical jargon
- Personalization features cannot be enabled

---

## Summary Style Examples

To illustrate the differences between each style, here's how the same HackerNews post would be summarized:

**Original Post:** "PostgreSQL 16: Performance Improvements and New Features"
**Article:** Technical deep-dive on PostgreSQL 16's new parallel query execution, improved COPY performance, logical replication enhancements, and SQL/JSON improvements.

---

### 📝 Basic (Default - Recommended)

**Target Audience:** General tech professionals, all backgrounds
**Length:** 2-3 sentences, 50-80 words
**Focus:** Main point + why it matters + key takeaway

**Example:**
> "PostgreSQL 16 brings significant performance improvements to OLTP workloads with up to 2x throughput on high-connection counts. Key additions include native JSON path indexing, async I/O for vacuum operations, and improved logical replication. The improvements strengthen Postgres's position as a competitive alternative to commercial databases."

**Characteristics:**
- ✅ Balanced technical depth
- ✅ Clear for non-specialists
- ✅ Highlights practical impact
- ✅ No excessive jargon

---

### 🔧 Technical (For Engineers)

**Target Audience:** Senior engineers, architects, database specialists
**Length:** 2-3 sentences, 60-90 words
**Focus:** Architecture decisions, implementation details, trade-offs

**Example:**
> "PostgreSQL 16's parallel query execution now supports incremental sort and Memoize nodes, enabling better performance on complex queries with multiple aggregations. The COPY protocol enhancement reduces overhead via zero-copy streaming for bulk loads, achieving 300% throughput improvement in benchmarks. Logical replication now supports row filtering at the publisher level using WHERE clauses, reducing network bandwidth and subscriber CPU usage."

**Characteristics:**
- ✅ Deep technical terminology
- ✅ Implementation specifics (protocols, algorithms)
- ✅ Performance metrics and benchmarks
- ✅ Architectural decisions explained

---

### 💼 Business (For Decision Makers)

**Target Audience:** CTOs, engineering managers, product leaders
**Length:** 2-3 sentences, 50-80 words
**Focus:** Business impact, competitive positioning, strategic implications

**Example:**
> "PostgreSQL 16's performance gains eliminate a key objection to using open-source databases over commercial alternatives like Oracle, potentially saving enterprises millions in licensing fees. The improved JSON support directly challenges MongoDB's market position in document-oriented workloads. For companies evaluating database migrations, these updates reduce risk and total cost of ownership while maintaining ACID compliance."

**Characteristics:**
- ✅ Non-technical language
- ✅ Cost and ROI focus
- ✅ Competitive analysis
- ✅ Strategic business value

---

### ⚡ Concise (Ultra-Brief)

**Target Audience:** Time-constrained readers, quick scanners
**Length:** 1 sentence, 20-35 words maximum
**Focus:** Single most important point

**Example:**
> "PostgreSQL 16 doubles query performance on high-concurrency workloads and adds native JSON indexing, closing the gap with commercial databases."

**Characteristics:**
- ✅ Maximum brevity
- ✅ One key insight only
- ✅ No supporting details
- ✅ Fastest to read (5 seconds)

---

### 🎯 Personalized (Adaptive)

**Target Audience:** Individual user with known interests and history
**Length:** 2-3 sentences, 50-80 words
**Focus:** Relevance to user's specific interests and past discussions

**Example (for user interested in "distributed systems" and "rust"):**
> "PostgreSQL 16's logical replication improvements enable building distributed systems with event-driven architectures, similar to the Kafka-based setup you discussed last week. The parallel query execution uses work-stealing task schedulers reminiscent of Tokio's runtime in Rust. These changes make Postgres more viable for the microservices architecture you're evaluating."

**Characteristics:**
- ✅ References user's interest tags
- ✅ Connects to past conversations
- ✅ Personalized comparisons
- ✅ Contextual relevance

**Note:** This style requires:
- User interests stored in `users.interests`
- Past conversation history
- Memory extraction enabled
- More LLM tokens (higher cost)

---

## Acceptance Criteria

### Database Schema
- [ ] Add `summary_preferences` JSON field to `users` table
- [ ] Default value: `{"style": "basic", "detail_level": "medium", "technical_depth": "intermediate"}`
- [ ] Create Alembic migration to add field
- [ ] Backfill existing users with default preferences
- [ ] Add index on summary style for analytics queries

### Bot Commands
- [ ] Implement `/settings` command to view all user preferences
- [ ] Implement `/settings summary` command with inline buttons:
  - 📝 Basic (recommended)
  - 🔧 Technical
  - 💼 Business
  - ⚡ Concise
  - 🎯 Personalized
- [ ] Show confirmation message after style change
- [ ] Update onboarding flow to ask for summary style preference

### Summarization Service
- [ ] Update `SummarizationAgent` to read user preferences
- [ ] Load appropriate prompt template based on `summary_preferences.style`
- [ ] For personalized style: inject user interests and feedback
- [ ] Fall back to "basic" if invalid style specified
- [ ] Log which prompt variant was used (for analytics)

### Testing
- [ ] Unit test: Prompt selection logic respects user preferences
- [ ] Unit test: Default to "basic" for new users
- [ ] Unit test: Personalized prompt injects user context
- [ ] Integration test: `/settings summary` changes preference in DB
- [ ] Integration test: Next digest uses new style
- [ ] Integration test: Migration backfills existing users correctly
- [ ] Manual test: Verify all 5 prompt variants produce different summaries

---

## Tasks

### Task 1: Database Schema Changes
**Estimated:** 1 hour

**Subtasks:**
- [ ] Create Alembic migration `add_summary_preferences_to_users`
- [ ] Add `summary_preferences` JSON column with default value
- [ ] Backfill existing users with `{"style": "basic"}`
- [ ] Update `User` ORM model in `models.py`
- [ ] Add helper methods: `get_summary_style()`, `update_summary_preferences()`
- [ ] Run migration on dev database
- [ ] Verify migration rollback works

**Files Modified:**
- `backend/alembic/versions/XXX_add_summary_preferences.py` (new)
- `backend/app/infrastructure/database/models.py`

---

### Task 2: Summarization Agent Updates
**Estimated:** 1.5 hours

**Subtasks:**
- [ ] Update `SummarizationAgent.summarize()` to accept `user_id` parameter
- [ ] Implement `get_prompt_for_user(user_id)` method
- [ ] Load prompt template based on `user.summary_preferences.style`
- [ ] Handle personalized style: inject `user.interests` into prompt
- [ ] Add fallback to "basic" if style invalid or missing
- [ ] Log prompt variant used (for observability)
- [ ] Update token tracking to include prompt type

**Files Modified:**
- `backend/app/infrastructure/agents/summarization_agent.py`
- `backend/app/application/use_cases/personalized_summarization.py` (existing)

---

### Task 3: Bot Commands for Settings
**Estimated:** 2 hours

**Subtasks:**
- [ ] Create `/settings` command handler (show all preferences)
- [ ] Create `/settings summary` command with inline keyboard:
  - Buttons: Basic, Technical, Business, Concise, Personalized
  - Callback data: `settings:summary:basic`, etc.
- [ ] Implement callback handler for style selection
- [ ] Update user preferences in database on selection
- [ ] Send confirmation message with preview of selected style
- [ ] Add help text explaining each style
- [ ] Handle errors gracefully (DB update failures)

**Files Modified:**
- `backend/app/presentation/bot/handlers/commands.py`
- `backend/app/presentation/bot/handlers/callbacks.py`

**Message Format:**
```
⚙️ Settings

Summary Style: 📝 Basic
Delivery: ▶️ Active
Memory: 🧠 Enabled

[Change Summary Style] [Pause Deliveries] [Memory Settings]
```

```
📝 Choose Your Summary Style

📝 Basic (Current) - Recommended
Balanced summaries for all content types
Example: "PostgreSQL 16 brings 2x performance improvements..."

🔧 Technical
Deep technical details, architecture, benchmarks
Example: "Parallel query execution supports Memoize nodes..."

💼 Business
Market impact, strategy, ROI focus
Example: "Performance gains eliminate objections to open-source..."

⚡ Concise
Ultra-brief, one sentence only
Example: "PostgreSQL 16 doubles query performance..."

🎯 Personalized
Adapts to your interests and past discussions
Example: "Logical replication enables event-driven architectures..."

[Basic] [Technical] [Business] [Concise] [Personalized]
```

---

### Task 4: Onboarding Flow Update
**Estimated:** 1 hour

**Subtasks:**
- [ ] Add summary style selection step to `/start` onboarding
- [ ] Show style picker after interest selection
- [ ] Store selected style in `user.summary_preferences`
- [ ] Allow skip (defaults to "basic")
- [ ] Update onboarding state machine (FSM states)

**Files Modified:**
- `backend/app/presentation/bot/handlers/commands.py` (start command)
- `backend/app/presentation/bot/states.py` (add ONBOARDING_SUMMARY_STYLE state)

**Onboarding Flow:**
```
/start
  ↓
Welcome + Interest Selection
  ↓
Summary Style Selection (NEW)
  ↓
Complete → IDLE state
```

---

### Task 5: Testing & Validation
**Estimated:** 1.5 hours

**Subtasks:**
- [ ] Write unit tests for prompt selection logic
- [ ] Write unit tests for default preferences
- [ ] Write integration test for `/settings summary` command
- [ ] Write integration test for onboarding flow
- [ ] Manually test all 5 prompt variants with same post
- [ ] Verify personalized style uses user interests
- [ ] Test migration on copy of production data (if applicable)
- [ ] Load test: 100 users with different styles

**Files Created:**
- `backend/tests/unit/test_summary_preferences.py`
- `backend/tests/integration/test_settings_command.py`

---

## Dev Notes

### Design Decisions

**Why JSON field instead of separate columns?**
- ✅ Future-proof: Easy to add new preferences without migrations
- ✅ Matches existing `interests` field pattern (also JSON)
- ✅ Supports nested configuration (detail_level, technical_depth, etc.)
- ✅ Activity 2.3 explicitly designed for extensible preferences

**JSON Structure:**
```json
{
  "style": "basic",              // basic | technical | business | concise | personalized
  "detail_level": "medium",       // brief | medium | detailed
  "technical_depth": "intermediate", // beginner | intermediate | advanced
  "preferred_length": "2-3 sentences", // Optional override
  "enable_key_points": false      // Show bullet points (future)
}
```

**Why high priority?**
- Core user experience feature (personalization is expected in 2026 AI products)
- Easier to add during initial development than retrofit later
- Activity 2.3 already designed 5 prompt variants for this purpose
- Unblocks personalization features in Phase 5 & 6

---

### Technical Considerations

**Prompt Selection Logic:**
```python
def get_prompt_for_user(user_id: int) -> str:
    """Get appropriate prompt based on user preferences."""
    user = db.get_user(user_id)
    prefs = user.summary_preferences or {"style": "basic"}

    style = prefs.get("style", "basic")
    prompt_file = f"summarizer_{style}.md"

    # Load base prompt
    prompt = load_prompt(prompt_file)

    # Personalized style: inject user context
    if style == "personalized":
        prompt = prompt.format(
            user_topics=", ".join(user.interests),
            user_style=prefs.get("detail_level", "medium"),
            user_feedback_summary=get_recent_feedback(user_id)
        )

    return prompt
```

**Migration Strategy:**
```sql
-- Alembic upgrade
ALTER TABLE users ADD COLUMN summary_preferences JSON;
UPDATE users SET summary_preferences = '{"style": "basic"}'::json WHERE summary_preferences IS NULL;
ALTER TABLE users ALTER COLUMN summary_preferences SET NOT NULL;

-- Alembic downgrade
ALTER TABLE users DROP COLUMN summary_preferences;
```

**Backward Compatibility:**
- Existing summaries (already generated) remain unchanged
- New summaries respect user preferences
- If preference missing or invalid → default to "basic"

---

### Testing Strategy

**Test Cases:**

1. **Default Behavior:**
   - New user → summary_preferences = `{"style": "basic"}`
   - Summary generated using basic prompt

2. **Style Selection:**
   - User selects "technical" → DB updated
   - Next summary uses technical prompt
   - Verify output is more technical (manual inspection)

3. **Personalized Style:**
   - User has interests: ["rust", "databases"]
   - Select "personalized" style
   - Verify prompt includes user interests
   - Verify summary emphasizes relevant topics

4. **Edge Cases:**
   - Invalid style in DB → falls back to "basic"
   - Missing preferences field → defaults to basic
   - User changes style mid-digest → next digest uses new style

5. **Migration Testing:**
   - Run migration on test DB with 100 users
   - Verify all users have default preferences
   - Verify no data loss
   - Test rollback

---

## File List

**New Files:**
- `backend/alembic/versions/XXX_add_summary_preferences.py`
- `backend/tests/unit/test_summary_preferences.py`
- `backend/tests/integration/test_settings_command.py`

**Modified Files:**
- `backend/app/infrastructure/database/models.py`
- `backend/app/infrastructure/agents/summarization_agent.py`
- `backend/app/application/use_cases/personalized_summarization.py`
- `backend/app/presentation/bot/handlers/commands.py`
- `backend/app/presentation/bot/handlers/callbacks.py`
- `backend/app/presentation/bot/states.py`

---

## Visual Comparison Table

| Aspect | 📝 Basic | 🔧 Technical | 💼 Business | ⚡ Concise | 🎯 Personalized |
|--------|---------|-------------|------------|-----------|----------------|
| **Length** | 2-3 sentences (50-80 words) | 2-3 sentences (60-90 words) | 2-3 sentences (50-80 words) | 1 sentence (20-35 words) | 2-3 sentences (50-80 words) |
| **Jargon Level** | Medium | High | Low | Medium | Adaptive |
| **Target Audience** | General tech professionals | Senior engineers, architects | CTOs, managers, leaders | Time-constrained readers | Individual user |
| **Focus** | Main point + impact | Architecture + implementation | Business value + ROI | Single key insight | User's specific interests |
| **Technical Depth** | Balanced | Deep (protocols, algorithms) | Minimal (outcomes only) | Surface level | Matches user's history |
| **Use Cases** | Default for most users | Database specialists, backend engineers | Decision makers, product leaders | Quick daily scan | Long-term engaged users |
| **Token Cost** | Baseline | +10-20% (more technical terms) | Similar to Basic | -30-40% (shorter) | +20-40% (context injection) |
| **Read Time** | 15-20 seconds | 20-25 seconds | 15-20 seconds | 5-10 seconds | 15-20 seconds |

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-15 | James (Dev Agent) | Initial story creation |
| 2026-02-15 | James (Dev Agent) | Added comprehensive examples for all 5 styles |
| 2026-02-15 | James (Dev Agent) | Added visual comparison table and bot message examples |

---

## Related Documents

- `docs/activities/activity-2.3-summarization-prompt-engineering.md` - Defines 5 prompt variants
- `docs/epics/epic-2-summarization-llm-integration.md` - Parent epic
- `docs/spec.md` - Product requirements
- `backend/app/infrastructure/prompts/` - Prompt template files
- `docs/architecture/source-tree.md` - Project structure

---

## Dev Agent Record

### Agent Model Used
- claude-sonnet-4-5-20250929

### Debug Log References
- None yet (story in draft mode)

### Completion Notes
- Story created based on gap analysis of specs vs implementation
- Ready for review and approval before implementation

---

**Status:** Draft
**Next Step:** Review story with team, approve, then assign to developer for implementation
**Blocked By:** None
**Blocks:** Epic 2 completion, Bot launch (Phase 3)
