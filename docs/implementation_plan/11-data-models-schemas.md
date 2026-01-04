# Data Models & Schemas

## Overview

This document defines the core data models, Pydantic schemas, JSON schemas for AI responses, and database models for the NewsAnalysis system.

## Core Domain Models (Pydantic)

### ArticleMetadata

Collected article metadata (Step 1 output):

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

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

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.nzz.ch/wirtschaft/konkurs-bei-ubs-ag",
                "normalized_url": "https://www.nzz.ch/wirtschaft/konkurs-bei-ubs-ag",
                "url_hash": "a" * 64,
                "title": "UBS AG meldet Konkurs an",
                "source": "NZZ",
                "published_at": "2026-01-04T10:30:00",
                "collected_at": "2026-01-04T11:00:00",
                "feed_priority": 3
            }
        }
```

### ClassificationResult

AI classification result (Step 2 output):

```python
class ClassificationResult(BaseModel):
    """AI classification of article relevance."""

    is_match: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    topic: str
    reason: str = Field(..., max_length=200)
    filtered_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "is_match": True,
                "confidence": 0.85,
                "topic": "creditreform_insights",
                "reason": "Article discusses bankruptcy proceedings",
                "filtered_at": "2026-01-04T11:05:00"
            }
        }
```

### ScrapedContent

Extracted article content (Step 3 output):

```python
from enum import Enum

class ExtractionMethod(str, Enum):
    TRAFILATURA = "trafilatura"
    PLAYWRIGHT = "playwright"
    JSON_LD = "json_ld"

class ScrapedContent(BaseModel):
    """Scraped article content."""

    content: str = Field(..., min_length=100)
    author: Optional[str] = None
    content_length: int = Field(..., gt=0)

    extraction_method: ExtractionMethod
    extraction_quality: float = Field(..., ge=0.0, le=1.0)
    scraped_at: datetime = Field(default_factory=datetime.now)

    @validator('content_length', always=True)
    def set_content_length(cls, v, values):
        if 'content' in values:
            return len(values['content'])
        return v
```

### ArticleSummary

AI-generated summary (Step 4 output):

```python
class EntityData(BaseModel):
    """Extracted entities from article."""

    companies: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)

class ArticleSummary(BaseModel):
    """AI-generated article summary."""

    summary_title: str = Field(..., max_length=150)
    summary: str = Field(..., min_length=100, max_length=1000)
    key_points: List[str] = Field(..., min_items=2, max_items=8)
    entities: EntityData

    summarized_at: datetime = Field(default_factory=datetime.now)

    @validator('key_points')
    def validate_key_points(cls, v):
        if len(v) < 2:
            raise ValueError('At least 2 key points required')
        return v
```

### Complete Article

Full article combining all pipeline stages:

```python
class Article(BaseModel):
    """Complete article with all processing stages."""

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

    # Metadata
    run_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### DailyDigest

Daily digest output (Step 5):

```python
class MetaAnalysis(BaseModel):
    """Meta-analysis of daily articles."""

    key_themes: List[str] = Field(..., min_items=1, max_items=5)
    credit_risk_signals: List[str] = Field(default_factory=list, max_items=5)
    regulatory_updates: List[str] = Field(default_factory=list, max_items=5)
    market_insights: List[str] = Field(default_factory=list, max_items=5)

class DailyDigest(BaseModel):
    """Daily news digest."""

    date: date
    version: int = Field(..., ge=1)

    articles: List[Article]
    article_count: int
    cluster_count: Optional[int] = None

    meta_analysis: MetaAnalysis

    generated_at: datetime = Field(default_factory=datetime.now)
    run_id: str

    @validator('article_count', always=True)
    def set_article_count(cls, v, values):
        if 'articles' in values:
            return len(values['articles'])
        return v
```

## JSON Schemas for AI Responses

### Classification Schema

```json
{
  "type": "object",
  "properties": {
    "match": {
      "type": "boolean",
      "description": "Whether article is relevant"
    },
    "conf": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence score"
    },
    "topic": {
      "type": "string",
      "description": "Topic category"
    },
    "reason": {
      "type": "string",
      "maxLength": 100,
      "description": "Brief explanation"
    }
  },
  "required": ["match", "conf", "topic", "reason"],
  "additionalProperties": false
}
```

### Summary Schema

```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "maxLength": 150,
      "description": "Normalized article title"
    },
    "summary": {
      "type": "string",
      "minLength": 100,
      "maxLength": 1000,
      "description": "Article summary (150-200 words)"
    },
    "key_points": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 2,
      "maxItems": 8,
      "description": "Key bullet points"
    },
    "entities": {
      "type": "object",
      "properties": {
        "companies": {"type": "array", "items": {"type": "string"}},
        "people": {"type": "array", "items": {"type": "string"}},
        "locations": {"type": "array", "items": {"type": "string"}},
        "topics": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["companies", "people", "locations", "topics"]
    }
  },
  "required": ["title", "summary", "key_points", "entities"],
  "additionalProperties": false
}
```

### Meta-Analysis Schema

```json
{
  "type": "object",
  "properties": {
    "key_themes": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "maxItems": 5
    },
    "credit_risk_signals": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 5
    },
    "regulatory_updates": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 5
    },
    "market_insights": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": 5
    }
  },
  "required": ["key_themes", "credit_risk_signals", "regulatory_updates", "market_insights"]
}
```

## Database Models (SQLAlchemy)

### Article Model

```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ArticleDB(Base):
    """SQLAlchemy model for articles table."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # URL Identification
    url = Column(String, nullable=False)
    normalized_url = Column(String, nullable=False)
    url_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Metadata
    title = Column(String, nullable=False)
    source = Column(String, nullable=False, index=True)
    published_at = Column(DateTime)
    collected_at = Column(DateTime, nullable=False)
    feed_priority = Column(Integer, nullable=False)

    # Classification
    is_match = Column(Boolean)
    confidence = Column(Float)
    topic = Column(String)
    classification_reason = Column(Text)
    filtered_at = Column(DateTime)

    # Content
    content = Column(Text)
    author = Column(String)
    content_length = Column(Integer)
    extraction_method = Column(String)
    extraction_quality = Column(Float)
    scraped_at = Column(DateTime)

    # Summary
    summary_title = Column(String)
    summary = Column(Text)
    key_points = Column(Text)  # JSON array
    entities = Column(Text)  # JSON object
    summarized_at = Column(DateTime)

    # Pipeline State
    pipeline_stage = Column(String, nullable=False, default="collected", index=True)
    processing_status = Column(String, default="pending")
    digest_date = Column(DateTime, index=True)
    digest_version = Column(Integer)
    included_in_digest = Column(Boolean, default=False)

    # Error Tracking
    error_message = Column(Text)
    error_count = Column(Integer, default=0)

    # Metadata
    run_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    def to_domain(self) -> Article:
        """Convert database model to domain model."""
        return Article(
            url=self.url,
            normalized_url=self.normalized_url,
            url_hash=self.url_hash,
            title=self.title,
            source=self.source,
            published_at=self.published_at,
            collected_at=self.collected_at,
            feed_priority=self.feed_priority,
            is_match=self.is_match,
            confidence=self.confidence,
            topic=self.topic,
            classification_reason=self.classification_reason,
            filtered_at=self.filtered_at,
            content=self.content,
            author=self.author,
            content_length=self.content_length,
            extraction_method=self.extraction_method,
            extraction_quality=self.extraction_quality,
            scraped_at=self.scraped_at,
            summary_title=self.summary_title,
            summary=self.summary,
            key_points=json.loads(self.key_points) if self.key_points else None,
            entities=EntityData(**json.loads(self.entities)) if self.entities else None,
            summarized_at=self.summarized_at,
            pipeline_stage=self.pipeline_stage,
            processing_status=self.processing_status,
            error_message=self.error_message,
            error_count=self.error_count,
            run_id=self.run_id,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @classmethod
    def from_domain(cls, article: Article) -> "ArticleDB":
        """Create database model from domain model."""
        return cls(
            url=str(article.url),
            normalized_url=article.normalized_url,
            url_hash=article.url_hash,
            title=article.title,
            source=article.source,
            published_at=article.published_at,
            collected_at=article.collected_at,
            feed_priority=article.feed_priority,
            # ... (all other fields)
        )
```

## Configuration Models

```python
class FeedConfig(BaseModel):
    """News feed configuration."""

    name: str
    type: Literal["rss", "sitemap", "html"]
    url: HttpUrl
    priority: int = Field(..., ge=1, le=3)
    max_age_hours: int = Field(..., gt=0)
    rate_limit_seconds: float = Field(..., gt=0)
    enabled: bool = True

class TopicConfig(BaseModel):
    """Topic classification configuration."""

    enabled: bool = True
    confidence_threshold: float = Field(..., ge=0.0, le=1.0)
    max_articles_per_run: int = Field(..., gt=0)
    max_article_age_days: int = Field(..., ge=0)
    focus_areas: Dict[str, List[str]]

class PipelineConfig(BaseModel):
    """Pipeline execution configuration."""

    mode: Literal["full", "express", "export"] = "full"
    limit: Optional[int] = None
    skip_collection: bool = False
    skip_filtering: bool = False
    skip_scraping: bool = False
    skip_summarization: bool = False
    skip_digest: bool = False
```

## Validation Examples

### Pydantic Validation

```python
# Valid article
article = Article(
    url="https://www.nzz.ch/article",
    normalized_url="https://www.nzz.ch/article",
    url_hash="a" * 64,
    title="Test Article",
    source="NZZ",
    collected_at=datetime.now(),
    feed_priority=3,
    run_id="run-123"
)

# Invalid - will raise ValidationError
try:
    article = Article(
        url="not-a-url",  # Invalid URL
        feed_priority=10,  # Out of range
        confidence=1.5  # Out of range
    )
except ValidationError as e:
    print(e.json())
```

## Schema Evolution

### Adding Fields

1. Add field to Pydantic model with default value
2. Add database migration
3. Update repository mapping
4. Deploy (backward compatible)

### Removing Fields

1. Mark deprecated in Pydantic model
2. Stop writing to field
3. Deploy and wait for data migration
4. Remove from database schema
5. Remove from Pydantic model

## Next Steps

- Review implementation phases (12-implementation-phases.md)
- Implement Pydantic models
- Create database migrations
