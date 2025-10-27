# HackerNews Digest Tool

A clean architecture application for collecting, processing, and summarizing HackerNews articles with AI-powered summaries delivered to Telegram.

## Features

- 📰 **Collect HackerNews Posts**: Fetch top stories from HackerNews API
- 🔍 **Content Extraction**: Extract article content from external URLs
- 🤖 **AI Summarization**: Generate concise summaries using OpenAI
- 📱 **Telegram Delivery**: Send summaries with clickable links to Telegram channel
- 🏗️ **Clean Architecture**: Follows domain-driven design with clear separation of concerns

## Architecture

The project follows clean architecture principles:

```
backend/
├── app/
│   ├── domain/           # Business entities (Post, User, Digest)
│   ├── application/      # Use cases and interfaces
│   ├── infrastructure/   # External adapters (repos, services)
│   └── presentation/     # API endpoints and schemas
├── data/
│   ├── raw/             # Raw HackerNews posts (JSONL)
│   ├── content/         # Extracted article content
│   │   ├── text/        # Plain text content
│   │   └── html/        # Raw HTML content
│   └── processed/       # Generated summaries
└── scripts/             # Automation scripts
```

## Setup

### Prerequisites

- Python 3.11+
- OpenAI API key
- Telegram Bot token and channel ID

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hackernews_digest
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add:
# - OPENAI_API_KEY
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHANNEL_ID
```

## Usage

### 1. Collect HackerNews Posts

Fetch and store posts from HackerNews:

```bash
python scripts/fetch_hn_posts.py
```

### 2. Extract Article Content

Crawl and extract content from article URLs:

```bash
python scripts/crawl_content.py
```

### 3. Generate Summaries

Summarize articles using AI:

```bash
# Summarize today's articles
python scripts/run_summarization.py

# Summarize specific date range
python scripts/run_summarization.py --start_time 2025-10-25 --end_time 2025-10-27
```

### 4. Push to Telegram

Send summaries to your Telegram channel:

```bash
# Send latest summaries
python scripts/push_to_telegram.py

# Send specific JSONL file
python scripts/push_to_telegram.py --jsonl data/processed/summaries/2025-10-27-summaries.jsonl
```

## Repository Pattern

The application uses repository pattern for data access:

- **PostRepository**: Manages HackerNews posts (date-partitioned JSONL files)
- **ContentRepository**: Manages article content (text and HTML files)
- **DigestRepository**: Manages daily digests
- **UserRepository**: Manages user data

### Example Usage

```python
from backend.app.infrastructure.repositories.jsonl_post_repo import JSONLPostRepository
from backend.app.infrastructure.repositories.jsonl_content_repo import JSONLContentRepository

# Initialize repositories
post_repo = JSONLPostRepository("data")
content_repo = JSONLContentRepository("data")

# Load posts by date
posts = await post_repo.find_by_date("2025-10-27")

# Load content for a post
content = await content_repo.get_text_content(post.hn_id)
```

## Telegram Message Format

Each summary is sent as a separate message with:

```
*Article Title*
[HN Discussion](https://news.ycombinator.com/item?id=12345678)

AI-generated summary text...

[Read Article](https://example.com/article)
```

## Project Structure

### Domain Layer
- `Post`, `User`, `Digest`, `Comment` entities
- Business logic and validation

### Application Layer
- Repository interfaces
- Service interfaces (ContentExtractor, SummarizationService, etc.)
- Use cases (collection, summarization, synthesis)

### Infrastructure Layer
- JSONL repository implementations
- OpenAI integration
- HackerNews API client
- Content extraction services
- Telegram notification service

### Presentation Layer
- FastAPI endpoints
- Request/response schemas
- API dependencies

## Development

### Running the API Server

```bash
cd backend
uvicorn app.main:app --reload
```

### Running Tests

```bash
pytest backend/tests/
```

## License

MIT
