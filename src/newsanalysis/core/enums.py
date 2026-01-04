"""Enums for NewsAnalysis system."""

from enum import Enum


class ExtractionMethod(str, Enum):
    """Content extraction methods."""

    TRAFILATURA = "trafilatura"
    PLAYWRIGHT = "playwright"
    JSON_LD = "json_ld"


class PipelineStage(str, Enum):
    """Pipeline processing stages."""

    COLLECTED = "collected"
    FILTERED = "filtered"
    SCRAPED = "scraped"
    SUMMARIZED = "summarized"
    COMPLETED = "completed"


class ProcessingStatus(str, Enum):
    """Processing status for pipeline items."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FeedType(str, Enum):
    """News feed types."""

    RSS = "rss"
    SITEMAP = "sitemap"
    HTML = "html"


class PipelineMode(str, Enum):
    """Pipeline execution modes."""

    FULL = "full"
    EXPRESS = "express"
    EXPORT = "export"
