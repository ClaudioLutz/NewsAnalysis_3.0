# Testing & Quality Assurance

## Overview

Comprehensive testing ensures reliability, maintainability, and confidence in system behavior. This document outlines testing strategies, quality gates, and tools for the NewsAnalysis system.

## Testing Pyramid

```
           /\
          /  \
         / E2E\        Few (5-10 tests)
        /------\       Slow, expensive, fragile
       /        \
      /Integration\    Some (20-30 tests)
     /------------\    Medium speed, moderate cost
    /              \
   /  Unit Tests    \  Many (100+ tests)
  /__________________\ Fast, cheap, reliable
```

## Unit Tests

### Purpose
Test individual functions and classes in isolation.

### Example: URL Normalizer

```python
# src/newsanalysis/services/url_normalizer.py
def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    # Remove tracking parameters
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Strip common tracking params
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'ref']
    filtered_params = {k: v for k, v in params.items() if k not in tracking_params}

    # Rebuild URL
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),  # Lowercase domain
        parsed.path,
        '',
        urlencode(filtered_params, doseq=True),
        ''  # Remove fragment
    ))

    return normalized

# tests/unit/test_url_normalizer.py
import pytest
from newsanalysis.services.url_normalizer import normalize_url

def test_normalize_url_removes_tracking_params():
    url = "https://www.nzz.ch/article?utm_source=google&id=123"
    expected = "https://www.nzz.ch/article?id=123"
    assert normalize_url(url) == expected

def test_normalize_url_lowercases_domain():
    url = "https://WWW.NZZ.CH/article"
    expected = "https://www.nzz.ch/article"
    assert normalize_url(url) == expected

def test_normalize_url_removes_fragment():
    url = "https://www.nzz.ch/article#section"
    expected = "https://www.nzz.ch/article"
    assert normalize_url(url) == expected
```

### Test Coverage Targets

- **Overall**: >80% code coverage
- **Core modules** (collectors, filters, scrapers): >90%
- **Utilities**: >95%
- **Integration layers**: >70%

## Integration Tests

### Purpose
Test module interactions and external dependencies.

### Example: Pipeline Integration

```python
# tests/integration/test_pipeline.py
import pytest
from newsanalysis.pipeline.orchestrator import PipelineOrchestrator
from newsanalysis.core.config import Config

@pytest.fixture
async def orchestrator(test_config, test_db):
    """Create orchestrator with test dependencies."""
    return PipelineOrchestrator(config=test_config, db=test_db)

@pytest.mark.asyncio
async def test_full_pipeline_execution(orchestrator, mock_openai_client):
    """Test complete pipeline execution."""

    # Configure mock responses
    mock_openai_client.complete.return_value = json.dumps({
        "match": True,
        "conf": 0.85,
        "topic": "creditreform_insights",
        "reason": "Article about bankruptcy"
    })

    # Run pipeline
    result = await orchestrator.run()

    # Assertions
    assert result.collected_count > 0
    assert result.filtered_count > 0
    assert result.status == "completed"
    assert mock_openai_client.complete.called
```

### Database Integration Tests

```python
@pytest.fixture
def test_db():
    """In-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")

    # Initialize schema
    with open("src/newsanalysis/database/schema.sql") as f:
        conn.executescript(f.read())

    yield conn
    conn.close()

def test_article_repository_save_and_find(test_db):
    """Test article repository operations."""
    repo = ArticleRepository(test_db)

    # Create article
    article = Article(
        url="https://www.nzz.ch/test",
        title="Test Article",
        source="NZZ"
    )

    # Save
    repo.save(article)

    # Find
    found = repo.find_by_url(article.url)
    assert found is not None
    assert found.title == article.title
```

## End-to-End Tests

### Purpose
Test complete workflows from input to output.

### Example: Daily Digest Generation

```python
@pytest.mark.e2e
@pytest.mark.slow
async def test_daily_digest_generation_end_to_end(tmp_path):
    """Test complete digest generation workflow."""

    # Setup: Configure with test data
    config = Config(
        db_path=tmp_path / "test.db",
        feeds_config=tmp_path / "feeds.yaml"
    )

    # Create test feed config
    create_test_feed_config(tmp_path / "feeds.yaml")

    # Run pipeline
    orchestrator = PipelineOrchestrator(config)
    result = await orchestrator.run()

    # Verify digest generated
    digest_file = tmp_path / f"digests/daily_digest_{date.today()}.json"
    assert digest_file.exists()

    # Verify digest content
    with open(digest_file) as f:
        digest = json.load(f)
        assert len(digest["articles"]) > 0
        assert "meta_analysis" in digest
```

## Testing LLM Interactions

### Challenges
- Non-deterministic outputs
- API costs for real calls
- Rate limits

### Strategies

**1. Mock OpenAI Responses**:
```python
@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client for testing."""
    mock = mocker.Mock()

    # Configure classification response
    mock.complete.return_value = json.dumps({
        "match": True,
        "conf": 0.85,
        "topic": "creditreform_insights",
        "reason": "Bankruptcy article"
    })

    return mock
```

**2. Golden Dataset**:
```python
# tests/fixtures/golden_dataset.json
[
  {
    "title": "UBS faces bankruptcy proceedings",
    "url": "https://example.com/ubs-bankruptcy",
    "expected_classification": {
      "match": true,
      "conf": 0.95,
      "topic": "creditreform_insights"
    }
  },
  ...
]

def test_classification_accuracy_on_golden_dataset():
    """Test classification accuracy against golden dataset."""

    with open("tests/fixtures/golden_dataset.json") as f:
        golden = json.load(f)

    correct = 0
    for item in golden:
        result = classify_article(item["title"], item["url"])

        if result.is_match == item["expected_classification"]["match"]:
            correct += 1

    accuracy = correct / len(golden)
    assert accuracy > 0.85  # 85% accuracy target
```

**3. Deterministic Testing**:
```python
# Use temperature=0 for deterministic outputs
response = await openai_client.complete(
    messages=messages,
    temperature=0.0  # Deterministic
)
```

**4. VCR (Record/Replay)**:
```python
import pytest
from pytest_recording import use_vcr

@pytest.mark.vcr
async def test_openai_classification_with_vcr():
    """Test OpenAI classification with recorded responses."""

    # First run: Records actual API responses
    # Subsequent runs: Replays recorded responses

    result = await openai_client.classify("Test article", "https://example.com")
    assert result.confidence > 0.5
```

## Test Fixtures

### Pytest Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def test_config():
    """Test configuration."""
    return Config(
        openai_api_key="test-key",
        db_path=":memory:",
        confidence_threshold=0.70
    )

@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed content."""
    with open("tests/fixtures/sample_rss.xml") as f:
        return f.read()

@pytest.fixture
def sample_article_html():
    """Sample article HTML."""
    with open("tests/fixtures/sample_article.html") as f:
        return f.read()

@pytest.fixture
async def mock_http_client(mocker):
    """Mock HTTP client."""
    mock = mocker.Mock()
    mock.get.return_value.text = sample_article_html()
    mock.get.return_value.status_code = 200
    return mock
```

## Code Quality Tools

### Ruff (Linting & Formatting)

```bash
# Configuration in pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A"]

# Run
ruff check src/ tests/
ruff format src/ tests/
```

### Mypy (Type Checking)

```bash
# Configuration in pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
check_untyped_defs = true

# Run
mypy src/newsanalysis
```

### Pytest (Testing Framework)

```bash
# Configuration in pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=newsanalysis --cov-report=term-missing --cov-report=html"

# Run
pytest                          # All tests
pytest tests/unit               # Unit tests only
pytest -k "test_classification" # Tests matching pattern
pytest --cov                    # With coverage
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run Ruff
        run: ruff check src/ tests/

      - name: Run Mypy
        run: mypy src/newsanalysis

      - name: Run tests
        run: pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Quality Gates

### Pre-Commit Checks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

### CI/CD Pipeline Gates

1. **Linting passes** (Ruff)
2. **Type checking passes** (Mypy)
3. **All tests pass** (Pytest)
4. **Coverage >80%** (pytest-cov)
5. **No security vulnerabilities** (bandit, safety)

## Performance Testing

### Load Testing

```python
import time

def test_pipeline_performance_under_load():
    """Test pipeline with 100 articles."""

    start = time.time()
    result = orchestrator.run()
    duration = time.time() - start

    # Assert performance targets
    assert duration < 300  # <5 minutes for 100 articles
    assert result.collected_count > 0
```

## Testing Best Practices

1. **Test behavior, not implementation**: Focus on outcomes, not internals
2. **One assertion per test**: Makes failures clear
3. **AAA pattern**: Arrange, Act, Assert
4. **Descriptive test names**: `test_normalize_url_removes_tracking_params`
5. **Use fixtures**: Reduce code duplication
6. **Mock external dependencies**: Isolate unit under test
7. **Test edge cases**: Null values, empty lists, errors
8. **Fast tests**: Unit tests <10ms, integration <1s
9. **Deterministic tests**: No random failures
10. **Coverage targets**: >80% overall, >90% critical paths

## Next Steps

- Review deployment guide (09-deployment-operations.md)
- Implement test suite for core modules
- Set up CI/CD pipeline
