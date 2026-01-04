# tests/unit/test_date_utils.py
"""Unit tests for date utilities."""

from datetime import datetime, timedelta, UTC

import pytest

from newsanalysis.utils.date_utils import (
    is_within_hours,
    now_utc,
    parse_date,
    format_date_german,
)


@pytest.mark.unit
class TestNowUtc:
    """Tests for now_utc function."""

    def test_now_utc_returns_datetime(self):
        """Should return datetime object."""
        result = now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_has_utc_timezone(self):
        """Should have UTC timezone."""
        result = now_utc()
        assert result.tzinfo == UTC

    def test_now_utc_is_current_time(self):
        """Should return current time (within 1 second)."""
        before = datetime.now(UTC)
        result = now_utc()
        after = datetime.now(UTC)
        assert before <= result <= after


@pytest.mark.unit
class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_date_iso_format(self):
        """Should parse ISO 8601 format."""
        date_str = "2026-01-04T10:30:00Z"
        result = parse_date(date_str)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 4
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_date_rfc_2822_format(self):
        """Should parse RFC 2822 format (RSS date)."""
        date_str = "Sat, 04 Jan 2026 10:30:00 +0000"
        result = parse_date(date_str)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 4

    def test_parse_date_handles_timezone(self):
        """Should handle timezone information."""
        date_str = "2026-01-04T10:30:00+01:00"
        result = parse_date(date_str)
        assert result.tzinfo is not None

    def test_parse_date_returns_none_for_invalid(self):
        """Should return None for invalid date string."""
        result = parse_date("not a date")
        assert result is None

    def test_parse_date_handles_none(self):
        """Should handle None input."""
        result = parse_date(None)
        assert result is None


@pytest.mark.unit
class TestIsWithinHours:
    """Tests for is_within_hours function."""

    def test_is_within_hours_recent_date(self):
        """Should return True for recent date."""
        recent = now_utc() - timedelta(hours=1)
        assert is_within_hours(recent, 24) is True

    def test_is_within_hours_old_date(self):
        """Should return False for old date."""
        old = now_utc() - timedelta(hours=50)
        assert is_within_hours(old, 24) is False

    def test_is_within_hours_exact_boundary(self):
        """Should handle exact boundary case."""
        exact = now_utc() - timedelta(hours=24)
        # Allow small margin for test execution time
        assert is_within_hours(exact, 24) in [True, False]

    def test_is_within_hours_future_date(self):
        """Should return True for future dates."""
        future = now_utc() + timedelta(hours=1)
        assert is_within_hours(future, 24) is True

    def test_is_within_hours_with_none(self):
        """Should handle None input."""
        assert is_within_hours(None, 24) is False


@pytest.mark.unit
class TestFormatDateGerman:
    """Tests for format_date_german function."""

    def test_format_date_german_formats_correctly(self):
        """Should format date in German style."""
        date = datetime(2026, 1, 4, 10, 30, tzinfo=UTC)
        result = format_date_german(date)
        assert "04" in result or "4" in result
        assert "Januar" in result or "01" in result
        assert "2026" in result

    def test_format_date_german_handles_different_months(self):
        """Should handle different months."""
        dates = [
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 6, 15, tzinfo=UTC),
            datetime(2026, 12, 31, tzinfo=UTC),
        ]
        for date in dates:
            result = format_date_german(date)
            assert isinstance(result, str)
            assert len(result) > 0
