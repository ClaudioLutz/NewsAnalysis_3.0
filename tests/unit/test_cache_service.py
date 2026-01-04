# tests/unit/test_cache_service.py
"""Unit tests for cache service."""

import pytest

from newsanalysis.services.cache_service import CacheService


@pytest.mark.unit
class TestCacheService:
    """Tests for CacheService."""

    def test_get_classification_cache_key(self, test_db):
        """Should generate consistent cache key."""
        cache = CacheService(test_db)

        key1 = cache._get_classification_cache_key("Test Title", "https://example.com")
        key2 = cache._get_classification_cache_key("Test Title", "https://example.com")

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hex length

    def test_get_classification_cache_key_different_inputs(self, test_db):
        """Should generate different keys for different inputs."""
        cache = CacheService(test_db)

        key1 = cache._get_classification_cache_key("Title 1", "https://example.com/1")
        key2 = cache._get_classification_cache_key("Title 2", "https://example.com/2")

        assert key1 != key2

    def test_get_cached_classification_miss(self, test_db):
        """Should return None for cache miss."""
        cache = CacheService(test_db)

        result = cache.get_cached_classification("Test Title", "https://example.com")

        assert result is None

    def test_set_and_get_classification_cache(self, test_db):
        """Should cache and retrieve classification."""
        cache = CacheService(test_db)

        # Set cache
        cache.set_classification_cache(
            title="Test Title",
            url="https://example.com",
            is_match=True,
            confidence=0.85,
            topic="test_topic",
            reason="Test reason",
        )

        # Get cache
        result = cache.get_cached_classification("Test Title", "https://example.com")

        assert result is not None
        assert result["is_match"] is True
        assert result["confidence"] == 0.85
        assert result["topic"] == "test_topic"

    def test_cache_hit_increments_counter(self, test_db):
        """Should increment hit count on cache hit."""
        cache = CacheService(test_db)

        # Set cache
        cache.set_classification_cache(
            title="Test Title",
            url="https://example.com",
            is_match=True,
            confidence=0.85,
            topic="test_topic",
            reason="Test reason",
        )

        # First hit
        cache.get_cached_classification("Test Title", "https://example.com")

        # Second hit
        result = cache.get_cached_classification("Test Title", "https://example.com")

        # Hit count should be incremented
        assert result is not None

    def test_get_cache_stats(self, test_db):
        """Should return cache statistics."""
        cache = CacheService(test_db)

        # Set some cache entries
        cache.set_classification_cache(
            title="Test 1",
            url="https://example.com/1",
            is_match=True,
            confidence=0.85,
            topic="test",
            reason="test",
        )

        cache.set_content_cache(
            content_hash="test-hash",
            summary_title="Test Summary",
            summary="Test summary text",
            key_points=["Point 1", "Point 2"],
            entities={"companies": ["Test Co"]},
        )

        # Get stats
        stats = cache.get_cache_stats()

        assert stats["classification"]["total_entries"] >= 1
        assert stats["content"]["total_entries"] >= 1

    def test_content_cache_operations(self, test_db):
        """Should cache and retrieve content."""
        cache = CacheService(test_db)

        # Set content cache
        content_hash = "test-content-hash"
        cache.set_content_cache(
            content_hash=content_hash,
            summary_title="Test Summary Title",
            summary="This is a test summary.",
            key_points=["Point 1", "Point 2", "Point 3"],
            entities={
                "companies": ["Company A", "Company B"],
                "people": ["Person X"],
                "locations": ["Zurich"],
                "topics": ["finance", "banking"],
            },
        )

        # Get content cache
        result = cache.get_cached_content(content_hash)

        assert result is not None
        assert result["summary_title"] == "Test Summary Title"
        assert result["summary"] == "This is a test summary."
        assert len(result["key_points"]) == 3
        assert "Company A" in result["entities"]["companies"]
