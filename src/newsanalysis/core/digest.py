"""Digest domain models."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from newsanalysis.core.article import Article


class MetaAnalysis(BaseModel):
    """Meta-analysis of daily articles."""

    key_themes: List[str] = Field(..., min_length=1, max_length=5)
    credit_risk_signals: List[str] = Field(default_factory=list, max_length=5)
    regulatory_updates: List[str] = Field(default_factory=list, max_length=5)
    market_insights: List[str] = Field(default_factory=list, max_length=5)


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
