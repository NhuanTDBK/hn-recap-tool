# Architecture Documentation Index

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1 - MVP Foundation)
**Last Updated:** 2025-10-21

---

## Architecture Overview

This directory contains the technical architecture documentation for the HackerNews Knowledge Graph Builder project. These documents guide development and ensure consistent implementation across sprints.

---

## Sprint 1 Architecture Documents

### Core Documents (Required Reading)

1. **[Tech Stack](./tech-stack.md)**
   - Technologies: Python 3.11+, FastAPI, Redis, JSONL files
   - Dependencies and versions
   - Environment configuration
   - Sprint 1 scope

2. **[Source Tree](./source-tree.md)**
   - Project structure
   - Directory organization
   - File naming conventions
   - Import patterns

3. **[Data Models](./data-models.md)**
   - JSONL file schemas
   - Pydantic API models
   - Redis cache keys
   - Data validation rules

4. **[Coding Standards](./coding-standards.md)**
   - Python style guide (Black, Ruff)
   - Naming conventions
   - Type hints and docstrings
   - Error handling patterns

5. **[Testing Strategy](./testing-strategy.md)**
   - Test types (unit, integration, manual)
   - Pytest configuration
   - Test fixtures
   - Sprint 1 test plan

---

## Reading Order for Developers

**For Story 1.1 (HN Data Collection):**
1. Tech Stack → understand dependencies
2. Source Tree → know where to create files
3. Data Models → understand JSONL schemas
4. Coding Standards → follow conventions
5. Testing Strategy → write tests

**For Story 1.2 (FastAPI Auth):**
1. Tech Stack → FastAPI + JWT setup
2. Source Tree → API route organization
3. Data Models → User models
4. Coding Standards → async patterns
5. Testing Strategy → API testing

**For Story 1.3 (Data Access API):**
1. Data Models → Digest/Post models
2. Source Tree → API endpoints location
3. Coding Standards → error handling
4. Testing Strategy → integration tests

---

## Quick Reference

### Key File Locations

**Backend Code:**
- Main app: `backend/app/main.py`
- API routes: `backend/app/api/`
- Services: `backend/app/services/`
- Background jobs: `backend/app/jobs/`
- Tests: `backend/tests/`

**Data Storage:**
- Raw HN data: `data/raw/`
- User data: `data/users/`

**Configuration:**
- Dependencies: `backend/pyproject.toml`
- Environment: `backend/.env`

### Essential Commands

**Setup:**
```bash
cd backend
poetry install
```

**Run API:**
```bash
poetry run uvicorn app.main:app --reload
```

**Run Tests:**
```bash
poetry run pytest
```

**Run Collector:**
```bash
poetry run python scripts/run_collector.py
```

---

## Architecture Principles

### Simplicity First
- JSONL files over database for MVP
- No CI/CD initially
- Manual deployment acceptable
- Focus on core functionality

### API-First Design
- All functionality exposed via REST API
- Stateless API (Redis for cache only)
- Future-proof for MCP, mobile apps

### Separation of Concerns
- Data collection independent from processing
- Background jobs separate from API
- Easy to debug and reprocess data

### Developer Experience
- Fast local setup
- Clear structure
- Good documentation
- Simple testing

---

## Future Architecture (Post-Sprint 1)

**Sprint 2 Additions:**
- LLM integration (clustering, summarization)
- Frontend architecture (Next.js)
- Email delivery system

**Sprint 3 Additions:**
- Personalization system
- User preferences

**Sprint 4 Additions:**
- Comment processing
- Community insights

**Post-MVP:**
- Database migration (if needed)
- Multi-source support
- Advanced caching strategies

---

## Document Ownership

| Document | Owner | Last Updated |
|----------|-------|--------------|
| index.md | Winston (Architect) | 2025-10-21 |
| tech-stack.md | Winston (Architect) | 2025-10-21 |
| source-tree.md | Winston (Architect) | 2025-10-21 |
| data-models.md | Winston (Architect) | 2025-10-21 |
| coding-standards.md | Winston (Architect) | 2025-10-21 |
| testing-strategy.md | Winston (Architect) | 2025-10-21 |

---

## Questions or Updates?

**For architecture questions:**
- Check existing docs first
- Ask Winston (Architect) if clarification needed

**For architecture updates:**
- Updates during sprints: Document in story notes
- Updates after sprints: Update architecture docs, increment version

---

**Architecture Status:** Sprint 1 Foundation Complete ✅

**Next Steps:**
1. Bob (Scrum Master) creates Story 1.1
2. James (Developer) implements Story 1.1
3. Architecture docs referenced during development
