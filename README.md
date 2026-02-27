# HN Pal - AI-Powered Hacker News Digest for Telegram

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![OpenAI](https://img.shields.io/badge/OpenAI-Agents-purple)
![License](https://img.shields.io/badge/License-MIT-green)

Stay informed with personalized Hacker News summaries delivered directly to Telegram. HN Pal automatically collects top stories, extracts article content, and generates AI-powered summaries tailored to your interests.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Automated Post Collection** - Hourly fetching of top Hacker News stories with metadata
- **Smart Content Extraction** - Extracts article content from web pages with caching
- **AI-Powered Summaries** - Five customizable styles (Basic, Technical, Business, Concise, Personalized)
- **Telegram Bot Interface** - Interactive settings, conversation threads, and reaction tracking
- **Cost Optimized** - Prompt caching and batch delivery reduce OpenAI API costs by 90-98%
- **Personalized Delivery** - Filter posts by your interests and preferred summary style
- **Conversation Support** - Discuss posts with multi-turn AI conversations

## How It Works

HN Pal operates as an automated pipeline with several stages:

1. **Collection** - Hourly job fetches top posts from Hacker News API and stores metadata in PostgreSQL
2. **Extraction** - Article content is extracted and cached in RocksDB for fast retrieval
3. **Summarization** - OpenAI Agents generate personalized summaries based on user preferences
4. **Delivery** - Summaries are batched and sent to users via Telegram bot
5. **Interaction** - Users can discuss posts, rate summaries, and adjust preferences through the bot

The system uses PostgreSQL for structured data (posts, users, summaries), RocksDB for content storage, Redis for caching, and integrates with OpenAI and Telegram APIs.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- Telegram bot token (from @BotFather)

### Installation

1. **Clone and setup**:
```bash
git clone https://github.com/yourusername/hackernews_digest.git
cd hackernews_digest
cp backend/.env.example backend/.env
```

2. **Configure environment** (edit `backend/.env`):
```env
# Required
OPENAI_API_KEY=sk-proj-xxxxx
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHANNEL_ID=your-channel-id

# Database (default values work for local development)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/hackernews_digest
REDIS_URL=redis://localhost:6379/0
```

See [Configuration Guide](docs/configuration.md) for all options.

3. **Start services and initialize**:
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Run database migrations
cd backend && python -m alembic upgrade head

# Collect initial posts
python scripts/trigger_posts_collection.py

# Generate summaries
python scripts/run_personalized_summarization.py
```

4. **Run the bot**:
```bash
python scripts/run_bot.py
```

Send `/start` to your Telegram bot to begin! The API is available at `http://localhost:8000/docs`.

## Configuration

### Essential Environment Variables

```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx        # Required: Your OpenAI API key
OPENAI_MODEL=gpt-4o-mini            # Optional: Default model

# Telegram
TELEGRAM_BOT_TOKEN=123:ABC-xyz      # Required: Bot token from @BotFather
TELEGRAM_CHANNEL_ID=123456789       # Required: Your Telegram user/channel ID

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/hackernews_digest
REDIS_URL=redis://localhost:6379/0

# Post Collection
HN_MAX_POSTS=30                     # Number of posts to fetch per cycle

# Monitoring (Optional)
LANGFUSE_ENABLED=true               # Enable cost/token tracking
LANGFUSE_PUBLIC_KEY=pk-xxxxx
LANGFUSE_SECRET_KEY=sk-xxxxx
```

For complete configuration options, see [Configuration Guide](docs/configuration.md).

## Documentation

### Guides
- [Configuration Guide](docs/configuration.md) - Complete environment variable reference
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions
- [Technology Stack](docs/tech-stack.md) - Detailed breakdown of all technologies used

### Architecture
- [Project Structure](docs/architecture/project-structure.md) - Detailed codebase organization
- [Product Specification](docs/spec.md) - Complete product spec with user stories
- [AI Agent Guide](AGENTS.md) - Extending summarization with custom agents

### API
- Interactive API docs: `http://localhost:8000/docs` (when running)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Code standards and style guide
- Testing requirements
- Pull request process
- Branching strategy

**Quick Start for Contributors**:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes, add tests
4. Run quality checks: `ruff check . && pytest`
5. Submit pull request to `develop` branch

## License

MIT License - See LICENSE file for details

---

**Questions?** Check the [docs](docs/) or open a [GitHub issue](https://github.com/yourusername/hackernews_digest/issues)

**Found a bug?** Include environment details and reproduction steps in your issue
