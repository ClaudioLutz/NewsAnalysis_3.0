"""Text processing utilities."""

import hashlib
import re
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL by removing tracking parameters and fragments.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    # Parse URL
    parsed = urlparse(url)

    # Remove common tracking parameters
    tracking_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "source",
    }

    # Parse query string
    query_params = parse_qs(parsed.query)

    # Filter out tracking parameters
    clean_params = {
        k: v for k, v in query_params.items() if k.lower() not in tracking_params
    }

    # Rebuild query string
    clean_query = urlencode(clean_params, doseq=True) if clean_params else ""

    # Rebuild URL without fragment
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc.lower(),  # Lowercase domain
            parsed.path,
            parsed.params,
            clean_query,
            "",  # Remove fragment
        )
    )

    # Remove trailing slash
    if normalized.endswith("/"):
        normalized = normalized[:-1]

    return normalized


def hash_url(url: str) -> str:
    """Generate SHA-256 hash of URL for fast lookups.

    Args:
        url: URL to hash

    Returns:
        64-character hex string (SHA-256 hash)
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def clean_whitespace(text: str) -> str:
    """Clean excessive whitespace from text.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Replace multiple spaces with single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: URL to parse

    Returns:
        Domain name
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Simple sentence splitting (good enough for German/English)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def count_words(text: str) -> int:
    """Count words in text.

    Args:
        text: Text to count

    Returns:
        Number of words
    """
    return len(text.split())


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove invalid characters for Windows and Unix
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Limit length
    max_length = 200
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        name = name[: max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name

    return filename
