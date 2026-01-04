# NewsAnalysis 2.0

AI-powered Swiss news analysis for credit risk intelligence at Creditreform Switzerland.

## Overview

NewsAnalysis 2.0 is a cost-optimized, modular system for automated Swiss business news collection, filtering, and analysis. It transforms high-volume news data into actionable credit risk insights through a 5-stage AI pipeline.

## Key Features

- **Cost-Optimized**: <$50/month for 100 articles/day through smart filtering and batch processing
- **Modular Pipeline**: 5 independent modules with clear interfaces
- **Local-First**: Runs on a single server with SQLite (scales to PostgreSQL)
- **AI-Powered**: OpenAI GPT models for classification and summarization
- **Swiss-Focused**: 18+ Swiss news sources (NZZ, SRF, Tamedia, FINMA, etc.)
- **Production-Ready**: Comprehensive error handling, monitoring, and cost tracking

## Architecture

### 5-Stage Pipeline

1. **NewsCollector**: Aggregates from RSS, sitemaps, and HTML sources
2. **ContentFilter**: AI classification (title/URL only - 90% cost reduction)
3. **ContentScraper**: Extracts full content with Trafilatura + Playwright fallback
4. **ArticleSummarizer**: Generates structured summaries with batch processing
5. **DigestGenerator**: Creates daily digests with deduplication and meta-analysis

### Technology Stack

- **Python 3.11+**: Modern type hints and performance
- **SQLite**: Local deployment with <100K articles
- **OpenAI API**: GPT-4o-mini for classification and summarization
- **Trafilatura**: Fast content extraction
- **Pydantic**: Data validation and type safety

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key

### Setup

```bash
# Clone repository
git clone <repository-url>
cd news_analysis_3.0

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Initialize database
python scripts/init_db.py
```

## Usage

### Basic Commands

```bash
# Run full pipeline
newsanalysis run

# Run with limit (for testing)
newsanalysis run --limit 10

# Skip specific stages
newsanalysis run --skip-scraping
newsanalysis run --skip-summarization

# Export digest
newsanalysis export                        # Today's digest (Markdown)
newsanalysis export --date 2026-01-03      # Specific date
newsanalysis export --format json          # JSON format
newsanalysis export --format german        # German report

# Show statistics
newsanalysis stats                    # Weekly statistics
newsanalysis stats --period today     # Today only
newsanalysis stats --period month     # Last 30 days
newsanalysis stats --detailed         # Detailed breakdown

# Cost report
newsanalysis cost-report              # Weekly cost report
newsanalysis cost-report --detailed   # With daily breakdown
newsanalysis cost-report --cache-only # Cache performance only

# Health check
newsanalysis health                   # Basic health check
newsanalysis health --verbose         # Detailed diagnostics
```

### Configuration

Configuration is managed through:
- **Environment variables** (`.env`): API keys, paths, thresholds
- **YAML files** (`config/`): Feeds, topics, prompts

## Project Structure

```
newsanalysis/
├── src/newsanalysis/       # Source code (src layout)
│   ├── cli/                # Command-line interface
│   ├── core/               # Domain models (Pydantic)
│   ├── pipeline/           # Pipeline modules
│   │   ├── collectors/     # News collection
│   │   ├── filters/        # AI filtering
│   │   ├── scrapers/       # Content extraction
│   │   ├── analyzers/      # Summarization
│   │   └── digest/         # Digest generation
│   ├── database/           # Repository layer
│   ├── integrations/       # External APIs
│   ├── services/           # Business logic
│   └── utils/              # Utilities
├── tests/                  # Test suite
├── config/                 # Configuration files
├── scripts/                # Maintenance scripts
└── out/                    # Output directory
```

## Development

### Code Quality

```bash
# Linting and formatting
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/newsanalysis

# Testing
pytest
pytest --cov=newsanalysis
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# Integration tests
pytest tests/integration

# With coverage
pytest --cov=newsanalysis --cov-report=html
```

## Performance Targets

- **Cost**: <$50/month for 100 articles/day
- **Speed**: <5 minutes for daily pipeline execution
- **Accuracy**: >85% classification accuracy
- **Quality**: >80% test coverage
- **Scalability**: Handle up to 500 articles/day on single server

## Cost Optimization

1. **Title/URL Filtering**: 90% reduction by avoiding content scraping
2. **Batch Processing**: 50% API cost savings
3. **Caching**: 15-30% additional savings
4. **Right-Sized Models**: nano → mini → sonnet as needed

## Production Deployment

### Automated Deployment (Linux)

```bash
# Run deployment script (as root)
sudo bash scripts/deploy.sh

# Start the timer
sudo systemctl start newsanalysis.timer
sudo systemctl enable newsanalysis.timer

# Check status
sudo systemctl status newsanalysis.timer
```

### Manual Deployment

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for detailed deployment instructions.

### Maintenance

```bash
# Database backup
bash scripts/backup.sh

# Database maintenance (vacuum, analyze, cleanup)
bash scripts/maintenance.sh

# View logs
tail -f /opt/newsanalysis/logs/pipeline.log
```

## Documentation

### User Guides

- [User Guide](docs/USER_GUIDE.md) - Complete setup and usage guide
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions

### Technical Documentation

Comprehensive technical documentation in `docs/implementation_plan/`:

- System Architecture
- LLM Cost Optimization
- Modular Pipeline Design
- Database Design
- Testing & Quality Assurance
- Deployment & Operations

### Progress Tracking

- [Phase 1](PROGRESS%20Phase%201.md) - Foundation ✅
- [Phase 2](PROGRESS%20Phase%202.md) - Pipeline Core ✅
- [Phase 3](PROGRESS%20Phase%203.md) - Content Processing ✅
- [Phase 4](PROGRESS%20Phase%204.md) - Digest Generation ✅
- [Phase 5](PROGRESS%20Phase%205.md) - Optimization ✅
- [Phase 6](PROGRESS%20Phase%206.md) - Production Readiness ✅

## Testing

### Test Coverage

- **Unit Tests**: Core utilities, models, services (>90% coverage)
- **Integration Tests**: Database, pipeline, API integration (>80% coverage)
- **End-to-End Tests**: Complete workflows (>70% coverage)
- **Overall Coverage**: >80% target achieved

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# End-to-end tests
pytest tests/test_e2e.py -v

# With coverage report
pytest --cov=newsanalysis --cov-report=html
open htmlcov/index.html
```

## Monitoring

### Health Checks

```bash
# Quick health check
newsanalysis health

# Detailed diagnostics
newsanalysis health --verbose
```

### Metrics Tracked

- **Pipeline Runs**: Success/failure rates, duration
- **API Costs**: Daily usage, budget utilization
- **Cache Performance**: Hit rates, cost savings
- **Article Processing**: Collected, filtered, scraped, summarized
- **Database Size**: Growth tracking

## Troubleshooting

### Common Issues

1. **High API costs**: Check cache hit rates, optimize prompts
2. **Low classification accuracy**: Review golden dataset, adjust threshold
3. **Slow performance**: Enable caching, optimize batch sizes
4. **Database size**: Run maintenance script

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

## License

MIT License - Copyright (c) 2026 Creditreform Switzerland

## Support

For questions or issues:
1. Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
3. Consult technical documentation in `docs/implementation_plan/`
#   N e w s A n a l y s i s _ 3 . 0  
 