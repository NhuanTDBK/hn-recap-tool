# Configuration Guide

Complete reference for configuring HN Pal.

## Environment Variables

All configuration is managed through environment variables in `backend/.env`.

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | Yes | `HN Pal` | Application name |
| `DEBUG` | No | `False` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | JWT signing key (use `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT expiration time |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string (format: `postgresql+asyncpg://user:password@host:port/database`) |
| `REDIS_URL` | Yes | - | Redis connection string (format: `redis://host:port/db`) |

### OpenAI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key from platform.openai.com |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model to use (gpt-4o-mini, gpt-4o, gpt-4-turbo) |
| `OPENAI_DEFAULT_TEMPERATURE` | No | `0.7` | Response temperature (0-2, higher = more creative) |
| `OPENAI_DEFAULT_MAX_TOKENS` | No | `1000` | Maximum tokens per response |

### Telegram

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Yes | - | Target channel or user ID for delivery |

### Hacker News API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HN_API_BASE_URL` | No | `https://hacker-news.firebaseio.com/v0` | HN API endpoint |
| `HN_MAX_POSTS` | No | `30` | Number of posts to fetch per collection cycle |
| `HN_MAX_COMMENTS` | No | `5` | Maximum comments per post to fetch |

### Langfuse (Observability)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_ENABLED` | No | `true` | Enable Langfuse tracking |
| `LANGFUSE_PUBLIC_KEY` | No | - | Langfuse public key from app.langfuse.com |
| `LANGFUSE_SECRET_KEY` | No | - | Langfuse secret key |

### Content Extraction

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT_EXTRACTION_TIMEOUT` | No | `30` | Timeout in seconds for article extraction |

### CORS

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | CORS allowed origins (JSON array format) |

## Docker Compose Services

The `docker-compose.yml` file defines these services:

### PostgreSQL
- **Port**: 5433 (mapped to avoid conflicts with local PostgreSQL)
- **Database**: `hackernews_digest`
- **User**: `user`
- **Password**: `password`
- **Volume**: `postgres_data` (persistent storage)

### Redis
- **Port**: 6379
- **Volume**: `redis_data` (persistent storage)

### pgAdmin
- **Port**: 5050
- **Login**: admin@admin.com / admin
- **Purpose**: Web-based database management UI

**Commands**:
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]
```

## Database Migrations

HN Pal uses Alembic for database schema migrations.

### Common Commands

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Create a new migration (after modifying models)
python -m alembic revision --autogenerate -m "description of changes"

# Rollback to previous version
python -m alembic downgrade -1

# View migration history
python -m alembic history

# View current version
python -m alembic current
```

### Migration Workflow

1. Modify models in `backend/app/infrastructure/database/models.py`
2. Generate migration: `python -m alembic revision --autogenerate -m "add new field"`
3. Review generated migration in `backend/alembic/versions/`
4. Apply migration: `python -m alembic upgrade head`

## Example .env File

```env
# Core
APP_NAME=HN Pal
DEBUG=False
LOG_LEVEL=INFO

# Security
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
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=123456789

# HackerNews API
HN_API_BASE_URL=https://hacker-news.firebaseio.com/v0
HN_MAX_POSTS=30
HN_MAX_COMMENTS=5

# Langfuse (optional)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-xxxxx
LANGFUSE_SECRET_KEY=sk-xxxxx

# Content Extraction
CONTENT_EXTRACTION_TIMEOUT=30

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

## Production Considerations

### Security
- Generate strong `SECRET_KEY` (at least 32 bytes)
- Never commit `.env` files to version control
- Use environment-specific configurations
- Rotate API keys regularly

### Database
- Use connection pooling in production
- Set appropriate `DATABASE_URL` with SSL for remote databases
- Regular backups recommended

### OpenAI
- Monitor API usage via platform.openai.com
- Set up billing alerts
- Consider rate limiting for production

### Telegram
- Use separate bot tokens for dev/staging/prod
- Verify webhook setup if using webhooks instead of polling

## Storage Configuration

### RocksDB
Article content is stored in `data/content.rocksdb/`.

**Permissions**:
```bash
# Ensure proper permissions
chmod -R 755 data/content.rocksdb/
chown -R $USER:$USER data/
```

**Storage location** can be changed by modifying the path in `backend/app/infrastructure/services/content_extractor.py`.

### Data Directory Structure
```
data/
├── content.rocksdb/    # Article content storage
└── test_posts.json     # Sample posts for testing
```
