# Source Tree Analysis

## Project Structure

```
news_analysis_3.0/
├── src/                          # Source code (src layout)
│   └── newsanalysis/             # Main package
│       ├── __init__.py
│       ├── __version__.py        # Version info
│       ├── cli/                  # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py           # CLI entry point (Click)
│       │   └── commands/         # CLI commands
│       │       ├── __init__.py
│       │       ├── run.py        # Pipeline execution
│       │       ├── export.py     # Digest export
│       │       ├── stats.py      # Statistics display
│       │       ├── cost_report.py # API cost reporting
│       │       ├── health.py     # System health check
│       │       └── email.py      # Email digest via Outlook
│       ├── core/                 # Domain models
│       │   ├── __init__.py
│       │   ├── article.py        # Article, ArticleSummary, etc.
│       │   ├── config.py         # Config, FeedConfig, etc.
│       │   ├── digest.py         # DailyDigest, MetaAnalysis
│       │   └── enums.py          # PipelineStage, ProcessingStatus
│       ├── database/             # Data access layer
│       │   ├── __init__.py
│       │   ├── connection.py     # SQLite connection manager
│       │   ├── migrations.py     # Schema migration system
│       │   ├── repository.py     # ArticleRepository
│       │   ├── digest_repository.py
│       │   ├── repositories/     # (Additional repos)
│       │   └── schema.sql        # Database schema
│       ├── integrations/         # External API clients
│       │   ├── __init__.py
│       │   ├── provider_factory.py  # LLM provider abstraction
│       │   ├── deepseek_client.py   # DeepSeek API client
│       │   ├── gemini_client.py     # Google Gemini API client
│       │   └── openai_client.py     # OpenAI API client (reference)
│       ├── pipeline/             # Pipeline modules
│       │   ├── __init__.py
│       │   ├── orchestrator.py   # Main pipeline coordinator
│       │   ├── collectors/       # Stage 1: News collection
│       │   │   ├── __init__.py
│       │   │   ├── base.py       # Collector base class
│       │   │   ├── rss.py        # RSS/Atom collector
│       │   │   ├── html.py       # HTML scraper
│       │   │   └── sitemap.py    # Sitemap collector
│       │   ├── filters/          # Stage 2: AI filtering
│       │   │   ├── __init__.py
│       │   │   └── ai_filter.py  # DeepSeek classification
│       │   ├── scrapers/         # Stage 3: Content extraction
│       │   │   ├── __init__.py
│       │   │   ├── base.py       # Scraper base class
│       │   │   ├── trafilatura_scraper.py
│       │   │   └── playwright_scraper.py
│       │   ├── dedup/            # Stage 3.5: Semantic deduplication
│       │   │   ├── __init__.py
│       │   │   └── duplicate_detector.py  # LLM-based duplicate detection
│       │   ├── summarizers/      # Stage 4: Summarization
│       │   │   ├── __init__.py
│       │   │   └── article_summarizer.py  # Gemini summarization
│       │   ├── generators/       # Stage 5: Digest generation
│       │   │   ├── __init__.py
│       │   │   └── digest_generator.py
│       │   ├── analyzers/        # Analysis utilities
│       │   │   └── __init__.py
│       │   ├── digest/           # Digest utilities
│       │   │   └── __init__.py
│       │   └── formatters/       # Output formatting
│       │       ├── __init__.py
│       │       ├── json_formatter.py
│       │       ├── markdown_formatter.py
│       │       └── german_formatter.py
│       ├── services/             # Business logic services
│       │   ├── __init__.py
│       │   ├── cache_service.py  # Caching logic
│       │   ├── config_loader.py  # YAML config loading
│       │   ├── digest_formatter.py  # Digest formatting
│       │   └── email_service.py  # Outlook email automation
│       └── utils/                # Utilities
│           ├── __init__.py
│           ├── date_utils.py
│           ├── text_utils.py
│           ├── logging.py        # structlog setup
│           └── exceptions.py     # Custom exceptions
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_e2e.py               # End-to-end tests
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_cache_service.py
│   │   ├── test_date_utils.py
│   │   └── test_text_utils.py
│   └── integration/              # Integration tests
│       ├── __init__.py
│       ├── test_repository.py
│       └── test_pipeline.py
├── config/                       # Configuration files
│   ├── feeds.yaml                # 24 news source definitions
│   ├── topics.yaml               # Classification topics
│   ├── prompts/                  # LLM prompts
│   │   ├── classification.yaml   # Filter prompts
│   │   ├── deduplication.yaml    # Duplicate detection prompts
│   │   ├── summarization.yaml    # Summary prompts
│   │   └── meta_analysis.yaml    # Digest prompts
│   └── templates/                # Output templates
│       └── german_report.md.j2
├── scripts/                      # Utility scripts
│   ├── init_db.py                # Database initialization
│   ├── migrate_phase5.py         # Schema migration
│   ├── check_costs.py            # Cost analysis
│   ├── test_multi_provider.py    # LLM provider testing
│   ├── run_test_pipeline.py      # Test pipeline run
│   ├── run_production_pipeline.py # Production pipeline
│   ├── run_summarize_digest.py   # Summarize and digest only
│   ├── run_full_production.py    # Full production run
│   ├── deploy.sh                 # Linux deployment
│   ├── backup.sh                 # Database backup
│   └── maintenance.sh            # DB maintenance
├── docs/                         # Documentation
│   ├── USER_GUIDE.md
│   ├── TROUBLESHOOTING.md
│   ├── implementation_plan/      # 13 technical docs
│   ├── stories/                  # Change documentation
│   └── project-documentation/    # Generated docs (this folder)
├── out/                          # Output directory
│   └── digests/                  # Generated digests
├── backups/                      # Database backups
├── pyproject.toml                # Project configuration
├── README.md                     # Project overview
├── CLAUDE.md                     # AI instructions
├── IMPLEMENTATION_SUMMARY.md     # Implementation summary
├── .env.example                  # Environment template
└── .gitignore
```

## Critical Directories

### src/newsanalysis/

Main package containing all application code.

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `cli/` | Command-line interface | `main.py` (entry point), `commands/` |
| `core/` | Domain models | `article.py`, `config.py`, `digest.py` |
| `database/` | Data access | `repository.py`, `migrations.py`, `schema.sql` |
| `integrations/` | LLM API clients | `provider_factory.py`, `deepseek_client.py`, `gemini_client.py` |
| `pipeline/` | Processing stages | `orchestrator.py`, stage subdirs |
| `services/` | Business logic | `cache_service.py`, `config_loader.py`, `email_service.py` |
| `utils/` | Utilities | `logging.py`, `exceptions.py` |

### pipeline/ Subdirectories

| Directory | Stage | Components |
|-----------|-------|------------|
| `collectors/` | 1 | RSS, HTML, Sitemap collectors |
| `filters/` | 2 | AI classification filter |
| `scrapers/` | 3 | Trafilatura, Playwright scrapers |
| `dedup/` | 3.5 | LLM-based semantic duplicate detector |
| `summarizers/` | 4 | Article summarization |
| `generators/` | 5 | Digest generation |
| `formatters/` | Output | JSON, Markdown, German formatters |

### config/

YAML-based configuration for runtime customization.

| File | Purpose |
|------|---------|
| `feeds.yaml` | 24 news source definitions |
| `topics.yaml` | Classification topics |
| `prompts/*.yaml` | LLM prompt templates (classification, deduplication, summarization, meta_analysis) |
| `templates/*.j2` | Output templates (German report) |

### tests/

pytest-based test suite with coverage targets.

| Directory | Type | Coverage Target |
|-----------|------|-----------------|
| `unit/` | Unit tests | >90% |
| `integration/` | Integration tests | >80% |
| Root | E2E tests | >70% |

## Entry Points

| Entry Point | Location | Purpose |
|-------------|----------|---------|
| CLI | `src/newsanalysis/cli/main.py` | `newsanalysis` command |
| Pipeline | `src/newsanalysis/pipeline/orchestrator.py` | `PipelineOrchestrator.run()` |
| DB Init | `scripts/init_db.py` | Database setup |

## Key File Locations

| Component | Location |
|-----------|----------|
| Database Schema | `src/newsanalysis/database/schema.sql` |
| Database Migrations | `src/newsanalysis/database/migrations.py` |
| Article Model | `src/newsanalysis/core/article.py` |
| Configuration Model | `src/newsanalysis/core/config.py` |
| Pipeline Orchestrator | `src/newsanalysis/pipeline/orchestrator.py` |
| AI Filter | `src/newsanalysis/pipeline/filters/ai_filter.py` |
| Duplicate Detector | `src/newsanalysis/pipeline/dedup/duplicate_detector.py` |
| Digest Generator | `src/newsanalysis/pipeline/generators/digest_generator.py` |
| Provider Factory | `src/newsanalysis/integrations/provider_factory.py` |
| Config Loader | `src/newsanalysis/services/config_loader.py` |
| Email Service | `src/newsanalysis/services/email_service.py` |
