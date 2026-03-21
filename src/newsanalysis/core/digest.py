"""Digest domain models."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from newsanalysis.core.article import Article


class ArticleGroup(BaseModel):
    """A thematic article group created by LLM meta-analysis."""

    label: str = Field(..., description="Short German label, e.g. 'Bausektor unter Druck'")
    icon: str = Field(default="", description="BMP Unicode HTML entity, e.g. '&#9888;'")
    article_indices: List[int] = Field(
        ..., description="1-based indices of articles belonging to this group"
    )


class MetaAnalysis(BaseModel):
    """Meta-analysis of daily articles."""

    key_themes: List[str] = Field(..., min_length=1, max_length=5)
    credit_risk_signals: List[str] = Field(default_factory=list, max_length=5)
    regulatory_updates: List[str] = Field(default_factory=list, max_length=5)
    market_insights: List[str] = Field(default_factory=list, max_length=5)

    # Executive summary for "Heute in 30 Sekunden" section
    executive_summary: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="1-5 factual sentences combining related articles into patterns",
    )

    # Dynamic thematic grouping of articles (replaces static topic grouping in email)
    # No max_length here — validated and trimmed in digest_generator._validate_article_groups()
    article_groups: List[ArticleGroup] = Field(
        default_factory=list,
        description="Dynamic thematic groups for email layout (trimmed to max 10 post-validation)",
    )


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

    @field_validator("article_count", mode="before")
    @classmethod
    def set_article_count(cls, v: int, info) -> int:
        """Auto-calculate article count from articles list."""
        if info.data.get("articles"):
            return len(info.data["articles"])
        return v
