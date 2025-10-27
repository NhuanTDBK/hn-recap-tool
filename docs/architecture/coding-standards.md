# Coding Standards

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1)
**Last Updated:** 2025-10-21

---

## Python Code Standards

### Style Guide

**Base:** PEP 8 with modifications

**Formatter:** Black (default settings)
- Line length: 88 characters
- String quotes: Double quotes preferred
- Trailing commas: Enabled

**Linter:** Ruff
- Replaces flake8, isort, pyupgrade
- Fast, comprehensive

**Configuration:**
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.ruff]
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
]
ignore = [
    "E501",  # line too long (handled by black)
]
```

---

### Naming Conventions

**Variables & Functions:** `snake_case`
```python
user_id = "123"
def fetch_posts(date: str) -> List[Post]:
    pass
```

**Classes:** `PascalCase`
```python
class HNClient:
    pass

class PostWithContent(BaseModel):
    pass
```

**Constants:** `UPPER_SNAKE_CASE`
```python
MAX_POSTS_PER_DAY = 30
DEFAULT_CACHE_TTL = 3600
```

**Private Methods:** Leading underscore
```python
def _validate_token(token: str) -> bool:
    pass
```

**Module Names:** `snake_case`
```python
hn_client.py
jsonl.py
```

---

### Type Hints

**Required:** All function signatures

```python
from typing import List, Optional, Dict, Any
from datetime import datetime

# Good
def get_digest(date: str) -> Optional[Dict[str, Any]]:
    return {"date": date, "posts": []}

# Bad
def get_digest(date):
    return {"date": date, "posts": []}
```

**Pydantic Models:** Use for data validation
```python
from pydantic import BaseModel

class Post(BaseModel):
    id: int
    title: str
    url: Optional[str] = None
```

**Return Types:** Always specify
```python
# Good
def process_data() -> None:
    pass

# Bad
def process_data():
    pass
```

---

### Imports

**Order:**
1. Standard library
2. Third-party packages
3. Local modules

**Style:** Absolute imports preferred
```python
# Good
from datetime import datetime
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.hn_client import HNClient
from app.models.digest import Post

# Bad
from datetime import *
from app.services import *
```

**Ruff** handles import sorting automatically

---

### Function Design

**Length:** Max 50 lines per function
- If longer, break into smaller functions

**Arguments:** Max 5 parameters
- Use dataclasses/Pydantic models for > 5 params

**Single Responsibility:** One function = one task
```python
# Good
def fetch_posts(date: str) -> List[Dict[str, Any]]:
    """Fetch posts from HN API for a specific date."""
    pass

def save_posts(posts: List[Dict[str, Any]], date: str) -> None:
    """Save posts to JSONL file."""
    pass

# Bad
def fetch_and_save_posts(date: str) -> None:
    """Fetch posts and save them."""
    # Does too much
    pass
```

---

### Docstrings

**Required:** All public functions, classes, modules

**Style:** Google-style docstrings
```python
def fetch_posts(date: str, limit: int = 30) -> List[Post]:
    """Fetch HN posts for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        limit: Maximum number of posts to fetch (default: 30)

    Returns:
        List of Post objects

    Raises:
        ValueError: If date format is invalid
        HTTPError: If HN API request fails
    """
    pass
```

**Class Docstrings:**
```python
class HNClient:
    """Client for interacting with HackerNews Algolia API.

    Handles fetching posts, comments, and user data from HN.
    Includes rate limiting and retry logic.

    Attributes:
        base_url: HN API base URL
        timeout: Request timeout in seconds
    """
    pass
```

---

### Error Handling

**Specific Exceptions:** Catch specific exceptions
```python
# Good
try:
    response = httpx.get(url)
    response.raise_for_status()
except httpx.HTTPError as e:
    logger.error(f"HTTP error: {e}")
except httpx.TimeoutException as e:
    logger.error(f"Timeout: {e}")

# Bad
try:
    response = httpx.get(url)
except Exception as e:
    logger.error(f"Error: {e}")
```

**Logging:** Use structured logging
```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Fetching posts for date: {date}")
logger.error(f"Failed to fetch posts: {error}", exc_info=True)
```

**FastAPI Exception Handling:**
```python
from fastapi import HTTPException, status

# Good
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

# Bad
if not user:
    return {"error": "User not found"}
```

---

### Async/Await

**Use When:**
- I/O operations (HTTP requests, file I/O, database queries)
- FastAPI endpoint handlers

**Pattern:**
```python
import httpx

async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# FastAPI endpoint
@router.get("/posts")
async def get_posts() -> List[Post]:
    posts = await fetch_posts_from_db()
    return posts
```

**Avoid:** Unnecessary async (CPU-bound operations)

---

### Configuration Management

**Use Pydantic Settings:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Never:** Hardcode secrets
```python
# Bad
SECRET_KEY = "my-secret-key"

# Good
SECRET_KEY = settings.secret_key
```

---

### File I/O

**Context Managers:** Always use `with`
```python
# Good
with open(file_path, "r") as f:
    data = f.read()

# Bad
f = open(file_path, "r")
data = f.read()
f.close()
```

**Gzip Files:**
```python
import gzip

# Write
with gzip.open(file_path, "wt") as f:
    f.write(data)

# Read
with gzip.open(file_path, "rt") as f:
    data = f.read()
```

**JSONL Operations:**
```python
import json

# Write
with open(file_path, "a") as f:
    f.write(json.dumps(obj) + "\n")

# Read (streaming)
with open(file_path, "r") as f:
    for line in f:
        obj = json.loads(line)
        yield obj
```

---

### Testing Standards

**Test File Naming:** `test_{module_name}.py`

**Test Function Naming:** `test_{function_name}_{scenario}`
```python
def test_fetch_posts_success():
    pass

def test_fetch_posts_invalid_date():
    pass
```

**Arrange-Act-Assert Pattern:**
```python
def test_create_user():
    # Arrange
    user_data = {"email": "test@example.com", "password": "password123"}

    # Act
    user = create_user(user_data)

    # Assert
    assert user.email == "test@example.com"
    assert user.is_active is True
```

**Fixtures:** Use pytest fixtures
```python
import pytest

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "password123"
    }

def test_login(test_user):
    response = login(test_user)
    assert response.status_code == 200
```

---

### Security Standards

**Password Hashing:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash
hashed = pwd_context.hash(plain_password)

# Verify
is_valid = pwd_context.verify(plain_password, hashed)
```

**JWT Tokens:**
```python
from jose import jwt
from datetime import datetime, timedelta

# Create
expire = datetime.utcnow() + timedelta(minutes=30)
token = jwt.encode(
    {"sub": user.email, "exp": expire},
    SECRET_KEY,
    algorithm=ALGORITHM
)

# Verify
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

**Input Validation:** Use Pydantic models
```python
from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

---

### Performance Best Practices

**Lazy Loading:** Use generators for large datasets
```python
# Good
def read_jsonl(file_path: str):
    with open(file_path, "r") as f:
        for line in f:
            yield json.loads(line)

# Bad
def read_jsonl(file_path: str) -> List[Dict]:
    with open(file_path, "r") as f:
        return [json.loads(line) for line in f]
```

**Caching:** Use Redis for hot data
```python
from app.utils.cache import cache_get, cache_set

async def get_digest(date: str) -> Digest:
    # Try cache first
    cached = await cache_get(f"digest:{date}")
    if cached:
        return cached

    # Fetch and cache
    digest = await fetch_digest_from_file(date)
    await cache_set(f"digest:{date}", digest, ttl=3600)
    return digest
```

**Async Batch Operations:**
```python
import asyncio

async def process_posts(posts: List[Post]):
    tasks = [process_post(post) for post in posts]
    results = await asyncio.gather(*tasks)
    return results
```

---

### Logging

**Configuration:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
```

**Levels:**
- `DEBUG` - Detailed diagnostic info
- `INFO` - General informational messages
- `WARNING` - Warning messages (potential issues)
- `ERROR` - Error messages (failures)
- `CRITICAL` - Critical failures

**Usage:**
```python
logger.info(f"Processing {len(posts)} posts")
logger.warning(f"Retry attempt {retry_count}/{max_retries}")
logger.error(f"Failed to fetch posts: {error}", exc_info=True)
```

---

### Code Review Checklist

Before submitting code for review:

- [ ] Code passes Black formatting
- [ ] Code passes Ruff linting
- [ ] All functions have type hints
- [ ] Public functions have docstrings
- [ ] Tests written and passing
- [ ] No hardcoded secrets or credentials
- [ ] Error handling in place
- [ ] Logging added for key operations
- [ ] Code follows single responsibility principle
- [ ] Imports organized correctly

---

### Git Commit Messages

**Format:**
```
<type>: <short description>

<detailed description>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `test` - Test additions/changes
- `refactor` - Code refactoring
- `chore` - Maintenance tasks

**Examples:**
```
feat: Add HN data collection job

Implements background job to fetch HN posts, article content, and comments.
Uses APScheduler for daily scheduling. Stores data to JSONL files with
gzip compression for article content.

fix: Handle missing article URLs in content extraction

Some HN posts (Ask HN, Show HN) don't have external URLs. Updated
extraction logic to handle null URLs and extract HN post text instead.
```

---

**Coding Standards Owner:** Winston (Architect)
**Last Review:** 2025-10-21
