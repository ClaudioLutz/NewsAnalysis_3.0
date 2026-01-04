# tests/unit/test_text_utils.py
"""Unit tests for text utilities."""

import pytest

from newsanalysis.utils.text import (
    clean_whitespace,
    hash_url,
    normalize_url,
    truncate_text,
)


@pytest.mark.unit
class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_normalize_url_removes_tracking_params(self):
        """Should remove UTM tracking parameters."""
        url = "https://www.nzz.ch/article?utm_source=google&utm_medium=social&id=123"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "id=123" in normalized

    def test_normalize_url_lowercases_domain(self):
        """Should lowercase the domain name."""
        url = "https://WWW.NZZ.CH/article"
        normalized = normalize_url(url)
        assert normalized == "https://www.nzz.ch/article"

    def test_normalize_url_removes_fragment(self):
        """Should remove URL fragment."""
        url = "https://www.nzz.ch/article#section"
        normalized = normalize_url(url)
        assert "#section" not in normalized

    def test_normalize_url_strips_trailing_slash(self):
        """Should remove trailing slash."""
        url = "https://www.nzz.ch/article/"
        normalized = normalize_url(url)
        assert normalized == "https://www.nzz.ch/article"

    def test_normalize_url_handles_http_to_https(self):
        """Should handle both HTTP and HTTPS."""
        url1 = "http://www.nzz.ch/article"
        url2 = "https://www.nzz.ch/article"
        assert normalize_url(url1) == normalize_url(url2).replace("https", "http")


@pytest.mark.unit
class TestHashUrl:
    """Tests for hash_url function."""

    def test_hash_url_creates_consistent_hash(self):
        """Should create same hash for same URL."""
        url = "https://www.nzz.ch/article"
        hash1 = hash_url(url)
        hash2 = hash_url(url)
        assert hash1 == hash2

    def test_hash_url_creates_different_hashes(self):
        """Should create different hashes for different URLs."""
        url1 = "https://www.nzz.ch/article-1"
        url2 = "https://www.nzz.ch/article-2"
        assert hash_url(url1) != hash_url(url2)

    def test_hash_url_returns_hex_string(self):
        """Should return hexadecimal string."""
        url = "https://www.nzz.ch/article"
        result = hash_url(url)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in result)


@pytest.mark.unit
class TestCleanWhitespace:
    """Tests for clean_whitespace function."""

    def test_clean_whitespace_removes_extra_spaces(self):
        """Should collapse multiple spaces to single space."""
        text = "Hello    world"
        assert clean_whitespace(text) == "Hello world"

    def test_clean_whitespace_removes_tabs_and_newlines(self):
        """Should remove tabs and newlines."""
        text = "Hello\t\n\r\nworld"
        assert clean_whitespace(text) == "Hello world"

    def test_clean_whitespace_trims_edges(self):
        """Should trim leading and trailing whitespace."""
        text = "   Hello world   "
        assert clean_whitespace(text) == "Hello world"

    def test_clean_whitespace_handles_empty_string(self):
        """Should handle empty string."""
        assert clean_whitespace("") == ""

    def test_clean_whitespace_handles_only_whitespace(self):
        """Should handle string with only whitespace."""
        assert clean_whitespace("   \t\n  ") == ""


@pytest.mark.unit
class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_text_preserves_short_text(self):
        """Should not truncate text shorter than max_length."""
        text = "Short text"
        assert truncate_text(text, 100) == text

    def test_truncate_text_adds_ellipsis(self):
        """Should add ellipsis when truncating."""
        text = "This is a very long text that needs to be truncated"
        result = truncate_text(text, 20)
        assert result.endswith("...")
        assert len(result) == 20

    def test_truncate_text_respects_max_length(self):
        """Should respect max_length parameter."""
        text = "A" * 100
        result = truncate_text(text, 50)
        assert len(result) == 50

    def test_truncate_text_handles_exact_length(self):
        """Should handle text exactly at max_length."""
        text = "A" * 50
        result = truncate_text(text, 50)
        assert result == text

    def test_truncate_text_with_custom_suffix(self):
        """Should use custom suffix when provided."""
        text = "This is a long text"
        result = truncate_text(text, 10, suffix="…")
        assert result.endswith("…")
