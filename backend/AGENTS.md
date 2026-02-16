# HackerNews Digest Backend - Agent Guide

## Project Overview

A Telegram bot that delivers personalized Hacker News summaries to users. This backend powers:

- **Ingest Pipeline**: Collects HN posts hourly, crawls content, stores in PostgreSQL + RocksDB
- **Summarization Pipeline**: Generates personalized summaries using OpenAI agents with prompt caching
- **Delivery System**: Sends digests via Telegram bot with interactive buttons
- **Discussion Flow**: Enables conversations about posts with memory tracking (future)

**Architecture**: Clean Architecture pattern (Domain → Application → Infrastructure → Presentation)

**Key Technologies**: Python 3.10+, PostgreSQL, RocksDB, aiogram 3.x, OpenAI API, Alembic migrations

## Quick Start

### Environment Setup

```bash
# From backend directory
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY, TELEGRAM_BOT_TOKEN

# Start services
docker-compose up -d

# Run migrations
python -m alembic upgrade head
```

### Common Development Commands

```bash
# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Lint and format
python -m ruff check .
python -m ruff format .

# Create migration
python -m alembic revision --autogenerate -m "description"

# Apply migrations
python -m alembic upgrade head

# Rollback migration
python -m alembic downgrade -1
```

### Running Pipelines

```bash
# Collect posts from HN (hourly job)
python scripts/trigger_posts_collection.py

# Generate personalized summaries for all users
python scripts/run_personalized_summarization.py

# Deliver summaries via Telegram bot
python scripts/run_delivery_pipeline.py

# Run the Telegram bot
python scripts/run_bot.py
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
│   └── versions/         # Migration files
├── app/
│   ├── domain/           # Core business entities (Post, User, etc.)
│   ├── application/      # Use cases and business logic
│   │   └── use_cases/    # Pipeline orchestration
│   ├── infrastructure/   # External dependencies
│   │   ├── agents/       # OpenAI agents for summarization
│   │   ├── database/     # SQLAlchemy models
│   │   ├── repositories/ # Data access (Postgres)
│   │   ├── storage/      # RocksDB content storage
│   │   ├── services/     # External services (HN API, crawlers)
│   │   └── jobs/         # Scheduler and background jobs
│   └── presentation/     # API and Bot interfaces
│       ├── api/          # REST API (FastAPI)
│       └── bot/          # Telegram bot (aiogram)
├── scripts/              # Standalone scripts for manual ops
└── tests/                # Test suite (pytest)
```

## Database Schema

### Core Tables

- **posts**: HN posts with crawled content metadata
- **users**: Telegram users with preferences (`summary_preferences` JSON)
- **summaries**: Personalized summaries per user/post/style
- **deliveries**: Tracks which posts were sent to users
- **conversations**: Discussion threads (for future feature)
- **agent_calls**: Token usage tracking per LLM call
- **user_token_usage**: Aggregated daily costs per user

### Key Foreign Keys

- `summaries.user_id → users.id` (CASCADE)
- `summaries.post_id → posts.id` (CASCADE)
- `deliveries.user_id → users.id` (CASCADE)
- `deliveries.post_id → posts.id` (CASCADE)

## Code Style Guidelines

### Python Standards

- **Style**: Follow PEP 8, enforced by `ruff`
- **Line Length**: 120 characters max
- **Imports**: Use absolute imports from `app.*` root
- **Type Hints**: Required for all function signatures
- **Docstrings**: Use Google-style for public classes/functions

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase` (e.g., `SummarizationAgent`)
- **Functions**: `snake_case` (e.g., `generate_summary`)
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: Prefix with `_` (e.g., `_validate_input`)

### Example

```python
from typing import Optional
from app.domain.entities import Post

class SummaryService:
    """Handles post summarization using OpenAI agents.

    Attributes:
        agent: The OpenAI agent instance
        token_tracker: Tracks API usage costs
    """

    def __init__(self, agent: BaseAgent) -> None:
        self.agent = agent

    async def summarize_post(
        self,
        post: Post,
        user_id: int,
        style: str = "basic"
    ) -> Optional[str]:
        """Generate personalized summary for a post.

        Args:
            post: The post to summarize
            user_id: Target user ID for personalization
            style: Summary style (basic, technical, business, etc.)

        Returns:
            Summary text or None if generation fails
        """
        # Implementation...
```

## Testing Guidelines

### Test Structure

```bash
tests/
├── unit/                 # Pure unit tests (no I/O)
├── integration/          # Database/API integration tests
└── application/          # End-to-end use case tests
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/application/use_cases/test_delivery_selection.py -v

# With coverage
pytest --cov=app --cov-report=term-missing

# Fast tests only (skip slow integrations)
pytest -m "not slow"
```

### Test Fixtures

Common fixtures are in `conftest.py`:
- `db_session`: Test database session
- `mock_openai_client`: Mocked OpenAI API
- `sample_post`: Factory for test posts

### Example Test

```python
import pytest
from app.application.use_cases.delivery_selection import select_posts_for_user

@pytest.mark.asyncio
async def test_delivery_selection_respects_user_preferences(db_session, sample_user):
    """Ensure posts match user's declared interests."""
    # Setup
    user = sample_user(interests=["rust", "distributed systems"])

    # Execute
    selected = await select_posts_for_user(db_session, user.id, limit=10)

    # Assert
    assert len(selected) > 0
    assert all(post.score > 100 for post in selected)
```

## Security Considerations

### API Keys and Secrets

- **Never commit**: `.env` files are in `.gitignore`
- **Required secrets**: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`
- **Access in code**: Use `app.infrastructure.config.settings.Settings`

### Database Access

- **Use ORM**: Always use SQLAlchemy models, never raw SQL
- **Transactions**: Wrap mutations in `async with db.begin()`
- **SQL injection**: Parameterized queries only (ORM handles this)

### Telegram Bot Security

- **Webhook vs Polling**: Use polling in dev, webhook in production
- **User validation**: Verify `telegram_id` before any operation
- **Rate limiting**: TODO - add rate limiting for user commands

### Dependencies

- **Update regularly**: `uv lock --upgrade` weekly
- **Scan for vulns**: Use `pip-audit` or GitHub Dependabot
- **Pin versions**: All deps pinned in `uv.lock`

## AI Agent Configuration

### OpenAI Agents

Located in `app/infrastructure/agents/`:

- **SummarizationAgent**: Generates post summaries with caching
- **Token tracking**: All calls logged to `agent_calls` table
- **Prompt templates**: In `app/infrastructure/prompts/*.md`

### Prompt Caching

**Critical for cost savings** (90% reduction):

```python
# System prompt is cached across requests
system_prompt = load_prompt("summarizer_system_base.md")

# Only article content changes per call
user_prompt = f"Article:\n\n{article_content}"

response = await agent.run(
    system_prompt=system_prompt,  # Cached
    user_prompt=user_prompt
)
```

### Adding New Prompt Styles

1. Create `app/infrastructure/prompts/summarizer_<style>.md`
2. Update `SummarizationAgent` to load new style
3. Add migration to allow `<style>` in `summaries.prompt_type` enum
4. Test with: `pytest tests/infrastructure/agents/test_summarization_agent.py`

## Alembic Migrations

### Creating Migrations

```bash
# Auto-generate from model changes
python -m alembic revision --autogenerate -m "add user preferences column"

# Empty migration for data changes
python -m alembic revision -m "backfill user summary preferences"
```

### Migration Guidelines

- **Review autogenerated SQL**: Always check before applying
- **Backwards compatible**: Use `op.add_column()` with `nullable=True` or defaults
- **Data migrations**: Separate from schema changes
- **Test locally**: Apply and rollback on dev DB first

### Example Migration

```python
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("summary_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb"))
    )

def downgrade() -> None:
    op.drop_column("users", "summary_preferences")
```

## Common Pitfalls

### 1. RocksDB Content Storage

**Problem**: RocksDB is used for HTML/Markdown content, not PostgreSQL.

```python
# ❌ Wrong - content not in DB
post = db.query(Post).filter_by(hn_id=12345).first()
content = post.html  # This field doesn't exist!

# ✅ Correct - fetch from RocksDB
from app.infrastructure.storage.rocksdb_store import RocksDBStore

store = RocksDBStore()
content = store.get(f"html:{post.hn_id}")
```

### 2. Async/Await Consistency

**Problem**: Mixing sync and async code causes blocking.

```python
# ❌ Wrong - blocking the event loop
def fetch_posts():
    posts = db.query(Post).all()  # Sync DB call in async context

# ✅ Correct - use async session
async def fetch_posts():
    async with AsyncSession() as session:
        result = await session.execute(select(Post))
        posts = result.scalars().all()
```

### 3. Agent Token Tracking

**Problem**: Forgetting to track token usage leads to cost surprises.

```python
# ❌ Wrong - no tracking
response = await openai_client.chat.completions.create(...)

# ✅ Correct - use BaseAgent wrapper
from app.infrastructure.agents.base_agent import BaseAgent

agent = BaseAgent(name="summarizer")
response = await agent.run(...)  # Automatically tracked
```

### 4. User Summary Preferences

**Problem**: Not checking user preferences before generating summaries.

```python
# ❌ Wrong - hardcoded style
summary = await summarize_post(post, style="basic")

# ✅ Correct - respect user preferences
user = await get_user(user_id)
style = user.get_summary_style()  # Returns user's preferred style
summary = await summarize_post(post, style=style)
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Use production database URL (not localhost)
- [ ] Enable `TELEGRAM_WEBHOOK_URL` for webhook mode
- [ ] Set up monitoring for `agent_calls` table (cost tracking)
- [ ] Configure log aggregation (CloudWatch, Datadog, etc.)
- [ ] Set up cron jobs for:
  - `trigger_posts_collection.py` (hourly)
  - `run_personalized_summarization.py` (every 30 min)
  - `run_delivery_pipeline.py` (based on user schedules)

### Environment Variables

Required in production:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
DEBUG=False
LOG_LEVEL=INFO
```

## Getting Help

- **Project Spec**: See `/docs/spec.md` for full product requirements
- **Database Schema**: Check `app/infrastructure/database/models.py`
- **API Docs**: Run `uvicorn app.main:app --reload` and visit `/docs`
- **Tests**: Look at existing tests in `tests/` for examples
- **Migrations**: Review `alembic/versions/` for schema history

## Useful Commands Reference

```bash
# Database queries (via psql)
docker exec -it hn-digest-postgres psql -U hn_pal -d hn_pal

# Check summaries by user
SELECT user_id, COUNT(*) FROM summaries GROUP BY user_id;

# Check API costs
SELECT SUM(cost_usd) as total_cost FROM agent_calls WHERE DATE(created_at) = CURRENT_DATE;

# Find uncrawled posts
SELECT COUNT(*) FROM posts WHERE is_crawl_success = false;

# View RocksDB keys
python -c "from app.infrastructure.storage.rocksdb_store import RocksDBStore; store = RocksDBStore(); print(list(store.db.iterkeys())[:10])"
```

## Notes for AI Agents

- **Never delete migration files** - they're version controlled history
- **Test database changes locally first** - always run migrations on dev DB before committing
- **Check for existing implementations** - grep for similar features before writing new code
- **Follow the layered architecture** - Domain → Application → Infrastructure → Presentation
- **Use type hints** - helps with IDE autocomplete and catches errors early
- **Write tests for new features** - aim for >80% coverage on business logic
- **Check costs before deploying** - review `agent_calls` table for unexpected token usage
- **Prompt changes affect costs** - coordinate with team before modifying prompts
