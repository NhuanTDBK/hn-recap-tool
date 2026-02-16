# HackerNews Digest - AI Agent Guide

## Project Overview

**HN Pal** is a Telegram bot that delivers personalized Hacker News summaries with AI-powered conversations. The project uses an agent-first architecture where AI agents handle content processing, summarization, and future conversational features.

**Status (2026-02-15)**: Production-ready delivery system with Telegram bot. Phases 1-4 complete.

## Repository Structure

```
hackernews_digest/
├── backend/              # Python backend (see backend/AGENTS.md)
│   ├── app/              # Application code (Clean Architecture)
│   │   ├── domain/       # Business entities
│   │   ├── application/  # Use cases and interfaces
│   │   ├── infrastructure/  # External integrations
│   │   └── presentation/    # API and Bot interfaces
│   ├── alembic/          # Database migrations
│   ├── scripts/          # Automation scripts
│   ├── tests/            # Test suite
│   └── AGENTS.md         # Detailed backend agent guide ⭐
├── data/                 # Local data storage
│   └── content.rocksdb/  # Content storage (HTML/Markdown)
├── docs/                 # Documentation
│   ├── spec.md           # Product specification
│   └── stories/          # User stories
├── docker-compose.yml    # Local development services
└── AGENTS.md             # This file - project overview
```

## Quick Start

### For Backend Development

See **[backend/AGENTS.md](backend/AGENTS.md)** for comprehensive backend development guide including:
- Setup instructions
- Code style guidelines
- Testing practices
- Database management
- Common pitfalls
- Deployment checklist

### Environment Setup

```bash
# 1. Start infrastructure services
docker-compose up -d

# 2. Configure environment (backend/.env)
cd backend
cp .env.example .env
# Add: OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, DATABASE_URL

# 3. Run migrations
python -m alembic upgrade head

# 4. Run pipelines
python scripts/trigger_posts_collection.py      # Collect HN posts
python scripts/run_personalized_summarization.py  # Generate summaries
python scripts/run_bot.py                        # Start Telegram bot
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.10+ | Core application |
| **Database** | PostgreSQL | Persistent storage |
| **Content Storage** | RocksDB | HTML/Markdown content |
| **Bot Framework** | aiogram 3.x | Telegram bot |
| **LLM** | OpenAI API | Summarization agents |
| **Migrations** | Alembic | Schema versioning |
| **Package Manager** | uv | Dependency management |

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│    (Telegram Bot, FastAPI)          │
├─────────────────────────────────────┤
│       Application Layer             │
│  (Use Cases, Business Logic)        │
├─────────────────────────────────────┤
│      Infrastructure Layer           │
│  (Database, OpenAI, RocksDB)        │
├─────────────────────────────────────┤
│         Domain Layer                │
│    (Entities, Value Objects)        │
└─────────────────────────────────────┘
```

### Key Pipelines

1. **Ingest Pipeline**: HN API → PostgreSQL + RocksDB (hourly)
2. **Summarization Pipeline**: Posts → OpenAI Agents → Summaries (every 30 min)
3. **Delivery Pipeline**: Summaries → Telegram Bot → Users (scheduled)
4. **Discussion Flow**: User ↔ Bot ↔ OpenAI (future)

## AI Agents

### Current Agents (Production)

- **SummarizationAgent** (`backend/app/infrastructure/agents/`)
  - Generates personalized post summaries
  - Supports 5 styles: basic, technical, business, concise, personalized
  - Uses prompt caching for 90% cost reduction
  - Tracks token usage in database

### Planned Agents (Roadmap)

- **Discussion Agent** (Phase 5)
  - Multi-turn conversations about posts
  - Memory-aware context
  - Auto-saves discussions

- **Memory Extraction Agent** (Phase 6)
  - Builds user interest profiles
  - Extracts insights from interactions
  - Powers personalization

## Development Workflow

### Working Directory Convention

**IMPORTANT**: Always run commands from the project root using the `.venv` Python:

```bash
# ✅ Correct - from project root
cd /path/to/hackernews_digest
.venv/bin/python backend/scripts/trigger_posts_collection.py

# ❌ Wrong - don't run from backend/
cd backend && python scripts/trigger_posts_collection.py
```

### Common Commands

```bash
# From project root:
.venv/bin/python backend/scripts/trigger_posts_collection.py
.venv/bin/python backend/scripts/run_personalized_summarization.py
.venv/bin/python -m pytest backend/tests/ -v

# Database operations (from backend/):
cd backend
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "description"
```

### Dependencies

```bash
# Add new dependency
cd backend
uv add package-name

# Update dependencies
uv lock --upgrade

# Sync environment
uv sync
```

## Documentation

- **[backend/AGENTS.md](backend/AGENTS.md)** - Comprehensive backend development guide
- **[docs/spec.md](docs/spec.md)** - Full product specification
- **[backend/README.md](backend/README.md)** - Backend quick start
- **[README.md](README.md)** - Project overview

## Key Principles

### For AI Coding Agents

1. **Read backend/AGENTS.md first** - Contains detailed guidelines for backend work
2. **Follow Clean Architecture** - Respect layer boundaries (Domain → Application → Infrastructure → Presentation)
3. **Never commit secrets** - Use `.env` files (already in `.gitignore`)
4. **Test database changes locally** - Run migrations on dev DB before committing
5. **Track AI costs** - All OpenAI calls logged to `agent_calls` table
6. **Use the project venv** - Always use `.venv/bin/python` from project root
7. **RocksDB for content** - HTML/Markdown stored in RocksDB, not PostgreSQL
8. **Prompt caching matters** - System prompts are cached; only change when necessary

### Code Style

- **Python**: PEP 8, enforced by `ruff`
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style for public classes/functions
- **Line length**: 120 characters max
- **Testing**: Aim for >80% coverage on business logic

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agents): add discussion agent with memory context
fix(crawler): handle rate limiting with exponential backoff
docs: update AGENTS.md with deployment checklist
test(summarization): add edge cases for long articles
```

## Infrastructure

### Local Development

Services run via Docker Compose:

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f postgres

# Stop services (preserves data)
docker-compose down

# Stop and remove data
docker-compose down -v
```

### Database Access

```bash
# PostgreSQL via psql
docker exec -it hn-digest-postgres psql -U hn_pal -d hn_pal

# Redis via redis-cli
docker exec -it hn-digest-redis redis-cli

# Check summaries count
docker exec hn-digest-postgres psql -U hn_pal -d hn_pal -c \
  "SELECT COUNT(*) FROM summaries;"
```

## Security

- **API Keys**: Store in `.env`, never commit
- **Database URL**: Use environment variables
- **Telegram Token**: Keep secret, rotate if exposed
- **User Data**: Handle according to privacy policy

## Performance

- **Prompt Caching**: 90% cost reduction on repeated system prompts
- **Grouped Delivery**: 95-98% fewer API calls by batching users
- **Incremental Processing**: Only process new posts since last run
- **RocksDB Storage**: Fast local content access without DB overhead

## Getting Help

1. **Backend-specific questions**: See [backend/AGENTS.md](backend/AGENTS.md)
2. **Product requirements**: See [docs/spec.md](docs/spec.md)
3. **Database schema**: Check `backend/app/infrastructure/database/models.py`
4. **API docs**: Run FastAPI server and visit `/docs`
5. **Tests**: Look at `backend/tests/` for usage examples

## Deployment

### Production Environment

Required services:
- PostgreSQL (managed service like Supabase)
- Redis (managed service like Upstash)
- Object storage (optional - can use RocksDB)

Environment variables:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=1234567890:ABC...
REDIS_URL=redis://user:pass@host:6379
DEBUG=False
LOG_LEVEL=INFO
```

### Cron Jobs

Schedule these scripts:
- `trigger_posts_collection.py` - Hourly (collect HN posts)
- `run_personalized_summarization.py` - Every 30 min (generate summaries)
- `run_delivery_pipeline.py` - User-scheduled (deliver summaries)

## Contributing

1. Read [backend/AGENTS.md](backend/AGENTS.md) for detailed guidelines
2. Create feature branch from `main`
3. Write tests for new features
4. Run checks: `pytest`, `ruff check`, `ruff format`
5. Submit PR with clear description
6. Ensure CI passes before merge

## License

MIT

---

**For detailed backend development instructions, see [backend/AGENTS.md](backend/AGENTS.md)**
