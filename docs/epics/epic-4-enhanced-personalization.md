# Epic 4: Enhanced Personalization & Delivery Optimization

**Status:** Draft
**Priority:** High
**Owner:** Product Team
**Created:** 2026-02-15

---

## Epic Overview

Enhance the personalized summarization pipeline to use post ID-based selection instead of timestamp-based selection, ensuring complete coverage without gaps and improving delivery reliability.

---

## Business Value

**Problem:**
The current personalization flow uses timestamp-based post selection (`created_at >= since`), which can miss posts if:
- Posts are ingested out of order
- There are delays in the ingestion pipeline
- Timezone inconsistencies occur
- Database clock drift happens

**Solution:**
Switch to post ID-based selection (`post.id > last_summary.post_id`), which guarantees:
- Sequential coverage of all posts
- No missed posts due to timing issues
- Deterministic behavior
- Easier debugging and testing

**Impact:**
- 100% post coverage (no gaps)
- More predictable user experience
- Better audit trail
- Foundation for incremental processing

---

## User Stories

### Story 4.1: Post ID-Based Candidate Selection

**As a** system administrator
**I want** the personalization pipeline to select candidate posts based on post IDs rather than timestamps
**so that** we guarantee complete coverage without gaps and improve reliability

**Acceptance Criteria:**
1. `find_posts_in_time_window()` uses post ID range instead of timestamp range
2. Group time window logic finds the minimum `last_summary.post_id` across users
3. Query selects posts where `post.id > min(last_summary.post_id)` for the group
4. Fallback logic uses highest N post IDs instead of latest timestamps
5. All existing functionality preserved (filtering, deduplication, ordering)
6. Unit tests verify ID-based selection logic
7. Integration tests confirm no posts are skipped

**Technical Notes:**
- Modify `get_group_time_window()` to return min post_id instead of min timestamp
- Update `find_posts_in_time_window()` to query by post_id range
- Ensure backward compatibility for users with no summaries (use default lookback)
- Update logging to show post ID ranges instead of time ranges

---

## Success Metrics

- Zero posts skipped in personalization pipeline
- 100% coverage verified via post ID sequence checks
- No regression in delivery performance
- Improved debuggability (ID ranges are clearer than timestamps)

---

## Dependencies

- Existing `summaries` table with `post_id` foreign key
- Existing `personalized_summarization.py` module
- PostgreSQL with proper indexes on `summaries.post_id`

---

## Technical Approach

### Current Flow (Timestamp-Based)
```python
# Get earliest last summary time across users
since = min([get_user_last_summary_time(user) for user in users])

# Find posts created after that time
posts = db.query(Post).filter(Post.created_at >= since).all()
```

### New Flow (Post ID-Based)
```python
# Get minimum last summary post_id across users
min_post_id = min([get_user_last_summary_post_id(user) for user in users])

# Find posts with ID greater than min_post_id
posts = db.query(Post).filter(Post.id > min_post_id).all()
```

### Fallback Logic
```python
# If no summaries exist for users, use default lookback
if min_post_id is None:
    # Get latest N posts by ID (highest IDs)
    posts = db.query(Post).order_by(Post.id.desc()).limit(N).all()
```

---

## Open Questions

1. Should we maintain timestamp-based logic as a secondary filter? (Answer: No, keep it simple)
2. How to handle users with no summaries? (Answer: Use latest N posts by ID)
3. Should we add a migration script to backfill missing summaries? (Answer: Not in this epic)

---

## Out of Scope

- Backfilling historical summaries
- Changing summary generation logic
- Modifying bot delivery system
- Performance optimization (covered in separate epic)

---

## Timeline

**Estimated Duration:** 1-2 days

**Story Breakdown:**
- Story 4.1: Post ID-Based Selection (1-2 days)

---

## References

- Current implementation: `backend/app/application/use_cases/personalized_summarization.py`
- Database models: `backend/app/infrastructure/database/models.py`
- Architecture: `docs/architecture/PERSONALIZATION_ARCHITECTURE.md`
