# Project Structure

Detailed breakdown of HN Pal's codebase organization.

## Overview

HN Pal follows Clean Architecture principles with clear separation between domain logic, application use cases, infrastructure, and presentation layers.

## Directory Tree

```
hackernews_digest/
├── backend/                           # Main application code
│   ├── app/
│   │   ├── domain/                    # Business entities & value objects
│   │   │   ├── entities.py            # Core entities: Post, User, Summary, Digest, etc.
│   │   │   ├── exceptions.py          # Domain-specific exceptions
│   │   │   └── value_objects.py       # Value objects: URL, Email, etc.
│   │   │
│   │   ├── application/               # Use cases & business logic
│   │   │   ├── interfaces.py          # Repository & service contracts
│   │   │   └── use_cases/             # Application use cases
│   │   │       ├── collection.py      # HN post collection logic
│   │   │       ├── crawl_content.py   # Article extraction logic
│   │   │       ├── summarization.py   # Summary generation logic
│   │   │       ├── delivery_pipeline.py     # Telegram delivery orchestration
│   │   │       ├── delivery_grouper.py      # Batch delivery optimization
│   │   │       └── auth.py            # Authentication use cases
│   │   │
│   │   ├── infrastructure/            # External integrations & implementations
│   │   │   ├── config/
│   │   │   │   └── settings.py        # Environment configuration (Pydantic settings)
│   │   │   │
│   │   │   ├── database/              # Database layer
│   │   │   │   ├── base.py            # SQLAlchemy setup, session management
│   │   │   │   └── models.py          # ORM models (Post, User, Summary, etc.)
│   │   │   │
│   │   │   ├── repositories/          # Data access implementations
│   │   │   │   ├── jsonl_*.py         # JSONL file-based repositories
│   │   │   │   └── postgres/          # PostgreSQL implementations
│   │   │   │       ├── post_repository.py
│   │   │   │       ├── user_repository.py
│   │   │   │       ├── summary_repository.py
│   │   │   │       ├── delivery_repository.py
│   │   │   │       └── conversation_repository.py
│   │   │   │
│   │   │   ├── services/              # External service integrations
│   │   │   │   ├── hn_client.py       # Hacker News API client
│   │   │   │   ├── content_extractor.py  # Trafilatura + RocksDB content extraction
│   │   │   │   ├── openai_summarization_service.py  # OpenAI API wrapper
│   │   │   │   ├── telegram_notifier.py  # Telegram bot delivery service
│   │   │   │   └── redis_cache.py     # Redis caching service
│   │   │   │
│   │   │   ├── agents/                # AI agent implementations
│   │   │   │   ├── base_agent.py      # Base agent class
│   │   │   │   ├── summarization_agent.py  # OpenAI Agents-based summarizer
│   │   │   │   └── token_tracker.py   # Token usage & cost tracking
│   │   │   │
│   │   │   └── jobs/                  # Background job schedulers
│   │   │       └── data_collector.py  # APScheduler jobs (hourly post collection)
│   │   │
│   │   ├── presentation/              # API & Bot interfaces
│   │   │   ├── api/                   # FastAPI routes
│   │   │   │   ├── auth.py            # Authentication endpoints
│   │   │   │   ├── digests.py         # Digest management endpoints
│   │   │   │   ├── deliveries.py      # Delivery tracking endpoints
│   │   │   │   └── posts.py           # Post endpoints
│   │   │   │
│   │   │   ├── bot/                   # Telegram bot implementation
│   │   │   │   ├── bot.py             # Bot initialization & main loop
│   │   │   │   ├── states.py          # FSM (Finite State Machine) states
│   │   │   │   ├── handlers/          # Command & callback handlers
│   │   │   │   │   ├── start.py       # /start command
│   │   │   │   │   ├── settings.py    # /settings command & preferences
│   │   │   │   │   ├── conversation.py  # Discussion handlers
│   │   │   │   │   └── reactions.py   # Thumbs up/down reactions
│   │   │   │   ├── keyboards/         # Interactive keyboard layouts
│   │   │   │   │   ├── main_menu.py
│   │   │   │   │   └── settings_menu.py
│   │   │   │   └── formatters/        # Message formatting
│   │   │   │       └── message_formatter.py
│   │   │   │
│   │   │   └── schemas/               # Pydantic models for API
│   │   │       ├── post.py
│   │   │       ├── user.py
│   │   │       ├── summary.py
│   │   │       └── auth.py
│   │   │
│   │   └── main.py                    # FastAPI app entry point
│   │
│   ├── alembic/                       # Database migrations
│   │   ├── versions/                  # Migration files
│   │   └── env.py                     # Alembic configuration
│   │
│   ├── scripts/                       # Utility scripts
│   │   ├── run_bot.py                 # Start Telegram bot
│   │   ├── trigger_posts_collection.py  # Manual post collection
│   │   ├── run_personalized_summarization.py  # Manual summarization
│   │   └── test_telegram.py           # Telegram connection test
│   │
│   ├── tests/                         # Test suite
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   ├── .env                           # Environment variables (not committed)
│   ├── .env.example                   # Environment template
│   ├── pyproject.toml                 # Python dependencies & config
│   └── uv.lock                        # Dependency lock file
│
├── data/                              # Local data storage
│   ├── content.rocksdb/               # RocksDB database for article content
│   │   ├── html/                      # HTML content namespace
│   │   ├── text/                      # Text content namespace
│   │   └── markdown/                  # Markdown content namespace
│   └── test_posts.json                # Sample posts for testing
│
├── docs/                              # Project documentation
│   ├── architecture/                  # Architecture documentation
│   │   ├── project-structure.md       # This file
│   │   └── system-design.md           # System design diagrams
│   ├── api/                           # API documentation
│   ├── activities/                    # Development activities
│   ├── design/                        # Design decisions
│   ├── epics/                         # Feature epics
│   ├── stories/                       # User stories
│   ├── configuration.md               # Configuration reference
│   ├── troubleshooting.md             # Common issues & solutions
│   ├── tech-stack.md                  # Technology details
│   ├── spec.md                        # Product specification
│   ├── prd.md                         # Product requirements
│   └── hn_api.md                      # Hacker News API docs
│
├── infra/                             # Infrastructure as Code
│   ├── ec2.tf                         # EC2 instance configuration
│   ├── iam.tf                         # IAM roles & policies
│   ├── s3.tf                          # S3 bucket configuration
│   ├── main.tf                        # Main Terraform config
│   ├── variables.tf                   # Terraform variables
│   ├── outputs.tf                     # Terraform outputs
│   ├── terraform.tfvars.example       # Example variables
│   └── scripts/
│       └── user-data.sh               # EC2 initialization script
│
├── scripts/                           # DevOps scripts
│   ├── deploy-auto.sh                 # Automated deployment
│   └── deploy-update.sh               # Update deployment
│
├── .github/                           # GitHub configuration
│   ├── instructions/                  # GitHub Copilot instructions
│   └── chatmodes/                     # Chat mode configurations
│
├── .vscode/                           # VS Code settings
│   └── settings.json
│
├── docker-compose.yml                 # Development services (PostgreSQL, Redis, pgAdmin)
├── AGENTS.md                          # AI agent development guide
├── CONTRIBUTING.md                    # Contribution guidelines
├── README.md                          # Main documentation
├── LICENSE                            # MIT license
├── pyproject.toml                     # Workspace-level Python config
└── uv.lock                            # Workspace dependency lock
```

## Layer Responsibilities

### Domain Layer (`app/domain/`)
**Purpose**: Core business entities and logic, framework-agnostic.

- **entities.py**: Business entities (Post, User, Summary, Digest, Delivery)
- **value_objects.py**: Immutable value objects (URL, Email)
- **exceptions.py**: Domain-specific exceptions

**Key Principle**: No external dependencies. Pure Python classes.

### Application Layer (`app/application/`)
**Purpose**: Use cases and business workflows.

- **interfaces.py**: Abstract contracts (Repository, Service interfaces)
- **use_cases/**: Orchestrates domain entities and infrastructure services

**Key Principle**: Depends on domain, defines contracts for infrastructure.

### Infrastructure Layer (`app/infrastructure/`)
**Purpose**: External integrations and technical implementations.

- **config/**: Environment variable management
- **database/**: ORM models and database setup
- **repositories/**: Data access implementations
- **services/**: External API clients (OpenAI, Telegram, HN)
- **agents/**: AI agent implementations
- **jobs/**: Background schedulers

**Key Principle**: Implements application interfaces, handles all external I/O.

### Presentation Layer (`app/presentation/`)
**Purpose**: User-facing interfaces (API, Bot).

- **api/**: REST API endpoints (FastAPI)
- **bot/**: Telegram bot interface (aiogram)
- **schemas/**: Request/response models

**Key Principle**: Thin layer that translates external requests to use cases.

## Data Flow

### Post Collection Flow
```
APScheduler → collection.py (use case)
    → hn_client.py (fetch posts)
    → post_repository.py (save to PostgreSQL)
```

### Content Extraction Flow
```
crawl_content.py (use case)
    → content_extractor.py (Trafilatura)
    → RocksDB (store HTML/text/markdown)
```

### Summarization Flow
```
summarization.py (use case)
    → summarization_agent.py (OpenAI Agents)
    → summary_repository.py (save to PostgreSQL)
    → token_tracker.py (track usage)
```

### Delivery Flow
```
delivery_pipeline.py (use case)
    → delivery_grouper.py (batch by style)
    → telegram_notifier.py (send messages)
    → delivery_repository.py (track deliveries)
```

## Key Files

### Entry Points
- `backend/app/main.py` - FastAPI application
- `backend/scripts/run_bot.py` - Telegram bot
- `backend/scripts/trigger_posts_collection.py` - Manual collection
- `backend/scripts/run_personalized_summarization.py` - Manual summarization

### Configuration
- `backend/.env` - Environment variables
- `backend/app/infrastructure/config/settings.py` - Settings class
- `docker-compose.yml` - Development services

### Database
- `backend/app/infrastructure/database/models.py` - ORM models
- `backend/alembic/versions/` - Migration files

### Core Business Logic
- `backend/app/application/use_cases/` - All use cases
- `backend/app/domain/entities.py` - Business entities

## Naming Conventions

### Files
- Snake_case for all Python files: `content_extractor.py`
- Prefix repositories with entity name: `post_repository.py`
- Suffix use cases with action: `delivery_pipeline.py`

### Classes
- PascalCase for classes: `ContentExtractor`, `PostRepository`
- Suffix repositories with `Repository`: `PostRepository`
- Suffix services with `Service` or `Client`: `OpenAISummarizationService`, `HNClient`

### Functions
- Snake_case for functions: `fetch_top_posts()`, `extract_content()`
- Use verb prefixes: `get_`, `create_`, `update_`, `delete_`, `fetch_`

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Test domain entities in isolation
- Mock all external dependencies
- Fast, no I/O

### Integration Tests (`tests/integration/`)
- Test repository implementations with test database
- Test API endpoints
- Test use cases with real services

### Test Files
- Mirror source structure: `tests/unit/domain/test_entities.py`
- Prefix with `test_`: `test_post_repository.py`
- Use fixtures in `conftest.py`

## Development Workflow

1. **Add Feature**: Start in domain layer (entities)
2. **Define Contract**: Add interface in application layer
3. **Implement**: Add implementation in infrastructure
4. **Expose**: Add route/handler in presentation
5. **Test**: Write unit and integration tests
6. **Migrate**: Create database migration if needed
7. **Document**: Update relevant docs

## Further Reading

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
