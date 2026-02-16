# Telegram Bot Settings Guide

Complete guide to the HackerNews Digest Telegram bot settings system.

## Overview

The bot provides a comprehensive settings system accessible via the `/settings` command. Users can customize their experience through an interactive inline keyboard interface.

## Accessing Settings

Simply send `/settings` to the bot to open the settings menu. You'll see your current configuration and a 2x2 grid of buttons:

```
⚙️ Settings

Current Configuration:
📝 Summary Style: 📝 Basic
📬 Delivery: ▶️ Active
🧠 Memory: Enabled
🏷️ Interests: Python, AI, DevOps

[📝 Summary Style] [📬 Delivery]
[🧠 Memory] [🏷️ Interests]
```

## Summary Styles

### Available Styles

#### 1. 📝 Basic (Recommended)
**Best for:** General tech professionals

**Description:** Balanced summaries suitable for all content types. Provides good coverage without overwhelming detail.

**Example:**
> "PostgreSQL 16 brings significant performance improvements to OLTP workloads, with up to 2x better query execution in benchmarks. The release includes enhanced parallel query support, better indexing strategies, and improved replication features. These changes make PostgreSQL more competitive with commercial databases while maintaining backward compatibility."

**Use when:**
- You want comprehensive but not overwhelming information
- Reading various types of tech content
- You're new to the topic

---

#### 2. 🔧 Technical (For Engineers)
**Best for:** Senior engineers, architects, specialists

**Description:** Deep technical details including implementation specifics, architecture patterns, performance benchmarks, and code examples.

**Example:**
> "PostgreSQL 16's parallel query execution now supports incremental sort and Memoize nodes within parallel workers. Benchmark tests show 2-3x improvements for analytical queries with ORDER BY clauses. The query planner now uses JIT compilation for complex joins involving >5 tables. B-tree index deduplication reduces index size by 15-40% for high-cardinality columns. Logical replication supports row filters and column lists, enabling fine-grained event streaming."

**Use when:**
- You're implementing similar solutions
- You need to evaluate technical feasibility
- You want to understand the "how" not just the "what"

---

#### 3. 💼 Business (For Leaders)
**Best for:** CTOs, engineering managers, product leaders

**Description:** Focuses on business impact, adoption strategy, ROI, and decision-making insights.

**Example:**
> "PostgreSQL 16's performance gains eliminate a major objection to open-source database adoption in enterprise environments. The 2x performance improvement means organizations can defer expensive hardware upgrades or cloud scaling costs. Enhanced replication features enable zero-downtime migrations from proprietary databases, reducing migration risk. These improvements strengthen PostgreSQL's position against commercial competitors, potentially saving $50-200K annually in licensing costs for mid-sized teams."

**Use when:**
- Making technology adoption decisions
- Planning budgets and resource allocation
- Communicating with non-technical stakeholders
- Evaluating strategic technology trends

---

#### 4. ⚡ Concise (Quick Scan)
**Best for:** Time-constrained readers

**Description:** Ultra-brief, single-sentence summaries. Perfect for quick scanning and deciding what to read in detail.

**Example:**
> "PostgreSQL 16 doubles query performance and adds enterprise-grade replication features."

**Use when:**
- You only have a few minutes
- You're triaging a large number of articles
- You just want headlines to stay current
- Reading on mobile during commute

---

#### 5. 🎯 Personalized (Adaptive)
**Best for:** Users with conversation history

**Description:** Adapts to your specific interests, past discussions, and feedback. Highlights aspects most relevant to you based on your profile.

**Example (for someone interested in distributed systems):**
> "PostgreSQL 16's logical replication improvements enable event-driven architectures. The new row filters and column lists let you build change data capture (CDC) pipelines similar to Kafka Connect, but with native database integration. Combined with parallel query execution, you can now use PostgreSQL for both OLTP and streaming workloads, potentially simplifying your architecture by replacing separate systems."

**Use when:**
- You want maximum relevance to your work
- You've been using the bot for a while
- You have specific interests configured
- Memory is enabled

**Note:** This style requires:
- Memory enabled (see Memory Settings below)
- Interests configured (via `/start` or settings)
- Some conversation history for better personalization

---

### How to Change Summary Style

1. Send `/settings` to the bot
2. Tap **📝 Summary Style**
3. You'll see all 5 styles with descriptions and examples
4. Tap the style you want
5. You'll see a confirmation: "✅ Summary style updated!"
6. Your next digest will use the new style

**Technical Details:**
- Style changes take effect immediately
- Old summaries keep their original style
- New summarization jobs will use your new style
- The style is stored in the `summary_preferences` JSON field in the database

---

## Delivery Settings

### Active vs Paused

**▶️ Active**: You receive daily HackerNews digests
**⏸ Paused**: No digests are delivered (you can still use `/digest` for on-demand)

### How to Pause/Resume

1. Send `/settings`
2. Tap **📬 Delivery**
3. Tap **Pause Deliveries** or **Resume Deliveries**
4. Status updates immediately

**Use Cases:**
- Going on vacation
- Too busy this week
- Want to batch-read later
- Testing other features without notifications

**Technical Details:**
- Updates the `status` field in the User model
- Values: `"active"` or `"paused"`
- Delivery pipeline checks status before sending
- No messages are queued during pause (they're skipped)

---

## Memory Settings

### What is Memory?

When enabled, the bot remembers:
- Past discussions and conversations
- Your preferences and feedback
- Topics you've shown interest in
- Questions you've asked
- Patterns in what you engage with

This enables:
- More relevant personalized summaries
- Better understanding of your questions
- Improved recommendations
- Contextual conversations

### How to Enable/Disable

1. Send `/settings`
2. Tap **🧠 Memory**
3. Tap **Enable Memory** or **Disable Memory**
4. Status updates immediately

### Privacy Considerations

**What is stored:**
- Your telegram_id, username, first_name, last_name
- Your interests list
- Summary style preferences
- Delivery status
- Conversation messages (when memory is enabled)

**What is NOT stored:**
- Messages when memory is disabled
- Payment information (no payments implemented)
- Location or contact data
- Messages in other chats

**Data retention:**
- Active users: Data retained indefinitely
- Paused users: Data retained (for when you resume)
- Deleted accounts: Data can be purged (contact admin)

**Technical Details:**
- Updates the `memory_enabled` boolean field
- When disabled, conversation context is not persisted
- Past memories are not deleted when disabled
- Re-enabling memory starts fresh (past is not recalled)

---

## Interests Settings

### What are Interests?

Topics you care about, used to:
- Personalize your summaries
- Highlight relevant content
- Filter digest items (future feature)
- Match you with related discussions

### How to Update Interests

**Option 1: Via /start command**
```
You: /start
Bot: Welcome back! What are your tech interests?
You: Python, Machine Learning, DevOps, Kubernetes
Bot: ✅ Interests updated!
```

**Option 2: Via conversation**
```
You: I'm interested in Python and AI
Bot: I've updated your interests to include Python and AI
```

**Option 3: View current interests**
```
You: /settings → Tap 🏷️ Interests
Bot: Shows your current interests with instructions
```

### Best Practices

**Good interests:**
- Specific technologies: "Python", "Kubernetes", "React"
- Domains: "Machine Learning", "DevOps", "Security"
- Methodologies: "Microservices", "Event-Driven", "TDD"

**Too broad:**
- "Technology" (not specific enough)
- "Everything" (defeats personalization)
- "Software" (too generic)

**Too narrow:**
- "Python 3.11 async await syntax" (overly specific)
- "React hooks in functional components" (too granular)

**Technical Details:**
- Stored as a PostgreSQL array of strings
- Used by the personalized summarization agent
- Combined with memory for best results
- Can be any text (no validation)

---

## Technical Implementation

### Database Schema

```python
class User(Base):
    id = UUID (Primary Key)
    telegram_id = Integer (Unique)
    status = String  # "active" or "paused"
    summary_preferences = JSON  # {
        "style": "basic" | "technical" | "business" | "concise" | "personalized",
        "detail_level": "low" | "medium" | "high",
        "technical_depth": "beginner" | "intermediate" | "advanced"
    }
    interests = Array[String]
    memory_enabled = Boolean
    created_at = DateTime
    updated_at = DateTime
```

### Callback Data Format

The bot uses a hierarchical callback data format:

```
settings:main                    # Return to main menu
settings:summary                 # Show summary style picker
settings:summary:technical       # Select technical style
settings:delivery                # Show delivery settings
settings:delivery:pause          # Pause deliveries
settings:delivery:resume         # Resume deliveries
settings:memory                  # Show memory settings
settings:memory:toggle           # Toggle memory
settings:interests               # Show interests
```

### Handler Architecture

```python
# app/presentation/bot/handlers/settings.py

@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession):
    """Main settings command handler"""

@router.callback_query(F.data == "settings:summary")
async def callback_summary_style_menu(callback: CallbackQuery, session: AsyncSession):
    """Show summary style picker"""

@router.callback_query(F.data.startswith("settings:summary:"))
async def callback_summary_style_selection(callback: CallbackQuery, session: AsyncSession):
    """Handle style selection"""

# Similar patterns for delivery, memory, interests
```

### Use Case Layer

```python
# app/application/use_cases/summary_preferences.py

async def get_user_summary_style(session, user_id) -> str:
    """Get user's current summary style"""

async def update_user_summary_style(session, user_id, style) -> bool:
    """Update user's summary style"""

def get_all_styles() -> Dict[str, Dict]:
    """Get all styles with metadata"""
```

---

## User Flows

### First-Time User Flow

```
1. User: /start
2. Bot: Welcome! Creates account with defaults:
   - Summary Style: basic
   - Delivery: active
   - Memory: enabled
   - Interests: empty
3. Bot: "What are your tech interests?"
4. User: "Python, AI"
5. Bot: ✅ "You're all set! You'll receive your first digest soon."
```

### Changing Summary Style

```
1. User: /settings
2. Bot: Shows current config with buttons
3. User: Taps [📝 Summary Style]
4. Bot: Shows all 5 styles with examples
5. User: Taps [🔧 Technical]
6. Bot: "✅ Summary style updated to 🔧 Technical"
7. Bot: Shows [← Back to Settings] button
```

### Pausing Delivery Before Vacation

```
1. User: /settings
2. Bot: Shows current config (Delivery: ▶️ Active)
3. User: Taps [📬 Delivery]
4. Bot: Shows delivery settings
5. User: Taps [Pause Deliveries]
6. Bot: "⏸ Deliveries paused"
7. User: (on vacation, receives no digests)
8. User: (returns) /settings → Delivery → Resume
9. Bot: "▶️ Deliveries resumed"
10. User: Starts receiving digests again
```

---

## Troubleshooting

### "Settings not saving"
**Cause:** Database connection issue
**Solution:** Check PostgreSQL is running, verify DATABASE_URL

### "Style changed but summaries look the same"
**Cause:** New summaries not generated yet
**Solution:** Wait for next scheduled run or trigger manually:
```bash
python scripts/run_personalized_summarization.py
```

### "Personalized style not very personalized"
**Cause:** Not enough data (new user, memory disabled, no interests)
**Solution:**
1. Enable memory via settings
2. Add interests via /start
3. Chat with the bot more
4. Wait for more conversation history

### "Back button not working"
**Cause:** Message edit conflict
**Solution:** Close the message and use /settings again

### "User not found" error
**Cause:** Account not created properly
**Solution:** Use /start to register

---

## Best Practices for Users

1. **Start with Basic** - Try the default style first before exploring others
2. **Enable Memory** - You get better personalization over time
3. **Set Interests** - Takes 10 seconds, improves quality significantly
4. **Try Different Styles** - Each style serves different use cases
5. **Pause When Needed** - Don't delete the chat, just pause delivery
6. **Use /digest** - Request instant digest when you need it

---

## Best Practices for Developers

### Adding a New Setting

1. Add database field if needed (Alembic migration)
2. Create callback handler in `settings.py`
3. Update keyboard creation function
4. Add to main settings display
5. Write tests
6. Update this documentation

### Testing Settings

```bash
# Unit tests
pytest tests/unit/test_summary_preferences.py

# Integration tests (requires running bot)
python scripts/test_bot_setup.py

# Manual testing
python scripts/run_bot.py
# Then interact via Telegram
```

### Monitoring Settings Changes

```sql
-- Check distribution of summary styles
SELECT
    summary_preferences->>'style' as style,
    COUNT(*) as user_count
FROM users
GROUP BY summary_preferences->>'style';

-- Check delivery status
SELECT
    status,
    COUNT(*) as user_count
FROM users
GROUP BY status;

-- Check memory usage
SELECT
    memory_enabled,
    COUNT(*) as user_count
FROM users
GROUP BY memory_enabled;
```

---

## Future Enhancements

Planned improvements to the settings system:

1. **Delivery Schedule**
   - Choose delivery time (morning/evening)
   - Set timezone
   - Weekend delivery toggle

2. **Content Filtering**
   - Filter by post score threshold
   - Exclude specific topics
   - Prioritize interests

3. **Digest Customization**
   - Choose number of items per digest
   - Summary length slider
   - Toggle comments/discussions

4. **Advanced Personalization**
   - Learning rate (how quickly to adapt)
   - Explicit like/dislike feedback
   - Topic categories

5. **Export Settings**
   - Share your configuration
   - Import from template
   - Reset to defaults

---

## Related Documentation

- **Story Document**: `docs/stories/story-summary-style-preferences.md`
- **Database Migration**: `alembic/versions/e7a718d85a59_add_summary_preferences_to_users.py`
- **Use Case Code**: `app/application/use_cases/summary_preferences.py`
- **Handler Code**: `app/presentation/bot/handlers/settings.py`
- **Main README**: `backend/README.md`

---

## Support

For issues or questions:
1. Check this guide
2. Review logs: `docker-compose logs bot`
3. Check database: `SELECT * FROM users WHERE telegram_id = YOUR_ID;`
4. Contact support team
