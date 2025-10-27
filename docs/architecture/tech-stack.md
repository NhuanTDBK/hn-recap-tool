# Tech Stack

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1 - MVP)
**Last Updated:** 2025-10-21

---

## Core Technologies

### Backend

**Language & Runtime:**
- **Python 3.11+** - Primary language
- **Reason:** Modern async support, type hints, excellent library ecosystem

**Web Framework:**
- **FastAPI 0.100+** - Async web framework
- **Reason:** High performance, auto-generated OpenAPI docs, native async support, type safety

**Task Scheduling:**
- **APScheduler 3.10+** - Background job scheduling
- **Reason:** Simple, Pythonic, supports cron-like scheduling

### Data Storage

**Primary Storage:**
- **JSONL Files** - Newline-delimited JSON
- **Location:** `data/` directory with date partitioning
- **Compression:** gzip for article content (`.jsonl.gz`)
- **Reason:** Simple, human-readable, no database overhead for MVP

**Cache:**
- **Redis 7.0+** - In-memory data store
- **Use Cases:** User sessions, latest digests, frequently accessed data
- **Reason:** Fast key-value access, supports TTL, simple to deploy

### External APIs

**HackerNews:**
- **HN Algolia API** - `http://hn.algolia.com/api/v1`
- **Rate Limit:** 10,000 requests/day
- **Endpoints:** `/search`, `/items/:id`

**Content Extraction:**
- **trafilatura 1.6+** - Article content extraction
- **Reason:** Best-in-class article extraction, handles paywalls/JS sites

**LLM Provider:**
- **Anthropic Claude API** or **OpenAI GPT-4 API**
- **Cost Budget:** ~$2-3/day for MVP (30 posts)

**Email Service:**
- **SendGrid** or **Postmark** - Email delivery
- **Reason:** High deliverability, simple API, free tier available

### Frontend

**Framework:**
- **Next.js 14+** - React framework
- **Reason:** SSR/SSG support, API routes, good DX

**Styling:**
- **Tailwind CSS 3.4+** - Utility-first CSS
- **Reason:** Fast development, mobile-first, small bundle

**State Management:**
- **React Context + Hooks** - Built-in state
- **SWR** - Data fetching and caching
- **Reason:** Simple, no additional dependencies for MVP

---

## Development Tools

### Package Management

**Backend:**
- **Poetry 1.7+** - Python dependency management
- **pyproject.toml** - Configuration file
- **Reason:** Modern Python packaging, lock files, virtual env management

**Frontend:**
- **npm** or **pnpm** - Node package manager
- **package.json** - Configuration file

### Code Quality

**Linting & Formatting:**
- **Black** - Code formatter (Python)
- **Ruff** - Fast Python linter
- **Reason:** Industry standard, fast, minimal config

**Type Checking:**
- **mypy** - Static type checker (optional for MVP)

### Testing

**Backend:**
- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **httpx** - HTTP client for API testing

**Frontend:**
- **Jest** - Testing framework
- **React Testing Library** - Component testing

### Version Control

**Repository:**
- **Git + GitHub**
- **Branching:** Simple feature branches for MVP

---

## Infrastructure & Deployment

### MVP Deployment

**Hosting:**
- **Docker Container** on any cloud VM
- **Options:** AWS EC2, DigitalOcean Droplet, Render, Railway
- **Reason:** Simple, portable, cost-effective

**Container:**
- **Docker** - Containerization
- **Docker Compose** - Local development + simple production

**Environment Management:**
- **.env files** - Configuration
- **python-dotenv** - Load env vars

### Monitoring (Minimal for MVP)

**Logging:**
- **Python logging** module to stdout
- **Docker logs** for collection

**Error Tracking:**
- **Manual log review** for MVP
- **Future:** Sentry or similar

---

## Library Dependencies (Sprint 1)

### Backend Core

```toml
# pyproject.toml (Poetry)
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.100.0"
uvicorn = {extras = ["standard"], version = "^0.23.0"}
python-dotenv = "^1.0.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"

# Authentication
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"

# HTTP Client
httpx = "^0.24.0"

# Data Processing
trafilatura = "^1.6.0"

# Task Scheduling
apscheduler = "^3.10.0"

# Caching
redis = "^5.0.0"

# Utilities
tiktoken = "^0.5.0"  # Token counting

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.7.0"
ruff = "^0.0.280"
```

### Frontend Core

```json
// package.json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "swr": "^2.2.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "typescript": "^5.0.0"
  }
}
```

---

## API Keys & Configuration

**Required Environment Variables (Sprint 1):**

```bash
# Backend (.env)
SECRET_KEY=<random-secret-for-jwt>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# HN API (no key required - public)

# Redis
REDIS_URL=redis://localhost:6379

# Email (for Sprint 2)
# SENDGRID_API_KEY=<key>
# FROM_EMAIL=noreply@yourapp.com

# LLM API (for Sprint 2)
# ANTHROPIC_API_KEY=<key>
# or
# OPENAI_API_KEY=<key>
```

---

## File Size & Performance Targets

**Data Storage Estimates:**
- Raw posts: ~50 KB/day (30 posts × ~2 KB)
- Compressed content: ~200 KB/day (30 posts × ~10 KB compressed)
- Comments: ~100 KB/day
- **Total:** ~350 KB/day = ~130 MB/year

**API Performance:**
- Endpoint response time: < 2 seconds
- Digest processing: < 30 minutes total
- Email delivery: < 5 seconds per user

**Redis Memory:**
- User sessions: ~1 KB/user
- Latest digest cache: ~500 KB
- **Total:** < 10 MB for 100 users

---

## Security Considerations

**Authentication:**
- JWT tokens with bcrypt password hashing
- HTTPS required in production
- No password reset (manual admin support for MVP)

**API Security:**
- CORS configured for frontend domain
- Rate limiting per user
- Input validation via Pydantic

**Data Privacy:**
- User data stored locally (JSONL files)
- No third-party analytics for MVP
- Comments paraphrased (no direct quotes)

---

## Sprint 1 Scope

**What We're Building:**
- Python FastAPI backend with JWT auth
- HN data collection job (posts, content, comments)
- JSONL file storage with gzip compression
- Basic API endpoints for data access
- Redis caching

**What We're NOT Building (Yet):**
- LLM integration (Sprint 2)
- Frontend UI (Sprint 2)
- Email delivery (Sprint 2)
- Personalization (Sprint 3)
- Comment insights (Sprint 4)

---

## Next Steps

After Sprint 1:
- Add LLM integration (Sprint 2)
- Build Next.js frontend (Sprint 2)
- Add email delivery (Sprint 2)
- Implement personalization (Sprint 3)

**Tech Stack Owner:** Winston (Architect)
**Last Review:** 2025-10-21
