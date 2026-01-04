# Technology Stack

## Overview

This document provides the complete technology stack for the NewsAnalysis system with rationale for each choice, alternatives considered, and version requirements.

## Core Technologies

### Python 3.11+

**Why**:
- Excellent ecosystem for web scraping and AI
- Type hints for code quality
- Performance improvements in 3.11+ (10-60% faster)
- AsyncIO for concurrent I/O operations
- Strong community and library support

**Alternatives Considered**:
- Node.js: Worse for AI/ML, better async but Python ecosystem superior
- Go: Faster but limited AI libraries, steeper learning curve
- Java: Verbose, slower development, unnecessary complexity

**Version Requirement**: >=3.11 (for performance and type hint improvements)

### SQLite 3.38+

**Why**:
- Zero configuration (embedded database)
- Perfect for <100K articles
- Excellent FTS5 full-text search
- ACID compliant
- Single-file backup
- Low operational overhead

**Alternatives Considered**:
- PostgreSQL: Better for >100K articles, but overkill for local deployment
- MySQL/MariaDB: Similar to PostgreSQL, unnecessary complexity
- MongoDB: NoSQL not suitable for structured news data

**Migration Path**: PostgreSQL when dataset >100K articles

**Version Requirement**: >=3.38 (for modern FTS5 features)

### OpenAI API

**Why**:
- State-of-the-art AI quality
- Structured output support (JSON schema)
- Batch API for 50% cost savings
- No model hosting complexity
- Reliable uptime

**Alternatives Considered**:
- Self-hosted LLMs (Llama, Mistral): Lower quality, high hosting costs
- Anthropic Claude: Similar quality, but no batch API
- Google Gemini: Less mature API, limited Swiss German support

**Cost**: ~$35/month for 100 articles/day (optimized)

## Key Libraries

### Web Scraping

**trafilatura 2.0+**
```bash
pip install trafilatura>=2.0.0
```

**Why**:
- Best-in-class content extraction
- 70-85% success rate on Swiss news sites
- Fast (2-3 seconds per article)
- Language detection (German optimization)
- Minimal dependencies

**Usage**: Primary content extraction method

---

**playwright 1.40+** (optional)
```bash
pip install playwright>=1.40
playwright install chromium
```

**Why**:
- Handles JavaScript-heavy sites
- 95% success rate (fallback method)
- Cookie consent handling
- Modern browser automation

**Usage**: Fallback when Trafilatura fails

**Alternatives Considered**:
- Selenium: Slower, more complex setup
- BeautifulSoup only: Cannot handle JavaScript
- Newspaper3k: Unmaintained, lower quality

---

**feedparser 6.0+**
```bash
pip install feedparser>=6.0.11
```

**Why**:
- Industry standard for RSS parsing
- Handles malformed feeds (bozo mode)
- Multiple date format support
- Robust and well-tested

---

**beautifulsoup4 4.11+**
```bash
pip install beautifulsoup4>=4.11.0
```

**Why**:
- HTML/XML parsing for sitemaps
- JSON-LD extraction
- Simple API
- Wide adoption

**Parser**: lxml (fast) with html.parser fallback

### AI Integration

**openai 1.47+**
```bash
pip install openai>=1.47
```

**Why**:
- Official Python SDK
- Async support
- Structured outputs (JSON schema)
- Batch API support
- Type hints

---

**langchain-openai 0.2+** (optional)
```bash
pip install langchain-openai>=0.2.0
```

**Why**: Optional for advanced prompt chaining and agent patterns

**Use Cases**: Future enhancements (multi-step reasoning)

### Data Validation

**pydantic 2.8+**
```bash
pip install pydantic>=2.8
```

**Why**:
- Runtime data validation
- JSON schema generation
- Type safety
- Fast (Rust-based in v2)
- Excellent error messages

**Usage**: All data models (Article, Digest, Config, etc.)

### Configuration

**python-dotenv 1.0+**
```bash
pip install python-dotenv>=1.0.0
```

**Why**:
- Simple .env file loading
- Widely adopted
- Zero dependencies

---

**PyYAML 6.0+**
```bash
pip install PyYAML>=6.0
```

**Why**:
- Human-readable config files
- Nested structures
- Industry standard

### Database

**sqlalchemy 2.0+** (optional)
```bash
pip install sqlalchemy>=2.0
```

**Why**:
- Database-agnostic ORM
- Easy migration to PostgreSQL
- Type-safe queries
- Connection pooling

**Alternative**: Direct sqlite3 (simpler, less abstraction)

### Testing

**pytest 8.0+**
```bash
pip install pytest>=8.0
```

**Why**:
- Industry standard
- Rich plugin ecosystem
- Fixtures and parametrization
- Excellent error messages

---

**pytest-asyncio 0.24+**
```bash
pip install pytest-asyncio>=0.24
```

**Why**: Async test support

---

**pytest-mock 3.14+**
```bash
pip install pytest-mock>=3.14
```

**Why**: Simplified mocking with pytest fixtures

---

**pytest-cov 5.0+**
```bash
pip install pytest-cov>=5.0
```

**Why**: Code coverage reporting

### Code Quality

**ruff 0.6+**
```bash
pip install ruff>=0.6
```

**Why**:
- 10-100x faster than Flake8/Black
- All-in-one (linting + formatting)
- Replaces: Flake8, Black, isort, pyupgrade
- Auto-fix capabilities

**Configuration**: See pyproject.toml in project structure doc

---

**mypy 1.11+**
```bash
pip install mypy>=1.11
```

**Why**:
- Static type checking
- Catches bugs before runtime
- Improves code quality
- IDE integration

### Logging

**structlog 24.0+**
```bash
pip install structlog>=24.0.0
```

**Why**:
- Structured logging (JSON)
- Context binding
- Better than stdlib logging
- Machine-readable logs

### HTTP Client

**requests 2.28+**
```bash
pip install requests>=2.28.0
```

**Why**:
- Simple, reliable HTTP client
- Connection pooling
- Retry strategies
- Industry standard

**Alternative**: httpx (async-first, but requests sufficient)

### Templating

**jinja2 3.0+**
```bash
pip install jinja2>=3.0.0
```

**Why**: Template-based output formatting (Markdown reports)

## Optional Enhancements

### Redis (Caching)

**When to Add**: >1000 articles/day OR distributed deployment

```bash
pip install redis>=5.0
```

**Why**:
- Fast in-memory caching
- Distributed cache support
- Pub/sub for multi-instance coordination

**Use Cases**:
- Semantic cache for classifications
- Rate limiting across instances
- Shared state for distributed pipeline

### Celery (Task Queue)

**When to Add**: Async/background processing needed

```bash
pip install celery>=5.4
```

**Why**:
- Distributed task queue
- Retry logic
- Scheduled tasks
- Monitoring (Flower)

**Use Cases**:
- Parallel scraping across workers
- Background digest generation
- Scheduled maintenance tasks

### FastAPI (Web Interface)

**When to Add**: Need web UI or REST API

```bash
pip install fastapi>=0.115
pip install uvicorn>=0.30
```

**Why**:
- Fast, modern Python web framework
- Auto-generated API docs
- Type-safe
- Async support

**Use Cases**:
- Web dashboard for monitoring
- REST API for integrations
- Manual article submission

### Sentence Transformers (Semantic Caching)

**When to Add**: Semantic cache optimization (Phase 4)

```bash
pip install sentence-transformers>=2.7
```

**Why**: Generate embeddings for semantic similarity

**Model**: all-MiniLM-L6-v2 (fast, small, good quality)

### FAISS (Vector Search)

**When to Add**: Semantic cache optimization (Phase 4)

```bash
pip install faiss-cpu>=1.8  # CPU version
# OR
pip install faiss-gpu>=1.8  # GPU version
```

**Why**: Fast similarity search for embeddings

## Avoided Technologies

### Why NOT MongoDB
- News data is structured (fits SQL better)
- ACID compliance important
- Relational queries frequent
- SQLite/PostgreSQL simpler

### Why NOT Scrapy
- Overkill for simple scraping
- Heavy framework overhead
- Trafilatura + Playwright sufficient
- Simpler to maintain

### Why NOT Kubernetes
- Local deployment target
- Single-server sufficient for <1000 articles/day
- Operational complexity not justified
- Docker Compose sufficient if needed

### Why NOT Airflow/Prefect
- Orchestration overkill
- Simple sequential pipeline
- Cron sufficient for scheduling
- Reduces complexity

## Dependency Management

### pyproject.toml (Recommended)

```toml
[project]
dependencies = [
    "openai>=1.47",
    "pydantic>=2.8",
    "trafilatura>=2.0.0",
    "feedparser>=6.0.11",
    "beautifulsoup4>=4.11.0",
    "requests>=2.28.0",
    "python-dotenv>=1.0.0",
    "PyYAML>=6.0",
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

playwright = ["playwright>=1.40"]
cache = ["redis>=5.0", "sentence-transformers>=2.7", "faiss-cpu>=1.8"]
```

### Version Pinning

**Development**: Use ranges (>=X.Y) for flexibility

**Production**: Pin exact versions for reproducibility

```bash
# Generate exact versions
pip freeze > requirements.txt

# Install exact versions
pip install -r requirements.txt
```

## Platform Compatibility

### Operating Systems

✅ **Linux** (Ubuntu 20.04+, Debian 11+)
- Primary target
- Best performance
- Systemd integration

✅ **Windows** (10, 11, Server 2019+)
- Fully supported
- Task Scheduler integration
- Slightly slower Trafilatura performance

✅ **macOS** (12+)
- Fully supported
- Development environment

### Python Versions

✅ **Python 3.11** (Recommended)
- Best performance
- All features supported

✅ **Python 3.12**
- Fully supported
- Even faster

❌ **Python 3.10 and below**
- Not supported (missing type hint features)

## Installation Commands

### Minimal Installation

```bash
pip install newsanalysis
```

### Development Installation

```bash
pip install -e ".[dev]"
```

### Full Installation (All Features)

```bash
pip install -e ".[dev,playwright,cache]"
playwright install chromium
```

## Upgrade Strategy

### Minor Updates (Patch Versions)

```bash
pip install --upgrade newsanalysis
```

### Major Updates

1. Review CHANGELOG
2. Test in development environment
3. Update production dependencies
4. Monitor for issues

## Technology Roadmap

### Phase 1 (MVP) - Current
- SQLite
- Trafilatura + Playwright
- OpenAI API
- Basic caching

### Phase 2 (Optimization)
- OpenAI Batch API
- Semantic caching (embeddings)
- Redis cache layer

### Phase 3 (Scale)
- PostgreSQL migration
- Celery task queue
- FastAPI web interface

### Phase 4 (Enterprise)
- Multi-tenant support
- Advanced analytics
- Custom ML models

## Next Steps

- Review data models and schemas (11-data-models-schemas.md)
- Review implementation phases (12-implementation-phases.md)
- Install required dependencies
