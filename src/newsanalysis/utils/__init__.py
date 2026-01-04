"""Utility modules for NewsAnalysis."""

from newsanalysis.utils.date_utils import (
    format_datetime,
    get_date_range,
    is_same_day,
    is_within_hours,
    now_utc,
    parse_date,
)
from newsanalysis.utils.exceptions import (
    APIError,
    CollectionError,
    ConfigurationError,
    CostLimitError,
    DatabaseError,
    DigestError,
    FilterError,
    NewsAnalysisError,
    OpenAIAPIError,
    PipelineError,
    RateLimitError,
    ScrapingError,
    SummarizationError,
    ValidationError,
)
from newsanalysis.utils.logging import get_logger, setup_logging
from newsanalysis.utils.text_utils import (
    clean_whitespace,
    count_words,
    extract_domain,
    hash_url,
    normalize_url,
    sanitize_filename,
    split_into_sentences,
    truncate_text,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    # Exceptions
    "NewsAnalysisError",
    "ConfigurationError",
    "PipelineError",
    "CollectionError",
    "FilterError",
    "ScrapingError",
    "SummarizationError",
    "DigestError",
    "DatabaseError",
    "APIError",
    "OpenAIAPIError",
    "RateLimitError",
    "CostLimitError",
    "ValidationError",
    # Date utils
    "parse_date",
    "is_within_hours",
    "is_same_day",
    "now_utc",
    "format_datetime",
    "get_date_range",
    # Text utils
    "normalize_url",
    "hash_url",
    "truncate_text",
    "clean_whitespace",
    "extract_domain",
    "split_into_sentences",
    "count_words",
    "sanitize_filename",
]
