# Database Design

## Overview

The database is the central persistence layer for the NewsAnalysis system, storing collected articles, classifications, summaries, and pipeline state. This document outlines the schema design, indexing strategy, and database technology selection optimized for local deployment.

## Database Technology Selection

### SQLite vs PostgreSQL Decision Matrix

| Criteria | SQLite | PostgreSQL | Recommendation |
|----------|--------|------------|----------------|
| **Setup Complexity** | Zero config | Requires installation/config | SQLite for MVP |
| **Concurrency** | Single writer | Multiple concurrent writers | SQLite adequate for local |
| **Dataset Size** | <100K articles optimal | Unlimited | SQLite for <100K articles |
| **Query Performance** | Excellent for reads | Better for complex queries | SQLite sufficient |
| **Full-Text Search** | FTS5 built-in | pg_trgm, pg_search | SQLite FTS5 excellent |
| **Backup** | Single file copy | pg_dump required | SQLite simpler |
| **Deployment** | Embedded (no server) | Requires server process | SQLite for local deployment |
| **Scalability** | Limited (single server) | Horizontal scaling | PostgreSQL when >100K articles |

### **Recommendation: Start with SQLite**

**Why SQLite**:
- Zero configuration (embedded database)
- Perfect for local deployment (<100K articles)
- Excellent full-text search with FTS5
- Simple backups (single file)
- ACID compliant and reliable
- Low operational overhead

**Migration Path to PostgreSQL**:
Migrate when ANY of these conditions met:
- Dataset exceeds 100K articles
- Need >10 concurrent users
- Require distributed deployment
- Hit performance bottlenecks with complex queries

**Migration Strategy**:
- Use SQLAlchemy ORM for database-agnostic code
- Abstract all queries through repository layer
- Test migration with sample data before production
- Maintain schema compatibility during transition

## Core Schema Design

### Table: `articles`

Primary table storing all article data across pipeline stages.

```sql
CREATE TABLE articles (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- URL Identification (for deduplication)
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    url_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hash for fast lookups

    -- Article Metadata
    title TEXT NOT NULL,
    source TEXT NOT NULL,  -- Feed name (e.g., "NZZ", "FINMA")
    published_at TIMESTAMP,
    collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Feed Configuration
    feed_priority INTEGER NOT NULL,  -- 1=govt, 2=financial, 3=general

    -- Classification Results (Step 2)
    is_match BOOLEAN,
    confidence REAL,  -- 0.0-1.0
    topic TEXT,
    classification_reason TEXT,
    filtered_at TIMESTAMP,

    -- Scraped Content (Step 3)
    content TEXT,
    author TEXT,
    content_length INTEGER,
    extraction_method TEXT,  -- "trafilatura", "playwright", "json_ld"
    extraction_quality REAL,  -- 0.0-1.0
    scraped_at TIMESTAMP,

    -- Summary (Step 4)
    summary_title TEXT,
    summary TEXT,
    key_points TEXT,  -- JSON array
    entities TEXT,  -- JSON object: {companies, people, locations, topics}
    summarized_at TIMESTAMP,

    -- Pipeline State
    pipeline_stage TEXT NOT NULL DEFAULT 'collected',
        -- collected → filtered → scraped → summarized → digested
    processing_status TEXT DEFAULT 'pending',
        -- pending, processing, completed, failed

    -- Digest Assignment (Step 5)
    digest_date DATE,
    digest_version INTEGER,
    included_in_digest BOOLEAN DEFAULT FALSE,

    -- Error Tracking
    error_message TEXT,
    error_count INTEGER DEFAULT 0,

    -- Run Tracking
    run_id TEXT NOT NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE UNIQUE INDEX idx_articles_url_hash ON articles(url_hash);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_pipeline_stage ON articles(pipeline_stage);
CREATE INDEX idx_articles_is_match ON articles(is_match);
CREATE INDEX idx_articles_digest_date ON articles(digest_date);
CREATE INDEX idx_articles_run_id ON articles(run_id);

-- Full-Text Search
CREATE VIRTUAL TABLE articles_fts USING fts5(
    title,
    summary,
    content='articles',
    content_rowid='id'
);

-- Trigger to keep FTS index updated
CREATE TRIGGER articles_fts_insert AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, new.title, new.summary);
END;

CREATE TRIGGER articles_fts_update AFTER UPDATE ON articles BEGIN
    UPDATE articles_fts
    SET title = new.title, summary = new.summary
    WHERE rowid = new.id;
END;

CREATE TRIGGER articles_fts_delete AFTER DELETE ON articles BEGIN
    DELETE FROM articles_fts WHERE rowid = old.id;
END;
```

### Table: `processed_links`

Cache table for fast URL deduplication across runs.

```sql
CREATE TABLE processed_links (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- URL Identification
    url_hash TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,

    -- Processing Results
    is_match BOOLEAN,
    confidence REAL,
    topic TEXT,
    reason TEXT,

    -- Timestamps
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional TTL for cache invalidation

    -- Run Tracking
    run_id TEXT NOT NULL
);

CREATE INDEX idx_processed_links_url_hash ON processed_links(url_hash);
CREATE INDEX idx_processed_links_processed_at ON processed_links(processed_at);
CREATE INDEX idx_processed_links_expires_at ON processed_links(expires_at);
```

### Table: `pipeline_runs`

Track pipeline execution history for debugging and analytics.

```sql
CREATE TABLE pipeline_runs (
    -- Primary Key
    run_id TEXT PRIMARY KEY,

    -- Run Configuration
    mode TEXT NOT NULL,  -- "full", "express", "export"
    config_snapshot TEXT,  -- JSON snapshot of config at run time

    -- Execution Tracking
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'running',
        -- running, completed, failed, cancelled

    -- Statistics
    collected_count INTEGER DEFAULT 0,
    filtered_count INTEGER DEFAULT 0,
    scraped_count INTEGER DEFAULT 0,
    summarized_count INTEGER DEFAULT 0,
    digested_count INTEGER DEFAULT 0,

    -- Error Tracking
    error_message TEXT,
    error_stage TEXT,

    -- Performance Metrics
    duration_seconds REAL,

    -- Cost Tracking
    total_cost REAL DEFAULT 0.0,
    total_tokens INTEGER DEFAULT 0
);

CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
```

### Table: `api_calls`

Track all OpenAI API calls for cost monitoring and debugging.

```sql
CREATE TABLE api_calls (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Call Identification
    run_id TEXT NOT NULL,
    module TEXT NOT NULL,  -- "filter", "summarizer", "digest_generator"
    model TEXT NOT NULL,  -- "gpt-5-nano", "gpt-4o-mini"

    -- Request Details
    request_type TEXT,  -- "classification", "summarization", "meta_analysis"
    batch_id TEXT,  -- For batch API requests

    -- Token Usage
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,

    -- Cost
    cost REAL NOT NULL,

    -- Response
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_api_calls_run_id ON api_calls(run_id);
CREATE INDEX idx_api_calls_module ON api_calls(module);
CREATE INDEX idx_api_calls_created_at ON api_calls(created_at);
CREATE INDEX idx_api_calls_batch_id ON api_calls(batch_id);
```

### Table: `digests`

Store daily digest metadata and outputs.

```sql
CREATE TABLE digests (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Digest Identification
    digest_date DATE NOT NULL,
    version INTEGER NOT NULL,

    -- Content
    articles_json TEXT NOT NULL,  -- JSON array of article IDs
    meta_analysis_json TEXT NOT NULL,  -- JSON object

    -- Outputs
    json_output TEXT,  -- Full JSON digest
    markdown_output TEXT,  -- Markdown report
    german_report TEXT,  -- Bonitäts-Tagesanalyse

    -- Statistics
    article_count INTEGER NOT NULL,
    cluster_count INTEGER,  -- After deduplication

    -- Timestamps
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Run Tracking
    run_id TEXT NOT NULL,

    UNIQUE(digest_date, version)
);

CREATE INDEX idx_digests_date ON digests(digest_date);
CREATE INDEX idx_digests_run_id ON digests(run_id);
```

### Table: `article_clusters`

Track article deduplication (which articles are duplicates).

```sql
CREATE TABLE article_clusters (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Cluster Identification
    cluster_id TEXT NOT NULL,
    digest_date DATE NOT NULL,

    -- Primary Article (chosen from cluster)
    primary_article_id INTEGER NOT NULL,

    -- Duplicate Articles
    duplicate_article_ids TEXT NOT NULL,  -- JSON array of article IDs

    -- Similarity Metadata
    similarity_method TEXT,  -- "gpt_based", "embedding_based"
    average_similarity REAL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (primary_article_id) REFERENCES articles(id)
);

CREATE INDEX idx_article_clusters_digest_date ON article_clusters(digest_date);
CREATE INDEX idx_article_clusters_primary_article_id ON article_clusters(primary_article_id);
```

## Query Patterns & Optimization

### Common Queries

**1. Get Unprocessed Articles for Stage**
```sql
-- Get articles ready for filtering
SELECT id, url, title, source, published_at, feed_priority
FROM articles
WHERE pipeline_stage = 'collected'
  AND processing_status = 'pending'
  AND run_id = ?
ORDER BY feed_priority ASC, published_at DESC
LIMIT 100;
```

**2. Check URL Cache (Deduplication)**
```sql
-- Check if URL already processed (within 7 days)
SELECT is_match, confidence, topic, reason
FROM processed_links
WHERE url_hash = ?
  AND processed_at > datetime('now', '-7 days')
LIMIT 1;
```

**3. Get Daily Digest Articles**
```sql
-- Get all articles for today's digest
SELECT *
FROM articles
WHERE digest_date = ?
  AND included_in_digest = TRUE
  AND pipeline_stage = 'summarized'
ORDER BY feed_priority ASC, confidence DESC, published_at DESC;
```

**4. Full-Text Search**
```sql
-- Search articles by keyword
SELECT articles.*, articles_fts.rank
FROM articles
JOIN articles_fts ON articles.id = articles_fts.rowid
WHERE articles_fts MATCH ?  -- e.g., "Konkurs OR Insolvenz"
ORDER BY rank
LIMIT 50;
```

**5. Cost Analytics**
```sql
-- Daily cost breakdown by module
SELECT
    DATE(created_at) as date,
    module,
    model,
    COUNT(*) as call_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost) as total_cost
FROM api_calls
WHERE created_at > datetime('now', '-30 days')
GROUP BY DATE(created_at), module, model
ORDER BY date DESC, total_cost DESC;
```

**6. Pipeline Statistics**
```sql
-- Run statistics with conversion funnel
SELECT
    run_id,
    started_at,
    status,
    collected_count,
    filtered_count,
    scraped_count,
    summarized_count,
    digested_count,
    ROUND(filtered_count * 100.0 / collected_count, 1) as filter_rate,
    ROUND(scraped_count * 100.0 / filtered_count, 1) as scrape_success_rate,
    total_cost,
    duration_seconds
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Indexing Strategy

**Principles**:
1. Index foreign keys for JOIN performance
2. Index filter columns (WHERE, GROUP BY)
3. Index sort columns (ORDER BY)
4. Avoid over-indexing (each index has write cost)

**Critical Indexes**:
- `url_hash`: Unique index for fast deduplication (most frequent query)
- `pipeline_stage + processing_status`: Composite index for stage queries
- `digest_date + included_in_digest`: For digest assembly
- `run_id`: Track articles by pipeline run
- `published_at`: Time-based queries and sorting

**FTS5 Full-Text Search**:
- Enables fast keyword search across title and summary
- ~10x faster than LIKE queries for text search
- Essential for manual article lookup

## Database Configuration

### SQLite Optimization Settings

```python
import sqlite3

def init_database(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)

    # Enable WAL mode for concurrent reads during writes
    conn.execute("PRAGMA journal_mode=WAL")

    # Increase cache size (10MB)
    conn.execute("PRAGMA cache_size=-10000")

    # Foreign key enforcement
    conn.execute("PRAGMA foreign_keys=ON")

    # Synchronous mode (NORMAL balances safety and performance)
    conn.execute("PRAGMA synchronous=NORMAL")

    # Temp store in memory
    conn.execute("PRAGMA temp_store=MEMORY")

    # Increase mmap size for better read performance (256MB)
    conn.execute("PRAGMA mmap_size=268435456")

    return conn
```

### Connection Pooling

```python
from contextlib import contextmanager

class DatabasePool:
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool = queue.Queue(maxsize=pool_size)

        # Pre-create connections
        for _ in range(pool_size):
            conn = init_database(db_path)
            self.pool.put(conn)

    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.put(conn)
```

## Data Retention Policies

### Tiered Retention by Source Priority

**Tier 1 (Government Sources)**: 365 days
- FINMA, SNB, SECO, BFS
- Rationale: Regulatory changes have long-term impact

**Tier 2 (Financial Sources)**: 90 days
- Handelszeitung, FineNews, Cash
- Rationale: Financial news relevant for quarter

**Tier 3 (General Sources)**: 30 days
- NZZ, SRF, Tages-Anzeiger
- Rationale: General news quickly becomes stale

### Retention Implementation

```sql
-- Delete old articles based on retention policy
DELETE FROM articles
WHERE feed_priority = 3  -- General news
  AND published_at < datetime('now', '-30 days');

DELETE FROM articles
WHERE feed_priority = 2  -- Financial news
  AND published_at < datetime('now', '-90 days');

DELETE FROM articles
WHERE feed_priority = 1  -- Government news
  AND published_at < datetime('now', '-365 days');

-- Clean up orphaned FTS entries
DELETE FROM articles_fts WHERE rowid NOT IN (SELECT id FROM articles);

-- Clean up old processed_links cache (7-day TTL)
DELETE FROM processed_links
WHERE processed_at < datetime('now', '-7 days');

-- Archive old pipeline runs (keep 90 days)
DELETE FROM pipeline_runs
WHERE started_at < datetime('now', '-90 days');

-- Archive old API call logs (keep 30 days for cost analysis)
DELETE FROM api_calls
WHERE created_at < datetime('now', '-30 days');
```

### Vacuum and Maintenance

```python
def vacuum_database(conn: sqlite3.Connection):
    """Reclaim space and optimize database"""
    # Full vacuum (blocking operation, run during off-hours)
    conn.execute("VACUUM")

    # Analyze tables for query planner
    conn.execute("ANALYZE")

    # Optimize FTS index
    conn.execute("INSERT INTO articles_fts(articles_fts) VALUES('optimize')")

# Schedule: Run weekly during low-traffic hours
```

## Backup Strategy

### Local File Backup

```python
import shutil
from datetime import datetime

def backup_database(db_path: str, backup_dir: str):
    """Create timestamped database backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/news_db_backup_{timestamp}.db"

    # Close all connections before backup
    # Copy database file
    shutil.copy2(db_path, backup_path)

    # Optional: Compress backup
    import gzip
    with open(backup_path, 'rb') as f_in:
        with gzip.open(f"{backup_path}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.remove(backup_path)  # Remove uncompressed

    return f"{backup_path}.gz"

# Schedule: Daily backups, keep last 7 days
```

### Incremental Backup (WAL)

```python
def backup_wal_file(db_path: str, backup_dir: str):
    """Backup WAL file for point-in-time recovery"""
    wal_path = f"{db_path}-wal"

    if os.path.exists(wal_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{backup_dir}/news_db_wal_{timestamp}"
        shutil.copy2(wal_path, backup_path)
        return backup_path

    return None

# Schedule: Hourly WAL backups during active processing
```

## Migration to PostgreSQL

### When to Migrate

**Triggers**:
- Dataset exceeds 100K articles
- Concurrent users >10
- Write performance bottlenecks
- Need distributed deployment
- Complex analytical queries slow

### Migration Process

**1. Schema Translation**
```sql
-- PostgreSQL schema equivalent
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    url_hash VARCHAR(64) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    published_at TIMESTAMP,
    collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ... (rest of columns same)

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- PostgreSQL-specific indexes
CREATE INDEX idx_articles_url_hash ON articles USING hash(url_hash);
CREATE INDEX idx_articles_published_at ON articles USING btree(published_at DESC);

-- Full-text search with pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_articles_title_trgm ON articles USING gin(title gin_trgm_ops);
CREATE INDEX idx_articles_summary_trgm ON articles USING gin(summary gin_trgm_ops);
```

**2. Data Migration**
```python
import sqlite3
import psycopg2

def migrate_sqlite_to_postgres(sqlite_path: str, pg_conn_str: str):
    # Connect to both databases
    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg2.connect(pg_conn_str)

    # Migrate articles table
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM articles")

    pg_cursor = pg_conn.cursor()
    for row in cursor:
        pg_cursor.execute("""
            INSERT INTO articles (id, url, normalized_url, url_hash, ...)
            VALUES (%s, %s, %s, %s, ...)
        """, row)

    pg_conn.commit()

    # Migrate other tables...
```

**3. ORM Abstraction (SQLAlchemy)**
```python
# Database-agnostic code using SQLAlchemy
from sqlalchemy import create_engine

# SQLite
engine = create_engine(f"sqlite:///{db_path}")

# PostgreSQL (same code!)
engine = create_engine(f"postgresql://{user}:{pwd}@{host}/{db}")
```

## Repository Pattern Implementation

### Abstract Database Access

```python
from abc import ABC, abstractmethod
from typing import Optional, List

class ArticleRepository(ABC):
    @abstractmethod
    def save(self, article: Article) -> None:
        """Save article to database"""

    @abstractmethod
    def find_by_url_hash(self, url_hash: str) -> Optional[Article]:
        """Find article by URL hash"""

    @abstractmethod
    def find_unprocessed(self, stage: str, limit: int) -> List[Article]:
        """Find articles pending processing at stage"""

class SQLiteArticleRepository(ArticleRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save(self, article: Article) -> None:
        self.conn.execute("""
            INSERT OR REPLACE INTO articles (url, normalized_url, ...)
            VALUES (?, ?, ...)
        """, (article.url, article.normalized_url, ...))

    def find_by_url_hash(self, url_hash: str) -> Optional[Article]:
        row = self.conn.execute("""
            SELECT * FROM articles WHERE url_hash = ?
        """, (url_hash,)).fetchone()

        return Article.from_row(row) if row else None

    def find_unprocessed(self, stage: str, limit: int) -> List[Article]:
        rows = self.conn.execute("""
            SELECT * FROM articles
            WHERE pipeline_stage = ? AND processing_status = 'pending'
            LIMIT ?
        """, (stage, limit)).fetchall()

        return [Article.from_row(row) for row in rows]
```

## Performance Monitoring

### Key Metrics

**Query Performance**:
- Track slow queries (>100ms)
- Monitor index usage
- Analyze query plans with EXPLAIN

**Database Size**:
- Total database size
- Growth rate (MB/day)
- Table sizes (identify largest tables)

**Write Performance**:
- Inserts per second
- Update latency
- Transaction commit time

**Read Performance**:
- Query response time (p50, p95, p99)
- Cache hit rate
- FTS query performance

### Monitoring Queries

```sql
-- Database size
SELECT page_count * page_size / 1024.0 / 1024.0 as size_mb
FROM pragma_page_count(), pragma_page_size();

-- Table sizes
SELECT name, SUM(pgsize) / 1024.0 / 1024.0 as size_mb
FROM dbstat
WHERE name IN ('articles', 'processed_links', 'api_calls')
GROUP BY name;

-- Index usage (PostgreSQL)
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

## Conclusion

The database design prioritizes:
- **Simplicity**: SQLite for zero-config local deployment
- **Performance**: Strategic indexing and FTS5 for fast queries
- **Cost Efficiency**: Tiered retention policies reduce storage
- **Scalability**: Clear migration path to PostgreSQL when needed
- **Maintainability**: Repository pattern for database-agnostic code

**Next Steps**:
- Review Python project structure (05-python-project-structure.md)
- Understand data models and SQLAlchemy ORM (11-data-models-schemas.md)
- Implement database initialization scripts
