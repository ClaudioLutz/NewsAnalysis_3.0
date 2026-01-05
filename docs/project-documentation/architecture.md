# System Architecture

## Overview

NewsAnalysis 3.0 is a **5-stage data pipeline** for Swiss business news analysis, optimized for cost efficiency through multi-provider LLM strategy and intelligent caching.

## Architecture Pattern

**Pipeline Architecture (ETL-style)** with:
- Sequential stage processing with clear interfaces
- Repository pattern for data access
- Domain-driven design with Pydantic models
- Multi-provider LLM abstraction for cost optimization
- Factory pattern for component creation

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface                             │
│                    (Click Framework)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                         │
│              (Coordinates all 5 stages)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────┬─────────┬─────────┬─────────┬─────────┐
        ▼         ▼         ▼         ▼         ▼
   ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
   │  Stage  ││  Stage  ││  Stage  ││  Stage  ││  Stage  │
   │    1    ││    2    ││    3    ││    4    ││    5    │
   │Collector││ Filter  ││ Scraper ││Summarize││ Digest  │
   └─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
        │         │         │         │         │
        └─────────┴─────────┴─────────┴─────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                              │
│         ArticleRepository │ DigestRepository                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SQLite Database                             │
│              (with FTS5 full-text search)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Pipeline Stages

### Stage 1: NewsCollector

**Purpose:** Aggregate news from multiple Swiss sources

**Components:**
- `RSSCollector` - RSS/Atom feed parsing (feedparser)
- `HTMLCollector` - HTML page scraping
- `SitemapCollector` - Sitemap-based collection

**Sources:** 25+ Swiss news feeds across 3 tiers:
- Tier 1: Government (FINMA) - 7-day retention
- Tier 2: Financial (Finews, Cash) - 3-day retention
- Tier 3: General (NZZ, SRF, Tamedia) - 1-day retention

**Output:** `ArticleMetadata` objects

### Stage 2: ContentFilter

**Purpose:** AI-powered relevance classification

**Provider:** DeepSeek (deepseek-chat) - cost-effective classification

**Key Features:**
- Title/URL-only filtering (90% cost reduction)
- Classification caching (30-day TTL)
- Configurable confidence threshold (default: 0.70)

**Output:** `ClassificationResult` with is_match, confidence, topic

### Stage 3: ContentScraper

**Purpose:** Extract full article content

**Components:**
- `TrafilaturaScraper` - Primary extractor (fast, reliable)
- `PlaywrightScraper` - Fallback for JS-rendered pages

**Output:** `ScrapedContent` with content, author, quality score

### Stage 4: ArticleSummarizer

**Purpose:** Generate structured German summaries

**Provider:** Google Gemini (gemini-2.0-flash) - quality summarization

**Key Features:**
- Content fingerprint caching (90-day TTL)
- Entity extraction (companies, people, locations)
- German language output (Hochdeutsch)

**Output:** `ArticleSummary` with title, summary, key_points, entities

### Stage 5: DigestGenerator

**Purpose:** Create daily analysis reports

**Provider:** Google Gemini - meta-analysis generation

**Key Features:**
- Article deduplication (clustering similar articles)
- Meta-analysis (trends, patterns, risk indicators)
- Multiple output formats (JSON, Markdown, German report)

**Output:** `DailyDigest` with articles, analysis, formatted reports

## Multi-Provider LLM Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProviderFactory                               │
└─────────────────────────────────────────────────────────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   DeepSeek    │   │ Google Gemini │   │    OpenAI     │
│ Classification │   │ Summarization │   │   Fallback    │
│   ~$0.001/1K  │   │  ~$0.01/1K    │   │  ~$0.03/1K    │
└───────────────┘   └───────────────┘   └───────────────┘
```

**Cost Optimization:** 88% savings vs OpenAI-only approach (~$2.50/month for 100 articles/day)

## Data Flow

```
RSS/HTML Sources
      │
      ▼
[1] Collector ──────► ArticleMetadata
      │                    │
      ▼                    ▼
[2] Filter ─────────► ClassificationResult
      │                    │ (is_match?)
      ▼                    │
[3] Scraper ────────► ScrapedContent
      │                    │
      ▼                    │
[4] Summarizer ─────► ArticleSummary
      │                    │
      ▼                    │
[5] Digest ─────────► DailyDigest ──► JSON/MD/German
```

## Configuration Architecture

```
config/
├── feeds.yaml      # 25+ news source configurations
├── topics.yaml     # Classification topics
└── prompts/
    ├── classification.yaml  # Filter prompts
    ├── summarization.yaml   # Summary prompts
    └── meta_analysis.yaml   # Digest prompts
```

Environment variables (`.env`):
- API keys for all providers
- Database path
- Pipeline thresholds
- Cost limits
- Feature flags

## Error Handling

- **Retry Logic:** 3 attempts per article before marking failed
- **Graceful Degradation:** Pipeline continues on individual failures
- **Fallback Scrapers:** Playwright fallback for Trafilatura failures
- **Provider Fallback:** OpenAI fallback for LLM failures

## Caching Strategy

| Cache | Purpose | TTL | Cost Savings |
|-------|---------|-----|--------------|
| Classification | Avoid re-classifying identical titles | 30 days | ~50% |
| Content Fingerprint | Avoid re-summarizing identical content | 90 days | ~30% |
| URL Dedup | Skip already-processed URLs | Permanent | Variable |

## Security Considerations

- API keys stored in environment variables
- No sensitive data logging
- Database file permissions
- Input validation via Pydantic
