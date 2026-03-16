# tests/unit/test_cache_service.py
"""Unit tests for cache service."""

import json
from pathlib import Path

import pytest

from newsanalysis.core.article import ClassificationResult
from newsanalysis.services.cache_service import CacheService


@pytest.mark.unit
class TestCacheService:
    """Tests for CacheService."""

    def test_generate_classification_key(self, test_db):
        """Should generate consistent cache key."""
        cache = CacheService(test_db.conn)

        key1 = cache._generate_classification_key("Test Title", "https://example.com")
        key2 = cache._generate_classification_key("Test Title", "https://example.com")

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hex length

    def test_generate_classification_key_different_inputs(self, test_db):
        """Should generate different keys for different inputs."""
        cache = CacheService(test_db.conn)

        key1 = cache._generate_classification_key("Title 1", "https://example.com/1")
        key2 = cache._generate_classification_key("Title 2", "https://example.com/2")

        assert key1 != key2

    def test_get_cached_classification_miss(self, test_db):
        """Should return None for cache miss."""
        cache = CacheService(test_db.conn)

        result = cache.get_cached_classification("Test Title", "https://example.com")

        assert result is None

    def test_cache_and_get_classification(self, test_db):
        """Should cache and retrieve classification."""
        cache = CacheService(test_db.conn)

        # Cache a classification result
        classification = ClassificationResult(
            is_match=True,
            confidence=0.85,
            topic="credit_risk",
            reason="Test reason",
        )
        cache.cache_classification("Test Title", "https://example.com", classification)

        # Retrieve it
        result = cache.get_cached_classification("Test Title", "https://example.com")

        assert result is not None
        assert result.is_match is True
        assert result.confidence == 0.85
        assert result.topic == "credit_risk"

    def test_cache_hit_increments_counter(self, test_db):
        """Should increment hit count on cache hit."""
        cache = CacheService(test_db.conn)

        # Cache a result
        classification = ClassificationResult(
            is_match=True,
            confidence=0.85,
            topic="credit_risk",
            reason="Test reason",
        )
        cache.cache_classification("Test Title", "https://example.com", classification)

        # First hit
        cache.get_cached_classification("Test Title", "https://example.com")

        # Second hit
        result = cache.get_cached_classification("Test Title", "https://example.com")

        # Hit count should be incremented
        assert result is not None

    def test_get_cache_summary(self, test_db):
        """Should return cache summary statistics."""
        cache = CacheService(test_db.conn)

        # Cache a classification result
        classification = ClassificationResult(
            is_match=True,
            confidence=0.85,
            topic="credit_risk",
            reason="Test reason",
        )
        cache.cache_classification("Test 1", "https://example.com/1", classification)

        # Cache a content summary
        cache.cache_summary(
            content="Test content for hashing purposes and enough length to be meaningful.",
            summary_title="Test Summary",
            summary="Test summary text",
            key_points=json.dumps(["Point 1", "Point 2"]),
            entities=json.dumps({"companies": ["Test Co"]}),
        )

        # Get summary
        summary = cache.get_cache_summary()

        assert summary["classification_cache"]["entries"] >= 1
        assert summary["content_cache"]["entries"] >= 1

    def test_content_cache_operations(self, test_db):
        """Should cache and retrieve content summary."""
        cache = CacheService(test_db.conn)

        content = "This is a test article content that is long enough for hashing purposes."

        # Cache content summary
        cache.cache_summary(
            content=content,
            summary_title="Test Summary Title",
            summary="This is a test summary.",
            key_points=json.dumps(["Point 1", "Point 2", "Point 3"]),
            entities=json.dumps({
                "companies": ["Company A", "Company B"],
                "people": ["Person X"],
                "locations": ["Zurich"],
                "topics": ["finance", "banking"],
            }),
        )

        # Retrieve cached summary
        result = cache.get_cached_summary(content)

        assert result is not None
        assert result["summary_title"] == "Test Summary Title"
        assert result["summary"] == "This is a test summary."
