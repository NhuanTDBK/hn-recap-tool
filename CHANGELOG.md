# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2026-02-28

### Added
- Update Save button label to "Saved" after tap in Telegram bot

### Fixed
- Resolve SQLAlchemy bidirectional relationship warning in models

### Refactored
- Improve message editing logic in `show_more` handler

---

## [0.7.0] — 2026-02-27

### Added
- Inline button refresh: Show More, Actions menu; remove Discuss UI (epic-9)

### Documentation
- Simplify README and reorganize documentation structure

---

## [0.6.0] — 2026-02-25

### Added
- User activity log for summary rating and save tracking (feedback)
- Crawler daemon service to docker-compose (story 8.2)
- Replace raw HTTP call with `Runner.run()` in grouped summarization
- Replace `hn_id` watermark with `collected_at` rolling window in summarizer

### Fixed
- Remove Langfuse tracing from `personalized_summarization`
- Default RocksDB to `read_only=True` to prevent lock contention
- Increase `max_posts` default to 100 and remove unused import in delivery

### Refactored
- Remove dead `_cache_post_metadata` code from hourly collector

---

## [0.5.0] — 2026-02-24

### Added
- Automate docker compose deploy workflow
- AWS infra and worker pipeline scripts for deployment

### Fixed
- Omit `temperature` parameter for gpt-5 chat completions
- Avoid `missinggreenlet` error and update gpt-5 token param in summarization
- Include uncrawled posts in fallback selection for summarization
- Open RocksDB read-only for summary jobs
- Run Alembic with docker compose v2
- Remove unused scripts

### Documentation
- Render database schema as Mermaid diagram
- Update project structure docs and remove unused/API reference sections

---

## [0.4.0] — 2026-02-13 to 2026-02-16

### Added
- Hourly delivery daemon with APScheduler integration; default LLM model changed to `gpt-5-nano`
- User summary style preferences (STORY-2.4)
- Telegram bot delivery system with full end-to-end pipeline
- APScheduler hourly posts collection job
- Alembic migration execution and test suite fixes

### Fixed
- Add backoff handler for resilient API retries

### Refactored
- Create personalized summaries table architecture (schema redesign)

### Documentation
- Add comprehensive scheduler trigger guides and CLI scripts

---

## [0.3.0] — 2026-02-13

### Added
- Agent-based summarization and orchestration pipeline
- OpenAI Agents SDK integration with Langfuse observability
- LLM-as-judge evaluation framework with test dataset

### Tests
- Comprehensive unit tests for agents and token tracking

### Refactored
- Migrate agents to OpenAI Agents Python SDK

### Documentation
- Add Epic 2 implementation summary and completion notes

---

## [0.2.0] — 2025-10-25 to 2025-10-28

### Added
- HackerNews content crawler with clean architecture
- Simplified LSH (Locality-Sensitive Hashing) model for deduplication

### Documentation
- Update README with comprehensive project documentation

---

## [0.1.0] — 2025-09-08

### Added
- Initial project commit
