# Testing Strategy

**Project:** HackerNews Knowledge Graph Builder
**Version:** 1.0 (Sprint 1)
**Last Updated:** 2025-10-21

---

## Testing Philosophy

**For MVP:**
- Focus on critical path testing
- Unit tests for business logic
- Integration tests for API endpoints
- Manual testing for end-to-end flows
- No CI/CD initially (manual test execution)

**Balance:** Test coverage vs. delivery speed
- Target: 70%+ coverage for core services
- 100% coverage for authentication/security
- Lower coverage acceptable for utils/helpers

---

## Test Types

### Unit Tests

**Purpose:** Test individual functions/classes in isolation

**Tools:**
- pytest
- pytest-asyncio (async test support)

**Coverage:** Services, utilities, models

**Example:**
```python
# backend/tests/test_hn_client.py
import pytest
from app.services.hn_client import HNClient

def test_parse_post_data():
    """Test parsing HN API response into Post model."""
    raw_data = {
        "objectID": "12345",
        "title": "Test Post",
        "url": "https://example.com",
        "author": "user1",
        "points": 100,
        "num_comments": 25,
        "created_at": "2025-10-21T10:00:00.000Z",
        "_tags": ["story", "front_page"]
    }

    client = HNClient()
    post = client.parse_post(raw_data)

    assert post.id == 12345
    assert post.title == "Test Post"
    assert post.points == 100
```

---

### Integration Tests

**Purpose:** Test API endpoints end-to-end

**Tools:**
- pytest
- httpx (async test client)
- FastAPI TestClient

**Coverage:** API routes, database operations, external API calls

**Example:**
```python
# backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    """Test user registration endpoint."""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "user_id" in data

def test_login_user():
    """Test user login endpoint."""
    # First register
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )

    # Then login
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
```

---

### Manual Tests

**Purpose:** Verify end-to-end user flows

**When:** Before each sprint review, before production deployment

**Test Cases:** See Sprint 1 Manual Test Plan below

---

## Test Organization

### Directory Structure

```
backend/tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_auth.py          # Authentication tests
├── test_digests.py       # Digest API tests
├── test_collector.py     # Data collection tests
├── test_hn_client.py     # HN API client tests
├── test_storage.py       # JSONL storage tests
└── test_utils.py         # Utility function tests
```

---

## Pytest Configuration

### `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "-v",                    # Verbose output
    "--tb=short",            # Short traceback format
    "--strict-markers",      # Strict marker checking
    "--cov=app",             # Coverage for app directory
    "--cov-report=term-missing",  # Show missing lines
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow-running tests",
]
```

---

## Test Fixtures

### `conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
import os

@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "password123"
    }

@pytest.fixture
def authenticated_client(test_client, test_user_data):
    """Test client with authenticated user."""
    # Register user
    test_client.post("/api/auth/register", json=test_user_data)

    # Login to get token
    response = test_client.post(
        "/api/auth/login",
        data={"username": test_user_data["email"], "password": test_user_data["password"]}
    )
    token = response.json()["access_token"]

    # Add token to client headers
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client

@pytest.fixture
def sample_hn_post():
    """Sample HN post data."""
    return {
        "id": 12345,
        "title": "Test Post",
        "url": "https://example.com",
        "author": "user1",
        "points": 100,
        "num_comments": 25,
        "created_at": "2025-10-21T10:00:00.000Z",
        "type": "story",
        "tags": ["story", "front_page"]
    }

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Set up test environment with temporary data directory."""
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir()

    # Override data directory for tests
    monkeypatch.setattr(settings, "data_dir", str(test_data_dir))

    yield test_data_dir

    # Cleanup happens automatically (tmp_path is cleaned up by pytest)
```

---

## Sprint 1 Test Plan

### Story 1.1: HN Data Collection

**Unit Tests:**
- `test_hn_client_fetch_front_page()` - Fetch posts from HN API
- `test_hn_client_fetch_comments()` - Fetch comment threads
- `test_content_extraction_success()` - Extract article content
- `test_content_extraction_failure()` - Handle extraction failures
- `test_jsonl_write()` - Write data to JSONL files
- `test_jsonl_write_gzip()` - Write gzipped content files
- `test_collector_job_run()` - Run full collection job

**Integration Tests:**
- `test_collector_end_to_end()` - Full collection flow with real HN API
- `test_collector_retry_logic()` - Retry on API failures
- `test_collector_rate_limiting()` - Respect rate limits

**Manual Tests:**
1. Run collector job manually: `python scripts/run_collector.py`
2. Verify JSONL files created in `data/raw/`
3. Verify gzipped content file can be decompressed
4. Verify 30 posts collected
5. Check logs for errors

---

### Story 1.2: FastAPI Authentication

**Unit Tests:**
- `test_hash_password()` - Password hashing
- `test_verify_password()` - Password verification
- `test_create_access_token()` - JWT token creation
- `test_verify_token()` - JWT token verification
- `test_user_model_validation()` - Pydantic model validation

**Integration Tests:**
- `test_register_user_success()` - Register new user
- `test_register_user_duplicate_email()` - Reject duplicate email
- `test_register_user_invalid_email()` - Reject invalid email
- `test_register_user_short_password()` - Reject short password
- `test_login_success()` - Login with correct credentials
- `test_login_wrong_password()` - Reject wrong password
- `test_login_nonexistent_user()` - Reject nonexistent user
- `test_get_current_user()` - Get user from token
- `test_get_current_user_invalid_token()` - Reject invalid token

**Manual Tests:**
1. Register user via Swagger UI: `http://localhost:8000/docs`
2. Login to get JWT token
3. Use token to access `/api/auth/me`
4. Verify user profile returned
5. Try accessing protected endpoint without token (should fail)

---

### Story 1.3: Data Access API

**Unit Tests:**
- `test_read_jsonl_file()` - Read JSONL file
- `test_read_gzip_file()` - Read gzipped JSONL file
- `test_list_digest_dates()` - List available digest dates
- `test_parse_digest_date()` - Parse date from filename

**Integration Tests:**
- `test_get_digests_list()` - GET `/api/digests`
- `test_get_digest_by_date()` - GET `/api/digests/{date}`
- `test_get_digest_not_found()` - 404 for nonexistent date
- `test_get_post_by_id()` - GET `/api/posts/{id}`
- `test_get_post_with_content()` - Post includes article content
- `test_get_post_with_comments()` - Post includes comments
- `test_api_requires_auth()` - All endpoints require authentication
- `test_api_pagination()` - Pagination works correctly

**Manual Tests:**
1. Get list of digests: `GET /api/digests`
2. Get specific digest: `GET /api/digests/2025-10-21`
3. Get single post: `GET /api/posts/12345`
4. Verify pagination with `limit=10&offset=0`
5. Try accessing without auth token (should fail)

---

## Running Tests

### Run All Tests

```bash
cd backend
poetry run pytest
```

### Run Specific Test File

```bash
poetry run pytest tests/test_auth.py
```

### Run Specific Test

```bash
poetry run pytest tests/test_auth.py::test_register_user_success
```

### Run with Coverage

```bash
poetry run pytest --cov=app --cov-report=html
```

### Run Only Unit Tests

```bash
poetry run pytest -m unit
```

### Run Only Integration Tests

```bash
poetry run pytest -m integration
```

---

## Mocking External Dependencies

### Mock HN API

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_posts_from_hn():
    """Test fetching posts with mocked HN API."""
    mock_response = {
        "hits": [
            {
                "objectID": "12345",
                "title": "Test Post",
                "url": "https://example.com",
                "author": "user1",
                "points": 100,
                "num_comments": 25,
                "created_at": "2025-10-21T10:00:00.000Z",
                "_tags": ["story", "front_page"]
            }
        ]
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value.json = AsyncMock(return_value=mock_response)

        client = HNClient()
        posts = await client.fetch_front_page()

        assert len(posts) == 1
        assert posts[0].id == 12345
```

### Mock Redis

```python
@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis client."""
    class MockRedis:
        def __init__(self):
            self.store = {}

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value, ex=None):
            self.store[key] = value

        async def delete(self, key):
            self.store.pop(key, None)

    mock = MockRedis()
    monkeypatch.setattr("app.utils.cache.redis_client", mock)
    return mock
```

---

## Test Data Management

### Sample Data Files

Create fixture files for testing:

```
backend/tests/fixtures/
├── sample_posts.json       # Sample HN posts
├── sample_comments.json    # Sample comments
└── sample_content.json     # Sample article content
```

### Load Fixture Data

```python
import json
from pathlib import Path

def load_fixture(filename: str):
    """Load test fixture data."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path) as f:
        return json.load(f)

@pytest.fixture
def sample_posts():
    return load_fixture("sample_posts.json")
```

---

## Performance Testing

**Not in Sprint 1 scope, but consider for future:**

- Load testing with locust
- API response time benchmarks
- Database query performance
- Cache hit/miss ratios

---

## Regression Testing

### Before Each Deployment

**Checklist:**
1. Run full test suite: `pytest`
2. Verify all tests pass
3. Check test coverage: `pytest --cov`
4. Run manual test plan (see above)
5. Test in staging environment (if available)

**Regression Triggers:**
- Code changes to core services
- Dependency updates
- Configuration changes
- Before production deployment

---

## Test Coverage Goals

### Sprint 1 Targets

| Module | Coverage Target |
|--------|-----------------|
| `app.services.auth` | 100% |
| `app.services.hn_client` | 80% |
| `app.services.storage` | 80% |
| `app.jobs.collector` | 70% |
| `app.api.*` | 90% |
| `app.utils.*` | 60% |
| **Overall** | **70%+** |

---

## Debugging Failed Tests

### View Detailed Output

```bash
pytest -vv --tb=long
```

### Run with pdb

```bash
pytest --pdb
```

### Run Last Failed Tests Only

```bash
pytest --lf
```

---

## CI/CD Integration (Future)

**Not for Sprint 1, but plan for later:**

- GitHub Actions workflow
- Run tests on every PR
- Block merge if tests fail
- Automated coverage reports

---

**Testing Strategy Owner:** Winston (Architect)
**Last Review:** 2025-10-21
