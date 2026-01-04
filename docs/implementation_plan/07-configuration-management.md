# Configuration Management

## Overview

Configuration management separates code from configuration, enabling environment-specific settings, feature flags, and secure secrets handling. This document outlines configuration strategies for the NewsAnalysis system.

## Configuration Layers

### 1. Environment Variables (.env)

Runtime configuration and secrets:

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-...
MODEL_NANO=gpt-5-nano
MODEL_MINI=gpt-4o-mini

# Database
DB_PATH=./news.db
DB_BACKUP_DIR=./backups

# Pipeline Settings
CONFIDENCE_THRESHOLD=0.70
MAX_ITEMS_PER_FEED=120
REQUEST_TIMEOUT_SEC=12
CRAWL_DELAY_SEC=2

# Features
ENABLE_BATCH_API=true
ENABLE_SEMANTIC_CACHE=false
SKIP_ROBOTS_TXT=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=./logs/newsanalysis.log

# Deployment
ENVIRONMENT=production  # development, staging, production
```

### 2. YAML Configuration Files

Structured configuration for feeds, topics, prompts:

**config/feeds.yaml**:
```yaml
feeds:
  # Tier 1: Government Sources (7-day retention)
  - name: "FINMA"
    type: "rss"
    url: "https://www.finma.ch/en/news/rss/"
    priority: 1
    max_age_hours: 168  # 7 days
    rate_limit_seconds: 5.0
    enabled: true

  - name: "SNB"
    type: "rss"
    url: "https://www.snb.ch/en/rss/news.rss"
    priority: 1
    max_age_hours: 168
    rate_limit_seconds: 5.0
    enabled: true

  # Tier 2: Financial Sources (3-day retention)
  - name: "Handelszeitung"
    type: "rss"
    url: "https://www.handelszeitung.ch/rss.xml"
    priority: 2
    max_age_hours: 72
    rate_limit_seconds: 3.0
    enabled: true

  # Tier 3: General News (1-day retention)
  - name: "NZZ"
    type: "rss"
    url: "https://www.nzz.ch/recent.rss"
    priority: 3
    max_age_hours: 24
    rate_limit_seconds: 2.0
    enabled: true

  - name: "20 Minuten"
    type: "sitemap"
    url: "https://www.20min.ch/sitemap-news.xml"
    priority: 3
    max_age_hours: 24
    rate_limit_seconds: 2.0
    enabled: true
```

**config/topics.yaml**:
```yaml
creditreform_insights:
  enabled: true
  confidence_threshold: 0.71
  max_articles_per_run: 35
  max_article_age_days: 0  # Same day only

  focus_areas:
    credit_risk:
      - Bonität
      - Rating
      - Score
      - Kreditwürdigkeit

    insolvency_bankruptcy:
      - Konkurs
      - Insolvenz
      - Zahlungsunfähigkeit
      - SchKG
      - Sanierung

    regulatory_compliance:
      - FINMA
      - Basel III
      - nDSG
      - Datenschutz
      - Compliance

    payment_behavior:
      - Zahlungsmoral
      - Zahlungsverzug
      - Inkasso
      - Forderungsmanagement

    market_intelligence:
      - KMU Finanzierung
      - Kreditversicherung
      - Factoring
      - Leasing
```

**config/prompts/classification.yaml**:
```yaml
system_prompt: |
  You are a Swiss financial analyst specializing in credit risk assessment for Creditreform.

  Focus areas:
  - Credit ratings and risk (Bonität, Rating, Kreditwürdigkeit)
  - Insolvency and bankruptcy (Konkurs, Insolvenz, Zahlungsunfähigkeit)
  - Regulatory compliance (FINMA, Basel III, nDSG, SchKG)
  - Payment behavior (Zahlungsmoral, Zahlungsverzug, Inkasso)
  - Market intelligence (KMU Finanzierung, Kreditversicherung)

user_prompt_template: |
  Title: {title}
  URL: {url}
  Source: {source}

  Is this article relevant to Creditreform's credit risk and business intelligence focus?

  Respond in JSON:
  {{
    "match": boolean,
    "conf": float,  // 0.0-1.0
    "topic": string,
    "reason": string  // max 100 chars
  }}

output_schema:
  type: object
  properties:
    match:
      type: boolean
    conf:
      type: number
      minimum: 0
      maximum: 1
    topic:
      type: string
    reason:
      type: string
      maxLength: 100
  required: [match, conf, topic, reason]
```

### 3. Pyproject.toml

Project metadata and dependencies (see 05-python-project-structure.md).

## Configuration Loading

### Environment Variable Loading

```python
"""Configuration loading from environment variables."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

@dataclass
class Config:
    # OpenAI
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model_nano: str = field(default_factory=lambda: os.getenv("MODEL_NANO", "gpt-5-nano"))
    model_mini: str = field(default_factory=lambda: os.getenv("MODEL_MINI", "gpt-4o-mini"))

    # Database
    db_path: Path = field(default_factory=lambda: Path(os.getenv("DB_PATH", "./news.db")))
    db_backup_dir: Path = field(default_factory=lambda: Path(os.getenv("DB_BACKUP_DIR", "./backups")))

    # Pipeline
    confidence_threshold: float = field(default_factory=lambda: float(os.getenv("CONFIDENCE_THRESHOLD", "0.70")))
    max_items_per_feed: int = field(default_factory=lambda: int(os.getenv("MAX_ITEMS_PER_FEED", "120")))
    request_timeout_sec: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SEC", "12")))

    # Features
    enable_batch_api: bool = field(default_factory=lambda: os.getenv("ENABLE_BATCH_API", "true").lower() == "true")
    enable_semantic_cache: bool = field(default_factory=lambda: os.getenv("ENABLE_SEMANTIC_CACHE", "false").lower() == "true")

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))

    # Environment
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    def validate(self):
        """Validate configuration."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set")

        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment."""
        config = cls()
        config.validate()
        return config
```

### YAML Configuration Loading

```python
"""YAML configuration loading."""

import yaml
from pathlib import Path
from typing import List, Dict

@dataclass
class FeedConfig:
    name: str
    type: str  # "rss", "sitemap", "html"
    url: str
    priority: int
    max_age_hours: int
    rate_limit_seconds: float
    enabled: bool = True

def load_feeds(config_path: Path = Path("config/feeds.yaml")) -> List[FeedConfig]:
    """Load feed configurations from YAML."""

    with open(config_path) as f:
        data = yaml.safe_load(f)

    feeds = []
    for feed_data in data.get("feeds", []):
        if feed_data.get("enabled", True):
            feeds.append(FeedConfig(**feed_data))

    return feeds

def load_topics(config_path: Path = Path("config/topics.yaml")) -> Dict:
    """Load topic configurations from YAML."""

    with open(config_path) as f:
        return yaml.safe_load(f)

def load_prompt_template(template_name: str) -> Dict:
    """Load prompt template from YAML."""

    config_path = Path(f"config/prompts/{template_name}.yaml")

    with open(config_path) as f:
        return yaml.safe_load(f)
```

## Secrets Management

### Development (.env file)

```bash
# .env (never commit to git!)
OPENAI_API_KEY=sk-proj-abc123...
```

### Production (Environment Variables)

```bash
# Set environment variables directly (systemd, Docker, etc.)
export OPENAI_API_KEY="sk-proj-abc123..."
export DB_PATH="/var/lib/newsanalysis/news.db"
export ENVIRONMENT="production"
```

### .env.example Template

```bash
# .env.example (commit this file as template)

# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NANO=gpt-5-nano
MODEL_MINI=gpt-4o-mini

# Database
DB_PATH=./news.db
DB_BACKUP_DIR=./backups

# Pipeline Settings
CONFIDENCE_THRESHOLD=0.70
MAX_ITEMS_PER_FEED=120

# Features
ENABLE_BATCH_API=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment
ENVIRONMENT=development
```

## Feature Flags

Enable/disable features without code changes:

```python
class FeatureFlags:
    def __init__(self, config: Config):
        self.config = config

    @property
    def batch_api_enabled(self) -> bool:
        """Use OpenAI Batch API for cost savings."""
        return self.config.enable_batch_api

    @property
    def semantic_cache_enabled(self) -> bool:
        """Use embedding-based semantic caching."""
        return self.config.enable_semantic_cache

    @property
    def playwright_enabled(self) -> bool:
        """Use Playwright for scraping (requires installation)."""
        return os.path.exists("/path/to/playwright")

# Usage
if feature_flags.batch_api_enabled:
    results = await process_with_batch_api(articles)
else:
    results = await process_individually(articles)
```

## Multi-Environment Support

### Configuration Profiles

```python
def get_config(environment: str = None) -> Config:
    """Get configuration for environment."""

    env = environment or os.getenv("ENVIRONMENT", "development")

    # Load base configuration
    config = Config.from_env()

    # Apply environment-specific overrides
    if env == "production":
        config.log_level = "WARNING"
        config.enable_batch_api = True
    elif env == "development":
        config.log_level = "DEBUG"
        config.enable_batch_api = False  # Faster for development

    return config
```

## Configuration Validation

### Pydantic Schemas

```python
from pydantic import BaseModel, Field, validator

class PipelineConfig(BaseModel):
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    max_items_per_feed: int = Field(gt=0, le=500)
    request_timeout_sec: int = Field(gt=0, le=60)

    @validator('confidence_threshold')
    def validate_threshold(cls, v):
        if v < 0.5:
            raise ValueError('Confidence threshold too low (min 0.5)')
        return v
```

## Configuration Best Practices

1. **Never commit secrets**: Use .env files (gitignored) or environment variables
2. **Provide .env.example**: Template for required configuration
3. **Validate on load**: Fail fast if configuration invalid
4. **Use type hints**: Clear configuration types
5. **Document defaults**: Explain default values
6. **Environment-specific**: Separate dev/staging/production configs
7. **Feature flags**: Enable gradual rollout of features
8. **Version control**: YAML configs in git, secrets externalized

## Next Steps

- Review testing strategy (08-testing-quality-assurance.md)
- Review deployment guide (09-deployment-operations.md)
- Implement configuration loading
