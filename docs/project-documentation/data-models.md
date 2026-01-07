# Data Models Documentation

## Overview

NewsAnalysis 3.0 uses SQLite with FTS5 for full-text search capabilities. The schema supports the 5-stage pipeline architecture with comprehensive caching for cost optimization.

## Entity Relationship

```
articles (main) ──────────────── pipeline_runs (tracking)
    │                                  │
    ├── articles_fts (FTS index)       └── api_calls
    │
    ├── processed_links (URL cache)
    ├── classification_cache (API cache)
    ├── content_fingerprints (content cache)
    │
    ├── duplicate_groups ─────── duplicate_members
    │   (canonical articles)      (duplicate articles)
    │
    ├── digests (output)
    ├── cache_stats (metrics)
    └── schema_info (version tracking)
```

## Core Tables

### articles

Primary table storing all article data across pipeline stages.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| url | TEXT | Original URL |
| normalized_url | TEXT | Canonical URL |
| url_hash | TEXT | SHA-256 hash (unique) |
| title | TEXT | Article title |
| source | TEXT | Feed name (NZZ, FINMA, etc.) |
| published_at | TIMESTAMP | Publication date |
| collected_at | TIMESTAMP | Collection timestamp |
| feed_priority | INTEGER | 1=govt, 2=financial, 3=general |

**Classification Fields (Stage 2):**
| Column | Type | Description |
|--------|------|-------------|
| is_match | BOOLEAN | Relevance classification |
| confidence | REAL | 0.0-1.0 confidence score |
| topic | TEXT | Matched topic |
| classification_reason | TEXT | AI reasoning |
| filtered_at | TIMESTAMP | Classification timestamp |

**Content Fields (Stage 3):**
| Column | Type | Description |
|--------|------|-------------|
| content | TEXT | Full article text |
| author | TEXT | Article author |
| content_length | INTEGER | Character count |
| extraction_method | TEXT | trafilatura/playwright |
| extraction_quality | REAL | 0.0-1.0 quality score |
| scraped_at | TIMESTAMP | Scraping timestamp |

**Summary Fields (Stage 4):**
| Column | Type | Description |
|--------|------|-------------|
| summary_title | TEXT | Generated title |
| summary | TEXT | AI summary |
| key_points | TEXT | JSON array of key points |
| entities | TEXT | JSON {companies, people, locations, topics} |
| summarized_at | TIMESTAMP | Summary timestamp |

**Digest Assignment (Stage 5):**
| Column | Type | Description |
|--------|------|-------------|
| digest_date | DATE | Date article was included in digest |
| digest_version | INTEGER | Digest version number |
| included_in_digest | BOOLEAN | Whether article is in a digest |

**Semantic Deduplication (Stage 3.5):**
| Column | Type | Description |
|--------|------|-------------|
| is_duplicate | BOOLEAN | TRUE if duplicate of another article |
| canonical_url_hash | TEXT | URL hash of the canonical article (if duplicate) |

**Pipeline State:**
| Column | Type | Description |
|--------|------|-------------|
| pipeline_stage | TEXT | collected/filtered/scraped/summarized/digested |
| processing_status | TEXT | pending/processing/completed/failed |
| error_message | TEXT | Error details if failed |
| error_count | INTEGER | Retry counter |
| run_id | TEXT | Pipeline run identifier |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### digests

Daily digest storage with multiple output formats.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| digest_date | DATE | Digest date |
| version | INTEGER | Version number (for updates) |
| articles_json | TEXT | JSON array of article IDs |
| meta_analysis_json | TEXT | AI meta-analysis |
| json_output | TEXT | Full JSON output |
| markdown_output | TEXT | Markdown report |
| german_report | TEXT | Bonitäts-Tagesanalyse |
| article_count | INTEGER | Number of articles |
| cluster_count | INTEGER | After deduplication |
| generated_at | TIMESTAMP | Generation timestamp |
| run_id | TEXT | Pipeline run ID |

### schema_info

Schema version tracking for database migrations.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| version | INTEGER | Schema version number |
| applied_at | TIMESTAMP | Migration timestamp |
| description | TEXT | Migration description |

### pipeline_runs

Pipeline execution tracking for monitoring and debugging.

| Column | Type | Description |
|--------|------|-------------|
| run_id | TEXT | Primary key (UUID + timestamp) |
| mode | TEXT | full/express/export |
| config_snapshot | TEXT | JSON snapshot of config at run time |
| started_at | TIMESTAMP | Start time |
| completed_at | TIMESTAMP | End time |
| status | TEXT | running/completed/failed/cancelled |
| collected_count | INTEGER | Articles collected |
| filtered_count | INTEGER | Articles filtered |
| scraped_count | INTEGER | Articles scraped |
| summarized_count | INTEGER | Articles summarized |
| digested_count | INTEGER | Articles digested |
| error_message | TEXT | Error message if failed |
| error_stage | TEXT | Stage where error occurred |
| duration_seconds | REAL | Pipeline execution time |
| total_cost | REAL | API costs |
| total_tokens | INTEGER | Token usage |

## Deduplication Tables

### duplicate_groups

Tracks semantic duplicate groups for cross-source deduplication.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| canonical_url_hash | TEXT | URL hash of the canonical article |
| confidence | REAL | Average confidence across comparisons |
| duplicate_count | INTEGER | Number of duplicates in group |
| detected_at | TIMESTAMP | Detection timestamp |
| run_id | TEXT | Pipeline run ID |

### duplicate_members

Tracks which articles belong to which duplicate group.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| group_id | INTEGER | Foreign key to duplicate_groups |
| duplicate_url_hash | TEXT | URL hash of the duplicate article |
| comparison_confidence | REAL | Confidence when compared to canonical |

## Cache Tables

### classification_cache

Saves API costs by caching classification results.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| cache_key | TEXT | SHA-256 of title + URL (unique) |
| title | TEXT | Original article title |
| url | TEXT | Original article URL |
| is_match | BOOLEAN | Cached classification result |
| confidence | REAL | Cached confidence score |
| topic | TEXT | Matched topic |
| reason | TEXT | Classification reason |
| hit_count | INTEGER | Cache hit counter |
| created_at | TIMESTAMP | Cache entry creation time |
| last_hit_at | TIMESTAMP | Last cache hit time |
| expires_at | TIMESTAMP | TTL (30 days default) |

### content_fingerprints

Avoids re-summarizing identical content across different URLs.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| content_hash | TEXT | SHA-256 of normalized content (unique) |
| content_length | INTEGER | Original content length |
| summary_title | TEXT | Cached summary title |
| summary | TEXT | Cached summary |
| key_points | TEXT | Cached key points (JSON) |
| entities | TEXT | Cached entities (JSON) |
| hit_count | INTEGER | Cache hit counter |
| created_at | TIMESTAMP | Cache entry creation time |
| last_hit_at | TIMESTAMP | Last cache hit time |
| expires_at | TIMESTAMP | TTL (90 days default) |

### cache_stats

Track cache performance metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| date | DATE | Stats period date |
| cache_type | TEXT | classification/content/url |
| requests | INTEGER | Total requests |
| hits | INTEGER | Cache hits |
| misses | INTEGER | Cache misses |
| hit_rate | REAL | Hits / requests ratio |
| api_calls_saved | INTEGER | API calls saved |
| cost_saved | REAL | Estimated cost savings |
| created_at | TIMESTAMP | Record creation |
| updated_at | TIMESTAMP | Last update |

### api_calls

Tracks all LLM API calls for cost monitoring.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| run_id | TEXT | Pipeline run |
| module | TEXT | filter/summarizer/digest_generator/dedup |
| model | TEXT | LLM model used |
| request_type | TEXT | classification/summarization/meta_analysis/duplicate_detection |
| batch_id | TEXT | Batch API request ID (optional) |
| input_tokens | INTEGER | Input token count |
| output_tokens | INTEGER | Output token count |
| total_tokens | INTEGER | Total token count |
| cost | REAL | API cost in USD |
| success | BOOLEAN | Request success status |
| error_message | TEXT | Error message if failed |
| created_at | TIMESTAMP | Request timestamp |
| completed_at | TIMESTAMP | Completion timestamp |

### processed_links

Cache table for fast URL deduplication across runs.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| url_hash | TEXT | SHA-256 of URL (unique) |
| url | TEXT | Original URL |
| normalized_url | TEXT | Normalized URL |
| is_match | BOOLEAN | Classification result |
| confidence | REAL | Classification confidence |
| topic | TEXT | Matched topic |
| reason | TEXT | Classification reason |
| processed_at | TIMESTAMP | Processing timestamp |
| expires_at | TIMESTAMP | Optional TTL |
| run_id | TEXT | Pipeline run ID |

## Pydantic Domain Models

### Article

Complete article model with all processing stages (see `src/newsanalysis/core/article.py`).

### ArticleMetadata

Initial collection data: URL, title, source, timestamps.

### ClassificationResult

AI classification output: is_match, confidence, topic, reason.

### ScrapedContent

Extracted content: content, author, extraction method/quality.

### ArticleSummary

AI summary: title, summary, key_points, entities.

### DailyDigest

Daily digest output: date, articles, meta_analysis, statistics.

### DuplicateGroup

Semantic duplicate group: canonical_url_hash, duplicate_url_hashes, confidence.

### DuplicateCheckResponse

Duplicate detection API response: is_duplicate, confidence, reason.

## Indexes

Performance indexes for common query patterns:

**Articles indexes:**
- `idx_articles_url_hash` - Fast URL deduplication (UNIQUE)
- `idx_articles_source` - Source-based queries
- `idx_articles_published_at` - Date-based queries
- `idx_articles_pipeline_stage` - Stage-based queries
- `idx_articles_is_match` - Filter relevant articles
- `idx_articles_digest_date` - Digest generation
- `idx_articles_run_id` - Run-based queries
- `idx_articles_stage_status` - Composite for pipeline queries
- `idx_articles_match_stage` - Composite for filtering
- `idx_articles_created_stage` - Composite for ordering
- `idx_articles_digest_included` - Digest inclusion queries
- `idx_articles_is_duplicate` - Duplicate detection
- `idx_articles_canonical_hash` - Canonical article lookups

**Deduplication indexes:**
- `idx_duplicate_groups_canonical` - Canonical article lookups
- `idx_duplicate_groups_run_id` - Run-based queries
- `idx_duplicate_groups_detected_at` - Time-based queries
- `idx_duplicate_members_group` - Group membership lookups
- `idx_duplicate_members_hash` - Hash-based lookups

**Cache indexes:**
- `idx_classification_cache_key` - Cache key lookups
- `idx_classification_cache_expires_at` - TTL expiration
- `idx_content_fingerprints_hash` - Content hash lookups
- `idx_content_fingerprints_expires_at` - TTL expiration

## Full-Text Search

FTS5 virtual table `articles_fts` enables full-text search on:
- title
- summary

**Note:** FTS triggers are DISABLED due to database corruption issues during concurrent UPDATE operations. The FTS index can be manually rebuilt if needed:
```sql
INSERT INTO articles_fts(articles_fts) VALUES('rebuild');
```
