# Agents & Services

This document describes the AI agents and services used in HN Pal. The project leverages OpenAI Agents SDK and various specialized services to automate content collection, extraction, summarization, and delivery.

## Vision

HN Pal is built around an **agent-first architecture** where AI agents handle different aspects of the user experience:

1. **Content Processing Agents** (Current - MVP)
   - Summarization Agent: Generate article summaries
   - Synthesis Agent: Identify themes across multiple articles

2. **Conversational Agents** (Phase 5 - Planned)
   - Discussion Agent: Facilitate deep conversations about articles
   - Memory Agent: Extract and surface user knowledge

3. **Personalization Agents** (Phase 6 - Planned)
   - Memory Extraction Agent: Build user profiles from interactions
   - Interest Tracking Agent: Recommend relevant content

See [Product Spec v2](docs/spec.md) and [Activity Documents](docs/activities/README.md) for implementation roadmap.

## Table of Contents

- [Current AI Agents (MVP)](#current-ai-agents-mvp)
  - [Content Summarizer Agent](#content-summarizer-agent)
  - [Summary Reducer Agent](#summary-reducer-agent)
  - [Content Synthesizer Agent](#content-synthesizer-agent)
  - [Topic-Focused Synthesizer Agent](#topic-focused-synthesizer-agent)
- [Planned AI Agents](#planned-ai-agents)
  - [Discussion Agent](#discussion-agent)
  - [Memory Extraction Agent](#memory-extraction-agent)
- [Services](#services)
  - [Content Extraction](#content-extraction)
  - [Summarization](#summarization)
  - [Synthesis](#synthesis)
  - [Notification](#notification)
- [Use Cases](#use-cases)
- [Development Workflow](#development-workflow)

---

## Current AI Agents (MVP)

The project uses OpenAI's Agents SDK to implement intelligent agents for content processing and summarization. All agents are implemented using the `agents` package (OpenAI Agents Python SDK) with configurable model settings.

### Content Summarizer Agent

**File**: `backend/app/infrastructure/services/openai_summarization_service.py:62-68`

**Purpose**: Summarizes individual content chunks from HackerNews articles with web search capabilities.

**Configuration**:
- **Model**: `gpt-4o-mini` (configurable)
- **Max Tokens**: 2000
- **Temperature**: 0.3 (focused output)
- **Tools**: WebSearchTool - enables the agent to search the web for additional context
- **Prompt**: Loaded from `backend/app/infrastructure/services/prompts/summarizer.md`

**Capabilities**:
- Analyzes article content
- Searches the web for more information
- Provides opinions and insights on the article
- Handles content chunks up to 8000 characters

### Summary Reducer Agent

**File**: `backend/app/infrastructure/services/openai_summarization_service.py:70-76`

**Purpose**: Combines multiple chunk summaries into a comprehensive final summary using map-reduce pattern.

**Configuration**:
- **Model**: `gpt-4o-mini` (configurable)
- **Max Tokens**: 2000
- **Temperature**: 0.3 (focused output)
- **Prompt**: Loaded from `backend/app/infrastructure/services/prompts/reducer.md`

**Capabilities**:
- Synthesizes partial summaries
- Maintains coherence across chunks
- Creates comprehensive final summaries

### Content Synthesizer Agent

**File**: `backend/app/infrastructure/services/openai_synthesis_service.py:56-61`

**Purpose**: Generates synthesized summaries from multiple posts, identifying common themes and patterns.

**Configuration**:
- **Model**: `gpt-4o-mini` (configurable)
- **Max Tokens**: 1000
- **Temperature**: 0.5 (balanced creativity)
- **Prompt**: Loaded from `backend/app/infrastructure/services/prompts/synthesis.md`

**Capabilities**:
- Identifies common themes across articles
- Finds patterns and connections
- Creates high-level insights from multiple sources

### Topic-Focused Synthesizer Agent

**File**: `backend/app/infrastructure/services/openai_synthesis_service.py:64-69`

**Purpose**: Generates topic-specific synthesis from multiple posts, focusing on a particular theme.

**Configuration**:
- **Model**: `gpt-4o-mini` (configurable)
- **Max Tokens**: 1000
- **Temperature**: 0.5 (balanced creativity)
- **Prompt**: Loaded from `backend/app/infrastructure/services/prompts/synthesis_topic.md`

**Capabilities**:
- Focuses on specific topics or themes
- Extracts relevant information about the topic
- Creates targeted insights

---

## Planned AI Agents

These agents are planned for future phases and will enable the interactive Telegram bot experience.

### Discussion Agent

**Phase**: 5 (Discussion System)
**Status**: Documented (Ready for Implementation)
**Activity**: [5.0 - Discussion System](docs/activities/activity-5.0-discussion-system.md)

**Purpose**: Facilitate multi-turn conversations about HackerNews articles with full context awareness.

**Planned Configuration**:
- **Model**: `gpt-4o` or `claude-3-5-sonnet` (configurable)
- **Max Tokens**: 4000
- **Temperature**: 0.7 (conversational)
- **Tools**:
  - Memory Search: Query user's past discussions and preferences
  - Article Search: Find related articles from database
  - HN Comments: Fetch and analyze top comments from HN
- **Context Window**: Article markdown + user memory + conversation history

**Planned Capabilities**:
- Load full article markdown from storage (RocksDB/S3)
- Access user memory (interests, past discussions, opinions)
- Reference previous conversations on related topics
- Summarize HN comment discussions
- Make connections across articles user has read
- Auto-save discussion on switch or timeout (30 min)

**State Management**:
- Tracks active discussion per user in database
- Auto-switches when user taps "Discuss" on another post
- Persists conversation history to PostgreSQL
- Extracts insights on discussion end for memory system

### Memory Extraction Agent

**Phase**: 6 (Memory System)
**Status**: Documented (Ready for Implementation)
**Activity**: [6.0 - Memory System](docs/activities/activity-6.0-memory-system.md)

**Purpose**: Extract and structure insights from user interactions to build a persistent user profile.

**Planned Configuration**:
- **Model**: `gpt-4o-mini` (cost-effective for batch extraction)
- **Max Tokens**: 2000
- **Temperature**: 0.3 (focused extraction)
- **Output Format**: Pydantic-structured memory entries
- **Extraction Triggers**:
  - Daily batch job (23:00 UTC) analyzing reactions, saves, discussions
  - Post-discussion extraction when conversation ends
  - Explicit capture when user says "remember this"

**Memory Categories** (Structured Output):
```python
class MemoryEntry(BaseModel):
    category: Literal["preference", "work_context", "personal", "reading_history"]
    content: str
    confidence: float  # 0.0-1.0
    source: str  # "discussion:post_id" | "reaction:post_id" | "explicit"
    timestamp: datetime
```

**Planned Capabilities**:
- Analyze user reactions (👍/👎) to infer topic preferences
- Extract opinions and insights from discussion transcripts
- Detect work context from conversation (role, tech stack, projects)
- Track reading patterns (topics, domains, authors)
- Identify learning goals from questions asked
- Merge duplicate memories and update existing ones
- Write to two-tier storage: `MEMORY.md` (durable) + `memory/YYYY-MM-DD.md` (daily notes)

**Integration Points**:
- Discussion Agent receives memory context in system prompt
- Summarization Agent can personalize summaries based on interests
- Digest ranking uses memory to prioritize relevant posts

---

## Services

### Content Extraction

#### EnhancedContentExtractor

**File**: `backend/app/infrastructure/services/enhanced_content_extractor.py:16`

**Purpose**: Robust web content extraction with retry logic, rate limiting, and robots.txt compliance.

**Features**:
- **User Agent Rotation**: 11+ different browser user agents to avoid blocking
- **Retry Logic**: Up to 3 retry attempts with exponential backoff
- **Rate Limiting**: Random delays (1-3 seconds) between requests
- **Robots.txt Compliance**: Respects website crawling policies
- **Error Handling**: Handles 403, 404, 429 (rate limit) status codes
- **Content Extraction**: Uses Trafilatura library for high-quality text extraction

**Configuration**:
```python
EnhancedContentExtractor(
    timeout=30,           # Request timeout in seconds
    max_retries=3,        # Maximum retry attempts
    min_delay=1.0,        # Minimum delay between requests
    max_delay=3.0,        # Maximum delay between requests
    respect_robots_txt=True  # Check robots.txt before crawling
)
```

### Summarization

#### OpenAISummarizationService

**File**: `backend/app/infrastructure/services/openai_summarization_service.py:21`

**Purpose**: AI-powered summarization with map-reduce strategy for long content.

**Strategy**:
1. **Map Phase**: Split long content into chunks (8000 chars each)
2. **Summarize**: Each chunk is summarized independently with web search
3. **Reduce Phase**: Chunk summaries are combined into final summary

**Features**:
- Handles content up to 128,000 characters
- Concurrent batch processing
- Web search integration for context
- Graceful error handling

**Interface**: Implements `SummarizationService` from `backend/app/application/interfaces.py:447-478`

**Methods**:
- `summarize(content: str) -> str`: Summarize single content
- `summarize_batch(contents: List[str]) -> List[str]`: Batch processing

### Synthesis

#### OpenAISynthesisService

**File**: `backend/app/infrastructure/services/openai_synthesis_service.py:20`

**Purpose**: Multi-post synthesis to identify themes, patterns, and connections.

**Features**:
- Cross-article analysis
- Theme identification
- Topic-focused synthesis
- Summary-based synthesis

**Interface**: Implements `SynthesisSummarizationService` from `backend/app/application/interfaces.py:481-528`

**Methods**:
- `synthesize(posts: List[Post]) -> str`: General synthesis
- `synthesize_by_topic(posts: List[Post], topic: str) -> str`: Topic-focused
- `synthesize_from_summaries(summaries: List[dict]) -> str`: From pre-generated summaries

### Notification

#### TelegramNotifier

**File**: `backend/app/infrastructure/services/telegram_notifier.py:12`

**Purpose**: Deliver digest summaries to Telegram channels.

**Features**:
- Markdown formatting support
- Message batching for large digests
- Statistics reporting
- Error handling and retry logic

**Methods**:
- `send_digest_summary(summaries, markdown_file)`: Send overview with top 5 articles
- `send_summary_details(summaries, limit=10)`: Send detailed summaries in batches

**Message Format**:
```
📰 HackerNews Digest Summary

📊 Statistics:
• Total: 30
• Successful: 28 ✓
• Failed: 2 ✗

✨ Top Articles:
1. Article title... (120pts)
...
```

---

## Use Cases

Use cases orchestrate the interaction between agents and services to accomplish business goals.

### CrawlContentUseCase

**File**: `backend/app/application/use_cases/crawl_content.py:17`

**Purpose**: Orchestrate content extraction from HackerNews posts.

**Dependencies**:
- `EnhancedContentExtractor`: For content extraction
- `CrawlStatusTracker`: For tracking crawl status

**Features**:
- Concurrent crawling with semaphore (max 3 concurrent requests)
- Skip already crawled posts
- Save both HTML and text content
- Track success/failure statistics
- Handle text-only posts (no URL)

**Statistics Tracking**:
- Total posts processed
- Successful/failed extractions
- Posts with/without content
- Skipped posts

### SummarizePostsUseCase

**File**: `backend/app/application/use_cases/summarization.py:19`

**Purpose**: Batch summarization of post content.

**Dependencies**:
- `PostRepository`: For post persistence
- `SummarizationService`: For AI summarization

**Features**:
- Batch processing
- Skip posts without content
- Skip already summarized posts
- Save summaries back to posts

**Workflow**:
1. Fetch posts by date or use provided list
2. Filter posts needing summarization
3. Extract content from posts
4. Generate summaries in batch
5. Update and save posts with summaries

### SummarizeSinglePostUseCase

**File**: `backend/app/application/use_cases/summarization.py:104`

**Purpose**: Summarize a single post by ID.

**Dependencies**:
- `PostRepository`: For post persistence
- `SummarizationService`: For AI summarization

**Features**:
- Single post processing
- Validation (requires content)
- Skip if already summarized
- Error handling

---

## Development Workflow

### Project Structure Guide

HN Pal follows **Clean Architecture** with clear separation between layers:

```
hackernews_digest/
├── backend/
│   ├── app/
│   │   ├── domain/              # Business entities (Post, User, Digest)
│   │   │   └── entities.py      # Core domain models
│   │   ├── application/         # Use cases and interfaces
│   │   │   ├── interfaces.py    # Port definitions (repositories, services)
│   │   │   └── use_cases/       # Business logic orchestration
│   │   │       ├── crawl_content.py
│   │   │       ├── summarization.py
│   │   │       └── collection.py
│   │   ├── infrastructure/      # External adapters (implementations)
│   │   │   ├── repositories/    # Data persistence implementations
│   │   │   │   ├── jsonl_post_repo.py
│   │   │   │   └── jsonl_content_repo.py
│   │   │   ├── services/        # External service integrations
│   │   │   │   ├── openai_summarization_service.py
│   │   │   │   ├── openai_synthesis_service.py
│   │   │   │   ├── enhanced_content_extractor.py
│   │   │   │   ├── hn_client.py
│   │   │   │   └── telegram_notifier.py
│   │   │   ├── config/
│   │   │   │   └── settings.py  # Environment configuration
│   │   │   └── prompts/         # Agent prompt templates
│   │   │       ├── summarizer.md
│   │   │       ├── reducer.md
│   │   │       ├── synthesis.md
│   │   │       └── synthesis_topic.md
│   │   └── presentation/        # API layer (future FastAPI endpoints)
│   └── tests/                   # Test suites
├── data/                        # Data storage (local development)
│   ├── raw/                     # Raw HN posts (JSONL)
│   ├── content/                 # Extracted article content
│   │   ├── html/                # Raw HTML
│   │   ├── text/                # Extracted text (trafilatura)
│   │   └── markdown/            # Converted markdown (future)
│   ├── processed/               # Generated summaries
│   │   ├── summaries/           # Per-article summaries (JSONL)
│   │   └── synthesis/           # Cross-article synthesis (JSONL)
│   └── crawl_status.jsonl       # Crawl tracking
├── scripts/                     # CLI automation scripts
│   ├── fetch_hn_posts.py        # Collect posts from HN API
│   ├── crawl_content.py         # Extract article content
│   ├── run_summarization.py     # Generate summaries
│   ├── push_to_telegram.py      # Deliver to Telegram
│   └── run_full_flow.py         # End-to-end pipeline
├── docs/                        # Documentation
│   ├── spec.md                  # Product spec v2 (Telegram bot vision)
│   ├── activities/              # Implementation activity docs
│   └── design/                  # Architecture decision records
├── AGENTS.md                    # This file - agent documentation
├── README.md                    # Project overview and setup
├── pyproject.toml               # Python dependencies (uv)
└── uv.lock                      # Lockfile (uv package manager)
```

**Key Principles**:
1. **Domain Independence**: Core entities have no external dependencies
2. **Dependency Inversion**: Use cases depend on interfaces, not implementations
3. **Infrastructure Isolation**: External services are swappable adapters
4. **Prompt Externalization**: Agent prompts in markdown files, not hardcoded

### Operation Guide

#### Daily Development Workflow

**IMPORTANT: Always use the project's virtual environment!**

The project uses `.venv` in the project root. Always run Python scripts with `.venv/bin/python` from the project root:

```bash
# ❌ WRONG - Don't do this
cd backend
python scripts/something.py

# ✅ CORRECT - Run from project root with venv
cd /path/to/hackernews_digest
.venv/bin/python backend/scripts/something.py
```

**Standard Workflow:**

```bash
# 1. Navigate to project root
cd /path/to/hackernews_digest

# 2. Sync dependencies (if pyproject.toml changed)
uv sync

# 3. Run individual pipeline steps (from project root!)
.venv/bin/python scripts/fetch_hn_posts.py          # Collect posts
.venv/bin/python scripts/crawl_content.py           # Extract content
.venv/bin/python scripts/run_summarization.py       # Generate summaries
.venv/bin/python scripts/push_to_telegram.py        # Deliver to Telegram

# 4. Run backend scripts (also from project root!)
.venv/bin/python backend/scripts/crawl_and_store.py --limit 50

# 5. Run tests
.venv/bin/python -m pytest backend/tests/ -v

# 6. Format and lint code (future)
make format
make lint
```

**Why this matters:**
- ✅ Ensures correct Python interpreter with all dependencies
- ✅ Maintains consistent working directory for relative paths
- ✅ Avoids "module not found" errors
- ✅ RocksDB paths resolve correctly to `data/content.rocksdb`

**Common Mistakes to Avoid:**
```bash
# ❌ Using system Python
python backend/scripts/crawl_and_store.py

# ❌ Running from wrong directory
cd backend && python scripts/crawl_and_store.py

# ❌ Using relative venv path from wrong location
cd backend && ../.venv/bin/python scripts/something.py
```

#### Pipeline Steps Explained

**Step 1: Collect Posts** (`fetch_hn_posts.py`)
- Polls HackerNews API (`/v0/topstories` or Algolia)
- Filters for score > 100, excludes Ask/Show HN
- Saves to `data/raw/YYYY-MM-DD-posts.jsonl`
- Deduplicates by HN ID

**Step 2: Crawl Content** (`crawl_content.py`)
- Reads posts from JSONL files
- Fetches article URLs with robust HTTP client
- Extracts text with trafilatura
- Saves HTML to `data/content/html/{hn_id}.html`
- Saves text to `data/content/text/{hn_id}.txt`
- Tracks status in `data/crawl_status.jsonl`

**Step 3: Summarize** (`run_summarization.py`)
- Reads text content from `data/content/text/`
- Generates summaries via OpenAI Agents SDK
- Uses map-reduce for long articles (>8000 chars)
- Saves to `data/processed/summaries/YYYY-MM-DD-summaries.jsonl`

**Step 4: Synthesize** (future - optional)
- Reads summaries from `data/processed/summaries/`
- Identifies common themes across articles
- Generates cross-article insights
- Saves to `data/processed/synthesis/YYYY-MM-DD-synthesis.jsonl`

**Step 5: Deliver** (`push_to_telegram.py`)
- Reads summaries from JSONL files
- Formats messages with markdown
- Sends to Telegram channel via Bot API
- Tracks delivery status

### Prerequisites

#### Required Tools

```bash
# Python 3.11+ (check version)
python --version  # Should be >= 3.11

# uv package manager (required)
# Install uv: https://github.com/astral-sh/uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Git (for version control)
git --version
```

#### Required API Keys

Create `backend/.env` file:

```bash
# OpenAI API (for summarization agents)
OPENAI_API_KEY=sk-proj-...

# Telegram Bot (for delivery)
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_CHANNEL_ID=@your_channel_username

# Optional: Claude API (future alternative)
# ANTHROPIC_API_KEY=sk-ant-...

# Optional: Langfuse (observability - future)
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_HOST=https://cloud.langfuse.com
```

#### Infrastructure Requirements

**Current (MVP - File-based)**:
- Disk space: ~1 GB for 30 days of data
- No database required (JSONL files)
- No external storage (local filesystem)

**Future (Production - Phase 3+)**:
- PostgreSQL (Supabase or local)
- S3 or compatible object storage (for HTML/markdown)
- Redis (for FSM state in Telegram bot)
- Vercel account (for bot hosting + cron jobs)

### Testing & Automated Checks

#### Test Structure (Planned)

```
backend/tests/
├── unit/                        # Unit tests (fast, isolated)
│   ├── domain/                  # Entity tests
│   ├── use_cases/               # Business logic tests
│   └── services/                # Service tests (mocked)
├── integration/                 # Integration tests (slower, real dependencies)
│   ├── repositories/            # JSONL file operations
│   ├── api_clients/             # HN API, OpenAI API
│   └── agents/                  # Agent behavior tests
└── e2e/                         # End-to-end tests (full pipeline)
    └── test_full_pipeline.py
```

#### Quality Gates (Future Makefile Targets)

```bash
# Format code with ruff
make format
# Expected: ruff format backend/ scripts/

# Lint code
make lint
# Expected: ruff check backend/ scripts/

# Type checking with mypy
make mypy
# Expected: mypy backend/ scripts/

# Run all tests
make tests
# Expected: pytest backend/tests/

# Run with coverage
make coverage
# Expected: pytest --cov=backend --cov-report=html

# Full pre-commit check
make check
# Expected: make format && make lint && make mypy && make tests
```

#### CI/CD Pipeline (Future GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: make format --check  # Fail if not formatted
      - run: make lint
      - run: make mypy
      - run: make tests
```

### Pull Request & Commit Guidelines

#### PR Checklist

Before submitting a pull request:

✅ **Checks pass** (make format, make lint, make mypy, make tests)
✅ **Tests cover new behavior and edge cases**
✅ **Code is readable, maintainable, and consistent with existing style**
✅ **Public APIs and user-facing behavior changes are documented**
✅ **Examples are updated if behavior changes**
✅ **History is clean with a clear PR description**

#### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature (e.g., `feat(agents): add discussion agent`)
- `fix`: Bug fix (e.g., `fix(crawler): handle timeout errors`)
- `docs`: Documentation only (e.g., `docs: update AGENTS.md`)
- `refactor`: Code refactoring (e.g., `refactor(repos): extract JSONL base class`)
- `test`: Adding tests (e.g., `test(summarization): add edge cases`)
- `chore`: Maintenance (e.g., `chore: update dependencies`)

**Examples**:

```
feat(agents): implement memory extraction agent

- Add MemoryExtractionAgent with structured output
- Support daily batch extraction from user interactions
- Integrate Pydantic models for memory categories
- Add BM25 search for memory retrieval

Closes #42
```

```
fix(crawler): handle rate limiting with exponential backoff

The enhanced content extractor now detects 429 status codes
and implements exponential backoff (1s, 2s, 4s, 8s) before
retrying. Max retries set to 3.

Fixes #38
```

#### PR Description Template

```markdown
## Summary
Brief description of changes (1-2 sentences)

## Motivation
Why is this change needed? What problem does it solve?

## Changes
- Bullet list of specific changes
- Include new files, modified behavior, etc.

## Testing
How was this tested? Include:
- Unit tests added/modified
- Manual testing steps
- Edge cases covered

## Screenshots (if applicable)
Before/after screenshots for UI changes

## Checklist
- [ ] Tests pass (`make tests`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make mypy`)
- [ ] Documentation updated
- [ ] Examples updated (if applicable)
```

### Review Process & What Reviewers Look For

#### Reviewer Checklist

**Code Quality**:
- [ ] Follows clean architecture principles (domain/application/infrastructure separation)
- [ ] No circular dependencies between layers
- [ ] Proper error handling with meaningful messages
- [ ] No hardcoded values (use config/settings)
- [ ] Follows existing naming conventions
- [ ] Functions are small and focused (single responsibility)

**Testing**:
- [ ] New code has corresponding tests
- [ ] Tests cover happy path and edge cases
- [ ] Test names clearly describe what they test
- [ ] No flaky tests (deterministic, no time-based failures)
- [ ] Integration tests use fixtures/mocks appropriately

**Documentation**:
- [ ] Docstrings for public functions/classes (Google style)
- [ ] README updated if user-facing behavior changes
- [ ] Activity documents updated if implementation deviates from plan
- [ ] Agent prompts documented in AGENTS.md if new agents added

**Agent-Specific Review**:
- [ ] Agent prompts externalized to markdown files (not hardcoded)
- [ ] Agent configuration is parameterized (model, temperature, tokens)
- [ ] Token usage is tracked (for cost monitoring)
- [ ] Structured outputs use Pydantic when appropriate
- [ ] Error handling for API failures (retries, fallbacks)

**Performance**:
- [ ] No unnecessary API calls (batch where possible)
- [ ] File I/O is async where appropriate
- [ ] Database queries are efficient (no N+1)
- [ ] Memory usage is reasonable (no loading full datasets)

**Security**:
- [ ] No API keys in code (use environment variables)
- [ ] User input is validated (if applicable)
- [ ] No SQL injection risks (use parameterized queries)
- [ ] Secrets are in `.gitignore`

#### Review Workflow

1. **Self-Review**: Author reviews their own PR before requesting review
2. **Automated Checks**: CI runs tests, linting, type checking
3. **Code Review**: Reviewer provides feedback on code quality, tests, docs
4. **Revisions**: Author addresses feedback, pushes updates
5. **Approval**: Reviewer approves when all checks pass and feedback is addressed
6. **Merge**: Squash and merge to main with clean commit message

#### Feedback Guidelines

**For Authors**:
- Respond to all comments (even if just "done")
- Ask clarifying questions if feedback is unclear
- Be open to suggestions and alternative approaches
- Update PR description if scope changes

**For Reviewers**:
- Be specific and constructive ("Consider X because Y" vs "This is bad")
- Distinguish between blocking issues and suggestions
- Praise good code ("Nice use of X here!")
- Link to relevant docs/examples when suggesting changes

---

## Tech Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Primary development language |
| **Package Manager** | uv | latest | Fast dependency management |
| **Database** | PostgreSQL | 14+ | Persistent data storage (Phase 3+) |
| **Cache/FSM** | Redis | 7+ | Telegram bot state, caching (Phase 3+) |
| **ORM** | SQLAlchemy | 2.x | Database models and queries |
| **Migrations** | Alembic | latest | Database schema versioning |
| **Bot Framework** | aiogram | 3.x | Telegram bot interactions (Phase 3+) |
| **LLM Framework** | OpenAI Agents SDK | latest | Agent orchestration and tool calling |
| **HTTP Client** | httpx | latest | Async HTTP requests |
| **Content Extraction** | trafilatura | 2.x | Article text extraction |
| **Validation** | Pydantic | 2.x | Data validation and settings |
| **Testing** | pytest | latest | Test framework |
| **Linting/Formatting** | ruff | latest | Code quality tools |

### Optional/Future Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Observability** | Langfuse | LLM call tracing and analytics |
| **Alternative LLM** | Claude API (Anthropic) | Alternative to OpenAI |
| **Hosting** | Vercel | Bot hosting + cron jobs (serverless) |
| **Database (Managed)** | Supabase | Managed PostgreSQL with APIs |
| **Object Storage** | S3 Compatible | HTML/Markdown files (Phase 3+) |

---

## Implementation Guidelines

### Database with SQLAlchemy & Alembic

**Key Principles**:
- Use SQLAlchemy 2.x async ORM for database operations
- Manage schema changes with Alembic migrations
- Read database URL from environment variables via Pydantic Settings
- Version all migrations in Git

**Essential Files**:
```
backend/app/infrastructure/database/
├── base.py          # Base class, engine setup
├── models.py        # SQLAlchemy models (User, Post, Conversation, etc.)
└── session.py       # Session management

backend/alembic/
├── env.py           # Migration environment (reads from settings)
├── versions/        # Migration files (versioned in Git)
└── script.py.mako   # Migration template
```

**Migration Workflow**:
```bash
# Create migration from model changes
alembic revision --autogenerate -m "add users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Configuration with Pydantic Settings

**Pattern**: All configuration from environment variables
```python
# backend/app/infrastructure/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="backend/.env")

    # Database
    database_url: str = "postgresql+asyncpg://localhost/hn_pal"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # Telegram
    telegram_bot_token: str
    telegram_channel_id: Optional[str] = None

settings = Settings()
```

### OpenAI Agents SDK

**Key Patterns**:
- Load agent prompts from markdown files (not hardcoded)
- Configure models via settings (model, temperature, max_tokens)
- Use Pydantic for structured outputs (type-safe responses)
- Track token usage for cost monitoring

**Agent Structure**:
```
backend/app/infrastructure/services/
├── openai_summarization_service.py  # Summarization agent
├── openai_synthesis_service.py      # Synthesis agent
└── prompts/
    ├── summarizer.md                # Summarization prompt
    ├── reducer.md                   # Reduction prompt
    └── synthesis.md                 # Synthesis prompt
```

### Redis Integration

**Usage**:
- **FSM Storage**: aiogram bot state (IDLE, DISCUSSION, ONBOARDING)
- **Caching**: Post metadata, user preferences
- **Session Management**: Active discussions, timeouts

**Configuration**: Read from `settings.redis_url` environment variable

---

## Deployment

### Local Development with Docker Compose

**Infrastructure Services**: Use Docker Compose for PostgreSQL and Redis

**File**: `docker-compose.yml` (project root)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: hn_pal_postgres
    environment:
      POSTGRES_USER: hn_pal
      POSTGRES_PASSWORD: hn_pal_dev
      POSTGRES_DB: hn_pal
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # Optional: init scripts
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hn_pal"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hn_pal_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Optional: Redis Commander (GUI)
  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: hn_pal_redis_commander
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis

  # Optional: pgAdmin (PostgreSQL GUI)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: hn_pal_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@hnpal.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    depends_on:
      - postgres

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  pgadmin_data:
    driver: local
```

### Local Development Workflow

```bash
# 1. Start infrastructure services
docker-compose up -d postgres redis

# 2. Verify services are healthy
docker-compose ps

# 3. Configure environment variables
cat > backend/.env << EOF
DATABASE_URL=postgresql+asyncpg://hn_pal:hn_pal_dev@localhost/hn_pal
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-proj-xxxxx
TELEGRAM_BOT_TOKEN=123456789:ABC...
EOF

# 4. Run database migrations
cd backend
alembic upgrade head

# 5. Start development
source ../.venv/bin/activate
python scripts/fetch_hn_posts.py

# 6. Stop services when done
docker-compose down  # Preserves volumes
docker-compose down -v  # Removes volumes (fresh start)
```

### Production Deployment (Future - Phase 3+)

**Infrastructure**:
- **Database**: Managed PostgreSQL (Supabase, AWS RDS, or DigitalOcean)
- **Redis**: Managed Redis (Upstash, AWS ElastiCache, or Redis Cloud)
- **Bot Hosting**: Vercel serverless functions (webhook mode)
- **Cron Jobs**: Vercel Cron for scheduled pipelines
- **Object Storage**: S3 or compatible service (Cloudflare R2, Backblaze B2)

**Environment Variables** (Production):
```bash
# Database (managed service)
DATABASE_URL=postgresql+asyncpg://user:pass@db.host.com/hn_pal

# Redis (managed service)
REDIS_URL=redis://user:pass@redis.host.com:6379

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# APIs
OPENAI_API_KEY=sk-proj-xxxxx
TELEGRAM_BOT_TOKEN=123456789:ABC...

# Optional: Observability
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
```

### Database Management

**Backup Strategy**:
```bash
# Local backup
docker exec hn_pal_postgres pg_dump -U hn_pal hn_pal > backup.sql

# Restore from backup
docker exec -i hn_pal_postgres psql -U hn_pal hn_pal < backup.sql
```

**Accessing Database**:
```bash
# Via psql
docker exec -it hn_pal_postgres psql -U hn_pal -d hn_pal

# Via pgAdmin (GUI)
# Open http://localhost:5050
# Login: admin@hnpal.local / admin
# Add server: postgres:5432
```

**Accessing Redis**:
```bash
# Via redis-cli
docker exec -it hn_pal_redis redis-cli

# Via Redis Commander (GUI)
# Open http://localhost:8081
```

---

## Architecture Patterns

### Clean Architecture

All services follow Clean Architecture principles:

1. **Domain Layer**: Entities (`Post`, `User`, `Digest`) with business logic
2. **Application Layer**: Interfaces defining contracts for services
3. **Infrastructure Layer**: Concrete implementations of services
4. **Presentation Layer**: API endpoints and schemas

### Dependency Inversion

High-level modules (use cases) depend on abstractions (interfaces), not concrete implementations:

```
Use Case → Interface ← Service Implementation
```

### Map-Reduce Pattern

Long content summarization uses map-reduce:

```
Content → Split → [Chunk1, Chunk2, ...]
                      ↓
                  Summarize each
                      ↓
                 [Summary1, Summary2, ...]
                      ↓
                  Reduce/Combine
                      ↓
                  Final Summary
```

### Repository Pattern

Data access through repository interfaces:

```
Use Case → Repository Interface ← JSONL Repository
                                ← Future: Database Repository
```

---

## Configuration

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Telegram Configuration
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHANNEL_ID=@your_channel

# Service Configuration
SUMMARIZATION_MODEL=gpt-4o-mini
SUMMARIZATION_MAX_TOKENS=2000
SUMMARIZATION_TEMPERATURE=0.3
```

### Service Initialization

```python
from backend.app.infrastructure.services import (
    OpenAISummarizationService,
    OpenAISynthesisService,
    EnhancedContentExtractor,
    TelegramNotifier
)

# Summarization
summarization_service = OpenAISummarizationService(
    model="gpt-4o-mini",
    max_tokens=2000,
    temperature=0.3,
    chunk_size=8000
)

# Synthesis
synthesis_service = OpenAISynthesisService(
    model="gpt-4o-mini",
    max_tokens=1000,
    temperature=0.5
)

# Content Extraction
content_extractor = EnhancedContentExtractor(
    timeout=30,
    max_retries=3,
    respect_robots_txt=True
)

# Telegram Notifications
telegram_notifier = TelegramNotifier(
    bot_token=settings.telegram_bot_token,
    channel_id=settings.telegram_channel_id
)
```

---

## Agent Prompts

Agent behavior is defined by markdown prompts in `backend/app/infrastructure/services/prompts/`:

- `summarizer.md`: Instructions for the Content Summarizer Agent
- `reducer.md`: Instructions for the Summary Reducer Agent
- `synthesis.md`: Instructions for the Content Synthesizer Agent
- `synthesis_topic.md`: Instructions for the Topic-Focused Synthesizer Agent

These prompts define the agent's personality, capabilities, and output format.

---

## Performance Considerations

### Rate Limiting

- **Content Extraction**: 1-3 second delays between requests
- **Concurrent Crawling**: Max 3 concurrent requests (configurable)
- **Telegram API**: Batching to respect message limits

### Token Optimization

- **Chunk Size**: 8000 characters to stay within context limits
- **Max Length**: 128,000 characters total per article
- **Batch Processing**: Process multiple summaries concurrently

### Caching

- **Robots.txt**: Cached per domain to reduce requests
- **Content**: HTML and text saved locally to avoid re-crawling
- **Summaries**: Saved with posts to avoid regeneration

---

## Future Enhancements

Potential improvements for the agent system:

1. **Adaptive Chunking**: Dynamic chunk sizes based on content complexity
2. **Multi-Language Support**: Detect and handle non-English content
3. **Sentiment Analysis**: Classify article sentiment
4. **Topic Classification**: Automatic categorization of articles
5. **Quality Scoring**: Rate summary quality and retry if needed
6. **Streaming Summaries**: Stream partial results to users
7. **Custom Agent Training**: Fine-tune models for HN-specific content
8. **Citation Tracking**: Link summary statements to source content
