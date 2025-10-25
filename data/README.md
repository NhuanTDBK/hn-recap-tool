# Data Directory

This directory stores all application data using JSONL (newline-delimited JSON) files.

## Directory Structure

```
data/
├── raw/              # Raw data collected from HackerNews
├── processed/        # Processed data (digests, summaries)
└── users/            # User data
```

## File Naming Conventions

### Raw Data (`raw/`)
- **Posts:** `YYYY-MM-DD-posts.jsonl`
  - Front page stories collected each day
  - Example: `2025-10-21-posts.jsonl`

- **Content:** `YYYY-MM-DD-content.jsonl.gz`
  - Extracted article content (gzipped)
  - Example: `2025-10-21-content.jsonl.gz`

- **Comments:** `YYYY-MM-DD-comments.jsonl`
  - Comment threads for posts
  - Example: `2025-10-21-comments.jsonl`

### Processed Data (`processed/`)
- **Digests:** `YYYY-MM-DD-digest.jsonl`
  - Daily digests combining posts and metadata
  - Example: `2025-10-21-digest.jsonl`

- **Topics:** `YYYY-MM-DD-topics.jsonl` (Future)
  - Topic clusters and classifications
  - Example: `2025-10-21-topics.jsonl`

- **Summaries:** `YYYY-MM-DD-summaries.jsonl` (Future)
  - LLM-generated summaries
  - Example: `2025-10-21-summaries.jsonl`

### User Data (`users/`)
- **User Profiles:** `user-profiles.jsonl`
  - Append-only user account data
  - One line per user

- **User Votes:** `user-votes.jsonl` (Future)
  - User voting/feedback history
  - Append-only

## JSONL Format

Each line is a valid JSON object:

```jsonl
{"id": "123", "email": "user@example.com", "created_at": "2025-10-21T10:00:00"}
{"id": "456", "email": "another@example.com", "created_at": "2025-10-21T11:00:00"}
```

## Storage Estimates

- **Daily posts:** ~50 KB (30 posts)
- **Daily content:** ~200 KB compressed
- **Daily comments:** ~100 KB
- **Daily digest:** ~300 KB
- **Total per day:** ~650 KB

**Annual estimate:** ~240 MB/year

## Backup Strategy

For production:
1. Daily backups to S3/cloud storage
2. Retention: 90 days for raw data, 1 year for digests
3. Compression: Use gzip for content files

## Migration Path

Current JSONL storage can be migrated to:
- **Parquet:** More efficient columnar storage
- **PostgreSQL:** Relational database with full-text search
- **DuckDB:** In-process analytical database

The clean architecture design makes this migration seamless - just implement new repository adapters.
