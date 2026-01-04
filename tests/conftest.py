# tests/conftest.py
"""Shared test fixtures and configuration."""

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, Mock

import pytest

from newsanalysis.core.article import Article, ArticleMetadata
from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Test configuration with temporary paths."""
    return Config(
        openai_api_key="test-key-12345",
        db_path=str(tmp_path / "test.db"),
        output_dir=str(tmp_path / "out"),
        cache_ttl_classification=30,
        cache_ttl_content=90,
        daily_cost_limit=100.0,
        confidence_threshold=0.70,
        max_age_hours=48,
    )


@pytest.fixture
def test_db(tmp_path: Path) -> Generator[DatabaseConnection, None, None]:
    """In-memory SQLite database with schema initialized."""
    db_path = tmp_path / "test.db"
    conn = DatabaseConnection(str(db_path))

    # Initialize schema
    schema_path = Path(__file__).parent.parent / "src" / "newsanalysis" / "database" / "schema.sql"
    with open(schema_path) as f:
        conn.conn.executescript(f.read())
    conn.conn.commit()

    yield conn

    conn.close()


@pytest.fixture
def sample_article() -> Article:
    """Sample article for testing."""
    return Article(
        url="https://www.nzz.ch/test-article",
        url_hash="test-hash-12345",
        title="Test Article: Swiss Company Files Bankruptcy",
        source="NZZ",
        published_at=datetime.now(UTC),
        metadata=ArticleMetadata(
            author="Test Author",
            description="Test description",
            language="de",
        ),
    )


@pytest.fixture
def sample_articles() -> list[Article]:
    """Multiple sample articles for batch testing."""
    return [
        Article(
            url=f"https://www.nzz.ch/article-{i}",
            url_hash=f"hash-{i}",
            title=f"Article {i}: Business News",
            source="NZZ",
            published_at=datetime.now(UTC),
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_rss_feed() -> str:
    """Sample RSS feed XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test RSS Feed</title>
    <link>https://example.com</link>
    <description>Test feed</description>
    <item>
      <title>Test Article 1</title>
      <link>https://example.com/article-1</link>
      <description>Test description 1</description>
      <pubDate>Sat, 04 Jan 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article-2</link>
      <description>Test description 2</description>
      <pubDate>Sat, 04 Jan 2026 11:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_sitemap() -> str:
    """Sample sitemap XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://example.com/article-1</loc>
    <news:news>
      <news:publication>
        <news:name>Example News</news:name>
        <news:language>de</news:language>
      </news:publication>
      <news:publication_date>2026-01-04T10:00:00Z</news:publication_date>
      <news:title>Test Article 1</news:title>
    </news:news>
  </url>
</urlset>"""


@pytest.fixture
def sample_article_html() -> str:
    """Sample article HTML."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Article</title>
</head>
<body>
    <article>
        <h1>Test Article Title</h1>
        <div class="author">By Test Author</div>
        <time datetime="2026-01-04">January 4, 2026</time>
        <div class="content">
            <p>This is the first paragraph of the article content.</p>
            <p>This is the second paragraph with more content.</p>
            <p>This is the third paragraph with even more content.</p>
        </div>
    </article>
</body>
</html>"""


@pytest.fixture
def mock_openai_client() -> Mock:
    """Mock OpenAI client for testing."""
    mock = Mock()

    # Mock classification response
    mock.create_completion = AsyncMock(return_value={
        "match": True,
        "conf": 0.85,
        "topic": "creditreform_insights",
        "reason": "Article discusses bankruptcy proceedings"
    })

    # Mock summary response
    mock.create_batch_completion = AsyncMock(return_value="batch-123")

    return mock


@pytest.fixture
def mock_http_response() -> Mock:
    """Mock HTTP response."""
    mock = Mock()
    mock.status_code = 200
    mock.text = """<html><body><article><p>Test content</p></article></body></html>"""
    mock.headers = {"content-type": "text/html"}
    return mock


@pytest.fixture
def sample_classification_result() -> dict:
    """Sample AI classification result."""
    return {
        "match": True,
        "conf": 0.85,
        "topic": "creditreform_insights",
        "reason": "Article discusses corporate bankruptcy and credit risk"
    }


@pytest.fixture
def sample_summary_result() -> dict:
    """Sample AI summary result."""
    return {
        "title": "Swiss Company Files for Bankruptcy",
        "summary": "A major Swiss company has filed for bankruptcy protection...",
        "key_points": [
            "Company filed Chapter 11 bankruptcy",
            "Affected 500+ employees",
            "Creditors owed CHF 50 million"
        ],
        "entities": {
            "companies": ["Swiss Corp AG"],
            "people": ["CEO John Doe"],
            "locations": ["Zurich", "Switzerland"],
            "topics": ["bankruptcy", "credit_risk"]
        }
    }


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


# Pytest configuration
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "asyncio: Async tests")
