# Personalization Architecture - Summary Storage Design

## Overview

The personalization system is built on a **separate summaries table** rather than storing summaries directly in the posts table. This architecture enables true multi-user personalization while maintaining scalability.

---

## Problem with Single-Summary Approach ❌

Storing summaries in `posts.summary` creates a critical bottleneck:

```sql
-- Old approach: ONE summary per post
posts table
├── id
├── title
├── url
└── summary  ← Only ONE summary possible!
```

**Limitations:**
- Only one summary version per post (defeats 5 prompt variants)
- No per-user customization
- No support for user preferences
- Can't A/B test different prompts
- Blocks memory system features
- No feedback collection per variant

---

## Personalization Architecture ✅

### Table Design

```sql
-- New approach: MANY summaries per post
posts table (unchanged)
├── id (UUID)
├── hn_id
├── title
├── url
└── (no summary column)

summaries table (new)
├── id (PK)
├── post_id (FK → posts)
├── user_id (FK → users, nullable)
├── prompt_type (basic/technical/business/concise/personalized)
├── summary_text (TEXT)
├── key_points (JSON)
├── technical_level
├── rating (1-5)
├── user_feedback (TEXT)
├── token_count
├── cost_usd
├── created_at, updated_at

Unique constraint: (post_id, user_id, prompt_type)
```

### Key Design Decisions

**1. Separate Table**
- Posts remain immutable core data
- Summaries are generated artifacts
- Easy to regenerate or update summaries
- No data duplication

**2. User-Specific Summaries**
- `user_id` = specific user → personalized summary
- `user_id` = NULL → shared/default summary
- Multiple variants per user possible
- Different users get different summaries

**3. Prompt Type Tracking**
- Track which prompt generated each summary
- Enable A/B testing different variants
- Support feedback per variant
- Measure quality by prompt type

**4. Feedback Collection**
- `rating`: 1-5 star user rating
- `user_feedback`: Text feedback
- Foundation for improving prompts
- Data for memory system learning

---

## Usage Scenarios

### Scenario 1: Multiple Users, Same Post

```
Post ID: 40000000 (RocksDB Article)
├── User 1 → basic summary ("General audience version")
├── User 2 → technical summary ("Deep architecture details")
├── User 3 → business summary ("Market implications")
└── NULL → shared/default (basic summary for all)

SELECT * FROM summaries WHERE post_id='40000000'
→ 4 rows (1 per user + 1 shared)
```

### Scenario 2: Same User, Different Preferences

```
User ID: 123
├── Post A: technical summary ⭐⭐⭐⭐⭐ (rated 5 stars)
├── Post B: business summary ⭐⭐⭐⭐ (rated 4 stars)
├── Post C: concise summary ⭐⭐ (rated 2 stars - not preferred)
└── Post D: personalized summary ⭐⭐⭐⭐⭐ (rated 5 stars)
```

### Scenario 3: A/B Testing

```
Post ID: 40000001
├── basic vs. technical (version A tested)
├── Measure engagement: basic=82%, technical=89%
├── Conclusion: Technical better for this topic
└── Next post: Use technical as default for this user
```

---

## Implementation

### Database Migration

```python
# File: backend/alembic/versions/20250213_add_summaries_table.py
# Creates summaries table with proper indexes and constraints
```

### ORM Model

```python
# File: backend/app/infrastructure/database/models.py
class Summary(Base):
    __tablename__ = "summaries"

    # Keys
    post_id: UUID  # FK to posts
    user_id: Optional[int]  # FK to users (NULL = shared)
    prompt_type: str  # basic, technical, business, concise, personalized

    # Content
    summary_text: str
    key_points: Optional[List]
    technical_level: Optional[str]

    # Metrics
    token_count: Optional[int]
    cost_usd: Optional[Decimal]
    rating: Optional[int]  # 1-5
    user_feedback: Optional[str]
```

### Use Cases

```python
# File: backend/app/application/use_cases/summarization_agent.py

class AgentSummarizeSinglePostUseCase:
    async def execute(self, post_id: str) -> dict:
        # Generate summary
        summary_text = summarize_post(...)

        # Create Summary record (NOT in posts table!)
        summary = Summary(
            post_id=post_id,
            user_id=self.user_id,  # per-user tracking
            prompt_type=self.prompt_type,
            summary_text=summary_text,
            token_count=...,
            cost_usd=...
        )

        db_session.add(summary)
        db_session.commit()

        return {"post_id": post_id, "user_id": user_id, "summary": summary_text}
```

---

## Queries for Personalization

### Get User's Preferred Summaries

```sql
-- User 123 prefers technical summaries
SELECT * FROM summaries
WHERE user_id = 123
ORDER BY rating DESC
```

### Get Best Performing Variant

```sql
-- Which prompt variant works best for this post?
SELECT prompt_type, AVG(rating) as avg_rating
FROM summaries
WHERE post_id = '40000000'
GROUP BY prompt_type
ORDER BY avg_rating DESC
```

### Shared Summary Fallback

```sql
-- If user hasn't seen this post, get shared summary
SELECT * FROM summaries
WHERE post_id = '40000000'
AND user_id IS NULL
AND prompt_type = 'basic'
```

### User Analytics

```sql
-- Which summary types does User 123 prefer?
SELECT prompt_type, AVG(rating) as preference
FROM summaries
WHERE user_id = 123
GROUP BY prompt_type
ORDER BY preference DESC
```

---

## Scalability

### Storage Efficiency

```
Approach 1 (single summary in posts):
- 10M posts × 1 summary = 10M rows
- No personalization

Approach 2 (summaries table):
- 10M posts × 5 variants × 10% of users = 5M rows typical
- Grows with personalization adoption
- Easily archived/aged

Approach 2 is MORE scalable because:
✓ Share computational load (generate once per variant)
✓ Cache popular variants
✓ Archive old summaries per user
✓ Compression friendly (many identical summaries)
```

### Query Performance

```sql
-- Fast lookups with proper indexes
CREATE INDEX idx_post_id ON summaries(post_id);
CREATE INDEX idx_user_id ON summaries(user_id);
CREATE INDEX idx_prompt_type ON summaries(prompt_type);
CREATE INDEX idx_post_user ON summaries(post_id, user_id);
```

---

## Integration with Other Systems

### Memory System (Phase 6)

```
Memory System needs to:
1. Know user's summary preferences (from ratings)
2. Learn user's style preferences (technical vs business)
3. Track engagement per summary variant
4. Update recommendation strategy

All data available in summaries table!
```

### Discussion System (Phase 5)

```
Discussion agents need:
1. User's preferred summary style
2. Post's technical level (from summary)
3. Key points for discussion (from key_points field)
4. User feedback (for context awareness)

All supported by this architecture!
```

### Telegram Bot

```
Bot can:
1. Store user's preference (rating, feedback)
2. Recommend summaries they'll like
3. Collect engagement metrics
4. Learn from user interactions
5. Personalize experience per user

Powered by summaries table!
```

---

## Future Enhancements

### 1. Smart Caching
```python
# Cache popular variants
class SummaryCache:
    # Cache top 80% summaries (20% of variants serve 80% of users)
    # Reduce generation cost by 80%
```

### 2. Adaptive Generation
```python
# Generate variants on-demand based on usage patterns
if user_likes_technical:
    generate_technical_variant()  # Priority
else:
    generate_basic_variant()  # Fallback
```

### 3. Collaborative Filtering
```sql
-- Find users similar to user_id based on summary ratings
SELECT user_id,
       COSINE_SIMILARITY(ratings_vector) as similarity
FROM user_ratings
ORDER BY similarity DESC
LIMIT 10
```

### 4. Summary Lifecycle
```python
# Fresh summaries for trending posts
# Archive summaries older than 30 days (user didn't engage)
# Regenerate low-rated summaries
```

---

## Summary

The separate summaries table is the **foundational architecture decision** that enables:

- ✅ Multi-user personalization
- ✅ Feedback collection and learning
- ✅ A/B testing different prompts
- ✅ Integration with memory system
- ✅ Scalability to millions of users
- ✅ Analytics and metrics tracking

This design supports the **full personalization vision** while maintaining clean separation between immutable posts data and generated/personalized summaries.

**Status**: ✅ Implemented and ready for production
