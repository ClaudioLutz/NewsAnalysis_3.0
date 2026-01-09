"""Article domain models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from newsanalysis.core.enums import ArticleTopic, ExtractionMethod


class ArticleMetadata(BaseModel):
    """Article metadata from news collection."""

    url: HttpUrl
    normalized_url: str
    url_hash: str = Field(..., min_length=64, max_length=64)

    title: str = Field(..., min_length=1)
    source: str
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.now)

    feed_priority: int = Field(..., ge=1, le=3)  # 1=govt, 2=financial, 3=general

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://www.nzz.ch/wirtschaft/konkurs-bei-ubs-ag",
                "normalized_url": "https://www.nzz.ch/wirtschaft/konkurs-bei-ubs-ag",
                "url_hash": "a" * 64,
                "title": "UBS AG meldet Konkurs an",
                "source": "NZZ",
                "published_at": "2026-01-04T10:30:00",
                "collected_at": "2026-01-04T11:00:00",
                "feed_priority": 3,
            }
        }
    }


class ClassificationResult(BaseModel):
    """AI classification of article relevance."""

    is_match: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    topic: str
    reason: str = Field(..., max_length=200)
    filtered_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_match": True,
                "confidence": 0.85,
                "topic": "creditreform_insights",
                "reason": "Article discusses bankruptcy proceedings",
                "filtered_at": "2026-01-04T11:05:00",
            }
        }
    }


class ScrapedContent(BaseModel):
    """Scraped article content."""

    content: str = Field(..., min_length=100)
    author: Optional[str] = None
    content_length: int = Field(..., gt=0)

    extraction_method: ExtractionMethod
    extraction_quality: float = Field(..., ge=0.0, le=1.0)
    scraped_at: datetime = Field(default_factory=datetime.now)

    @field_validator("content_length", mode="before")
    @classmethod
    def set_content_length(cls, v: int, info) -> int:
        """Auto-calculate content length from content field."""
        if info.data.get("content"):
            return len(info.data["content"])
        return v


class EntityData(BaseModel):
    """Extracted entities from article."""

    companies: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


class ArticleSummary(BaseModel):
    """AI-generated article summary."""

    summary_title: str = Field(..., max_length=200)
    summary: str = Field(...)  # Removed length constraints
    key_points: List[str] = Field(...)  # Removed length constraints
    entities: EntityData
    topic: ArticleTopic = Field(default=ArticleTopic.OTHER)

    summarized_at: datetime = Field(default_factory=datetime.now)

    @field_validator("key_points")
    @classmethod
    def validate_key_points(cls, v: List[str]) -> List[str]:
        """Ensure at least 2 key points."""
        if len(v) < 2:
            raise ValueError("At least 2 key points required")
        return v


class ArticleImage(BaseModel):
    """Metadata for an image associated with an article."""

    # Database ID
    id: Optional[int] = None

    # Article Reference
    article_id: Optional[int] = None

    # Image URLs and Paths
    image_url: str = Field(..., min_length=1)
    local_path: Optional[str] = None

    # Image Metadata
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    format: Optional[str] = None  # JPEG, PNG, WebP, etc.
    file_size: Optional[int] = None  # In bytes

    # Extraction Details
    extraction_quality: Optional[str] = None  # 'high', 'medium', 'low'
    is_featured: bool = False  # Primary article image
    extraction_method: Optional[str] = None  # 'newspaper3k', 'beautifulsoup', 'og_image'

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)


class Article(BaseModel):
    """Complete article with all processing stages."""

    # Database ID
    id: Optional[int] = None

    # Metadata (Step 1)
    url: HttpUrl
    normalized_url: str
    url_hash: str
    title: str
    source: str
    published_at: Optional[datetime]
    collected_at: datetime
    feed_priority: int

    # Classification (Step 2)
    is_match: Optional[bool] = None
    confidence: Optional[float] = None
    topic: Optional[str] = None
    classification_reason: Optional[str] = None
    filtered_at: Optional[datetime] = None

    # Content (Step 3)
    content: Optional[str] = None
    author: Optional[str] = None
    content_length: Optional[int] = None
    extraction_method: Optional[ExtractionMethod] = None
    extraction_quality: Optional[float] = None
    scraped_at: Optional[datetime] = None

    # Summary (Step 4)
    summary_title: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    entities: Optional[EntityData] = None
    summarized_at: Optional[datetime] = None

    # Pipeline State
    pipeline_stage: str = "collected"
    processing_status: str = "pending"
    error_message: Optional[str] = None
    error_count: int = 0

    # Semantic Deduplication
    is_duplicate: bool = False
    canonical_url_hash: Optional[str] = None

    # Images (Step 3.5 - after scraping)
    images: Optional[List[ArticleImage]] = None

    # Digest Grouping (added at digest generation time)
    duplicate_sources: Optional[List[dict]] = None  # Sources from grouped similar articles

    # Metadata
    run_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
