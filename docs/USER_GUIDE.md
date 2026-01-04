# NewsAnalysis 2.0 - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Configuration](#configuration)
3. [Running the Pipeline](#running-the-pipeline)
4. [Understanding Output](#understanding-output)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Advanced Usage](#advanced-usage)

## Getting Started

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+) or macOS
- **Python**: 3.11 or higher
- **Memory**: 2 GB RAM minimum, 4 GB recommended
- **Disk Space**: 5 GB minimum (database grows ~100 MB/month)
- **Internet**: Stable connection for API calls and news feed access

### Installation

#### Option 1: Automated Deployment (Linux)

```bash
# Download the project
git clone <repository-url>
cd news_analysis_3.0

# Run deployment script (as root)
sudo bash scripts/deploy.sh

# The script will:
# - Create system user 'newsanalysis'
# - Install dependencies
# - Initialize database
# - Setup systemd service
# - Configure automated backups
```

#### Option 2: Manual Installation

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Install Playwright browsers (for JavaScript-heavy sites)
playwright install chromium

# 4. Create environment file
cp .env.example .env

# 5. Edit .env with your settings
nano .env  # or use your preferred editor

# 6. Initialize database
python scripts/init_db.py
```

## Configuration

### Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-your-api-key-here

# Optional (with defaults)
DB_PATH=news.db
OUTPUT_DIR=out
LOG_LEVEL=INFO
CONFIDENCE_THRESHOLD=0.70
MAX_AGE_HOURS=48
DAILY_COST_LIMIT=10.0
```

### Feed Configuration (config/feeds.yaml)

```yaml
feeds:
  - name: "NZZ"
    url: "https://www.nzz.ch/recent.rss"
    feed_type: "rss"
    enabled: true
    priority: 1

  - name: "Tages-Anzeiger"
    url: "https://www.tagesanzeiger.ch/rss.html"
    feed_type: "rss"
    enabled: true
    priority: 2
```

To add a new feed:
1. Add entry to `config/feeds.yaml`
2. Set `feed_type`: `rss`, `sitemap`, or `html`
3. Set `enabled: true`
4. No code changes needed!

### Topic Configuration (config/topics.yaml)

```yaml
topics:
  creditreform_insights:
    description: "Credit risk and financial news"
    keywords:
      - bankruptcy
      - insolvency
      - credit rating
      - financial distress
```

## Running the Pipeline

### Basic Usage

```bash
# Run complete pipeline
newsanalysis run

# Test with limited articles
newsanalysis run --limit 10

# Express mode (faster, fewer articles)
newsanalysis run --mode express
```

### Stage Control

```bash
# Skip specific stages
newsanalysis run --skip-scraping        # Collection and filtering only
newsanalysis run --skip-summarization   # No AI summaries
newsanalysis run --skip-digest          # No digest generation

# Run specific stages only
newsanalysis run --skip-collection      # Process existing articles
```

### Scheduled Execution

#### Using systemd (Linux)

```bash
# Check timer status
sudo systemctl status newsanalysis.timer

# View timer schedule
systemctl list-timers newsanalysis.timer

# Manual trigger
sudo systemctl start newsanalysis.service

# View logs
journalctl -u newsanalysis.service -f
```

#### Using cron

```bash
# Edit crontab
crontab -e

# Add daily execution at 6 AM
0 6 * * * cd /opt/newsanalysis && ./venv/bin/newsanalysis run >> logs/cron.log 2>&1
```

## Understanding Output

### Digest Files

Generated in the `out/` directory:

- **digest_YYYY-MM-DD.json**: Machine-readable format
- **digest_YYYY-MM-DD.md**: Human-readable report
- **digest_YYYY-MM-DD_german.md**: German credit risk report

### JSON Structure

```json
{
  "date": "2026-01-04",
  "version": 1,
  "article_count": 15,
  "meta_analysis": {
    "key_themes": ["Banking sector stress", "SME credit risk"],
    "credit_risk_signals": ["Increased bankruptcies in retail"],
    "regulatory_updates": ["New FINMA guidelines"],
    "market_insights": ["Rising interest rates impact"]
  },
  "articles": [
    {
      "title": "Swiss Company Files Bankruptcy",
      "source": "NZZ",
      "url": "https://...",
      "summary": "...",
      "key_points": ["..."],
      "entities": {
        "companies": ["Swiss Corp AG"],
        "people": ["CEO Name"],
        "locations": ["Zurich"],
        "topics": ["bankruptcy"]
      }
    }
  ]
}
```

### Markdown Report

Structured document with:
- Executive summary
- Articles grouped by topic
- Key points and entities
- Source attribution

### German Report (Bonitäts-Tagesanalyse)

Professional credit risk analysis:
- Risk assessment summary
- Key risk signals
- Market insights
- Regulatory updates
- Detailed article analysis

## Monitoring & Maintenance

### Health Checks

```bash
# Quick health check
newsanalysis health

# Detailed diagnostics
newsanalysis health --verbose
```

Health check verifies:
- ✓ Configuration validity
- ✓ Database connectivity
- ✓ Recent pipeline runs
- ✓ API quota status
- ✓ Disk space

### Statistics

```bash
# Weekly statistics
newsanalysis stats

# Today only
newsanalysis stats --period today

# Last 30 days
newsanalysis stats --period month

# Detailed breakdown
newsanalysis stats --detailed
```

### Cost Monitoring

```bash
# Weekly cost report
newsanalysis cost-report

# With daily breakdown
newsanalysis cost-report --detailed

# Cache performance only
newsanalysis cost-report --cache-only
```

### Database Maintenance

```bash
# Manual backup
bash scripts/backup.sh

# Maintenance (vacuum, analyze, cleanup)
bash scripts/maintenance.sh

# View database size
du -h news.db
```

Automated backups run daily via cron (if deployed with deploy.sh).

### Log Management

```bash
# View pipeline logs
tail -f logs/pipeline.log

# View error logs
tail -f logs/error.log

# Search logs for errors
grep ERROR logs/pipeline.log

# View backup logs
tail -f logs/backup.log
```

Logs are automatically rotated (30 days retention).

## Advanced Usage

### Export Options

```bash
# Export today's digest
newsanalysis export

# Export specific date
newsanalysis export --date 2026-01-03

# Export as JSON
newsanalysis export --format json

# Export German report
newsanalysis export --format german

# Custom output path
newsanalysis export --output /path/to/output.md
```

### Pipeline Modes

```bash
# Express mode (faster, fewer articles)
newsanalysis run --mode express

# Standard mode (default)
newsanalysis run --mode standard

# Deep mode (comprehensive)
newsanalysis run --mode deep
```

### Cache Management

Cache is automatic. To monitor:

```bash
# View cache performance
newsanalysis cost-report --cache-only

# Cache statistics in database
sqlite3 news.db "SELECT * FROM cache_stats WHERE date = date('now')"
```

### Database Queries

```bash
# Open database
sqlite3 news.db

# View recent articles
SELECT title, source, pipeline_stage, is_match
FROM articles
WHERE created_at > datetime('now', '-7 days')
ORDER BY created_at DESC
LIMIT 10;

# View today's API costs
SELECT module, SUM(cost) as total_cost, COUNT(*) as calls
FROM api_calls
WHERE created_at >= date('now')
GROUP BY module;

# Exit
.quit
```

### Customization

#### Adding Custom News Sources

1. Edit `config/feeds.yaml`
2. Add feed entry with appropriate type
3. Test with `newsanalysis run --limit 5`

#### Adjusting Classification Prompts

1. Edit `config/prompts/classification.yaml`
2. Modify system prompt or examples
3. Test classification accuracy

#### Modifying Summary Format

1. Edit `config/prompts/summarization.yaml`
2. Adjust output structure
3. Verify with test run

## Best Practices

### Daily Operations

1. **Monitor health**: Run `newsanalysis health` daily
2. **Check costs**: Review `newsanalysis cost-report` weekly
3. **Verify outputs**: Check digest files in `out/` directory
4. **Review logs**: Check for errors in `logs/` directory

### Cost Optimization

1. **Enable caching**: Automatic, verify hit rates >70%
2. **Adjust limits**: Use `--limit` for testing
3. **Monitor budget**: Set `DAILY_COST_LIMIT` in `.env`
4. **Review prompts**: Optimize for shorter responses

### Performance Tuning

1. **Database maintenance**: Run weekly
2. **Clean old data**: Configure retention in maintenance script
3. **Monitor disk space**: Keep >20% free
4. **Optimize feeds**: Disable low-value sources

### Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Support

For additional help:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review technical documentation in `docs/implementation_plan/`
3. Check logs in `logs/` directory
4. Run `newsanalysis health --verbose` for diagnostics
