# tests/unit/test_models.py
"""Unit tests for Pydantic models."""

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from newsanalysis.core.article import (
    Article,
    ArticleMetadata,
    ArticleSummary,
    ClassificationResult,
    EntityData,
)
from newsanalysis.core.config import FeedConfig
from newsanalysis.core.enums import ArticleTopic


@pytest.mark.unit
class TestArticle:
    """Tests for Article model."""

    def test_article_creation_with_required_fields(self):
        """Should create article with required fields."""
        article = Article(
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            url_hash="a" * 64,
            title="Test Article",
            source="Test Source",
            published_at=datetime.now(UTC),
            collected_at=datetime.now(UTC),
            feed_priority=3,
            run_id="test-run",
        )
        assert str(article.url) == "https://example.com/article"
        assert article.title == "Test Article"
        assert article.source == "Test Source"

    def test_article_with_metadata(self):
        """Should create article with all fields."""
        article = Article(
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            url_hash="a" * 64,
            title="Test Article",
            source="Test Source",
            published_at=datetime.now(UTC),
            collected_at=datetime.now(UTC),
            feed_priority=3,
            run_id="test-run",
            author="Test Author",
        )
        assert article.author == "Test Author"

    def test_article_with_published_date(self):
        """Should handle published date."""
        pub_date = datetime.now(UTC)
        article = Article(
            url="https://example.com/article",
            normalized_url="https://example.com/article",
            url_hash="a" * 64,
            title="Test Article",
            source="Test Source",
            published_at=pub_date,
            collected_at=datetime.now(UTC),
            feed_priority=3,
            run_id="test-run",
        )
        assert article.published_at == pub_date

    def test_article_requires_url(self):
        """Should require URL field."""
        with pytest.raises(ValidationError):
            Article(
                normalized_url="https://example.com/article",
                url_hash="a" * 64,
                title="Test Article",
                source="Test Source",
                published_at=datetime.now(UTC),
                collected_at=datetime.now(UTC),
                feed_priority=3,
                run_id="test-run",
            )

    def test_article_requires_title(self):
        """Should require title field."""
        with pytest.raises(ValidationError):
            Article(
                url="https://example.com/article",
                normalized_url="https://example.com/article",
                url_hash="a" * 64,
                source="Test Source",
                published_at=datetime.now(UTC),
                collected_at=datetime.now(UTC),
                feed_priority=3,
                run_id="test-run",
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
            type="rss",
            priority=3,
            max_age_hours=48,
            rate_limit_seconds=5.0,
            enabled=True,
        )
        assert config.name == "Test Feed"
        assert config.type == "rss"
        assert config.enabled is True

    def test_feed_config_validates_feed_type(self):
        """Should validate feed type."""
        # Valid feed types
        for feed_type in ["rss", "sitemap", "html"]:
            FeedConfig(
                name="Test",
                url="https://example.com",
                type=feed_type,
                priority=3,
                max_age_hours=48,
                rate_limit_seconds=5.0,
            )

        # Invalid feed type
        with pytest.raises(ValidationError):
            FeedConfig(
                name="Test",
                url="https://example.com",
                type="invalid",
                priority=3,
                max_age_hours=48,
                rate_limit_seconds=5.0,
            )

    def test_feed_config_default_enabled(self):
        """Should default enabled to True."""
        config = FeedConfig(
            name="Test",
            url="https://example.com",
            type="rss",
            priority=3,
            max_age_hours=48,
            rate_limit_seconds=5.0,
        )
        assert config.enabled is True


@pytest.mark.unit
class TestArticleTopic:
    """Tests for ArticleTopic enum."""

    def test_article_topic_valid_values(self):
        """Should create ArticleTopic from valid string values."""
        assert ArticleTopic("insolvency_bankruptcy") == ArticleTopic.INSOLVENCY_BANKRUPTCY
        assert ArticleTopic("credit_risk") == ArticleTopic.CREDIT_RISK
        assert ArticleTopic("business_scams") == ArticleTopic.BUSINESS_SCAMS
        assert ArticleTopic("board_changes") == ArticleTopic.BOARD_CHANGES

    def test_article_topic_all_13_values(self):
        """Should have exactly 13 topic values."""
        assert len(ArticleTopic) == 13

    def test_article_topic_invalid_value_raises(self):
        """Should raise ValueError for invalid topic string."""
        with pytest.raises(ValueError):
            ArticleTopic("invalid_topic")

    def test_article_topic_is_string_enum(self):
        """ArticleTopic should be usable as string."""
        topic = ArticleTopic.CREDIT_RISK
        assert topic.value == "credit_risk"
        # String enum value accessible via .value or direct comparison
        assert topic == "credit_risk"


@pytest.mark.unit
class TestArticleSummary:
    """Tests for ArticleSummary model with topic field."""

    def test_article_summary_with_topic(self):
        """Should create ArticleSummary with explicit topic."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=["Point 1", "Point 2"],
            entities=EntityData(),
            topic=ArticleTopic.INSOLVENCY_BANKRUPTCY,
        )
        assert summary.topic == ArticleTopic.INSOLVENCY_BANKRUPTCY

    def test_article_summary_default_topic_is_market_intelligence(self):
        """Should default topic to MARKET_INTELLIGENCE when not provided."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=["Point 1", "Point 2"],
            entities=EntityData(),
        )
        assert summary.topic == ArticleTopic.MARKET_INTELLIGENCE

    def test_article_summary_topic_from_string(self):
        """Should accept topic as string value."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=["Point 1", "Point 2"],
            entities=EntityData(),
            topic="credit_risk",
        )
        assert summary.topic == ArticleTopic.CREDIT_RISK

    def test_article_summary_allows_zero_key_points(self):
        """Should allow 0 key points (simple articles)."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=[],
            entities=EntityData(),
        )
        assert len(summary.key_points) == 0

    def test_article_summary_allows_up_to_four_key_points(self):
        """Should allow up to 4 key points."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=["Point 1", "Point 2", "Point 3", "Point 4"],
            entities=EntityData(),
        )
        assert len(summary.key_points) == 4

    def test_article_summary_truncates_excess_key_points(self):
        """Should truncate to 4 if more than 4 key points provided."""
        summary = ArticleSummary(
            summary_title="Test Title",
            summary="Test summary text",
            key_points=["P1", "P2", "P3", "P4", "P5"],
            entities=EntityData(),
        )
        assert len(summary.key_points) == 4
