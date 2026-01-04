"""Core domain models and configurations."""

from newsanalysis.core.article import (
    Article,
    ArticleMetadata,
    ArticleSummary,
    ClassificationResult,
    EntityData,
    ScrapedContent,
)
from newsanalysis.core.config import (
    Config,
    FeedConfig,
    PipelineConfig,
    PromptConfig,
    TopicConfig,
)
from newsanalysis.core.digest import DailyDigest, MetaAnalysis
from newsanalysis.core.enums import (
    ExtractionMethod,
    FeedType,
    PipelineMode,
    PipelineStage,
    ProcessingStatus,
)

__all__ = [
    # Article models
    "Article",
    "ArticleMetadata",
    "ArticleSummary",
    "ClassificationResult",
    "EntityData",
    "ScrapedContent",
    # Digest models
    "DailyDigest",
    "MetaAnalysis",
    # Configuration models
    "Config",
    "FeedConfig",
    "PipelineConfig",
    "PromptConfig",
    "TopicConfig",
    # Enums
    "ExtractionMethod",
    "FeedType",
    "PipelineMode",
    "PipelineStage",
    "ProcessingStatus",
]
