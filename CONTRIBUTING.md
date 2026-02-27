# Contributing to HN Pal

Thank you for your interest in contributing to HN Pal! This guide will help you get started.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Branching Strategy](#branching-strategy)
- [Code Review Guidelines](#code-review-guidelines)

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- uv (recommended) or pip

### Setup Development Environment

1. **Fork and clone the repository**:
```bash
git clone https://github.com/yourusername/hackernews_digest.git
cd hackernews_digest
```

2. **Install dependencies**:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

3. **Start infrastructure services**:
```bash
docker-compose up -d
```

4. **Set up environment**:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials
```

5. **Run database migrations**:
```bash
cd backend
python -m alembic upgrade head
```

6. **Verify setup**:
```bash
# Run tests
pytest

# Start API server
uvicorn app.main:app --reload

# Start Telegram bot (in another terminal)
python scripts/run_bot.py
```

## Development Workflow

### 1. Create a Branch

Always create a feature branch from `develop`:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

**Branch naming conventions**:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions/improvements

### 2. Make Changes

Follow the architecture principles:
- Domain logic goes in `app/domain/`
- Use cases go in `app/application/use_cases/`
- External integrations go in `app/infrastructure/`
- API/Bot interfaces go in `app/presentation/`

### 3. Write Tests

**Required**:
- Unit tests for new domain logic
- Integration tests for repository implementations
- API tests for new endpoints

**Coverage goal**: Maintain >80% coverage

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 4. Run Code Quality Checks

```bash
# Format code
ruff format .

# Lint
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type check
mypy backend/app
```

### 5. Create Database Migrations (if needed)

If you modified `app/infrastructure/database/models.py`:

```bash
# Generate migration
python -m alembic revision --autogenerate -m "description of changes"

# Review generated migration in alembic/versions/

# Test migration
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic upgrade head
```

### 6. Update Documentation

- Update README.md if adding user-facing features
- Update relevant docs in `docs/`
- Add docstrings to new functions/classes
- Update API documentation if modifying endpoints

## Code Standards

### Python Style

We follow PEP 8 with some modifications (enforced by Ruff):

- **Line length**: 100 characters
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Import order**: stdlib, third-party, local (handled by Ruff)

### Type Hints

**Required** for all functions:

```python
# Good
def fetch_posts(limit: int) -> list[Post]:
    pass

# Bad
def fetch_posts(limit):
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def summarize_post(post: Post, style: str) -> str:
    """Generate a summary for a Hacker News post.

    Args:
        post: The post to summarize
        style: Summary style (basic, technical, business, concise, personalized)

    Returns:
        The generated summary text

    Raises:
        OpenAIError: If API call fails
        ValueError: If style is invalid
    """
    pass
```

### Error Handling

- Use specific exceptions from `app/domain/exceptions.py`
- Always log errors with context
- Don't catch generic `Exception` unless necessary

```python
# Good
try:
    post = await repository.get(post_id)
except PostNotFoundError as e:
    logger.error(f"Post {post_id} not found: {e}")
    raise

# Bad
try:
    post = await repository.get(post_id)
except Exception:
    pass
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info("Fetched posts", extra={"count": len(posts), "source": "HN"})

# Bad
print(f"Got {len(posts)} posts")
```

### Async/Await

- Use async for I/O operations (database, HTTP, file)
- Don't use async for CPU-bound operations
- Properly await all async calls

```python
# Good
async def fetch_post(post_id: int) -> Post:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/{post_id}")
        return Post(**response.json())

# Bad (blocking call in async function)
async def fetch_post(post_id: int) -> Post:
    response = requests.get(f"{API_URL}/{post_id}")  # Blocking!
    return Post(**response.json())
```

## Testing

### Test Structure

Mirror source structure in tests:

```
backend/
├── app/
│   └── domain/
│       └── entities.py
└── tests/
    └── unit/
        └── domain/
            └── test_entities.py
```

### Test Naming

- Prefix test files with `test_`
- Test functions: `test_<what>_<condition>_<expected>`

```python
def test_post_creation_with_valid_data_succeeds():
    pass

def test_post_creation_with_invalid_url_raises_error():
    pass
```

### Fixtures

Use fixtures in `conftest.py`:

```python
# tests/conftest.py
import pytest

@pytest.fixture
async def db_session():
    """Provide a test database session."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def sample_post():
    """Provide a sample post for testing."""
    return Post(
        hn_id=12345,
        title="Test Post",
        url="https://example.com",
        score=100
    )
```

### Mocking

Use pytest-mock:

```python
async def test_fetch_posts_calls_api(mocker):
    mock_client = mocker.patch("app.infrastructure.services.hn_client.httpx.AsyncClient")
    mock_client.return_value.get.return_value.json.return_value = {"id": 123}

    client = HNClient()
    await client.fetch_post(123)

    mock_client.return_value.get.assert_called_once()
```

## Pull Request Process

### Before Submitting

**Checklist**:
- [ ] Tests pass: `pytest`
- [ ] Linting passes: `ruff check .`
- [ ] Type checking passes: `mypy backend/app`
- [ ] Code is formatted: `ruff format .`
- [ ] Migrations created (if needed)
- [ ] Documentation updated
- [ ] No secrets in code or commits

### PR Template

Use this template when creating a PR:

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- Change 1
- Change 2
- Change 3

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring

## Testing
Describe how you tested this

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Migrations created (if needed)
```

### PR Review Process

1. **Automated checks** must pass (CI/CD)
2. **At least one approving review** required
3. **Address all comments** before merging
4. **Squash commits** when merging (keep history clean)

## Branching Strategy

```
main (production-ready code)
  ↑
develop (integration branch)
  ↑
feature/*, bugfix/*, etc. (individual changes)
```

### Branch Lifecycle

1. Create feature branch from `develop`
2. Work on feature, commit regularly
3. Open PR to merge into `develop`
4. After review, squash and merge to `develop`
5. Periodically, `develop` is merged to `main` for releases

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add personalized summary style
fix: resolve database connection timeout
docs: update configuration guide
refactor: simplify delivery pipeline
test: add integration tests for post collection
```

**Format**: `<type>: <description>`

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Maintenance
- `perf` - Performance improvement

## Code Review Guidelines

### As a Reviewer

**Focus on**:
- Architecture and design
- Test coverage
- Performance implications
- Security concerns
- Code clarity and maintainability

**Be constructive**:
- Explain *why* when suggesting changes
- Ask questions rather than demand changes
- Acknowledge good work

**Example comments**:
- "Consider extracting this logic into a separate function for testability"
- "Could this cause a race condition if multiple requests arrive?"
- "Nice use of the repository pattern here!"

### As an Author

**Respond to all comments**:
- Either make the suggested change
- Or explain why you disagree (politely)

**Request clarification** if needed:
- "Could you elaborate on the performance concern?"

**Thank reviewers** for their time:
- "Good catch, fixed in the latest commit"

## Community Guidelines

- **Be respectful** - We're all here to learn and improve
- **Be patient** - Maintainers may not respond immediately
- **Be helpful** - Help other contributors when you can
- **Be open-minded** - Different approaches can be valid

## Questions?

- Check the [documentation](docs/)
- Open a [GitHub Discussion](https://github.com/yourusername/hackernews_digest/discussions)
- Create an [issue](https://github.com/yourusername/hackernews_digest/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to HN Pal!
