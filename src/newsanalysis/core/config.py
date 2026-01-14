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
    today_only: bool = False  # Only include articles collected today in digest


class PromptConfig(BaseModel):
    """Prompt template configuration."""

    system_prompt: str
    user_prompt_template: str
    output_schema: Dict


class Config(BaseSettings):
    """Main application configuration from environment variables."""

    # OpenAI API (Primary & Fallback)
    openai_api_key: str = Field(..., min_length=1)
    model_nano: str = "gpt-4o-mini"
    model_mini: str = "gpt-4o-mini"
    model_sonnet: str = "gpt-4o"

    # DeepSeek API (For Classification)
    deepseek_api_key: Optional[str] = Field(default=None)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Google Gemini API (For Summarization & Digest)
    google_api_key: Optional[str] = Field(default=None)
    gemini_model: str = "gemini-2.0-flash"

    # LLM Provider Selection
    classification_provider: Literal["deepseek", "openai"] = "deepseek"
    summarization_provider: Literal["gemini", "openai"] = "gemini"
    digest_provider: Literal["gemini", "openai"] = "gemini"

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
    log_dir: Path = Path("./logs")

    # Output
    output_dir: Path = Path("./out")

    # Feature Flags
    enable_batch_api: bool = True
    enable_caching: bool = True
    enable_playwright_fallback: bool = True
    skip_robots_txt: bool = False

    # Environment
    environment: Literal["development", "staging", "production"] = "development"

    # Email Settings
    email_recipients: Optional[str] = Field(
        default=None,
        description="Comma-separated list of email recipients",
    )
    email_subject_template: str = "Creditreform News-Digest: {date} - {count} relevante Artikel"
    email_auto_send: bool = Field(
        default=False,
        description="Automatically send email after digest generation",
    )

    @property
    def email_recipient(self) -> Optional[str]:
        """Get first email recipient for backward compatibility."""
        if self.email_recipients:
            return self.email_recipients.split(",")[0].strip()
        return None

    @property
    def email_recipient_list(self) -> list[str]:
        """Get list of email recipients."""
        if not self.email_recipients:
            return []
        return [r.strip() for r in self.email_recipients.split(",") if r.strip()]

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
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
