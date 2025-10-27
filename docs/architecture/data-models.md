# Data Models - JSONL Schemas & API Models

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1)
**Last Updated:** 2025-10-21

---

## Overview

This document defines:
1. **JSONL File Schemas** - Data stored in `data/` directory
2. **Pydantic API Models** - Request/response validation
3. **Redis Cache Keys** - Caching structure

---

## JSONL File Schemas

### HN Posts (`data/raw/YYYY-MM-DD-posts.jsonl`)

**Purpose:** Raw HN story metadata from Algolia API

**Schema:**
```json
{
  "id": 12345,
  "title": "Example HN Post Title",
  "url": "https://example.com/article",
  "author": "username",
  "points": 250,
  "num_comments": 45,
  "created_at": "2025-10-21T10:30:00.000Z",
  "type": "story",
  "tags": ["story", "front_page"]
}
```

**Fields:**
- `id` (integer, required) - HN item ID
- `title` (string, required) - Post title
- `url` (string, optional) - External link (null for Ask HN, Show HN text posts)
- `author` (string, required) - HN username
- `points` (integer, required) - Upvote count
- `num_comments` (integer, required) - Comment count
- `created_at` (ISO 8601 string, required) - Post creation timestamp
- `type` (string, required) - Item type: "story", "poll", "job"
- `tags` (array of strings, required) - HN tags (e.g., ["story", "show_hn", "front_page"])

**Example:**
```json
{"id": 38543210, "title": "Show HN: My New Open Source Project", "url": "https://github.com/user/project", "author": "developer123", "points": 180, "num_comments": 32, "created_at": "2025-10-21T08:15:00.000Z", "type": "story", "tags": ["story", "show_hn", "front_page"]}
{"id": 38543211, "title": "Ask HN: Best practices for API design?", "url": null, "author": "curious_dev", "points": 95, "num_comments": 67, "created_at": "2025-10-21T09:22:00.000Z", "type": "story", "tags": ["story", "ask_hn", "front_page"]}
```

---

### Article Content (`data/raw/YYYY-MM-DD-content.jsonl.gz`)

**Purpose:** Extracted article text (gzip compressed)

**Schema:**
```json
{
  "post_id": 12345,
  "url": "https://example.com/article",
  "content": "Full article text extracted via trafilatura...",
  "extracted_at": "2025-10-21T10:35:00.000Z",
  "extraction_success": true,
  "word_count": 1250
}
```

**Fields:**
- `post_id` (integer, required) - HN item ID (foreign key to posts)
- `url` (string, required) - Article URL
- `content` (string, required) - Extracted clean text (empty string if extraction failed)
- `extracted_at` (ISO 8601 string, required) - Extraction timestamp
- `extraction_success` (boolean, required) - Whether extraction succeeded
- `word_count` (integer, required) - Number of words in content (0 if failed)

**Notes:**
- File is gzip compressed to save disk space (~10x compression)
- Only main article text, no ads/navigation/boilerplate
- For Ask HN/Show HN text posts, `content` = HN post text

---

### Comments (`data/raw/YYYY-MM-DD-comments.jsonl`)

**Purpose:** HN comment threads (up to 3 levels deep)

**Schema:**
```json
{
  "id": 67890,
  "post_id": 12345,
  "parent_id": null,
  "author": "commenter1",
  "text": "Great article! I've been using this approach...",
  "points": 15,
  "created_at": "2025-10-21T10:45:00.000Z",
  "depth": 0
}
```

**Fields:**
- `id` (integer, required) - Comment ID
- `post_id` (integer, required) - Parent HN post ID
- `parent_id` (integer, optional) - Parent comment ID (null for root comments)
- `author` (string, required) - HN username
- `text` (string, required) - Comment text
- `points` (integer, required) - Upvote count
- `created_at` (ISO 8601 string, required) - Comment creation timestamp
- `depth` (integer, required) - Nesting level (0 = root, 1-3 = nested)

**Example:**
```json
{"id": 67890, "post_id": 38543210, "parent_id": null, "author": "expert_user", "text": "This is a solid implementation. One thing to watch out for...", "points": 22, "created_at": "2025-10-21T08:30:00.000Z", "depth": 0}
{"id": 67891, "post_id": 38543210, "parent_id": 67890, "author": "developer123", "text": "Thanks! Good point about...", "points": 8, "created_at": "2025-10-21T08:45:00.000Z", "depth": 1}
```

---

### User Profiles (`data/users/user-profiles.jsonl`)

**Purpose:** User accounts (append-only log)

**Schema:**
```json
{
  "user_id": "uuid-v4-here",
  "email": "user@example.com",
  "hashed_password": "$2b$12$...",
  "created_at": "2025-10-21T11:00:00.000Z",
  "is_active": true,
  "updated_at": "2025-10-21T11:00:00.000Z"
}
```

**Fields:**
- `user_id` (UUID v4 string, required) - Unique user identifier
- `email` (string, required) - User email (unique)
- `hashed_password` (string, required) - Bcrypt hashed password
- `created_at` (ISO 8601 string, required) - Account creation timestamp
- `is_active` (boolean, required) - Account active status
- `updated_at` (ISO 8601 string, required) - Last update timestamp

**Notes:**
- Append-only: new record added on every update (latest record = current state)
- To find current user: read all records, filter by email, take latest `updated_at`
- Passwords hashed with bcrypt (cost factor 12)

---

## Pydantic API Models

### User Models (`backend/app/models/user.py`)

**UserCreate** (Registration request):
```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str  # Min 8 characters (validated in endpoint)
```

**UserInDB** (Internal representation):
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserInDB(BaseModel):
    user_id: str  # UUID v4
    email: EmailStr
    hashed_password: str
    created_at: datetime
    is_active: bool
    updated_at: datetime
```

**User** (Public response):
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class User(BaseModel):
    user_id: str
    email: EmailStr
    created_at: datetime
    is_active: bool
```

**Token** (JWT response):
```python
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str  # Always "bearer"
```

**TokenData** (JWT payload):
```python
from pydantic import BaseModel
from typing import Optional

class TokenData(BaseModel):
    email: Optional[str] = None
```

---

### Digest Models (`backend/app/models/digest.py`)

**Post** (Single HN post):
```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List

class Post(BaseModel):
    id: int
    title: str
    url: Optional[HttpUrl] = None
    author: str
    points: int
    num_comments: int
    created_at: datetime
    type: str
    tags: List[str]
```

**PostWithContent** (Post + article content):
```python
from pydantic import BaseModel
from typing import Optional

class PostWithContent(Post):
    content: Optional[str] = None
    word_count: Optional[int] = None
```

**Comment** (HN comment):
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Comment(BaseModel):
    id: int
    post_id: int
    parent_id: Optional[int] = None
    author: str
    text: str
    points: int
    created_at: datetime
    depth: int
```

**DigestList** (List of available digests):
```python
from pydantic import BaseModel
from datetime import date
from typing import List

class DigestList(BaseModel):
    dates: List[date]  # ["2025-10-21", "2025-10-20", ...]
```

**Digest** (Full digest response):
```python
from pydantic import BaseModel
from datetime import date
from typing import List

class Digest(BaseModel):
    date: date
    posts: List[Post]
    total_posts: int
```

---

## Redis Cache Keys

### User Sessions

**Key Pattern:** `user:{user_id}:session`

**Value:** JSON string
```json
{
  "user_id": "uuid-v4",
  "email": "user@example.com",
  "is_active": true
}
```

**TTL:** 30 minutes (matches JWT expiration)

---

### Latest Digest

**Key Pattern:** `digest:{YYYY-MM-DD}`

**Value:** JSON string (full Digest object)
```json
{
  "date": "2025-10-21",
  "posts": [...],
  "total_posts": 30
}
```

**TTL:** 7 days

---

### User Profile Cache

**Key Pattern:** `user:{user_id}:profile`

**Value:** JSON string (UserInDB object)
```json
{
  "user_id": "uuid-v4",
  "email": "user@example.com",
  "hashed_password": "$2b$12$...",
  "created_at": "2025-10-21T11:00:00Z",
  "is_active": true,
  "updated_at": "2025-10-21T11:00:00Z"
}
```

**TTL:** 1 hour

---

## Data Validation Rules

### Email Validation
- Format: RFC 5322 compliant (via Pydantic EmailStr)
- Lowercase normalization
- No duplicates (enforced at application level)

### Password Validation
- Minimum length: 8 characters
- Hashing: bcrypt with cost factor 12
- Validation in endpoint, not Pydantic model

### HN Post Validation
- `id` must be positive integer
- `title` max length: 500 characters
- `url` must be valid HTTP(S) URL or null
- `type` must be one of: "story", "poll", "job"

### Date Validation
- Format: ISO 8601 (`YYYY-MM-DD`)
- Range: 2006-10-09 (HN launch) to today

---

## Database Migration Strategy

**Current:** No database (JSONL files + Redis)

**Future Migration Path (if needed):**
1. Keep JSONL for raw data (archival)
2. Move user data to PostgreSQL (relational)
3. Move processed data to PostgreSQL (query performance)
4. Use Redis for caching only

**Migration Trigger:** > 1000 users OR query performance < 2s

---

## Error Handling

### JSONL File Operations

**File Not Found:**
- Return empty list or null
- Log warning
- Continue execution

**Corrupt JSON Line:**
- Skip line
- Log error with line number
- Continue to next line

**Gzip Decompression Failure:**
- Return extraction_success = false
- Log error
- Store empty content

### Redis Operations

**Connection Failure:**
- Fallback to JSONL file read
- Log error
- Continue execution (degraded mode)

**Key Not Found:**
- Generate data from JSONL
- Cache for future use
- Return result

---

## Performance Considerations

### JSONL File Reads
- Read files line-by-line (streaming)
- Don't load entire file into memory
- Use generators for large files

### Redis Caching
- Cache hot data (latest digest, active users)
- Set appropriate TTLs
- Invalidate on data updates

### Date Partitioning
- Files named by date for efficient lookup
- No need to scan all files
- Direct file path construction

---

**Data Models Owner:** Winston (Architect)
**Last Review:** 2025-10-21
