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


class ArticleTopic(str, Enum):
    """Article topic classification for digest grouping.

    NOTE: Enum member order has no functional meaning.
    Display priority is controlled by TOPIC_PRIORITY list in german_formatter.py
    """

    INSOLVENCY_BANKRUPTCY = "insolvency_bankruptcy"
    CREDIT_RISK = "credit_risk"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    KYC_AML_SANCTIONS = "kyc_aml_sanctions"
    PAYMENT_BEHAVIOR = "payment_behavior"
    DEBT_COLLECTION = "debt_collection"
    BOARD_CHANGES = "board_changes"
    COMPANY_LIFECYCLE = "company_lifecycle"
    ECONOMIC_INDICATORS = "economic_indicators"
    MARKET_INTELLIGENCE = "market_intelligence"
    ECOMMERCE_FRAUD = "ecommerce_fraud"
    OTHER = "other"
