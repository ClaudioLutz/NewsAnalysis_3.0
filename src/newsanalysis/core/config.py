"""Configuration models."""

from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class PromptConfig(BaseModel):
    """Prompt template configuration."""

    system_prompt: str
    user_prompt_template: str
    output_schema: Dict


class Config(BaseSettings):
    """Main application configuration from environment variables."""

    # OpenAI API
    openai_api_key: str = Field(..., min_length=1)
    model_nano: str = "gpt-4o-mini"
    model_mini: str = "gpt-4o-mini"
    model_sonnet: str = "gpt-4o"

    # Database
    db_path: Path = Path("./news.db")
    db_backup_dir: Path = Path("./backups")

    # Pipeline Settings
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    max_items_per_feed: int = Field(default=120, gt=0)
    request_timeout_sec: int = Field(default=12, gt=0)
    scraping_timeout_sec: int = Field(default=30, gt=0)
    max_concurrent_requests: int = Field(default=10, gt=0)
    crawl_delay_sec: float = Field(default=2.0, ge=0.0)

    # Cost Limits
    daily_cost_limit: float = Field(default=2.0, gt=0.0)
    monthly_cost_limit: float = Field(default=50.0, gt=0.0)

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[Path] = None

    # Output
    output_dir: Path = Path("./out")

    # Feature Flags
    enable_batch_api: bool = True
    enable_caching: bool = True
    enable_playwright_fallback: bool = True
    skip_robots_txt: bool = False

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_paths(self) -> None:
        """Validate and create necessary paths."""
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "digests").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)

        # Create backup directory
        if self.db_backup_dir:
            self.db_backup_dir.mkdir(parents=True, exist_ok=True)

        # Create log directory
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
