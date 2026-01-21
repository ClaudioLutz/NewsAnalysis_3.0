<p align="center">
  <img src="docs/assets/logo.png" alt="NewsAnalysis" width="120" height="120" />
</p>

<h1 align="center">NewsAnalysis 3.0</h1>

<p align="center">
  <strong>AI-Powered Swiss Business News Intelligence for Credit Risk Analysis</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#usage">Usage</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#documentation">Docs</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/coverage-80%25+-brightgreen.svg" alt="Coverage">
  <img src="https://img.shields.io/badge/cost-~%242.50%2Fmonth-orange.svg" alt="Cost">
</p>

---

## Overview

NewsAnalysis 3.0 transforms high-volume Swiss business news into actionable credit risk intelligence. Built for **Creditreform Switzerland**, it monitors 30+ news sources, filters relevant articles using AI, and delivers structured daily digests via email.

**Key Benefits:**
- **88% cost savings** via multi-provider LLM strategy (DeepSeek + Gemini)
- **Automated daily delivery** with professional HTML email digests
- **Swiss-focused intelligence** covering insolvency, regulatory, and market news
- **Production-ready** with comprehensive logging, monitoring, and error handling

---

## Features

### Intelligent Pipeline

| Stage | Description | Technology |
|-------|-------------|------------|
| **Collection** | Aggregates from 30+ Swiss RSS feeds | Feedparser, aiohttp |
| **Filtering** | AI classification on title/URL only (90% cost reduction) | DeepSeek |
| **Scraping** | Full content extraction with bot-protection bypass | Trafilatura, curl_cffi |
| **Deduplication** | Semantic duplicate detection across sources | LLM-powered clustering |
| **Summarization** | Structured German summaries with entity extraction | Gemini Flash |
| **Digest** | Daily email digest with images and meta-analysis | Jinja2, Outlook |

### News Sources

**Tier 1 - Government & Regulatory:**
- FINMA (News, Sanctions)
- SNB (Monetary Policy, Interest Rates, Press Releases)
- Federal Administration
- Bundesgericht (Federal Supreme Court)

**Tier 2 - Financial Media:**
- Finews, NZZ Business, Handelszeitung
- FinTech News Switzerland

**Tier 3 - General Swiss Media:**
- NZZ, Tages-Anzeiger, Der Bund
- SRF, 20 Minuten, Blick
- Le Temps, RSI, LaRegione

### Topic Coverage

```
Credit Risk        │  Insolvency/Bankruptcy  │  Regulatory Compliance
Payment Behavior   │  Debt Collection        │  KYC/AML/Sanctions
Economic Indicators│  Company Lifecycle      │  Board Changes
Data Protection    │  E-Commerce Fraud       │  Market Intelligence
```

---

## Quick Start

### Prerequisites

- Python 3.11+ (3.13 supported)
- API keys for at least one provider:
  - [DeepSeek](https://platform.deepseek.com/) (recommended for classification)
  - [Google AI](https://aistudio.google.com/) (recommended for summarization)
  - [OpenAI](https://platform.openai.com/) (fallback)

### Installation

```bash
# Clone repository
git clone https://github.com/ClaudioLutz/NewsAnalysis_3.0.git
cd NewsAnalysis_3.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -e ".[dev,email]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
python -m newsanalysis.cli.main run --limit 5
```

### Environment Variables

```bash
# Required: At least one LLM provider
DEEPSEEK_API_KEY=your-deepseek-key      # Classification
GOOGLE_API_KEY=your-google-key          # Summarization & Digest
OPENAI_API_KEY=your-openai-key          # Fallback

# Optional: Email delivery
EMAIL_RECIPIENTS=analyst@company.com
EMAIL_AUTO_SEND=true
```

---

## Usage

### Daily Pipeline

```bash
# Full pipeline: collect → filter → scrape → summarize → digest → email
python -m newsanalysis.cli.main run

# Test with limited articles
python -m newsanalysis.cli.main run --limit 10

# Skip collection (reprocess existing articles)
python -m newsanalysis.cli.main run --skip-collection

# Regenerate today's digest
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

### Pipeline Options

| Option | Description |
|--------|-------------|
| `--limit N` | Process only N articles |
| `--skip-collection` | Skip RSS collection |
| `--skip-filtering` | Skip AI classification |
| `--skip-scraping` | Skip content extraction |
| `--skip-summarization` | Skip article summarization |
| `--skip-digest` | Skip digest generation |
| `--reset digest` | Regenerate digest from existing summaries |
| `--reset all` | Full reprocess from scratch |
| `--today-only` | Only include today's articles in digest |

### Export & Reports

```bash
# Export digest
newsanalysis export                    # Today (Markdown)
newsanalysis export --format json      # JSON format
newsanalysis export --date 2026-01-15  # Specific date

# Statistics
newsanalysis stats                     # Weekly summary
newsanalysis stats --period today      # Today only
newsanalysis stats --detailed          # Full breakdown

# Cost report
newsanalysis cost-report               # API costs
newsanalysis cost-report --detailed    # Daily breakdown

# Health check
newsanalysis health --verbose          # System diagnostics
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NewsAnalysis Pipeline                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│   │   RSS    │   │    AI    │   │ Content  │   │   Deduplication  │ │
│   │ Collect  │──▶│  Filter  │──▶│  Scrape  │──▶│   (Semantic)     │ │
│   │ 30+ feeds│   │ DeepSeek │   │Trafilatura│   │   DeepSeek      │ │
│   └──────────┘   └──────────┘   └──────────┘   └────────┬─────────┘ │
│                                                          │          │
│   ┌──────────────────────────────────────────────────────▼────────┐ │
│   │                                                               │ │
│   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │ │
│   │   │  Summarize   │──▶│    Digest    │──▶│   Email Digest   │ │ │
│   │   │   Gemini     │   │  Generation  │   │  HTML + Images   │ │ │
│   │   └──────────────┘   └──────────────┘   └──────────────────┘ │ │
│   │                                                               │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Runtime** | Python 3.11+ | Modern async, type hints |
| **Database** | SQLite | Local-first, zero config |
| **LLM - Classification** | DeepSeek | Cost-effective filtering |
| **LLM - Summarization** | Gemini Flash | Quality German output |
| **LLM - Fallback** | OpenAI | Reliability guarantee |
| **Content Extraction** | Trafilatura | Fast, accurate scraping |
| **Bot Bypass** | curl_cffi | TLS fingerprint impersonation |
| **Validation** | Pydantic | Type safety, data integrity |
| **Logging** | structlog | Structured JSON logs |
| **Email** | Outlook COM | Windows native delivery |

### Project Structure

```
newsanalysis/
├── src/newsanalysis/
│   ├── cli/                 # Command-line interface
│   ├── core/                # Domain models (Article, Digest, Config)
│   ├── database/            # SQLite repository layer
│   ├── integrations/        # LLM providers (DeepSeek, Gemini, OpenAI)
│   ├── pipeline/
│   │   ├── collectors/      # RSS, sitemap, HTML collectors
│   │   ├── filters/         # AI classification
│   │   ├── scrapers/        # Content extraction
│   │   ├── dedup/           # Semantic deduplication
│   │   ├── summarizers/     # Article summarization
│   │   ├── generators/      # Digest generation
│   │   ├── formatters/      # Output formatters
│   │   ├── extractors/      # Image extraction
│   │   └── orchestrator.py  # Pipeline coordinator
│   ├── services/            # Email, caching, metrics
│   ├── templates/           # Email HTML templates
│   └── utils/               # Logging, exceptions, utilities
├── config/
│   ├── feeds.yaml           # RSS feed configuration
│   ├── topics.yaml          # Classification topics
│   └── prompts/             # LLM prompt templates
├── tests/                   # Test suite (>80% coverage)
├── docs/                    # Documentation
└── out/                     # Output directory
```

---

## Cost Optimization

NewsAnalysis achieves **~$2.50/month** for 100 articles/day through:

| Strategy | Savings | Description |
|----------|---------|-------------|
| **Multi-Provider** | 88% | DeepSeek ($0.14/M) + Gemini ($0.075/M) vs OpenAI |
| **Title-Only Filter** | 90% | Classify on title/URL before scraping |
| **Batch Processing** | 50% | Reduced API overhead |
| **Response Caching** | 90% | DeepSeek cache discount on repeated content |
| **Smart Fallback** | - | OpenAI only when primary providers fail |

---

## Development

### Code Quality

```bash
# Linting
ruff check src/ tests/

# Formatting
ruff format src/ tests/

# Type checking
mypy src/newsanalysis

# Run tests
pytest

# Coverage report
pytest --cov=newsanalysis --cov-report=html
```

### Testing

```bash
pytest tests/unit           # Unit tests
pytest tests/integration    # Integration tests
pytest -v --tb=short        # Verbose with short tracebacks
```

---

## Production Deployment

### Windows Task Scheduler

```powershell
# Run twice daily (8:30 AM and 1:00 PM)
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m newsanalysis.cli.main run"
$trigger1 = New-ScheduledTaskTrigger -Daily -At 8:30AM
$trigger2 = New-ScheduledTaskTrigger -Daily -At 1:00PM
Register-ScheduledTask -TaskName "NewsAnalysis" -Action $action -Trigger $trigger1,$trigger2
```

### Linux Systemd

```bash
sudo bash scripts/deploy.sh
sudo systemctl enable --now newsanalysis.timer
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Complete setup and usage |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Duplicate Handling](docs/duplicate-handling-analysis.md) | Deduplication strategy |
| [Implementation Plan](docs/implementation_plan/) | Technical architecture |

---

## License

MIT License - Copyright (c) 2026 Creditreform Switzerland

---

<p align="center">
  Built with precision for Swiss business intelligence
</p>
