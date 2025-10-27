# Source Tree - Project Structure

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1)
**Last Updated:** 2025-10-21

---

## Project Root Structure

```
hackernews_digest/
├── .bmad-core/              # BMAD agent configuration (do not modify)
├── .ai/                     # AI debug logs
├── backend/                 # Python FastAPI backend
│   ├── app/                 # Application code
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── config.py        # Configuration & settings
│   │   ├── api/             # API routes
│   │   │   ├── __init__.py
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   └── digests.py   # Digest endpoints
│   │   ├── models/          # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── user.py      # User models
│   │   │   └── digest.py    # Digest models
│   │   ├── services/        # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py      # Auth logic (JWT, password hashing)
│   │   │   ├── hn_client.py # HN API client
│   │   │   └── storage.py   # JSONL file operations
│   │   ├── jobs/            # Background jobs
│   │   │   ├── __init__.py
│   │   │   └── collector.py # HN data collection job
│   │   └── utils/           # Utilities
│   │       ├── __init__.py
│   │       ├── jsonl.py     # JSONL read/write helpers
│   │       └── cache.py     # Redis cache helpers
│   ├── tests/               # Test files
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_digests.py
│   │   └── test_collector.py
│   ├── pyproject.toml       # Poetry dependencies
│   ├── poetry.lock          # Locked dependencies
│   └── .env.example         # Environment variable template
│
├── frontend/                # Next.js frontend (Sprint 2+)
│   ├── src/
│   │   ├── app/             # Next.js 14 app directory
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities
│   ├── public/              # Static assets
│   ├── package.json
│   └── tsconfig.json
│
├── data/                    # Data storage (JSONL files)
│   ├── raw/                 # Raw HN data
│   │   ├── YYYY-MM-DD-posts.jsonl
│   │   ├── YYYY-MM-DD-content.jsonl.gz
│   │   └── YYYY-MM-DD-comments.jsonl
│   ├── processed/           # Processed data (Sprint 2+)
│   │   ├── YYYY-MM-DD-topics.jsonl
│   │   ├── YYYY-MM-DD-summaries.jsonl
│   │   └── YYYY-MM-DD-digest.jsonl
│   └── users/               # User data
│       ├── user-profiles.jsonl
│       └── user-votes.jsonl
│
├── docs/                    # Documentation
│   ├── architecture/        # Architecture docs (this folder)
│   ├── epics/               # Epic files
│   ├── stories/             # Story files for development
│   ├── prd.md               # Product Requirements Document
│   └── sprint-plan.md       # Sprint plan
│
├── scripts/                 # Utility scripts
│   ├── setup.sh             # Initial setup script
│   └── run_collector.py     # Run data collection manually
│
├── docker-compose.yml       # Local development environment
├── Dockerfile               # Backend Docker image
├── .env                     # Environment variables (gitignored)
├── .gitignore
└── README.md
```

---

## Backend Directory Details

### `/backend/app/main.py`
**Purpose:** FastAPI application entry point

**Contents:**
- FastAPI app initialization
- CORS configuration
- Router registration
- Startup/shutdown events (Redis connection, job scheduler)

### `/backend/app/config.py`
**Purpose:** Configuration and settings

**Contents:**
- Pydantic Settings class
- Environment variable loading
- Constants (JWT settings, file paths, etc.)

### `/backend/app/api/`
**Purpose:** API route handlers

**Files:**
- `auth.py` - `/api/auth/*` endpoints (register, login, me)
- `digests.py` - `/api/digests/*` endpoints (list, get by date, get post)

### `/backend/app/models/`
**Purpose:** Pydantic models for request/response validation

**Files:**
- `user.py` - User, UserCreate, UserInDB, Token models
- `digest.py` - Post, Digest, DigestList models

### `/backend/app/services/`
**Purpose:** Business logic and external integrations

**Files:**
- `auth.py` - JWT token creation/validation, password hashing
- `hn_client.py` - HN Algolia API client (fetch posts, comments)
- `storage.py` - JSONL file read/write, caching logic

### `/backend/app/jobs/`
**Purpose:** Background scheduled jobs

**Files:**
- `collector.py` - HN data collection job (runs daily via APScheduler)

### `/backend/app/utils/`
**Purpose:** Shared utilities

**Files:**
- `jsonl.py` - JSONL read/write helpers, gzip compression
- `cache.py` - Redis connection and caching helpers

---

## Data Directory Structure

### `/data/raw/`
**Purpose:** Raw data from HN API

**File Naming:**
- `YYYY-MM-DD-posts.jsonl` - Front page stories metadata
- `YYYY-MM-DD-content.jsonl.gz` - Article content (gzipped)
- `YYYY-MM-DD-comments.jsonl` - Comment threads

**Example:** `2025-10-21-posts.jsonl`

### `/data/processed/`
**Purpose:** Processed data (Sprint 2+)

**Files:**
- `YYYY-MM-DD-topics.jsonl` - Topic clusters
- `YYYY-MM-DD-summaries.jsonl` - Generated summaries
- `YYYY-MM-DD-digest.jsonl` - Assembled digest

### `/data/users/`
**Purpose:** User data

**Files:**
- `user-profiles.jsonl` - User accounts (append-only)
- `user-votes.jsonl` - Voting history (Sprint 3+)

---

## File Naming Conventions

### Python Files
- **Modules:** `snake_case.py` (e.g., `hn_client.py`)
- **Classes:** `PascalCase` (e.g., `HNClient`)
- **Functions:** `snake_case` (e.g., `fetch_front_page`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_POSTS_PER_DAY`)

### Data Files
- **Date-partitioned:** `YYYY-MM-DD-{type}.jsonl`
- **User data:** `{type}.jsonl` (append-only)
- **Compressed:** Add `.gz` extension

### Test Files
- **Pattern:** `test_{module_name}.py`
- **Example:** `test_hn_client.py`

---

## Import Patterns

### Absolute Imports (Preferred)
```python
from app.services.hn_client import HNClient
from app.models.digest import Post
from app.utils.jsonl import read_jsonl, write_jsonl
```

### Relative Imports (Within Same Package)
```python
# In app/api/digests.py
from ..services.storage import get_digest
from ..models.digest import Digest
```

---

## Configuration Files

### `/backend/pyproject.toml`
**Purpose:** Poetry project configuration

**Sections:**
- `[tool.poetry]` - Project metadata
- `[tool.poetry.dependencies]` - Production dependencies
- `[tool.poetry.dev-dependencies]` - Development dependencies
- `[tool.black]` - Black formatter config
- `[tool.ruff]` - Ruff linter config
- `[tool.pytest.ini_options]` - Pytest config

### `/backend/.env`
**Purpose:** Environment variables (gitignored)

**Example:**
```bash
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://localhost:6379
DATA_DIR=../data
```

### `/.env.example`
**Purpose:** Template for `.env` (committed to git)

---

## Docker Structure

### `/Dockerfile`
**Purpose:** Backend container image

**Stages:**
1. Base Python 3.11 image
2. Install Poetry and dependencies
3. Copy application code
4. Set up non-root user
5. Expose port 8000
6. Run uvicorn server

### `/docker-compose.yml`
**Purpose:** Local development environment

**Services:**
- `backend` - FastAPI app (port 8000)
- `redis` - Cache (port 6379)
- `frontend` - Next.js app (port 3000) - Sprint 2+

---

## Sprint 1 Files to Create

**Backend Application:**
```
backend/app/main.py
backend/app/config.py
backend/app/api/auth.py
backend/app/api/digests.py
backend/app/models/user.py
backend/app/models/digest.py
backend/app/services/auth.py
backend/app/services/hn_client.py
backend/app/services/storage.py
backend/app/jobs/collector.py
backend/app/utils/jsonl.py
backend/app/utils/cache.py
```

**Configuration:**
```
backend/pyproject.toml
backend/.env.example
docker-compose.yml
Dockerfile
```

**Tests:**
```
backend/tests/test_auth.py
backend/tests/test_digests.py
backend/tests/test_collector.py
```

**Data Directories:**
```
data/raw/ (empty, files created by collector)
data/users/ (empty, files created by API)
```

---

## Git Ignore Patterns

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/

# Poetry
poetry.lock (optional - commit for reproducibility)

# Data files
data/
!data/.gitkeep

# Environment
.env
.env.local

# Logs
*.log
.ai/debug-log.md

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Redis
dump.rdb
```

---

## Directory Creation Script

```bash
#!/bin/bash
# scripts/setup.sh

# Create backend structure
mkdir -p backend/app/{api,models,services,jobs,utils}
mkdir -p backend/tests

# Create data directories
mkdir -p data/{raw,processed,users}

# Create docs structure (already exists)
mkdir -p docs/{architecture,epics,stories}

# Create scripts directory
mkdir -p scripts

# Touch __init__.py files
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/jobs/__init__.py
touch backend/app/utils/__init__.py
touch backend/tests/__init__.py

echo "Project structure created!"
```

---

**Project Structure Owner:** Winston (Architect)
**Last Review:** 2025-10-21
