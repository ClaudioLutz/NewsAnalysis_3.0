"""Date and time utilities."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as date_parser


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse date string to datetime object.

    Handles various date formats commonly found in news feeds.

    Args:
        date_string: Date string to parse

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Use dateutil parser for flexible parsing
        dt = date_parser.parse(date_string)

        # Ensure timezone-aware datetime (convert to UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except (ValueError, TypeError):
        return None


def is_within_hours(dt: datetime, hours: int) -> bool:
    """Check if datetime is within specified hours from now.

    Args:
        dt: Datetime to check
        hours: Number of hours

    Returns:
        True if datetime is within hours from now
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    return dt >= cutoff


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """Check if two datetimes are on the same day.

    Args:
        dt1: First datetime
        dt2: Second datetime

    Returns:
        True if same day
    """
    return dt1.date() == dt2.date()


def now_utc() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current UTC datetime (timezone-aware)
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string.

    Args:
        dt: Datetime to format
        format_str: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def get_date_range(days: int = 7) -> tuple[datetime, datetime]:
    """Get datetime range for the last N days.

    Args:
        days: Number of days

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    end = now_utc()
    start = end - timedelta(days=days)
    return start, end
