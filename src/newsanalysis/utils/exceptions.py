"""Custom exceptions for NewsAnalysis."""


class NewsAnalysisError(Exception):
    """Base exception for NewsAnalysis."""


class ConfigurationError(NewsAnalysisError):
    """Configuration error."""


class PipelineError(NewsAnalysisError):
    """Pipeline execution error."""


class CollectionError(PipelineError):
    """News collection error."""


class CollectorError(PipelineError):
    """Collector error."""


class FilterError(PipelineError):
    """Filtering error."""


class ScrapingError(PipelineError):
    """Content scraping error."""


class SummarizationError(PipelineError):
    """Summarization error."""


class DigestError(PipelineError):
    """Digest generation error."""


class DatabaseError(NewsAnalysisError):
    """Database operation error."""


class APIError(NewsAnalysisError):
    """External API error."""


class AIServiceError(APIError):
    """AI service error."""


class OpenAIAPIError(APIError):
    """OpenAI API error."""


class RateLimitError(APIError):
    """Rate limit exceeded error."""


class CostLimitError(NewsAnalysisError):
    """Cost limit exceeded error."""


class ValidationError(NewsAnalysisError):
    """Data validation error."""
