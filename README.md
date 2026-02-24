# HN Pal - AI-Powered Hacker News Digest for Telegram

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-Agents-purple)
![License](https://img.shields.io/badge/License-MIT-green)

**Personalized Hacker News summaries delivered to Telegram with AI-powered insights and customizable summary styles.**

HN Pal automatically collects posts from Hacker News, extracts article content, generates intelligent summaries using OpenAI Agents, and delivers them to your Telegram bot with full interactivity. With five distinct summary styles, cost optimization through prompt caching, and comprehensive preference tracking, it's a production-ready solution for staying informed.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture-overview)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Core Concepts](#core-concepts)
- [Usage Guide](#usage-guide)
- [Development](#development)
- [Technology Stack](#technology-stack)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Capabilities

- **Automated Collection**: Hourly fetching of top Hacker News posts with post metadata (score, comments, etc.)
- **Smart Content Extraction**: Multi-format extraction (HTML, text, markdown) using Trafilatura with caching
- **AI-Powered Summarization**: Five customizable summary styles:
  - **Basic** - Balanced coverage for all content types
  - **Technical** - Deep technical details and implementation insights
  - **Business** - Market impact, strategy, and business implications
  - **Concise** - One-sentence distilled summaries
  - **Personalized** - User interest-aware customization
- **Telegram Bot Integration**: Interactive `/settings` menu with:
  - Summary style preferences
  - Delivery pause/resume controls
  - Interest topic management
  - Conversation threads for discussions
  - Reaction tracking (thumbs up/down)

### Advanced Features

- **Cost Optimization**:
  - Prompt caching for 90% cost reduction on repeated system prompts
  - Grouped delivery batching to reduce API calls by 95-98%
  - Token usage tracking per user, per day, per agent call

- **Intelligent Delivery**: Personalized post selection and scheduling with user preference awareness
- **Full Conversation Support**: Multi-turn discussions about posts with message history and memory toggle
- **User Preference Persistence**: Delivery styles, interests, memory settings stored in database
- **Comprehensive Monitoring**: Cost and token usage tracking via Langfuse integration
- **Production Ready**: Clean architecture, error resilience, comprehensive logging

## Architecture Overview

```
┌─────────────────────┐
│   Hacker News API   │
└──────────┬──────────┘
           │ Hourly (APScheduler)
           ▼
┌──────────────────────────────────┐
│  Post Collection Pipeline        │
│  (fetch_hn_posts.py)             │
└──────────┬───────────────────────┘
           │
           ├────────────────────────┐
           ▼                        ▼
    ┌────────────┐         ┌─────────────┐
    │ PostgreSQL │         │   RocksDB   │
    │  (Posts)   │         │  (Content)  │
    └────────────┘         └─────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Content Extraction              │
│  (crawl_content.py)              │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  AI Summarization (OpenAI Agents)│
│  - Per-user personalization      │
│  - Prompt caching enabled        │
│  - Token tracking via Langfuse   │
└──────────┬───────────────────────┘
           │
           ├────────────────────┐
           ▼                    ▼
    ┌────────────┐       ┌──────────────┐
    │ PostgreSQL │       │   Redis      │
    │(Summaries) │       │  (Cache)     │
    └────────────┘       └──────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Delivery Pipeline               │
│  - Batch delivery optimization   │
│  - User preference filtering     │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Telegram Bot                    │
│  - Interactive settings          │
│  - Conversation threads          │
│  - Reaction tracking             │
└──────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for PostgreSQL, Redis, pgAdmin)
- **API Keys**:
  - OpenAI API key (for GPT models)
  - Telegram Bot token (from @BotFather)
  - Telegram user/channel ID (for delivery)

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/hackernews_digest.git
cd hackernews_digest
```

2. **Set up environment variables**:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your credentials:
```env
# Core
APP_NAME=HN Pal
DEBUG=False
LOG_LEVEL=INFO

# Security (generate with: python -c "from passlib.context import CryptContext; print(__import__('secrets').token_urlsafe(32))")
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/hackernews_digest
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_DEFAULT_TEMPERATURE=0.7
OPENAI_DEFAULT_MAX_TOKENS=1000

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHANNEL_ID=your-channel-id

# HackerNews API
HN_API_BASE_URL=https://hacker-news.firebaseio.com/v0
HN_MAX_POSTS=30
HN_MAX_COMMENTS=5

# Langfuse (optional - for cost tracking)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-xxxxx
LANGFUSE_SECRET_KEY=sk-xxxxx

# Content Extraction
CONTENT_EXTRACTION_TIMEOUT=30

# CORS (adjust for production)
CORS_ORIGINS=["http://localhost:3000"]
```

3. **Start infrastructure services**:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5433)
- Redis (port 6379)
- pgAdmin (port 5050)

4. **Initialize database**:
```bash
cd backend
python -m alembic upgrade head
```

5. **Collect initial posts**:
```bash
python scripts/trigger_posts_collection.py
```

6. **Generate summaries**:
```bash
python scripts/run_personalized_summarization.py
```

7. **Start the Telegram bot**:
```bash
python scripts/run_bot.py
```

8. **Start the API server** (in a new terminal):
```bash
cd backend
uvicorn app.main:app --reload
```

**Verify it works**:
- Send `/start` to your Telegram bot
- API docs available at `http://localhost:8000/docs`

## Project Structure

```
hackernews_digest/
├── backend/
│   ├── app/
│   │   ├── domain/                    # Business entities & value objects
│   │   │   ├── entities.py            # Post, User, Summary, Digest, etc.
│   │   │   ├── exceptions.py          # Domain exceptions
│   │   │   └── value_objects.py       # URL, Email, etc.
│   │   │
│   │   ├── application/               # Use cases & business logic
│   │   │   ├── interfaces.py          # Repository & service contracts
│   │   │   └── use_cases/
│   │   │       ├── collection.py      # HN post collection
│   │   │       ├── crawl_content.py   # Article extraction
│   │   │       ├── summarization.py   # Summary generation
│   │   │       ├── delivery_pipeline.py     # Telegram delivery
│   │   │       ├── delivery_grouper.py      # Batch optimization
│   │   │       └── auth.py            # Authentication
│   │   │
│   │   ├── infrastructure/            # External integrations
│   │   │   ├── config/
│   │   │   │   └── settings.py        # Environment configuration
│   │   │   ├── database/
│   │   │   │   ├── base.py            # SQLAlchemy setup
│   │   │   │   └── models.py          # ORM models
│   │   │   ├── repositories/          # Data access
│   │   │   │   ├── jsonl_*.py         # JSONL implementations
│   │   │   │   └── postgres/          # PostgreSQL implementations
│   │   │   ├── services/              # External services
│   │   │   │   ├── hn_client.py       # HN API client
│   │   │   │   ├── content_extractor.py
│   │   │   │   ├── openai_summarization_service.py
│   │   │   │   ├── telegram_notifier.py
│   │   │   │   └── redis_cache.py
│   │   │   ├── agents/                # AI agent implementations
│   │   │   │   ├── base_agent.py
│   │   │   │   ├── summarization_agent.py
│   │   │   │   └── token_tracker.py
│   │   │   └── jobs/                  # Background schedulers
│   │   │       └── data_collector.py  # APScheduler jobs
│   │   │
│   │   ├── presentation/              # API & Bot interfaces
│   │   │   ├── api/                   # FastAPI routes
│   │   │   │   ├── auth.py
│   │   │   │   ├── digests.py
│   │   │   │   └── deliveries.py
│   │   │   ├── bot/                   # Telegram bot
│   │   │   │   ├── bot.py
│   │   │   │   ├── states.py          # FSM states
│   │   │   │   ├── handlers/          # Command & callback handlers
│   │   │   │   ├── keyboards/         # Interactive menus
│   │   │   │   └── formatters/        # Message formatting
│   │   │   └── schemas/               # Pydantic models
│   │   │
│   │   └── main.py                    # FastAPI app entry
│   
├── data/                              # Local storage
│   ├── content.rocksdb/               # Article content storage
│   └── test_posts.json                 # Sample posts for tests
│
├── docs/                              # Project documentation
│   ├── activities/
│   ├── api/
│   ├── architecture/
│   ├── design/
│   ├── epics/
│   ├── stories/
│   ├── brainstorming-session-results.md
│   ├── hn_api.md
│   ├── prd.md
│   ├── spec.md
│   └── sprint-plan.md
│
├── infra/                             # Terraform infrastructure
│   ├── ec2.tf
│   ├── iam.tf
│   ├── main.tf
│   ├── outputs.tf
│   ├── s3.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── terraform.tfvars.example
│   ├── terraform.tfstate
│   ├── terraform.tfstate.backup
│   └── scripts/
│       └── user-data.sh
│
├── scripts/                           # Devops helpers
│   ├── deploy-auto.sh
│   └── deploy-update.sh
│
├── docker-compose.yml                 # Development services orchestration
├── .github/                           # GitHub tooling
│   └── chatmodes/
├── .vscode/                           # Editor settings
├── AGENTS.md                          # AI agent guide
├── README.md                          # This file
├── uv.lock                            # Dependency lock
├── pyproject.toml                     # Workspace config
└── .env.example                       # Environment template
```
## Configuration

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_NAME` | Yes | Application name (default: HN Pal) |
| `DEBUG` | No | Debug mode (default: false) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `SECRET_KEY` | Yes | JWT signing key |
| `ALGORITHM` | No | JWT algorithm (default: HS256) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | LLM model (default: gpt-4o-mini) |
| `OPENAI_DEFAULT_TEMPERATURE` | No | Response temperature (0-2, default: 0.7) |
| `OPENAI_DEFAULT_MAX_TOKENS` | No | Max tokens per response |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Yes | Target channel/user ID for delivery |
| `HN_API_BASE_URL` | No | HN API endpoint (default: Firebase) |
| `HN_MAX_POSTS` | No | Posts to fetch per cycle (default: 30) |
| `HN_MAX_COMMENTS` | No | Comments per post (default: 5) |
| `LANGFUSE_ENABLED` | No | Enable Langfuse tracking (default: true) |
| `LANGFUSE_PUBLIC_KEY` | No | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | No | Langfuse secret key |
| `CONTENT_EXTRACTION_TIMEOUT` | No | Extraction timeout in seconds (default: 30) |
| `CORS_ORIGINS` | No | CORS allowed origins (JSON array) |

### Docker Compose Services

The `docker-compose.yml` provides:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 | Primary database (hackernews_digest) |
| Redis | 6379 | In-memory cache |
| pgAdmin | 5050 | Database UI (admin@admin.com / admin) |

Start with: `docker-compose up -d`
Stop with: `docker-compose down`

### Database Migrations

Run migrations with Alembic:

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Create a new migration
python -m alembic revision --autogenerate -m "description"

# Revert to previous version
python -m alembic downgrade -1
```

## Core Concepts

### Summary Styles

Each user can select their preferred summary style:

1. **Basic** - Neutral, factual coverage with key points
2. **Technical** - Deep technical details, architecture, implementation patterns
3. **Business** - Market implications, strategic impact, business models
4. **Concise** - Single sentence essence of the story
5. **Personalized** - Tailored to user's stated interests (AI, backend, security, etc.)

Styles are stored per-user in the database and used to filter articles and customize summaries.

### Storage Architecture

**PostgreSQL** stores:
- Post metadata (title, URL, score, comment count)
- User profiles and preferences
- Summaries and ratings
- Delivery tracking
- Token usage & costs
- Conversation history

**RocksDB** (`data/content.rocksdb/`) stores:
- HTML article content
- Text extraction
- Markdown formatted content

This split optimizes for both query performance (PostgreSQL) and fast content retrieval (RocksDB).

### Cost Optimization Strategies

**Prompt Caching** (90% reduction):
- System prompts cached for 5-minute window
- Repeated summarization reuses cached tokens at 10% cost

**Batch Delivery** (95-98% reduction):
- Groups users by delivery_style
- One API call per style covers multiple users
- Reduces from N users × N posts to ~5 batch calls

**Incremental Processing**:
- Only processes posts since user's last summary
- Skips already-crawled content
- Reuses cached extraction results

### Entity Relationships

```
User (telegram_id)
├── has many Summaries (post_id, user_id)
├── has many Deliveries (post_id, user_id, batch_id)
└── has many Conversations (post_id, messages[], token_usage)

Post (hn_id)
├── has many Summaries (multiple styles per user)
└── has many Deliveries (tracks who received it)

Summary (id)
├── belongs to User
├── belongs to Post
└── has UserTokenUsage (daily cost tracking)
```

## Usage Guide

### Running the Application

#### API Server
```bash
cd backend
uvicorn app.main:app --reload
```
Access docs at `http://localhost:8000/docs`

#### Telegram Bot
```bash
python scripts/run_bot.py
```
Send `/start` to your bot to begin.

#### Background Jobs
The following run automatically when the API server starts:
- Hourly post collection (midnight UTC)
- 30-minute summarization cycles (during business hours)
- Scheduled delivery (8am, 12pm, 6pm UTC)

Override in code or trigger manually:
```bash
python scripts/trigger_posts_collection.py
python scripts/run_personalized_summarization.py
python scripts/run_delivery_pipeline.py
```

## Development

### Setting Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with Poetry
pip install poetry
poetry install

# Or with uv (faster)
pip install uv
uv sync
```

### Running Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend/app --cov-report=html

# Run specific test file
pytest backend/tests/unit/test_entities.py -v

# Run async tests
pytest backend/tests/ -k "async" --asyncio-mode=auto
```

### Code Quality

```bash
# Format code
ruff format backend/

# Check for issues
ruff check backend/ --fix

# Type checking
mypy backend/app --strict

# All checks
ruff check backend/ && mypy backend/app --strict
```

### Making Changes

1. **Create a feature branch**:
```bash
git checkout -b feature/summary-filtering
```

2. **Follow the architecture**:
   - Domain logic → `app/domain/`
   - Use cases → `app/application/use_cases/`
   - Implementations → `app/infrastructure/`
   - APIs/UI → `app/presentation/`

3. **Add tests** for new functionality:
```bash
# Unit tests
touch backend/tests/unit/test_new_feature.py

# Integration tests
touch backend/tests/integration/test_new_feature.py
```

4. **Create database migration** if needed:
```bash
python -m alembic revision --autogenerate -m "add new feature"
```

5. **Submit PR** with test coverage and description.

### Database Migrations

Create a new migration:
```bash
python -m alembic revision --autogenerate -m "add user_preferences column"
```

Review and apply:
```bash
python -m alembic upgrade head
```

View migration status:
```bash
python -m alembic current
python -m alembic history
```

## Technology Stack

### Backend & Framework
- **FastAPI** ^0.104.0 - Modern web framework
- **Uvicorn** ^0.24.0 - ASGI server
- **Pydantic** ^2.5.0 - Data validation

### Database & Caching
- **PostgreSQL** 15 - Primary database
- **SQLAlchemy** ^2.0.0 - ORM with async support
- **Alembic** ^1.13.0 - Schema migrations
- **asyncpg** ^0.29.0 - PostgreSQL async driver
- **Redis** 7 - In-memory cache
- **RocksDB** - Fast embedded key-value storage

### AI & LLM
- **OpenAI** >=2.6.1 - GPT models
- **openai-agents** >=0.4.2 - Agents SDK for complex tasks
- **Langfuse** >=3.14.1 - LLM observability & cost tracking
- **tiktoken** >=0.12.0 - Token counting

### Content & Integration
- **Trafilatura** ^2.0.0 - Article extraction
- **httpx** ^0.25.0 - Async HTTP client
- **aiogram** ^3.0.0 - Telegram bot framework

### Task Scheduling
- **APScheduler** >=3.11.2 - Background job scheduling

### Security
- **python-jose** ^3.3.0 - JWT tokens
- **passlib** ^1.7.4 - Password hashing
- **bcrypt** ^4.1.0 - Secure hashing

### Development & Testing
- **pytest** ^7.4.0 - Testing framework
- **pytest-asyncio** ^0.21.0 - Async test support
- **pytest-cov** ^4.1.0 - Coverage reporting
- **ruff** >=0.14.2 - Linting & formatting
- **mypy** ^1.7.0 - Type checking

## Database Schema

```mermaid
erDiagram
    POSTS {
        int id PK "Auto-increment"
        int hn_id "Hacker News ID (unique)"
        string title
        string url
        int score
        int comment_count
        timestamp created_at
        bool has_html
        bool has_text
        bool is_crawl_success
        string summary
    }

    USERS {
        int id PK
        int telegram_id "Unique chat/user ID"
        string username
        json interests
        string status
        json summary_preferences
        string delivery_style
        bool memory_enabled
        timestamp created_at
        timestamp updated_at
    }

    SUMMARIES {
        int id PK
        int post_id FK
        int user_id FK
        string prompt_type
        text summary_text
        decimal cost_usd
        int token_count
        int rating
        timestamp created_at
    }

    DELIVERIES {
        int id PK
        int user_id FK
        int post_id FK
        string batch_id
        string message_id
        string reaction
        timestamp delivered_at
    }

    CONVERSATIONS {
        int id PK
        int user_id FK
        int post_id FK
        json messages
        json token_usage
        timestamp created_at
        timestamp updated_at
    }

    USER_TOKEN_USAGE {
        int id PK
        int user_id FK
        date day
        string model
        int input_tokens
        int output_tokens
        decimal cost_usd
    }

    POSTS ||--o{ SUMMARIES : has
    USERS ||--o{ SUMMARIES : generates
    USERS ||--o{ DELIVERIES : receives
    POSTS ||--o{ DELIVERIES : references
    USERS ||--o{ CONVERSATIONS : participates
    POSTS ||--o{ CONVERSATIONS : discusses
    USERS ||--o{ USER_TOKEN_USAGE : tracks
```

See `backend/app/infrastructure/database/models.py` for the definitive schema implementation.

## Troubleshooting

### Database Connection Errors

**Problem**: `could not connect to server: Connection refused`

**Solution**:
```bash
# Verify PostgreSQL is running
docker-compose ps

# Restart services
docker-compose down && docker-compose up -d

# Check logs
docker-compose logs postgres
```

### OpenAI API Errors

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
- Wait 1-2 minutes before retrying
- Check your API quota at platform.openai.com
- Consider upgrading your plan

**Problem**: `AuthenticationError: Invalid API key`

**Solution**:
- Verify `OPENAI_API_KEY` in `.env`
- Ensure no leading/trailing whitespace
- Regenerate key at platform.openai.com if needed

### Telegram Bot Not Responding

**Problem**: Bot doesn't respond to `/start`

**Solution**:
```bash
# Verify bot token
python scripts/test_telegram.py

# Check bot is running
ps aux | grep run_bot.py

# Restart bot
python scripts/run_bot.py

# Verify in logs
tail -f /var/log/hn_pal.log
```

**Problem**: `telegram.error.Unauthorized: Forbidden`

**Solution**:
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Confirm bot was started with @BotFather
- Ensure channel/user ID is valid

### RocksDB Permission Issues

**Problem**: `Error: IO error: Permission denied`

**Solution**:
```bash
# Fix permissions
chmod -R 755 data/content.rocksdb/

# Or restart with proper permissions
sudo chown -R $USER:$USER data/
```

### Content Extraction Failures

**Problem**: Some articles not being extracted

**Solution**:
- Check timeout: `CONTENT_EXTRACTION_TIMEOUT` (default 30s)
- Website may be blocking extraction
- Verify `is_crawl_success` flag in database
- Check extraction service logs for details

### High Token/Cost Usage

**Problem**: Costs unexpectedly high

**Solution**:
- Review `user_token_usage` table for abnormal usage
- Check if prompt caching is enabled: `OPENAI_DEFAULT_*` settings
- Verify `openai_api_key` isn't being used elsewhere
- Monitor with Langfuse dashboard for API call details

## Documentation

Extended documentation available in `/docs`:

- **`spec.md`** - Complete product specification with user stories
- **`prd.md`** - Product requirements and feature breakdown
- **`hn_api.md`** - Hacker News API integration details
- **`AGENTS.md`** - AI agent development guide for extending summarization
- **`architecture/`** - System design and component architecture

## Contributing

### Branching Strategy

- `main` - Stable production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches (create from develop)
- `bugfix/*` - Bug fix branches (create from develop)

### Pull Request Process

1. Create feature branch: `git checkout -b feature/description`
2. Make changes following code style (Ruff)
3. Add tests for new functionality
4. Create database migrations if needed
5. Open PR with description and test plan
6. Ensure CI passes (tests, linting, coverage)
7. Code review approval required
8. Merge to develop, then promote to main

### Code Review Checklist

- Architecture follows clean architecture principles
- Tests included and passing
- Type hints present (mypy compatible)
- No hardcoded values or secrets
- Documentation updated
- Performance impact considered
- Error handling implemented

## License

MIT License - See LICENSE file for details

---

**Need help?** Check the documentation in `/docs` or open an issue on GitHub.

**Want to extend summarization?** See `AGENTS.md` for the AI agent development guide.

**Found a bug?** Please include your environment details and reproduction steps.
