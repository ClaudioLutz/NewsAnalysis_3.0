-- NewsAnalysis 2.0 Database Schema
-- SQLite 3.38+ with FTS5 support

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Table: articles
-- Primary table storing all article data across pipeline stages
CREATE TABLE IF NOT EXISTS articles (
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

    -- Semantic Deduplication (Step 3.5 - after scraping, before summarization)
    is_duplicate BOOLEAN DEFAULT FALSE,  -- TRUE if this is a duplicate of another article
    canonical_url_hash TEXT,  -- If duplicate, points to the canonical article's url_hash

    -- Run Tracking
    run_id TEXT NOT NULL,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_url_hash ON articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_articles_pipeline_stage ON articles(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_articles_is_match ON articles(is_match);
CREATE INDEX IF NOT EXISTS idx_articles_digest_date ON articles(digest_date);
CREATE INDEX IF NOT EXISTS idx_articles_run_id ON articles(run_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_articles_stage_status ON articles(pipeline_stage, processing_status);
CREATE INDEX IF NOT EXISTS idx_articles_match_stage ON articles(is_match, pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_articles_created_stage ON articles(created_at, pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_articles_digest_included ON articles(digest_date, included_in_digest);
CREATE INDEX IF NOT EXISTS idx_articles_is_duplicate ON articles(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_articles_canonical_hash ON articles(canonical_url_hash);

-- Full-Text Search
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title,
    summary,
    content='articles',
    content_rowid='id'
);

-- Triggers to keep FTS index updated
CREATE TRIGGER IF NOT EXISTS articles_fts_insert AFTER INSERT ON articles BEGIN
    INSERT INTO articles_fts(rowid, title, summary)
    VALUES (new.id, new.title, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS articles_fts_update AFTER UPDATE ON articles BEGIN
    UPDATE articles_fts
    SET title = new.title, summary = new.summary
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS articles_fts_delete AFTER DELETE ON articles BEGIN
    DELETE FROM articles_fts WHERE rowid = old.id;
END;

-- Table: processed_links
-- Cache table for fast URL deduplication across runs
CREATE TABLE IF NOT EXISTS processed_links (
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

CREATE INDEX IF NOT EXISTS idx_processed_links_url_hash ON processed_links(url_hash);
CREATE INDEX IF NOT EXISTS idx_processed_links_processed_at ON processed_links(processed_at);
CREATE INDEX IF NOT EXISTS idx_processed_links_expires_at ON processed_links(expires_at);

-- Table: classification_cache
-- Cache for exact match classification results (title + URL combination)
-- Saves API costs by avoiding re-classification of identical articles
CREATE TABLE IF NOT EXISTS classification_cache (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Cache Key (hash of title + URL)
    cache_key TEXT NOT NULL UNIQUE,  -- SHA-256 of normalized title + URL
    title TEXT NOT NULL,
    url TEXT NOT NULL,

    -- Classification Result
    is_match BOOLEAN NOT NULL,
    confidence REAL NOT NULL,
    topic TEXT NOT NULL,
    reason TEXT,

    -- Cache Metadata
    hit_count INTEGER DEFAULT 0,  -- Track cache usage
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_hit_at TIMESTAMP,
    expires_at TIMESTAMP  -- Optional TTL (default: 30 days)
);

CREATE INDEX IF NOT EXISTS idx_classification_cache_key ON classification_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_classification_cache_created_at ON classification_cache(created_at);
CREATE INDEX IF NOT EXISTS idx_classification_cache_expires_at ON classification_cache(expires_at);

-- Table: content_fingerprints
-- Cache for content fingerprints to avoid re-summarizing identical content
-- Uses content hash to detect duplicate articles across different URLs
CREATE TABLE IF NOT EXISTS content_fingerprints (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Content Fingerprint
    content_hash TEXT NOT NULL UNIQUE,  -- SHA-256 of normalized content
    content_length INTEGER NOT NULL,

    -- Summary Results
    summary_title TEXT,
    summary TEXT,
    key_points TEXT,  -- JSON array
    entities TEXT,  -- JSON object

    -- Cache Metadata
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_hit_at TIMESTAMP,
    expires_at TIMESTAMP  -- Optional TTL (default: 90 days)
);

CREATE INDEX IF NOT EXISTS idx_content_fingerprints_hash ON content_fingerprints(content_hash);
CREATE INDEX IF NOT EXISTS idx_content_fingerprints_created_at ON content_fingerprints(created_at);
CREATE INDEX IF NOT EXISTS idx_content_fingerprints_expires_at ON content_fingerprints(expires_at);

-- Table: cache_stats
-- Track cache performance metrics
CREATE TABLE IF NOT EXISTS cache_stats (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Stats Period
    date DATE NOT NULL,
    cache_type TEXT NOT NULL,  -- "classification", "content", "url"

    -- Performance Metrics
    requests INTEGER DEFAULT 0,
    hits INTEGER DEFAULT 0,
    misses INTEGER DEFAULT 0,
    hit_rate REAL DEFAULT 0.0,  -- hits / requests

    -- Cost Savings
    api_calls_saved INTEGER DEFAULT 0,
    cost_saved REAL DEFAULT 0.0,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date, cache_type)
);

CREATE INDEX IF NOT EXISTS idx_cache_stats_date ON cache_stats(date);
CREATE INDEX IF NOT EXISTS idx_cache_stats_type ON cache_stats(cache_type);

-- Table: pipeline_runs
-- Track pipeline execution history for debugging and analytics
CREATE TABLE IF NOT EXISTS pipeline_runs (
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

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);

-- Table: api_calls
-- Track all OpenAI API calls for cost monitoring and debugging
CREATE TABLE IF NOT EXISTS api_calls (
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

CREATE INDEX IF NOT EXISTS idx_api_calls_run_id ON api_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_api_calls_module ON api_calls(module);
CREATE INDEX IF NOT EXISTS idx_api_calls_created_at ON api_calls(created_at);
CREATE INDEX IF NOT EXISTS idx_api_calls_batch_id ON api_calls(batch_id);

-- Table: digests
-- Store daily digest metadata and outputs
CREATE TABLE IF NOT EXISTS digests (
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

CREATE INDEX IF NOT EXISTS idx_digests_date ON digests(digest_date);
CREATE INDEX IF NOT EXISTS idx_digests_run_id ON digests(run_id);

-- Table: duplicate_groups
-- Track semantic duplicate groups for cross-source deduplication
CREATE TABLE IF NOT EXISTS duplicate_groups (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Canonical Article (the one that will be summarized)
    canonical_url_hash TEXT NOT NULL,

    -- Group Metadata
    confidence REAL NOT NULL,  -- Average confidence across comparisons
    duplicate_count INTEGER NOT NULL,  -- Number of duplicates in group

    -- Timestamps
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Run Tracking
    run_id TEXT NOT NULL,

    FOREIGN KEY (canonical_url_hash) REFERENCES articles(url_hash)
);

CREATE INDEX IF NOT EXISTS idx_duplicate_groups_canonical ON duplicate_groups(canonical_url_hash);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_run_id ON duplicate_groups(run_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_detected_at ON duplicate_groups(detected_at);

-- Table: duplicate_members
-- Track which articles belong to which duplicate group
CREATE TABLE IF NOT EXISTS duplicate_members (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Group Reference
    group_id INTEGER NOT NULL,

    -- Duplicate Article
    duplicate_url_hash TEXT NOT NULL,

    -- Comparison Details
    comparison_confidence REAL,  -- Confidence when compared to canonical

    FOREIGN KEY (group_id) REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (duplicate_url_hash) REFERENCES articles(url_hash),
    UNIQUE(group_id, duplicate_url_hash)
);

CREATE INDEX IF NOT EXISTS idx_duplicate_members_group ON duplicate_members(group_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_members_hash ON duplicate_members(duplicate_url_hash);
