# Development Guide

## Prerequisites

- **Python 3.11+** (Python 3.13 supported)
- **Git** for version control
- API keys (at least one required):
  - DeepSeek API key (recommended for classification)
  - Google API key (recommended for summarization)
  - OpenAI API key (fallback provider)

## Environment Setup

### 1. Clone and Create Virtual Environment

```bash
# Clone repository
git clone <repository-url>
cd news_analysis_3.0

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Optional: Install Playwright for JS-rendered pages
pip install -e ".[playwright]"
playwright install chromium

# Optional: Install caching dependencies
pip install -e ".[cache]"
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: At least one LLM provider
OPENAI_API_KEY=sk-your-key
DEEPSEEK_API_KEY=your-deepseek-key
GOOGLE_API_KEY=your-google-key
```

### 4. Initialize Database

```bash
python scripts/init_db.py
```

## Running the Application

### Basic Commands

```bash
# Run full pipeline
newsanalysis run

# Run with article limit (for testing)
newsanalysis run --limit 10

# Skip specific stages
newsanalysis run --skip-scraping
newsanalysis run --skip-summarization

# Export digest
newsanalysis export                    # Today's digest
newsanalysis export --date 2026-01-03  # Specific date
newsanalysis export --format german    # German report

# Show statistics
newsanalysis stats
newsanalysis stats --detailed

# Health check
newsanalysis health --verbose
```

### Development Scripts

```bash
# Test multi-provider LLM setup
python scripts/test_multi_provider.py

# Check API costs
python scripts/check_costs.py

# Run test pipeline with limited data
python scripts/run_test_pipeline.py
```

## Code Quality

### Linting and Formatting

```bash
# Run ruff linter
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/
```

### Type Checking

```bash
# Run mypy
mypy src/newsanalysis
```

### All Quality Checks

```bash
# Run all checks (recommended before commit)
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/newsanalysis
```

## Testing

### Running Tests

```bash
# All tests with coverage
pytest

# Unit tests only
pytest tests/unit -v

# Integration tests only
pytest tests/integration -v

# End-to-end tests
pytest tests/test_e2e.py -v

# Specific test file
pytest tests/unit/test_models.py -v

# With coverage report
pytest --cov=newsanalysis --cov-report=html
# Open htmlcov/index.html in browser
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Coverage Targets

| Type | Target | Current |
|------|--------|---------|
| Unit | >90% | TBD |
| Integration | >80% | TBD |
| E2E | >70% | TBD |
| **Overall** | **>80%** | TBD |

## Project Structure

See [source-tree-analysis.md](source-tree-analysis.md) for detailed structure.

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `src/newsanalysis/` | Main application code |
| `tests/` | Test suite |
| `config/` | YAML configurations |
| `scripts/` | Utility scripts |
| `docs/` | Documentation |

## Adding New Features

### Adding a New Collector

1. Create `src/newsanalysis/pipeline/collectors/new_collector.py`
2. Inherit from `BaseCollector` in `base.py`
3. Implement `collect()` method
4. Register in `__init__.py` and `create_collector()` factory
5. Add tests in `tests/unit/` and `tests/integration/`

### Adding a New LLM Provider

1. Implement client in `src/newsanalysis/integrations/`
2. Update `ProviderFactory` to support new provider
3. Add configuration in `.env.example`
4. Update documentation

### Modifying Database Schema

1. Update `src/newsanalysis/database/schema.sql`
2. Create migration script in `scripts/`
3. Update affected models in `src/newsanalysis/core/`
4. Update repository methods
5. Update tests

## Configuration

### Environment Variables

See `.env.example` for all available options:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API key |
| `GOOGLE_API_KEY` | - | Google Gemini API key |
| `DB_PATH` | `./news.db` | Database file path |
| `CONFIDENCE_THRESHOLD` | `0.70` | Classification threshold |
| `DAILY_COST_LIMIT` | `2.0` | Daily API cost limit |

### YAML Configuration

| File | Purpose |
|------|---------|
| `config/feeds.yaml` | News source definitions |
| `config/topics.yaml` | Classification topics |
| `config/prompts/` | LLM prompt templates |

## Debugging

### Logging

```bash
# Set log level in .env
LOG_LEVEL=DEBUG

# View structured logs
newsanalysis run 2>&1 | jq .
```

### Database Inspection

```bash
# SQLite CLI
sqlite3 news.db

# Common queries
.tables
SELECT COUNT(*) FROM articles;
SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;
```

### API Call Tracking

```bash
# Check API costs
python scripts/check_costs.py

# View recent API calls
sqlite3 news.db "SELECT * FROM api_calls ORDER BY created_at DESC LIMIT 10;"
```

## Troubleshooting

See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for common issues and solutions.

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **API key errors**: Check `.env` file configuration
3. **Database locked**: Close other connections, check permissions
4. **Playwright errors**: Run `playwright install chromium`

## Contributing

### Commit Convention

Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run quality checks
4. Create PR with description
5. Address review feedback

### Documentation

- Update relevant docs for any user-facing changes
- Add story file in `docs/stories/` for significant changes
- Follow the format: `YYYYMMddHHmmss-topic-slug.md`
