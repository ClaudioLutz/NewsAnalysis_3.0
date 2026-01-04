# tests/unit/test_models.py
"""Unit tests for Pydantic models."""

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from newsanalysis.core.article import (
    Article,
    ArticleMetadata,
    ClassificationResult,
)
from newsanalysis.core.config import FeedConfig


@pytest.mark.unit
class TestArticle:
    """Tests for Article model."""

    def test_article_creation_with_required_fields(self):
        """Should create article with required fields only."""
        article = Article(
            url="https://example.com/article",
            url_hash="test-hash",
            title="Test Article",
            source="Test Source",
        )
        assert article.url == "https://example.com/article"
        assert article.title == "Test Article"
        assert article.source == "Test Source"

    def test_article_with_metadata(self):
        """Should create article with metadata."""
        metadata = ArticleMetadata(
            author="Test Author",
            description="Test description",
            language="de",
        )
        article = Article(
            url="https://example.com/article",
            url_hash="test-hash",
            title="Test Article",
            source="Test Source",
            metadata=metadata,
        )
        assert article.metadata.author == "Test Author"
        assert article.metadata.language == "de"

    def test_article_with_published_date(self):
        """Should handle published date."""
        pub_date = datetime.now(UTC)
        article = Article(
            url="https://example.com/article",
            url_hash="test-hash",
            title="Test Article",
            source="Test Source",
            published_at=pub_date,
        )
        assert article.published_at == pub_date

    def test_article_requires_url(self):
        """Should require URL field."""
        with pytest.raises(ValidationError):
            Article(
                url_hash="test-hash",
                title="Test Article",
                source="Test Source",
            )

    def test_article_requires_title(self):
        """Should require title field."""
        with pytest.raises(ValidationError):
            Article(
                url="https://example.com/article",
                url_hash="test-hash",
                source="Test Source",
            )


@pytest.mark.unit
class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_classification_result_creation(self):
        """Should create classification result."""
        result = ClassificationResult(
            is_match=True,
            confidence=0.85,
            topic="creditreform_insights",
            reason="Article discusses bankruptcy",
        )
        assert result.is_match is True
        assert result.confidence == 0.85
        assert result.topic == "creditreform_insights"

    def test_classification_result_validates_confidence_range(self):
        """Should validate confidence is between 0 and 1."""
        # Valid confidence
        ClassificationResult(
            is_match=True,
            confidence=0.85,
            topic="test",
            reason="test",
        )

        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            ClassificationResult(
                is_match=True,
                confidence=1.5,
                topic="test",
                reason="test",
            )

        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            ClassificationResult(
                is_match=True,
                confidence=-0.1,
                topic="test",
                reason="test",
            )


@pytest.mark.unit
class TestFeedConfig:
    """Tests for FeedConfig model."""

    def test_feed_config_creation(self):
        """Should create feed configuration."""
        config = FeedConfig(
            name="Test Feed",
            url="https://example.com/feed.xml",
            feed_type="rss",
            enabled=True,
        )
        assert config.name == "Test Feed"
        assert config.feed_type == "rss"
        assert config.enabled is True

    def test_feed_config_validates_feed_type(self):
        """Should validate feed type."""
        # Valid feed types
        for feed_type in ["rss", "sitemap", "html"]:
            FeedConfig(
                name="Test",
                url="https://example.com",
                feed_type=feed_type,
            )

        # Invalid feed type
        with pytest.raises(ValidationError):
            FeedConfig(
                name="Test",
                url="https://example.com",
                feed_type="invalid",
            )

    def test_feed_config_default_enabled(self):
        """Should default enabled to True."""
        config = FeedConfig(
            name="Test",
            url="https://example.com",
            feed_type="rss",
        )
        assert config.enabled is True
