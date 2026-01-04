# Python Project Structure

## Overview

This document defines the recommended Python project structure for the NewsAnalysis system using modern best practices: the **src layout**, type hints, dependency management with `pyproject.toml`, and clear separation of concerns.

## Recommended Project Layout

```
newsanalysis/
├── src/
│   └── newsanalysis/
│       ├── __init__.py
│       ├── __version__.py
│       │
│       ├── cli/                      # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py              # Entry point (argparse/click)
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── run.py           # Run pipeline
│       │       ├── export.py        # Export digest
│       │       └── stats.py         # Show statistics
│       │
│       ├── core/                     # Domain models (Pydantic)
│       │   ├── __init__.py
│       │   ├── article.py           # Article dataclasses
│       │   ├── digest.py            # Digest models
│       │   ├── config.py            # Configuration models
│       │   └── enums.py             # Enums (PipelineStage, etc.)
│       │
│       ├── pipeline/                 # Pipeline modules
│       │   ├── __init__.py
│       │   ├── orchestrator.py      # Pipeline coordinator
│       │   │
│       │   ├── collectors/          # Step 1: News collection
│       │   │   ├── __init__.py
│       │   │   ├── base.py          # Base collector interface
│       │   │   ├── rss_collector.py
│       │   │   ├── sitemap_collector.py
│       │   │   └── html_collector.py
│       │   │
│       │   ├── filters/             # Step 2: AI filtering
│       │   │   ├── __init__.py
│       │   │   ├── ai_filter.py     # Main filter implementation
│       │   │   ├── cache.py         # Classification cache
│       │   │   └── batching.py      # Batch processing logic
│       │   │
│       │   ├── scrapers/            # Step 3: Content scraping
│       │   │   ├── __init__.py
│       │   │   ├── base.py          # Base scraper interface
│       │   │   ├── trafilatura_scraper.py
│       │   │   ├── playwright_scraper.py
│       │   │   └── quality.py       # Content quality scoring
│       │   │
│       │   ├── analyzers/           # Step 4: Summarization
│       │   │   ├── __init__.py
│       │   │   ├── summarizer.py    # Article summarization
│       │   │   └── entity_extractor.py
│       │   │
│       │   └── digest/              # Step 5: Digest generation
│       │       ├── __init__.py
│       │       ├── generator.py     # Digest generator
│       │       ├── deduplicator.py  # Article deduplication
│       │       └── formatter.py     # Output formatting
│       │
│       ├── database/                 # Repository layer
│       │   ├── __init__.py
│       │   ├── connection.py        # Connection management
│       │   ├── models.py            # SQLAlchemy models
│       │   ├── schema.sql           # Database schema
│       │   │
│       │   └── repositories/        # Repository pattern
│       │       ├── __init__.py
│       │       ├── base.py          # Base repository
│       │       ├── article_repo.py
│       │       ├── digest_repo.py
│       │       └── pipeline_repo.py
│       │
│       ├── integrations/             # External API clients
│       │   ├── __init__.py
│       │   ├── openai_client.py     # OpenAI API wrapper
│       │   ├── news_sources.py      # News source clients
│       │   └── cost_tracker.py      # API cost tracking
│       │
│       ├── services/                 # Business logic layer
│       │   ├── __init__.py
│       │   ├── url_normalizer.py    # URL normalization
│       │   ├── prompt_builder.py    # Prompt construction
│       │   └── state_manager.py     # Pipeline state management
│       │
│       └── utils/                    # Shared utilities
│           ├── __init__.py
│           ├── logging.py           # Logging setup
│           ├── date_utils.py        # Date/time helpers
│           ├── text_utils.py        # Text processing
│           └── exceptions.py        # Custom exceptions
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   │
│   ├── unit/                        # Unit tests
│   │   ├── __init__.py
│   │   ├── test_collectors.py
│   │   ├── test_filters.py
│   │   ├── test_scrapers.py
│   │   ├── test_analyzers.py
│   │   └── test_digest.py
│   │
│   ├── integration/                 # Integration tests
│   │   ├── __init__.py
│   │   ├── test_pipeline.py
│   │   ├── test_database.py
│   │   └── test_openai_integration.py
│   │
│   └── fixtures/                    # Test data
│       ├── sample_feeds.yaml
│       ├── sample_rss.xml
│       ├── sample_article.html
│       └── golden_dataset.json
│
├── config/                           # Configuration files
│   ├── feeds.yaml                   # News source definitions
│   ├── topics.yaml                  # Classification topics
│   ├── pipeline_config.yaml         # Pipeline settings
│   │
│   └── prompts/                     # Prompt templates
│       ├── classification.yaml
│       ├── summarization.yaml
│       └── meta_analysis.yaml
│
├── scripts/                          # Maintenance scripts
│   ├── init_db.py                   # Initialize database
│   ├── backup_db.py                 # Backup database
│   ├── vacuum_db.py                 # Database maintenance
│   ├── migrate_data.py              # Data migration
│   └── analyze_costs.py             # Cost analysis
│
├── docs/                             # Project documentation
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
│
├── out/                              # Output directory
│   ├── digests/                     # Daily digests (JSON)
│   └── reports/                     # German reports (Markdown)
│
├── .env.example                      # Example environment variables
├── .gitignore                        # Git ignore patterns
├── pyproject.toml                    # Project metadata & dependencies
├── README.md                         # Project overview
└── LICENSE                           # License file
```

## Why the Src Layout?

### Benefits

1. **Test Isolation**: Tests import the installed package, not local files
2. **Import Clarity**: Forces proper package imports (`from newsanalysis.core import Article`)
3. **Editable Installs**: `pip install -e .` works correctly
4. **Build Correctness**: Ensures packaging includes all necessary files
5. **Industry Standard**: Recommended by pytest, Nox, and modern Python tooling

### Comparison with Flat Layout

**Flat Layout** (❌ Not recommended):
```
newsanalysis/
├── newsanalysis/
│   ├── __init__.py
│   └── core.py
├── tests/
├── setup.py
```

**Src Layout** (✅ Recommended):
```
newsanalysis/
├── src/
│   └── newsanalysis/
│       ├── __init__.py
│       └── core.py
├── tests/
├── pyproject.toml
```

**Why Flat Layout Fails**:
- Tests import local files instead of installed package
- Brittle in CI/CD environments
- Import errors hard to debug
- Package installation issues

## Module Organization Principles

### 1. **Single Responsibility**

Each module has one clear purpose:
- `collectors/`: Only collect URLs and metadata
- `filters/`: Only classify article relevance
- `scrapers/`: Only extract content from web pages
- `analyzers/`: Only summarize and analyze content
- `digest/`: Only generate daily digests

### 2. **Dependency Injection**

Modules receive dependencies via constructor:
```python
class AIFilter:
    def __init__(self,
                 openai_client: OpenAIClient,
                 cache: ClassificationCache,
                 cost_tracker: CostTracker):
        self.openai_client = openai_client
        self.cache = cache
        self.cost_tracker = cost_tracker
```

Benefits:
- Easy to test (inject mocks)
- Flexible configuration
- Clear dependencies

### 3. **Interface Abstraction**

Use protocols/abstract classes for swappable implementations:
```python
from typing import Protocol

class ContentExtractor(Protocol):
    def extract(self, url: str) -> Optional[str]:
        """Extract article content from URL"""
        ...

class TrafilaturaExtractor:
    def extract(self, url: str) -> Optional[str]:
        # Implementation using trafilatura
        ...

class PlaywrightExtractor:
    def extract(self, url: str) -> Optional[str]:
        # Implementation using Playwright
        ...
```

### 4. **Layered Architecture**

**Presentation Layer** (`cli/`):
- User interface
- Command parsing
- Output formatting

**Business Logic** (`pipeline/`, `services/`):
- Domain rules
- Workflow orchestration
- Data transformation

**Data Access** (`database/`):
- Database queries
- ORM models
- Repository pattern

**Integration** (`integrations/`):
- External API clients
- Third-party services

**Core** (`core/`):
- Domain models (Pydantic)
- Shared types
- Business entities

## Key Files Explained

### `pyproject.toml`

Modern Python project configuration (replaces `setup.py`, `requirements.txt`, `setup.cfg`):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "newsanalysis"
version = "2.0.0"
description = "AI-powered Swiss news analysis for credit risk intelligence"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Creditreform Switzerland"}
]

dependencies = [
    "openai>=1.47",
    "pydantic>=2.8",
    "trafilatura>=2.0.0",
    "feedparser>=6.0.11",
    "beautifulsoup4>=4.11.0",
    "requests>=2.28.0",
    "python-dotenv>=1.0.0",
    "PyYAML>=6.0",
    "sqlalchemy>=2.0",
    "jinja2>=3.0.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-mock>=3.14",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.11",
]

playwright = [
    "playwright>=1.40",
]

[project.scripts]
newsanalysis = "newsanalysis.cli.main:main"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=newsanalysis --cov-report=term-missing"
```

### `src/newsanalysis/__init__.py`

Package initialization:
```python
"""NewsAnalysis 2.0 - AI-powered Swiss news intelligence for credit risk."""

from newsanalysis.__version__ import __version__

__all__ = ["__version__"]
```

### `src/newsanalysis/__version__.py`

Version management:
```python
"""Package version."""

__version__ = "2.0.0"
```

### `src/newsanalysis/cli/main.py`

CLI entry point using Click:
```python
"""Command-line interface for NewsAnalysis."""

import click
from newsanalysis.__version__ import __version__
from newsanalysis.cli.commands import run, export, stats

@click.group()
@click.version_option(version=__version__)
def cli():
    """NewsAnalysis - AI-powered Swiss news intelligence."""
    pass

cli.add_command(run.run)
cli.add_command(export.export)
cli.add_command(stats.stats)

def main():
    """Main entry point."""
    cli()

if __name__ == "__main__":
    main()
```

### `tests/conftest.py`

Pytest fixtures for testing:
```python
"""Shared pytest fixtures."""

import pytest
from newsanalysis.database.connection import init_database
from newsanalysis.core.config import Config

@pytest.fixture
def test_config():
    """Test configuration."""
    return Config.from_file("tests/fixtures/test_config.yaml")

@pytest.fixture
def test_db():
    """In-memory test database."""
    conn = init_database(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client."""
    return mocker.Mock()
```

## Configuration Management

### Environment Variables (`.env`)

```bash
# OpenAI API
OPENAI_API_KEY=sk-...
MODEL_NANO=gpt-5-nano
MODEL_MINI=gpt-4o-mini

# Database
DB_PATH=./news.db

# Pipeline
CONFIDENCE_THRESHOLD=0.70
MAX_ITEMS_PER_FEED=120
REQUEST_TIMEOUT_SEC=12

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration Loading

```python
"""Configuration management."""

from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Config:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_nano: str = os.getenv("MODEL_NANO", "gpt-5-nano")
    model_mini: str = os.getenv("MODEL_MINI", "gpt-4o-mini")

    # Database
    db_path: str = os.getenv("DB_PATH", "./news.db")

    # Pipeline
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.70"))
    max_items_per_feed: int = int(os.getenv("MAX_ITEMS_PER_FEED", "120"))

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()
```

## Dependency Injection

### Factory Pattern for Module Creation

```python
"""Module factory for dependency injection."""

from newsanalysis.pipeline.collectors import RSSCollector, SitemapCollector
from newsanalysis.pipeline.filters import AIFilter
from newsanalysis.integrations.openai_client import OpenAIClient
from newsanalysis.database.repositories import ArticleRepository

class ModuleFactory:
    def __init__(self, config: Config):
        self.config = config
        self._openai_client = None
        self._article_repo = None

    @property
    def openai_client(self) -> OpenAIClient:
        if self._openai_client is None:
            self._openai_client = OpenAIClient(
                api_key=self.config.openai_api_key,
                default_model=self.config.model_nano
            )
        return self._openai_client

    @property
    def article_repo(self) -> ArticleRepository:
        if self._article_repo is None:
            self._article_repo = ArticleRepository(
                db_path=self.config.db_path
            )
        return self._article_repo

    def create_filter(self) -> AIFilter:
        return AIFilter(
            openai_client=self.openai_client,
            article_repo=self.article_repo,
            confidence_threshold=self.config.confidence_threshold
        )

    # ... other factory methods
```

## Packaging & Distribution

### Installation

**Development Install** (editable):
```bash
# Clone repository
git clone https://github.com/creditreform/newsanalysis.git
cd newsanalysis

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install with Playwright support
pip install -e ".[dev,playwright]"
playwright install chromium
```

**Production Install**:
```bash
pip install newsanalysis
```

### Building Distribution

```bash
# Build wheel and source distribution
pip install build
python -m build

# Output: dist/newsanalysis-2.0.0-py3-none-any.whl
#         dist/newsanalysis-2.0.0.tar.gz
```

## Code Quality Tools

### Ruff (Linting & Formatting)

```bash
# Check code quality
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Mypy (Type Checking)

```bash
# Type check
mypy src/newsanalysis
```

### Pytest (Testing)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=newsanalysis --cov-report=html

# Run specific test file
pytest tests/unit/test_collectors.py

# Run tests matching pattern
pytest -k "test_rss"
```

## Import Conventions

### Absolute Imports (Preferred)

```python
# ✅ Good: Absolute imports
from newsanalysis.core.article import Article
from newsanalysis.pipeline.collectors import RSSCollector
from newsanalysis.database.repositories import ArticleRepository
```

### Relative Imports (Avoid)

```python
# ❌ Bad: Relative imports
from ..core.article import Article
from .collectors import RSSCollector
```

### Type Hints

```python
from typing import Optional, List
from newsanalysis.core.article import Article

def filter_articles(
    articles: List[Article],
    confidence_threshold: float = 0.70
) -> List[Article]:
    """Filter articles by confidence threshold.

    Args:
        articles: List of articles to filter
        confidence_threshold: Minimum confidence (0.0-1.0)

    Returns:
        Filtered list of articles
    """
    return [a for a in articles if a.confidence >= confidence_threshold]
```

## Error Handling

### Custom Exception Hierarchy

```python
"""Custom exceptions."""

class NewsAnalysisError(Exception):
    """Base exception for NewsAnalysis."""

class PipelineError(NewsAnalysisError):
    """Pipeline execution error."""

class CollectionError(PipelineError):
    """News collection error."""

class FilterError(PipelineError):
    """Filtering error."""

class ScrapingError(PipelineError):
    """Content scraping error."""

class SummarizationError(PipelineError):
    """Summarization error."""

class DigestError(PipelineError):
    """Digest generation error."""
```

## Logging

### Structured Logging with Structlog

```python
"""Logging setup."""

import structlog
import logging
import sys

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Configure structured logging."""

    if log_format == "json":
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

# Usage
logger = structlog.get_logger(__name__)
logger.info("pipeline_started", run_id="abc123", mode="full")
```

## Best Practices Summary

1. **Use src layout** for all projects
2. **Type hints everywhere** (enforce with mypy)
3. **Dependency injection** for testability
4. **Repository pattern** for data access
5. **Pydantic models** for data validation
6. **Structured logging** with context
7. **Comprehensive tests** (unit + integration)
8. **Code quality tools** (ruff, mypy, pytest)
9. **pyproject.toml** for configuration
10. **Clear module boundaries** (no circular imports)

## Next Steps

- Review API integration strategy (06-api-integration-strategy.md)
- Understand data models and schemas (11-data-models-schemas.md)
- Begin implementation with Phase 1 (Foundation)
