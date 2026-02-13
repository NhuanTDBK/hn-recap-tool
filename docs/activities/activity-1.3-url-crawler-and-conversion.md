# Activity 1.3: URL crawler and HTML to Markdown conversion

**Phase**: 1 - Ingest Pipeline
**Status**: ✅ Completed (Crawler) / 🔄 To Implement (Markdown conversion)
**Owner**: Engineering Team
**Estimated Effort**: Crawler done, Markdown: 1-2 days

---

## Overview

Fetches HTML content from HackerNews post URLs, extracts clean text using trafilatura, and converts HTML to Markdown using the markitdown library. All content (HTML, extracted text, Markdown) is stored in the filesystem for downstream processing.

**Current State:**
- ✅ **URL Crawler**: Fully implemented with `EnhancedContentExtractor`
- 🔄 **Markdown Conversion**: Need to integrate markitdown library

---

## Prerequisites

### Upstream Dependencies
- [x] **Activity 1.1**: HN API polling (provides posts with URLs)
- [x] Filtered posts with external URLs and score > 100

### Required Libraries
- [x] `httpx` - Async HTTP client
- [x] `trafilatura` - Content extraction
- [ ] `markitdown` - HTML to Markdown conversion
- [x] `asyncio` - Concurrent processing

---

## Objectives

1. ✅ **Fetch HTML**: Download HTML from external URLs
2. ✅ **Extract Text**: Extract clean article text with trafilatura
3. 🔄 **Convert to Markdown**: Use markitdown to convert HTML → Markdown
4. ✅ **File Storage**: Save HTML, text, and markdown to filesystem
5. ✅ **Rate Limiting**: Respect server limits with delays
6. ✅ **Error Handling**: Retry logic for transient failures
7. ✅ **Status Tracking**: Track crawl results

---

## Implementation Flow

### Overall Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│ INPUT: Filtered Posts (20-30 posts)                    │
│ • Has external URL                                      │
│ • Score > 100                                           │
│ • Not already crawled                                   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Fetch HTML                                      │
│                                                          │
│ EnhancedContentExtractor.extract_content(url)           │
│ • Check robots.txt                                      │
│ • Rotate user agents                                    │
│ • Retry on failures (max 3)                             │
│ • Follow redirects                                      │
│                                                          │
│ Returns: (success, html_content, extracted_text)        │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Save HTML                                       │
│                                                          │
│ File: data/content/html/{hn_id}.html                    │
│                                                          │
│ Raw HTML from source (for re-processing if needed)      │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Save Extracted Text                             │
│                                                          │
│ File: data/content/text/{hn_id}.txt                     │
│                                                          │
│ Clean text extracted by trafilatura (no HTML tags)      │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Convert HTML → Markdown (NEW)                   │
│                                                          │
│ Use markitdown library:                                 │
│ • Read HTML from file                                   │
│ • Convert to Markdown format                            │
│ • Preserve headings, links, lists, code blocks         │
│ • Clean formatting                                      │
│                                                          │
│ markdown_content = markitdown.convert(html_content)     │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 5: Save Markdown                                   │
│                                                          │
│ File: data/content/markdown/{hn_id}.md                  │
│                                                          │
│ Markdown format (readable, AI-friendly for summaries)   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 6: Update Database                                 │
│                                                          │
│ UPDATE posts SET                                         │
│   is_crawl_success = true,                              │
│   crawl_retry_count = 0,                                │
│   crawled_at = NOW(),                                   │
│   crawl_error = NULL,                                   │
│   content_length = 5420                                 │
│ WHERE hn_id = 12345;                                    │
│                                                          │
│ Prevents re-crawling same post (no recursive loops)     │
└─────────────────────────────────────────────────────────┘
```

---

## Storage Structure

### File Storage
```
data/
└── content/
    ├── html/
    │   ├── 12345.html      # Raw HTML from URL
    │   ├── 12346.html
    │   └── ...
    ├── text/
    │   ├── 12345.txt       # Clean text (trafilatura)
    │   ├── 12346.txt
    │   └── ...
    └── markdown/           # Markdown files
        ├── 12345.md
        ├── 12346.md
        └── ...
```

**File Naming Convention:**
- Use `hn_id` as filename
- Example: Post with hn_id=39301285 → `39301285.html`, `39301285.txt`, `39301285.md`

### Database Tracking (PostgreSQL)

**Crawl status tracked in posts table:**
```sql
-- Update posts table to track crawl status
UPDATE posts SET
  html_content = '/path/to/12345.html',      -- or store inline
  markdown_content = '/path/to/12345.md',    -- or store inline
  crawled_at = NOW(),
  is_crawl_success = true,                   -- Success flag
  crawl_retry_count = 0,                     -- Number of retry attempts
  crawl_error = NULL,
  content_length = 5420
WHERE hn_id = 12345;
```

**Crawl Logic with Retry Tracking:**
- `is_crawl_success = true` → Skip, already crawled successfully
- `is_crawl_success = false AND retry_count < MAX_RETRIES` → Retry crawl
- `is_crawl_success = false AND retry_count >= MAX_RETRIES` → Skip, permanent failure

**Alternative: Separate crawl_logs table:**
```sql
CREATE TABLE crawl_logs (
  id UUID PRIMARY KEY,
  post_id UUID REFERENCES posts(id),
  hn_id INT,
  url TEXT,
  is_success BOOLEAN,                        -- Success flag
  retry_count INT DEFAULT 0,                 -- Retry attempts
  has_html BOOLEAN,
  has_text BOOLEAN,
  has_markdown BOOLEAN,
  content_length INT,
  error_message TEXT,
  crawled_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Benefits of Database Tracking:**
- Query crawl statistics easily
- Track retry attempts per post (avoid infinite loops)
- Identify failed URLs for re-crawling
- Skip successfully crawled posts (no recursive loops)
- Analytics on success rates by domain
- Transactional integrity with post records

**Retry Logic:**
1. Check `is_crawl_success` before crawling
   - If `true` → Skip (already successful)
   - If `false` or `NULL` → Check retry count
2. Check `retry_count < MAX_RETRIES` (e.g., 3)
   - If under limit → Attempt crawl, increment retry_count
   - If at/over limit → Skip, mark as permanent failure
3. On successful crawl → Set `is_crawl_success = true`, reset retry_count
4. On failed crawl → Increment retry_count, log error

---

## Markdown Conversion with markitdown

### Why markitdown?
- Preserves document structure (headings, lists, links)
- Better for LLM processing than plain text
- Maintains code blocks and formatting
- More readable than HTML for humans

### Conversion Process
1. Read HTML content from file or memory
2. Pass to markitdown library
3. Get structured Markdown output
4. Save to file: `data/content/markdown/{hn_id}.md`

---

## Enhanced Crawl Flow

### Complete Pipeline
1. **Fetch HTML** - EnhancedContentExtractor downloads URL
2. **Extract Text** - Trafilatura cleans HTML → plain text
3. **Convert Markdown** - markitdown converts HTML → Markdown
4. **Save Files** - Write all three formats to disk
5. **Update Database** - Record crawl status in PostgreSQL

### Directory Management
- Create `html/`, `text/`, `markdown/` directories on initialization
- Ensure directories exist before writing files
- Use `hn_id` as consistent filename across formats

---

## Key Features

### 1. Concurrent Crawling
- Semaphore limits concurrent requests (default: 3)
- Processes multiple URLs in parallel
- Batch of 20 URLs: ~60-90 seconds

### 2. Robust HTTP Fetching
- User-agent rotation (11 realistic agents)
- Retry logic (max 3 attempts)
- Handles 403/404/429 errors gracefully
- Respects robots.txt

### 3. Multiple Output Formats
- **HTML**: Raw source (for debugging/re-processing)
- **Text**: Clean extracted text (trafilatura)
- **Markdown**: Structured format (markitdown) - best for LLM summarization

### 4. Rate Limiting
- Random delays: 1-3 seconds between requests
- Prevents server overload
- Ethical crawling

---

## Configuration

```python
# Crawler settings
output_dir: str = "data/content"
max_concurrent: int = 3

# Extractor settings
timeout: int = 30
max_retries: int = 3
min_delay: float = 1.0
max_delay: float = 3.0
respect_robots_txt: bool = True
```

---

## Testing & Validation

### Manual Testing

**Test Crawl Pipeline:**
- Run crawler on sample posts
- Verify HTML files created in `data/content/html/`
- Verify text files created in `data/content/text/`
- Verify markdown files created in `data/content/markdown/`
- Check database for crawl status records

**Verify Markdown Quality:**
- Open markdown file and check readability
- Verify headings preserved
- Verify links maintained
- Verify code blocks formatted correctly

### Validation Checklist

- [x] HTML fetched and saved to `data/content/html/`
- [x] Text extracted and saved to `data/content/text/`
- [ ] Markdown converted and saved to `data/content/markdown/`
- [ ] Markdown preserves headings, links, lists
- [ ] Markdown is readable and well-formatted
- [x] Concurrent crawling works with semaphore
- [ ] Database tracks crawl status (not JSONL file)
- [ ] Can query successful/failed crawls from database

---

## Acceptance Criteria

- [x] Fetches HTML from external URLs
- [x] Saves HTML files to `data/content/html/{hn_id}.html`
- [x] Extracts clean text with trafilatura
- [x] Saves text files to `data/content/text/{hn_id}.txt`
- [ ] Converts HTML to Markdown using markitdown
- [ ] Saves Markdown files to `data/content/markdown/{hn_id}.md`
- [ ] Markdown format is clean and structured
- [x] Concurrent crawling with rate limiting works
- [x] Error handling and retry logic functional
- [ ] Crawl status stored in PostgreSQL database
- [ ] Database schema includes crawl tracking fields

---

## Performance Characteristics

**Crawl Speed:**
- 3 concurrent requests
- ~3-5 seconds per URL (fetch + extract + convert)
- Batch of 20 URLs: 60-90 seconds

**File Sizes (typical):**
- HTML: 50-500 KB
- Text: 10-100 KB
- Markdown: 15-120 KB

**Success Rate:**
- 80-90% success rate
- Failures: timeouts, 403/404, paywalls

---

## Migration to Spec (Future)

According to spec.md, production should use:
- **S3 Storage**: `s3://hn-pal/html/{hn_id}.html` and `s3://hn-pal/md/{hn_id}.md`
- **Database References**: Store S3 keys in PostgreSQL

Current filesystem approach works for MVP. Migration to S3 in Phase 3.

---

## Related Activities

**Upstream:**
- ✅ **Activity 1.1**: HN API polling

**Downstream:**
- 🔄 **Activity 2.1**: Summarization (uses markdown files)

**Related Files:**
- `backend/app/application/use_cases/crawl_content.py`
- `backend/app/infrastructure/services/enhanced_content_extractor.py`
- `scripts/crawl_content.py`

---

## Notes & Assumptions

**Why Three Formats?**
1. **HTML**: Source of truth, allows re-processing
2. **Text**: Clean extraction, good for search/indexing
3. **Markdown**: Best for LLM summarization (structured, readable)

**Why markitdown?**
- Better structure preservation than plain text
- More readable than HTML
- LLM-friendly format for summarization
- Maintains links, headings, code blocks

**Future Enhancements:**
- Migrate to S3 storage (per spec)
- Add quality scoring for extraction
- Handle JavaScript-heavy sites with Playwright
