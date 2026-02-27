# Technology Stack

Complete overview of technologies, libraries, and tools used in HN Pal.

## Backend Framework

### FastAPI ^0.104.0
Modern, high-performance web framework for building APIs.

**Why FastAPI?**
- Native async/await support for non-blocking I/O
- Automatic API documentation (OpenAPI/Swagger)
- Type hints with Pydantic for validation
- High performance (comparable to Node.js/Go)

**Usage**: REST API endpoints in `app/presentation/api/`

### Uvicorn ^0.24.0
Lightning-fast ASGI server.

**Usage**: Runs FastAPI application in production

### Pydantic ^2.5.0
Data validation using Python type hints.

**Usage**:
- API request/response schemas
- Environment configuration validation
- Domain value objects

## Database & ORM

### PostgreSQL 15
Primary relational database.

**Why PostgreSQL?**
- ACID compliance for data integrity
- JSON support for flexible fields (user preferences, interests)
- Excellent performance for complex queries
- Mature ecosystem

**Storage**:
- Post metadata (title, URL, score, comments)
- User profiles and preferences
- Summaries and ratings
- Delivery tracking
- Token usage & costs
- Conversation history

### SQLAlchemy ^2.0.0
SQL toolkit and ORM with async support.

**Features Used**:
- Async engine and sessions
- ORM models with relationships
- Query building
- Connection pooling

**Usage**: All database access in `app/infrastructure/database/` and `app/infrastructure/repositories/postgres/`

### Alembic ^1.13.0
Database migration tool.

**Usage**: Schema versioning in `backend/alembic/versions/`

### asyncpg ^0.29.0
Fast PostgreSQL async driver.

**Why asyncpg?**
- Pure Python implementation
- Significantly faster than psycopg2
- Native async/await support

## Caching

### Redis 7
In-memory data store for caching.

**Usage**:
- Cache API responses
- Session storage
- Rate limiting (future)

**Service**: `app/infrastructure/services/redis_cache.py`

### RocksDB
Embedded key-value store for article content.

**Why RocksDB?**
- Fast local storage
- No network overhead
- Efficient for large text content
- Persistent storage

**Storage**:
- HTML article content
- Extracted text
- Markdown formatted content

**Location**: `data/content.rocksdb/`

## AI & LLM

### OpenAI >=2.6.1
OpenAI API client.

**Models Used**:
- `gpt-4o-mini` (default, cost-effective)
- `gpt-4o` (higher quality)
- `gpt-4-turbo` (legacy support)

**Usage**: `app/infrastructure/services/openai_summarization_service.py`

### openai-agents >=0.4.2
OpenAI Agents SDK for complex AI tasks.

**Features Used**:
- Prompt caching for cost reduction
- Multi-turn conversations
- Context management
- Token tracking

**Usage**: `app/infrastructure/agents/summarization_agent.py`

### Langfuse >=3.14.1
LLM observability and cost tracking platform.

**Metrics Tracked**:
- Token usage (input/output)
- API costs per user, per day
- Agent performance
- Prompt effectiveness

**Integration**: Automatic tracking in agent calls

### tiktoken >=0.12.0
Fast BPE tokenizer for OpenAI models.

**Usage**: Token counting before API calls to optimize costs

## Content Extraction

### Trafilatura ^2.0.0
Advanced article content extraction.

**Features**:
- HTML parsing and cleaning
- Main content detection
- Metadata extraction
- Multiple format output (HTML, text, markdown)

**Usage**: `app/infrastructure/services/content_extractor.py`

### httpx ^0.25.0
Modern async HTTP client.

**Why httpx?**
- Async/await support
- HTTP/2 support
- Connection pooling
- Timeout management

**Usage**: All HTTP requests (HN API, web scraping, OpenAI API)

## Telegram Integration

### aiogram ^3.0.0
Modern Telegram bot framework.

**Features Used**:
- Async bot implementation
- FSM (Finite State Machine) for multi-step interactions
- Inline keyboards
- Callback query handlers
- Conversation threads

**Usage**: `app/presentation/bot/`

## Task Scheduling

### APScheduler >=3.11.2
Advanced Python scheduler.

**Schedulers Used**:
- BackgroundScheduler for in-process jobs
- AsyncIOScheduler for async tasks

**Jobs**:
- Hourly post collection
- Periodic summarization
- Delivery scheduling

**Usage**: `app/infrastructure/jobs/data_collector.py`

## Security

### python-jose ^3.3.0
JavaScript Object Signing and Encryption for Python.

**Usage**: JWT token generation and validation

### passlib ^1.7.4
Comprehensive password hashing library.

**Algorithms Used**: bcrypt

### bcrypt ^4.1.0
Secure password hashing.

**Usage**: User authentication (future feature)

## Development Tools

### pytest ^7.4.0
Testing framework.

**Plugins Used**:
- pytest-asyncio ^0.21.0 - Async test support
- pytest-cov ^4.1.0 - Coverage reporting
- pytest-mock - Mocking utilities

**Usage**: `backend/tests/`

### ruff >=0.14.2
Fast Python linter and formatter.

**What it replaces**:
- flake8 (linting)
- black (formatting)
- isort (import sorting)
- pyupgrade (syntax modernization)

**Configuration**: `pyproject.toml`

### mypy ^1.7.0
Static type checker.

**Usage**: Type checking in CI/CD pipeline

### uv
Ultra-fast Python package installer and resolver.

**Why uv?**
- 10-100x faster than pip
- Deterministic dependency resolution
- Workspace support

**Usage**: Dependency management via `uv.lock`

## Infrastructure

### Docker & Docker Compose
Containerization for development and deployment.

**Services**:
- PostgreSQL 15
- Redis 7
- pgAdmin 4

**Configuration**: `docker-compose.yml`

### Terraform
Infrastructure as Code for AWS deployment.

**Resources**:
- EC2 instances
- S3 buckets
- IAM roles

**Location**: `infra/`

## Python Version

**Required**: Python 3.11+

**Why 3.11+?**
- Significant performance improvements
- Better error messages
- Type hint improvements
- TaskGroup for async concurrency

## Dependency Management

### pyproject.toml
Modern Python project configuration.

**Sections**:
- `[project]` - Package metadata
- `[project.dependencies]` - Runtime dependencies
- `[project.optional-dependencies]` - Dev dependencies
- `[tool.ruff]` - Linter configuration
- `[tool.mypy]` - Type checker configuration
- `[tool.pytest]` - Test configuration

### uv.lock
Dependency lock file for reproducible builds.

**Benefits**:
- Exact version pinning
- Cross-platform consistency
- Faster installation

## Architecture Patterns

### Clean Architecture
Separation of concerns across layers:
- Domain (entities, value objects)
- Application (use cases)
- Infrastructure (external integrations)
- Presentation (API, Bot)

### Repository Pattern
Abstract data access behind interfaces.

**Benefits**:
- Easy to swap implementations (JSONL ↔ PostgreSQL)
- Testable with mocks
- Clear contracts

### Dependency Injection
Dependencies passed via constructor, not created internally.

**Benefits**:
- Testability
- Flexibility
- Explicit dependencies

## Monitoring & Observability

### Langfuse
LLM-specific observability.

**Dashboards**:
- Token usage over time
- Cost per user
- Model performance
- Error tracking

### Python Logging
Built-in logging with configurable levels.

**Configuration**: `LOG_LEVEL` environment variable

**Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Future Technologies (Roadmap)

### Potential Additions
- **Celery** - Distributed task queue for heavy workloads
- **Prometheus + Grafana** - Metrics and monitoring
- **Sentry** - Error tracking
- **ElasticSearch** - Full-text search for posts
- **Docker Swarm/Kubernetes** - Container orchestration for scaling

## Version Compatibility

| Component | Minimum Version | Recommended |
|-----------|----------------|-------------|
| Python | 3.11 | 3.11+ |
| PostgreSQL | 13 | 15 |
| Redis | 6 | 7 |
| Docker | 20.10 | Latest |
| Docker Compose | 2.0 | Latest |

## Installation Methods

### Using uv (Recommended)
```bash
uv sync
```

### Using pip
```bash
pip install -r requirements.txt
```

## Performance Characteristics

### API Response Time
- **Average**: 50-200ms (cached)
- **P95**: 500ms
- **P99**: 1s

### Summarization
- **Per post**: 2-5s (with prompt caching)
- **Batch (30 posts)**: 30-60s

### Database Queries
- **Simple reads**: 1-5ms
- **Complex joins**: 10-50ms

## Cost Optimization

### Prompt Caching
**Savings**: 90% on repeated system prompts

**How**: OpenAI caches system prompts for 5-minute window, charges 10% for cache hits

### Batch Delivery
**Savings**: 95-98% on API calls

**How**: Groups users by delivery style, one API call per group

### RocksDB Storage
**Savings**: No cloud storage costs

**Trade-off**: Local disk space usage

## Scaling Considerations

### Current Limits
- Single instance handles ~1000 users
- PostgreSQL connection pool: 20 connections
- RocksDB: Limited by disk I/O

### Scaling Options
1. **Vertical**: Increase instance size
2. **Horizontal**: Add read replicas for PostgreSQL
3. **Distributed**: Move to Celery + Redis for task queue
4. **CDN**: Cache static API responses

## Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [OpenAI Agents SDK](https://github.com/openai/openai-python)
- [Langfuse Docs](https://langfuse.com/docs)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
