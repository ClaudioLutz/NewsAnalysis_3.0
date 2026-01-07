# System Architecture

## Overview

NewsAnalysis 3.0 is a **5-stage data pipeline** (with semantic deduplication sub-stage) for Swiss business news analysis, optimized for cost efficiency through multi-provider LLM strategy and intelligent caching.

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
│              (Coordinates all stages)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
   ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
   ▼         ▼         ▼         ▼         ▼         ▼
┌───────┐┌───────┐┌───────┐┌───────┐┌───────┐┌───────┐
│Stage 1││Stage 2││Stage 3││  3.5  ││Stage 4││Stage 5│
│Collect││Filter ││Scrape ││ Dedup ││Summary││Digest │
└───────┘└───────┘└───────┘└───────┘└───────┘└───────┘
   │         │         │         │         │         │
   └─────────┴─────────┴─────────┴─────────┴─────────┘
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

**Sources:** 24 Swiss news feeds across 3 tiers:
- Tier 1: Government (FINMA News, FINMA Sanctions) - 7-day retention
- Tier 2: Financial (Finews, Cash, Finanzen.ch, StartupTicker, FinTech News) - 3-day retention
- Tier 3: General (NZZ, SRF, Tamedia, Swissinfo, French-language) - 1-day retention

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

### Stage 3.5: DuplicateDetector

**Purpose:** Semantic deduplication across different news sources

**Provider:** DeepSeek (cost-effective for pairwise comparisons)

**Key Features:**
- LLM-powered title comparison for duplicate detection
- Time-window grouping (48-hour default) for candidate pairs
- Union-Find clustering for transitive duplicates
- Canonical article selection (highest priority source)
- Configurable confidence threshold (default: 0.75)

**Output:** `DuplicateGroup` with canonical article and duplicate URL hashes

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
│        (Bidirectional fallback: DeepSeek ↔ Gemini)               │
└─────────────────────────────────────────────────────────────────┘
                    │                   │
                    ▼                   ▼
          ┌───────────────┐     ┌───────────────┐
          │   DeepSeek    │     │ Google Gemini │
          │ Classification │     │ Summarization │
          │ Deduplication  │     │    Digest     │
          │   ~$0.001/1K  │     │  ~$0.01/1K    │
          └───────────────┘     └───────────────┘
```

**Provider Assignment:**
- **Classification:** DeepSeek (primary) → Gemini (fallback)
- **Deduplication:** DeepSeek (primary) → Gemini (fallback)
- **Summarization:** Gemini (primary) → DeepSeek (fallback)
- **Digest Generation:** Gemini (primary) → DeepSeek (fallback)

**Cost Optimization:** 88% savings vs OpenAI-only approach (~$2.50/month for 100 articles/day)

## Data Flow

```
RSS/HTML Sources
      │
      ▼
[1] Collector ──────► ArticleMetadata
      │                    │
      ▼                    ▼
[2] Filter ─────────► ClassificationResult (is_match?)
      │                    │
      ▼                    │
[3] Scraper ────────► ScrapedContent
      │                    │
      ▼                    │
[3.5] Dedup ────────► DuplicateGroup (mark duplicates)
      │                    │
      ▼                    │
[4] Summarizer ─────► ArticleSummary (canonical only)
      │                    │
      ▼                    │
[5] Digest ─────────► DailyDigest ──► JSON/MD/German
                                          │
                                          ▼
                                    Email Service
                                  (Outlook automation)
```

## Configuration Architecture

```
config/
├── feeds.yaml      # 24 news source configurations
├── topics.yaml     # Classification topics
├── prompts/
│   ├── classification.yaml  # Filter prompts
│   ├── deduplication.yaml   # Duplicate detection prompts
│   ├── summarization.yaml   # Summary prompts
│   └── meta_analysis.yaml   # Digest prompts
└── templates/
    └── german_report.md.j2  # German report template
```

Environment variables (`.env`):
- API keys for all providers (OpenAI, DeepSeek, Google)
- Database path
- Pipeline thresholds
- Cost limits
- Feature flags
- Email settings (recipients, auto-send)

## Error Handling

- **Retry Logic:** 3 attempts per article before marking failed
- **Graceful Degradation:** Pipeline continues on individual failures
- **Fallback Scrapers:** Playwright fallback for Trafilatura failures
- **Provider Fallback:** Bidirectional DeepSeek ↔ Gemini fallback for LLM failures

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
