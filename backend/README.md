# HackerNews Digest Backend

## Quick Start

### 1. Setup Environment

```bash
# Create .env file
cp .env.example .env

# Add your OpenAI API key
echo "OPENAI_API_KEY=sk-proj-your-key-here" >> .env

# Start services
docker-compose up -d

# Run migrations
python -m alembic upgrade head
```

### 2. Crawling Pipeline

```bash
# Collect posts from HackerNews (hourly)
python scripts/trigger_posts_collection.py

# Check collected posts
docker exec hn-digest-postgres psql -U hn_pal -d hn_pal -c \
  "SELECT COUNT(*) FROM posts WHERE is_crawl_success = true;"
```

### 3. Summarization Pipeline

```bash
# Generate personalized summaries for all active users
python scripts/run_personalized_summarization.py

# Test with specific users
python scripts/run_personalized_summarization.py --user-ids 1,2,3 --post-limit 10

# Dry run to preview
python scripts/run_personalized_summarization.py --dry-run
```

### 4. Automation (Optional)

Add to cron for automatic execution:

```bash
# Collect posts every hour
0 * * * * cd /path/to/backend && python scripts/trigger_posts_collection.py

# Generate summaries every 30 minutes
*/30 * * * * cd /path/to/backend && python scripts/run_personalized_summarization.py
```

## Key Features

- **Prompt Caching**: 90% cost reduction on cached tokens
- **Grouped Summarization**: 95-98% fewer API calls by grouping users by delivery_style
- **Incremental Processing**: Only processes posts since user's last summary
- **Personalized Summaries**: Each user gets summaries tailored to their style
- **Telegram Bot Integration**: Full-featured bot with settings management
- **5 Summary Styles**: Basic, Technical, Business, Concise, Personalized
- **Interactive Settings Menu**: Inline keyboards for easy preference management
- **User Memory System**: Remembers conversations and preferences

## Documentation

- **PERSONALIZED_SUMMARIZATION_GUIDE.md** - Complete usage guide
- **PROMPT_CACHING_OPTIMIZATION.md** - Caching details
- **IMPLEMENTATION_COMPLETE.md** - Full implementation summary

## Database Verification

```bash
# Check summaries
docker exec hn-digest-postgres psql -U hn_pal -d hn_pal -c \
  "SELECT user_id, COUNT(*) FROM summaries GROUP BY user_id;"

# Check costs
docker exec hn-digest-postgres psql -U hn_pal -d hn_pal -c \
  "SELECT SUM(cost_usd) as total_cost FROM summaries;"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No posts found | Run `python scripts/trigger_posts_collection.py` |
| No summaries created | Ensure users are active and posts exist |
| High API costs | Verify prompt caching is enabled (check logs for "Cache hit") |
| Database errors | Check PostgreSQL is running: `docker-compose ps` |

## Telegram Bot Commands

### User Commands

- **`/start`** - Initialize account and set up preferences
- **`/settings`** - Manage your preferences via interactive menu
- **`/digest`** - Request instant digest of today's top stories
- **`/help`** - Get help with available commands

### Settings Menu

The `/settings` command provides an interactive interface to manage:

1. **📝 Summary Style** - Choose from 5 different summary styles:
   - **📝 Basic** (Recommended) - Balanced summaries for all content
   - **🔧 Technical** (For Engineers) - Deep technical details and benchmarks
   - **💼 Business** (For Leaders) - Market impact and strategy focus
   - **⚡ Concise** (Quick Scan) - Ultra-brief, one sentence only
   - **🎯 Personalized** (Adaptive) - Adapts to your interests and history

2. **📬 Delivery** - Pause or resume daily digests
3. **🧠 Memory** - Enable/disable conversation memory
4. **🏷️ Interests** - View and update your topic interests

### Running the Bot

```bash
# Start the bot in polling mode
python scripts/run_bot.py

# Or use the delivery pipeline (includes bot + scheduler)
python scripts/run_delivery_pipeline.py
```

### Group Topic Feed

The digest can also be posted into one topic of a Telegram forum group. The group is stored as its own row in `users` (with `telegram_id` set to the group chat ID), so it gets its own summaries and delivery tracking.

1. Add `@HNDigestBot` to the group and let it post in the target topic.
2. In that topic, copy a message link: `https://t.me/c/<A>/<TOPIC>/<MSG>`.
3. Set `TELEGRAM_GROUP_CHAT_ID=-100<A>` and `TELEGRAM_GROUP_TOPIC_ID=<TOPIC>` in `.env`. Optionally set `TELEGRAM_GROUP_SUMMARY_STYLE` (default `basic`).

The row is created on the next summarization run. To stop DM summaries and pushes and keep only the group feed, set `TELEGRAM_DM_DELIVERY_ENABLED=false`. Bot commands in DMs keep working.

In the group, the buttons act on the group's feed, so members do not need to run `/start`. Because the bot runs in privacy mode, a Discuss follow-up must be a **reply** to the bot's message.

## Architecture

```
Posts Collection → Personalized Summarization → Telegram Bot Delivery
     (hourly)            (every 30 min)            (scheduled)
```

Ready to use! 🚀
