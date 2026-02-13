# Activity 1.5: RocksDB Content Storage

## Overview
Implement RocksDB-based storage for HTML, text, and Markdown content from crawled HackerNews posts. Eliminates filesystem fragmentation by storing content in an embedded key-value database with built-in compression, optimized for single-writer workloads.

## Prerequisites
- ✅ Activity 1.1: HN API polling system (provides post IDs)
- ✅ Activity 1.3: URL crawler and Markdown conversion (generates content to store)
- PostgreSQL database with posts table

## Objectives
1. Implement RocksDB storage for three content formats (HTML, text, markdown)
2. Eliminate filesystem overhead (no per-file inodes/blocks/metadata)
3. Leverage single-writer architecture (crawler process only)
4. Enable fast O(1) key-value access by HN ID
5. Use built-in compression (Zstandard) to minimize storage
6. Support simple backup and archival strategies

---

## Technical Details

### Storage Approach Analysis

#### Option 1: Individual Files (Current Baseline)
**Structure:**
```
data/content/{type}/{hn_id}.{ext}
```

**Pros:**
- Simple implementation
- Direct file access (no library needed)
- Easy manual inspection
- Familiar tooling (grep, cat, ls)
- Language-agnostic (any tool can read)

**Cons:**
- ❌ Filesystem overhead: 730K inodes for 10 years
- ❌ Block allocation waste: 4KB minimum per file (small files waste space)
- ❌ Directory performance: slows down at 100K+ files per directory
- ❌ Backup inefficiency: slow rsync with many small files
- ❌ No built-in compression
- ❌ Per-file metadata overhead (timestamps, permissions)

**Verdict:** Simple but wasteful at scale.

---

#### Option 2: SQLite Database
**Structure:**
```sql
CREATE TABLE content (hn_id INT PRIMARY KEY, html TEXT, text TEXT, markdown TEXT);
```

**Pros:**
- ✅ Single file storage
- ✅ SQL query interface
- ✅ Built-in full-text search (FTS5)
- ✅ ACID transactions
- ✅ Simple Python API (stdlib)
- ✅ No filesystem fragmentation

**Cons:**
- ❌ B-tree architecture (not optimized for write-heavy)
- ❌ Write locks (single writer bottleneck)
- ❌ VACUUM needed to reclaim space
- ❌ Large TEXT columns can bloat database
- ❌ Compression not built-in (need separate library)

**Verdict:** Good for small-medium scale, but B-tree overhead for writes.

---

#### Option 3: PostgreSQL TEXT Columns
**Structure:**
```sql
ALTER TABLE posts ADD COLUMN html TEXT, text_content TEXT, markdown TEXT;
```

**Pros:**
- ✅ Use existing infrastructure
- ✅ Single database for everything
- ✅ Full-text search with tsvector
- ✅ JSONB support for metadata

**Cons:**
- ❌ Mixes metadata with blob storage (different access patterns)
- ❌ Large TEXT fields cause TOAST overhead
- ❌ Bloats PostgreSQL (slower metadata queries)
- ❌ Backup complexity (large database files)
- ❌ No efficient compression for TEXT columns

**Verdict:** Architectural mixing of concerns; PostgreSQL best for structured data.

---

#### Option 4: RocksDB (Recommended)
**Structure:**
```
data/content.rocksdb/ (column families: html, text, markdown)
Key: hn_id (8-byte integer)
Value: content (bytes, compressed)
```

**Pros:**
- ✅ **LSM tree architecture** - optimized for write-heavy workloads (perfect for crawler)
- ✅ **Single writer optimized** - no write locks, sequential writes
- ✅ **Built-in compression** - Zstandard/LZ4 per column family (~70% space savings)
- ✅ **No filesystem fragmentation** - manages storage internally with SST files
- ✅ **Fast random reads** - bloom filters, block cache, prefix seek
- ✅ **Column families** - separate tuning for html/text/markdown
- ✅ **Automatic compaction** - background maintenance built-in
- ✅ **Simple backup** - copy directory or use backup API
- ✅ **No inode waste** - all data in ~10-20 SST files
- ✅ **Separation of concerns** - PostgreSQL for metadata, RocksDB for blobs

**Cons:**
- ❌ Requires `python-rocksdb` dependency (not stdlib)
- ❌ No SQL interface (key-value only)
- ❌ Manual inspection requires code (can't just `cat` files)
- ❌ Less familiar to developers (learning curve)
- ❌ No built-in full-text search (need separate index)
- ❌ Compaction can spike CPU (configurable)

**Verdict:** Best fit for single-writer, write-heavy blob storage with compression needs.

---

### Context-Specific Analysis

**Your Requirements:**
1. ✅ Single writer (crawler only) → **RocksDB LSM tree perfect**
2. ✅ ~200 posts/day (write-heavy) → **RocksDB optimized for sequential writes**
3. ✅ Read pattern: random access by `hn_id` → **RocksDB O(1) key lookup**
4. ✅ Storage efficiency matters → **RocksDB compression saves 70% space**
5. ✅ 730K posts over 10 years → **RocksDB handles millions easily**
6. ✅ Separate metadata (PostgreSQL) → **RocksDB keeps concerns separated**

**Trade-offs Accepted:**
- No manual file inspection → Worth it for compression/performance
- External dependency → `python-rocksdb` is stable, well-maintained
- No SQL → Don't need SQL for blob storage (metadata in PostgreSQL)

**Why Not Others:**
- **Files:** Too much filesystem overhead
- **SQLite:** B-tree not optimized for writes, no built-in compression
- **PostgreSQL:** Mixes metadata with blobs, TOAST overhead

---

### Scale Analysis

**Daily Volume:** ~200 posts/day
**Annual Volume:** ~73,000 posts/year
**10-Year Volume:** ~730,000 posts

**Storage per Post (uncompressed):**
- HTML: ~100 KB
- Text: ~20 KB
- Markdown: ~25 KB
- **Total: ~145 KB/post**

**With Zstandard Compression (~70% reduction):**
- HTML: ~30 KB
- Text: ~6 KB
- Markdown: ~8 KB
- **Total: ~44 KB/post**

**Storage Projections (compressed):**
| Timeframe | Posts   | Uncompressed | Compressed |
|-----------|---------|--------------|------------|
| 1 year    | 73,000  | ~10 GB       | ~3 GB      |
| 5 years   | 365,000 | ~50 GB       | ~15 GB     |
| 10 years  | 730,000 | ~100 GB      | ~30 GB     |

---

## RocksDB Architecture Design

### Storage Structure

**Three Column Families (for content types):**
```
data/content.rocksdb/
├── [default]    - metadata/bookkeeping
├── [html]       - HTML content column family
├── [text]       - extracted text column family
└── [markdown]   - markdown column family
```

**Physical Storage (SST files):**
```
data/content.rocksdb/
├── 000005.sst   - Level 0 SST file
├── 000012.sst   - Level 1 SST file
├── MANIFEST-000001
├── CURRENT
├── OPTIONS-000003
└── LOG
```

**Key-Value Schema:**
```
Column Family: html
  Key:   40000000 (8-byte big-endian integer)
  Value: <html><body>...</body></html> (compressed bytes)

Column Family: text
  Key:   40000000
  Value: "Article text content..." (compressed bytes)

Column Family: markdown
  Key:   40000000
  Value: "# Article Title\n\nContent..." (compressed bytes)
```

### Column Families Explained

**What are Column Families?**
- Isolated key-value namespaces within a single RocksDB instance
- Share the same WAL (Write-Ahead Log) but separate SST files
- Independent configuration (compression, compaction, bloom filters)

**Why Use Column Families?**
1. **Separate compression per type:**
   - HTML: Zstandard level 3 (high compression)
   - Text: LZ4 (fast decompression)
   - Markdown: Zstandard level 1 (balanced)

2. **Independent compaction schedules:**
   - HTML: rarely accessed → less aggressive compaction
   - Markdown: frequently accessed → more aggressive compaction

3. **Logical separation without overhead:**
   - Single database instance (shared resources)
   - No need for multiple RocksDB instances
   - Atomic writes across column families

---

## RocksDB Configuration

### Database-Level Options

```yaml
Database Path: data/content.rocksdb/

Options:
  # Creation
  create_if_missing: true
  create_missing_column_families: true

  # WAL (Write-Ahead Log)
  wal_dir: data/content.rocksdb/wal/
  wal_ttl_seconds: 3600  # Keep WAL for 1 hour
  wal_size_limit_mb: 1024  # 1GB max WAL size

  # Memory
  write_buffer_size: 64_MB  # Per column family memtable
  max_write_buffer_number: 3  # Allow 3 memtables before flush
  db_write_buffer_size: 256_MB  # Total memory for all CFs

  # Block Cache (for reads)
  block_cache_size: 512_MB  # LRU cache for hot data

  # Compaction
  max_background_jobs: 4  # Parallel compaction threads
  max_background_compactions: 2
  max_background_flushes: 2

  # File Management
  target_file_size_base: 64_MB  # Target SST file size
  max_bytes_for_level_base: 256_MB  # Level 1 size
  max_bytes_for_level_multiplier: 10  # Each level 10x bigger

  # Logging
  info_log_level: INFO
  max_log_file_size: 10_MB
  keep_log_file_num: 5
```

### Column Family: HTML

```yaml
Column Family: html

Purpose: Store raw HTML for re-processing

Compression:
  type: zstd  # Zstandard compression
  level: 3  # Medium compression (HTML compresses well)

Compaction:
  style: leveled  # LSM leveled compaction
  target_file_size_base: 64_MB

Bloom Filter:
  bits_per_key: 10  # Standard bloom filter
  block_based: true

Access Pattern: Cold (rare reads after initial crawl)
Expected Compression Ratio: ~75% (100KB → 25KB)
```

### Column Family: Text

```yaml
Column Family: text

Purpose: Extracted text content for search/indexing

Compression:
  type: lz4  # Fast decompression
  level: 1  # Low compression overhead

Compaction:
  style: leveled
  target_file_size_base: 32_MB  # Smaller files (text is smaller)

Bloom Filter:
  bits_per_key: 10

Access Pattern: Medium (occasional search index rebuilds)
Expected Compression Ratio: ~60% (20KB → 8KB)
```

### Column Family: Markdown

```yaml
Column Family: markdown

Purpose: Markdown for summarization (hot data)

Compression:
  type: zstd
  level: 1  # Light compression (faster decompression)

Compaction:
  style: leveled
  level0_file_num_compaction_trigger: 4  # Compact earlier (hot data)

Bloom Filter:
  bits_per_key: 10
  whole_key_filtering: true  # Optimize for Get() operations

Block Cache Priority: HIGH  # Keep in cache longer

Access Pattern: Hot (daily summarization reads)
Expected Compression Ratio: ~65% (25KB → 9KB)
```

### Performance Tuning

```yaml
Write Performance (Crawler):
  # Batch writes in groups of 100-1000 posts
  batch_size: 500

  # Disable WAL for non-critical writes (optional)
  disable_wal: false  # Keep enabled for durability

  # Allow memtable to grow before flush
  write_buffer_size: 64_MB

  Expected: 1000-5000 posts/sec on SSD

Read Performance (Summarization):
  # Block cache for hot data
  block_cache_size: 512_MB

  # Pin index/filter blocks in cache
  cache_index_and_filter_blocks: true
  pin_l0_filter_and_index_blocks_in_cache: true

  # Read-ahead for sequential scans
  compaction_readahead_size: 2_MB

  Expected: 10,000-50,000 reads/sec
```

### Compaction Strategy

```yaml
Leveled Compaction (Default):
  Level 0: 256 MB (memtable flushes)
  Level 1: 256 MB
  Level 2: 2.5 GB  (10x multiplier)
  Level 3: 25 GB
  Level 4: 250 GB

Compaction Triggers:
  level0_file_num_compaction_trigger: 4  # Start when 4 L0 files
  level0_slowdown_writes_trigger: 20  # Slow writes at 20 files
  level0_stop_writes_trigger: 36  # Stop writes at 36 files

Background Jobs:
  max_background_compactions: 2
  max_background_flushes: 2

Compaction Schedule:
  - Automatic: continuous background compaction
  - Manual: monthly full compaction (optimize command)
```

---

## Storage Layout Evolution

### Initial State (Year 1)
```
Total Posts: 73,000
Total Size: ~3 GB (compressed)

SST File Distribution:
  Level 0: 100 MB (active writes)
  Level 1: 200 MB
  Level 2: 1.5 GB
  Level 3: 1.2 GB

File Count: ~50 SST files
```

### After 5 Years
```
Total Posts: 365,000
Total Size: ~15 GB (compressed)

SST File Distribution:
  Level 0: 100 MB (active writes)
  Level 1: 256 MB
  Level 2: 2.5 GB
  Level 3: 12 GB

File Count: ~200 SST files
```

### After 10 Years
```
Total Posts: 730,000
Total Size: ~30 GB (compressed)

SST File Distribution:
  Level 0: 100 MB (active writes)
  Level 1: 256 MB
  Level 2: 2.5 GB
  Level 3: 25 GB
  Level 4: 2 GB

File Count: ~400 SST files
```

**Key Insight:** Even with 730K posts, RocksDB maintains ~400 SST files vs 2.19M individual files (730K × 3 formats)

---

## Implementation Overview

### Core Components

**1. RocksDBContentStore Class**
- Location: `backend/app/infrastructure/storage/rocksdb_store.py`
- Responsibility: Manage RocksDB connection and content operations
- Key Methods:
  - `save(hn_id, html, text, markdown)` - Store all three formats
  - `get_markdown(hn_id)` - Retrieve markdown for summarization
  - `get_content(hn_id, content_type)` - Retrieve specific format
  - `exists(hn_id, content_type)` - Check if content exists
  - `delete(hn_id)` - Remove all content for a post
  - `compact()` - Manual compaction trigger
  - `get_stats()` - Database statistics

**2. Key Design Decisions**

**Key Encoding:**
- Convert HN ID (integer) to 8-byte big-endian bytes
- Ensures sorted order in RocksDB
- Example: `40000000 → b'\x00\x00\x00\x00\x02b\\\xa0'`

**Value Encoding:**
- Store content as UTF-8 encoded bytes
- RocksDB handles compression transparently
- No application-level serialization needed

**Column Family Selection:**
```
hn_id → key (8 bytes big-endian)

html column family:
  key → compressed HTML bytes

text column family:
  key → compressed text bytes

markdown column family:
  key → compressed markdown bytes
```

### Integration Points

**1. Crawler Integration**
- Location: `backend/app/infrastructure/services/content_crawler.py`
- Update `EnhancedContentExtractor` to use `RocksDBContentStore`
- Replace filesystem writes with `storage.save(hn_id, html, text, markdown)`

**2. Summarization Pipeline**
- Location: Activity 2.x (future)
- Read markdown: `markdown = storage.get_markdown(hn_id)`
- No filesystem path needed, direct key-value access

**3. Database Coordination**
- PostgreSQL stores metadata (hn_id, title, url, score, timestamps)
- RocksDB stores content blobs (html, text, markdown)
- Use `hn_id` as the foreign key between systems

---

## Database Integration

**PostgreSQL stores metadata only:**

```sql
-- Existing posts table (no changes needed!)
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    hn_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL,
    title TEXT,
    url TEXT,
    score INTEGER,
    is_crawl_success BOOLEAN DEFAULT FALSE
);
```

**RocksDB stores content blobs:**
- HTML (for re-processing)
- Text (for search/indexing)
- Markdown (for summarization)

**Clean separation of concerns:**
- PostgreSQL: Structured metadata, relations, queries
- RocksDB: Blob storage, key-value access

---

## Optimization Strategy

### Regular Maintenance

**Monthly Compaction Script:**
- Purpose: Manually trigger full compaction to reclaim space and optimize reads
- Location: `scripts/optimize_rocksdb.py`
- Operations:
  - Compact all column families (html, text, markdown)
  - Print database statistics (key count, total size)
  - Log compaction results

**Cron Schedule:**
```bash
# Run monthly at 3am on the 1st
0 3 1 * * /path/to/scripts/optimize_rocksdb.py
```

### Archival Strategy (Optional)

**For data older than 2 years:**
- Create separate archive RocksDB instance: `data/archive_2023.rocksdb`
- Process:
  1. Query PostgreSQL for posts older than cutoff date
  2. Copy content from main RocksDB to archive RocksDB
  3. Delete from main RocksDB
  4. Compact main RocksDB to reclaim space

**Benefits:**
- Keeps main database lean (<3 years of data)
- Archive can be compressed/moved to cold storage
- Restore old content by opening archive database

---

## Backup Strategy

### Full Backup (Simple)
```bash
# RocksDB is just a directory - simple rsync/cp
rsync -av data/content.rocksdb/ backup/content.rocksdb/
tar -czf content.rocksdb.tar.gz data/content.rocksdb/
```

**Schedule:** Daily at 2am

### Incremental Backup (RocksDB Built-in API)
- Use RocksDB `BackupEngine` for efficient incremental backups
- Only copies new SST files since last backup
- Maintains backup history (keep last N backups)
- Fast restore to any backup point

**Backup Location:** `data/backups/`

**Restore Process:**
- Stop application
- Use `BackupEngine.restore_latest_backup()`
- Restart application

---

## Testing & Validation

### Unit Tests

**Location:** `tests/infrastructure/storage/test_rocksdb_store.py`

**Test Coverage:**
1. **test_save_and_retrieve**
   - Save all three content formats
   - Retrieve by HN ID and content type
   - Verify content matches

2. **test_exists**
   - Check existence before save (should be False)
   - Save content
   - Check existence after save (should be True)

3. **test_delete**
   - Save content
   - Delete by HN ID
   - Verify content is gone

4. **test_compression**
   - Save repetitive content (compresses well)
   - Check total SST file size
   - Verify compression ratio (~70% reduction)

**Test Fixture:**
- Use temporary RocksDB instance for each test
- Clean up after test completion

### Integration Tests

**Location:** `tests/integration/test_crawler_rocksdb.py`

**Test Scenario:**
1. Initialize crawler with RocksDB storage
2. Crawl a test URL
3. Verify all three formats stored in RocksDB
4. Verify content can be retrieved

---

## Performance Benchmarks

### Write Performance

**Benchmark:** Write 10,000 posts sequentially
- Content size: ~150KB per post (html + text + markdown)
- Batch size: 500 posts
- Expected throughput: **1,000-5,000 posts/sec** on SSD

**Factors:**
- SSD vs HDD: 10x difference
- Compression level: Higher = slower writes
- WAL sync: Enabled = slower but safer

### Read Performance

**Benchmark:** Random reads of 10,000 posts
- Access pattern: Random HN ID selection
- Operation: Get markdown only
- Expected throughput: **10,000-50,000 reads/sec**

**Factors:**
- Block cache hit rate: 90%+ with 512MB cache
- Bloom filters: Skip unnecessary SST file reads
- Compression: Slight overhead on decompression

---

## Acceptance Criteria

- [ ] `python-rocksdb` installed and tested
- [ ] `RocksDBContentStore` class implemented with column families
- [ ] Crawler integrated with RocksDB storage
- [ ] Unit tests passing (>95% coverage)
- [ ] Integration tests with crawler passing
- [ ] Compression enabled and verified (Zstandard)
- [ ] Performance benchmarks documented
- [ ] Backup strategy tested
- [ ] Optimization script created (compaction)
- [ ] Documentation updated with RocksDB approach

---

## Related Activities

**Upstream Dependencies:**
- ✅ Activity 1.1: HN API polling (provides post IDs)
- ✅ Activity 1.3: URL crawler (generates content to store)

**Downstream Dependencies:**
- Activity 2.1: Summarization prompt template (reads markdown from RocksDB)
- Activity 2.2: Claude API integration (uses `store.get_markdown()`)

---

## Notes & Assumptions

### Design Decisions

**Why RocksDB over SQLite?**
- Optimized for write-heavy workloads (LSM tree vs B-tree)
- Better compression (column family level)
- No SQL overhead (pure key-value)
- Single-writer is natural fit

**Why RocksDB over PostgreSQL TEXT columns?**
- Separates blob storage from structured metadata
- Better compression for large text fields
- No TOAST overhead
- Keeps PostgreSQL lean and fast

**Why Column Families?**
- Separate compression settings per content type
- Logical separation without multiple databases
- Independent tuning (e.g., markdown accessed more often)

### Future Considerations

**If you need full-text search:**
- Add separate search index (Tantivy, Meilisearch)
- RocksDB remains storage layer
- Search index rebuilt from RocksDB on demand

**If you migrate to cloud:**
- RocksDB works on EBS/persistent disks
- Backup to S3 via simple tar/rsync
- No changes to application code

**If you need multi-reader:**
- RocksDB supports multiple read-only processes
- Only crawler writes, all others read
- No locking needed

---

## Migration from Flat Files

**Script Location:** `scripts/migrate_to_rocksdb.py`

**Migration Process:**
1. Scan existing flat file structure:
   - `data/content/html/*.html`
   - `data/content/text/*.txt`
   - `data/content/markdown/*.md`

2. For each HN ID:
   - Read all three content formats
   - Save to RocksDB using `store.save(hn_id, html, text, markdown)`
   - Log progress

3. Post-migration:
   - Compact RocksDB to optimize storage
   - Verify migration completeness (count files vs RocksDB keys)
   - Backup old flat files before deletion

**Estimated Time:**
- ~1,000 posts/sec migration speed
- 100K posts = ~2 minutes
- Compaction = ~1 minute

**Rollback Plan:**
- Keep flat files until verification complete
- Can regenerate RocksDB from flat files if needed

---

## Implementation Checklist

- [ ] Install `python-rocksdb` dependency
- [ ] Create `backend/app/infrastructure/storage/rocksdb_store.py`
- [ ] Implement `RocksDBContentStore` class
- [ ] Add unit tests in `tests/infrastructure/storage/test_rocksdb_store.py`
- [ ] Update crawler to use RocksDB
- [ ] Write integration tests
- [ ] Create migration script for existing files
- [ ] Test migration on sample data
- [ ] Create optimization script
- [ ] Document backup procedures
- [ ] Run performance benchmarks
- [ ] Update project README

---

**Estimated Effort:** 4-6 hours
**Priority:** High (eliminates filesystem overhead)
**Status:** Ready to implement

---

**Last Updated:** 2025-02-12
