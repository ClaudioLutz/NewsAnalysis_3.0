# Data Models Documentation

## Overview

NewsAnalysis 3.0 uses SQLite with FTS5 for full-text search capabilities. The schema supports the 5-stage pipeline architecture with comprehensive caching for cost optimization.

## Entity Relationship

```
articles (main) ──── pipeline_runs (tracking)
    │                    │
    ├── articles_fts     └── api_calls
    │   (FTS index)
    │
    ├── processed_links (URL cache)
    ├── classification_cache (API cache)
    ├── content_fingerprints (content cache)
    └── digests (output)
         │
         └── cache_stats (metrics)
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

**Pipeline State:**
| Column | Type | Description |
|--------|------|-------------|
| pipeline_stage | TEXT | collected/filtered/scraped/summarized/digested |
| processing_status | TEXT | pending/processing/completed/failed |
| error_message | TEXT | Error details if failed |
| error_count | INTEGER | Retry counter |
| run_id | TEXT | Pipeline run identifier |

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
| run_id | TEXT | Pipeline run ID |

### pipeline_runs

Pipeline execution tracking for monitoring and debugging.

| Column | Type | Description |
|--------|------|-------------|
| run_id | TEXT | Primary key (UUID + timestamp) |
| mode | TEXT | full/express/export |
| started_at | TIMESTAMP | Start time |
| completed_at | TIMESTAMP | End time |
| status | TEXT | running/completed/failed/cancelled |
| collected_count | INTEGER | Articles collected |
| filtered_count | INTEGER | Articles filtered |
| scraped_count | INTEGER | Articles scraped |
| summarized_count | INTEGER | Articles summarized |
| total_cost | REAL | API costs |
| total_tokens | INTEGER | Token usage |

## Cache Tables

### classification_cache

Saves API costs by caching classification results.

| Column | Type | Description |
|--------|------|-------------|
| cache_key | TEXT | SHA-256 of title + URL |
| is_match | BOOLEAN | Cached result |
| confidence | REAL | Cached confidence |
| hit_count | INTEGER | Usage counter |
| expires_at | TIMESTAMP | TTL (30 days default) |

### content_fingerprints

Avoids re-summarizing identical content across different URLs.

| Column | Type | Description |
|--------|------|-------------|
| content_hash | TEXT | SHA-256 of normalized content |
| summary | TEXT | Cached summary |
| key_points | TEXT | Cached key points |
| expires_at | TIMESTAMP | TTL (90 days default) |

### api_calls

Tracks all LLM API calls for cost monitoring.

| Column | Type | Description |
|--------|------|-------------|
| run_id | TEXT | Pipeline run |
| module | TEXT | filter/summarizer/digest_generator |
| model | TEXT | LLM model used |
| input_tokens | INTEGER | Input token count |
| output_tokens | INTEGER | Output token count |
| cost | REAL | API cost in USD |

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

## Indexes

Performance indexes for common query patterns:

- `idx_articles_url_hash` - Fast deduplication
- `idx_articles_pipeline_stage` - Stage-based queries
- `idx_articles_is_match` - Filter relevant articles
- `idx_articles_digest_date` - Digest generation
- `idx_articles_stage_status` - Composite for pipeline queries

## Full-Text Search

FTS5 virtual table `articles_fts` enables full-text search on:
- title
- summary

Automatically maintained via INSERT/UPDATE/DELETE triggers.
