# Project Overview

## NewsAnalysis 3.0

**AI-powered Swiss news analysis for credit risk intelligence**

### Purpose

NewsAnalysis 3.0 transforms high-volume Swiss business news into actionable credit risk insights through automated collection, AI-powered filtering, and intelligent summarization. Designed for Creditreform Switzerland's credit risk analysis workflows.

### Key Value Propositions

| Feature | Benefit |
|---------|---------|
| **Cost-Optimized** | ~$2.50/month for 100 articles/day (88% savings) |
| **Multi-Provider LLM** | DeepSeek + Gemini (bidirectional fallback) |
| **German Output** | All summaries in Hochdeutsch |
| **Swiss-Focused** | 24 Swiss news sources |
| **Production-Ready** | Error handling, monitoring, cost tracking |

## Quick Reference

| Attribute | Value |
|-----------|-------|
| **Version** | 2.0.0 |
| **Language** | Python 3.11+ |
| **Database** | SQLite (FTS5) |
| **License** | MIT |
| **Author** | Creditreform Switzerland |

### Technology Stack Summary

| Layer | Technologies |
|-------|--------------|
| **CLI** | Click |
| **Models** | Pydantic |
| **Database** | SQLite + SQLAlchemy |
| **AI** | DeepSeek, Gemini |
| **Scraping** | Trafilatura, Playwright |
| **Testing** | pytest |

### Architecture Type

**5-Stage Data Pipeline** (ETL-style with semantic deduplication)

```
RSS/HTML → Collect → Filter → Scrape → Dedup → Summarize → Digest
                       ↓                          ↓          ↓
              DeepSeek (classify)        Gemini (summarize)  │
                       ↓                          ↓          │
                       └──────────────────────────┴──────────┘
                                         ↓
                              German Reports → Email
```

## Repository Structure

| Type | Classification |
|------|----------------|
| **Repository** | Monolith |
| **Primary Type** | Backend/Data Pipeline |
| **Secondary Types** | CLI, Data Processing |

## News Sources

### Tier 1: Government (7-day retention)
- FINMA News
- FINMA Sanctions

### Tier 2: Financial (3-day retention)
- Finews, Cash, Finanzen.ch
- StartupTicker, FinTech News Switzerland

### Tier 3: General (1-day retention)
- NZZ (Recent, Business, Switzerland)
- Tages-Anzeiger, Der Bund (Tamedia)
- SRF (Latest, Switzerland, Business)
- Swissinfo
- Tribune de Genève, 24 heures (French)

## Performance Targets

| Metric | Target |
|--------|--------|
| **Cost** | ~$2.50/month (100 articles/day) |
| **Speed** | <5 minutes daily pipeline |
| **Accuracy** | >85% classification |
| **Coverage** | >80% test coverage |
| **Scalability** | Up to 500 articles/day |

## Cost Optimization Strategies

1. **Multi-Provider Strategy**: DeepSeek + Gemini = 88% savings
2. **Title/URL Filtering**: 90% reduction (no content scraping for filtering)
3. **Batch Processing**: 50% API cost savings
4. **DeepSeek Cache**: 90% off cached inputs
5. **Content Fingerprinting**: Avoid re-summarizing duplicates

## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Configure API keys
python scripts/init_db.py

# Run
newsanalysis run --limit 10  # Test run
newsanalysis export          # Export digest
newsanalysis stats           # View statistics
newsanalysis cost-report     # View API costs
newsanalysis health          # System health check
newsanalysis email           # Send digest via Outlook
```

## Documentation Map

| Document | Purpose |
|----------|---------|
| [README.md](../../README.md) | Quick start guide |
| [USER_GUIDE.md](../USER_GUIDE.md) | Complete usage guide |
| [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) | Problem solving |
| [Architecture](architecture.md) | System design |
| [Data Models](data-models.md) | Database schema |
| [Source Tree](source-tree-analysis.md) | Code structure |
| [Development Guide](development-guide.md) | Developer setup |
| [Implementation Plan](../implementation_plan/) | Technical specs |

## Support

1. Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
2. Review [USER_GUIDE.md](../USER_GUIDE.md)
3. Consult technical docs in `docs/implementation_plan/`
