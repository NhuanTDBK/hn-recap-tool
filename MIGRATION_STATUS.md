# Database Migration Status

**Date**: 2026-02-13
**Status**: ✅ Complete
**Current Version**: `7be4bb0d3cdd`

---

## Applied Migrations

### Migration: `7be4bb0d3cdd` - Create posts table with crawl tracking
**Applied**: ✅ Yes
**Date**: 2026-02-13

**Schema Created**:
- Table: `posts`
- Indexes: `hn_id`, `created_at`, `type`, `score`
- Unique Constraint: `hn_id` (prevents duplicate posts)

**Fields**:
```sql
-- Core fields
id               UUID PRIMARY KEY
hn_id            INT UNIQUE NOT NULL
type             TEXT
title            TEXT
author           TEXT
url              TEXT
domain           TEXT
score            INT
comment_count    INT
created_at       TIMESTAMPTZ
collected_at     TIMESTAMPTZ

-- Content flags
has_html         BOOLEAN
has_text         BOOLEAN
has_markdown     BOOLEAN

-- Crawl tracking
is_crawl_success BOOLEAN
crawl_retry_count INT
crawl_error      TEXT
crawled_at       TIMESTAMPTZ
content_length   INT

-- Summary (future)
summary          TEXT
summarized_at    TIMESTAMPTZ

-- Metadata
updated_at       TIMESTAMPTZ
```

---

## Database Configuration

**Connection Details**:
- Host: `localhost`
- Port: `5433` (external), `5432` (internal Docker)
- Database: `hn_pal`
- User: `hn_pal`
- Password: `hn_pal_dev`

**Connection String**:
```
postgresql+asyncpg://hn_pal:hn_pal_dev@localhost:5433/hn_pal
```

---

## Migration Commands

### Check current version
```bash
cd backend
../.venv/bin/python -m alembic current
```

### Apply migrations
```bash
../.venv/bin/python -m alembic upgrade head
```

### View history
```bash
../.venv/bin/python -m alembic history
```

### Rollback one version
```bash
../.venv/bin/python -m alembic downgrade -1
```

### Create new migration
```bash
../.venv/bin/python -m alembic revision --autogenerate -m "description"
```

---

## Testing

### Database Connectivity Test
```bash
cd backend
../.venv/bin/python test_database.py
```

**Expected Output**:
```
✅ All database tests passed!
```

### Verify Schema
```bash
# Using Docker
docker exec -it hn-digest-postgres psql -U hn_pal -d hn_pal -c "\d posts"

# Or run test script
../.venv/bin/python test_database.py
```

---

## Docker Services

### Start Database
```bash
docker-compose up -d postgres
```

### Check Status
```bash
docker ps --filter "name=hn-digest-postgres"
```

### View Logs
```bash
docker logs hn-digest-postgres
```

### Stop Database
```bash
docker-compose down
```

---

## pgAdmin Access

**URL**: http://localhost:5050
**Login**: `admin@hnpal.local` / `admin`

**Add Server**:
1. Right-click "Servers" → "Register" → "Server"
2. General Tab:
   - Name: `HN Pal Local`
3. Connection Tab:
   - Host: `postgres` (Docker network name)
   - Port: `5432`
   - Username: `hn_pal`
   - Password: `hn_pal_dev`
   - Database: `hn_pal`

---

## Troubleshooting

### Migration fails with "database does not exist"
```bash
docker-compose down
docker-compose up -d postgres
# Wait for health check
sleep 5
../.venv/bin/python -m alembic upgrade head
```

### Port 5432 already in use
Database is configured to use port `5433` externally to avoid conflicts.
Check `docker-compose.yml` for port mapping: `5433:5432`

### "No module named 'greenlet'"
```bash
uv pip install greenlet
```

### Alembic can't import app modules
Make sure you're in the `backend/` directory when running Alembic commands.

---

## Next Steps

1. ✅ Database schema applied
2. ✅ PostgreSQL repository implemented
3. ✅ Firebase HN client created
4. ✅ Markdown conversion integrated
5. ⏭️ **Next**: Implement pipeline orchestration (Story 1.4)
6. ⏭️ **Next**: Start Epic 2 (Summarization)

---

**Migration Status**: ✅ **COMPLETE AND VERIFIED**
