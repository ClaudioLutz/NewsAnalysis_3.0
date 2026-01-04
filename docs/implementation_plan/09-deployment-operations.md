# Deployment & Operations

## Overview

This document covers deployment strategies, operational procedures, monitoring, and maintenance for local/on-premise NewsAnalysis deployment.

## Deployment Options

### Option A: Direct Python Execution (Recommended for Start)

**Pros**:
- Simple setup
- Easy debugging
- Quick iteration
- No containerization overhead

**Cons**:
- Manual dependency management
- Environment-specific issues
- No isolation

**Setup**:
```bash
# Install Python 3.11+
python --version

# Clone repository
git clone https://github.com/creditreform/newsanalysis.git
cd newsanalysis

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install package
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key

# Initialize database
python scripts/init_db.py

# Run
newsanalysis run
```

### Option B: Docker Containerization

**Pros**:
- Reproducible environment
- Isolated dependencies
- Easy to deploy anywhere
- Version control

**Cons**:
- Additional complexity
- Resource overhead
- Build time

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create output directories
RUN mkdir -p /data/out/digests /data/out/reports

# Run
CMD ["newsanalysis", "run"]
```

**Docker Compose**:
```yaml
version: '3.8'

services:
  newsanalysis:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DB_PATH=/data/news.db
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/data
      - ./config:/app/config
    restart: unless-stopped
```

**Run**:
```bash
# Build
docker-compose build

# Run
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option C: Systemd Service (Production)

**Pros**:
- Auto-restart on failure
- Integrated with system
- Log management
- Resource limits

**Cons**:
- Linux-only
- Systemd knowledge required

**Service File** (`/etc/systemd/system/newsanalysis.service`):
```ini
[Unit]
Description=NewsAnalysis Pipeline
After=network.target

[Service]
Type=simple
User=newsanalysis
WorkingDirectory=/opt/newsanalysis
Environment="PATH=/opt/newsanalysis/.venv/bin"
EnvironmentFile=/opt/newsanalysis/.env
ExecStart=/opt/newsanalysis/.venv/bin/newsanalysis run
Restart=on-failure
RestartSec=5m

# Resource limits
MemoryLimit=1G
CPUQuota=50%

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/newsanalysis/data

[Install]
WantedBy=multi-user.target
```

**Setup**:
```bash
# Install
sudo cp newsanalysis.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start
sudo systemctl start newsanalysis

# Enable auto-start
sudo systemctl enable newsanalysis

# Check status
sudo systemctl status newsanalysis

# View logs
sudo journalctl -u newsanalysis -f
```

## Scheduled Execution

### Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Run daily at 6 AM, 12 PM, and 6 PM
0 6,12,18 * * * cd /opt/newsanalysis && .venv/bin/newsanalysis run >> /var/log/newsanalysis/cron.log 2>&1

# Run hourly during business hours (8 AM - 6 PM)
0 8-18 * * * cd /opt/newsanalysis && .venv/bin/newsanalysis run

# Backup daily at 2 AM
0 2 * * * cd /opt/newsanalysis && .venv/bin/python scripts/backup_db.py
```

### Windows Task Scheduler

```powershell
# Create scheduled task (PowerShell)
$action = New-ScheduledTaskAction -Execute "C:\newsanalysis\.venv\Scripts\newsanalysis.exe" -Argument "run"
$trigger = New-ScheduledTaskTrigger -Daily -At "6:00AM"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "NewsAnalysis" -Action $action -Trigger $trigger -Settings $settings
```

### Python Schedule Library

```python
# scripts/scheduler.py
import schedule
import time
from newsanalysis.pipeline.orchestrator import PipelineOrchestrator

def run_pipeline():
    """Run pipeline with error handling."""
    try:
        orchestrator = PipelineOrchestrator()
        orchestrator.run()
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")

# Schedule runs
schedule.every().day.at("06:00").do(run_pipeline)
schedule.every().day.at("12:00").do(run_pipeline)
schedule.every().day.at("18:00").do(run_pipeline)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Logging Strategy

### Structured Logging (JSON)

```python
import structlog

logger = structlog.get_logger(__name__)

# Log with structured context
logger.info(
    "pipeline_started",
    run_id=run_id,
    mode="full",
    feeds_count=len(feeds)
)

logger.warning(
    "feed_failed",
    feed="NZZ",
    error="Connection timeout",
    retry_count=3
)

logger.error(
    "pipeline_failed",
    run_id=run_id,
    stage="scraping",
    error=str(exception)
)
```

### Log Rotation

```python
# Use Python's RotatingFileHandler
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/newsanalysis.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### Log Levels

- **DEBUG**: Detailed diagnostic (development only)
- **INFO**: General informational (default production)
- **WARNING**: Something unexpected (e.g., feed failed, but pipeline continues)
- **ERROR**: Serious problem (e.g., pipeline stage failed)
- **CRITICAL**: System unusable

## Monitoring

### Health Checks

```python
# src/newsanalysis/cli/commands/health.py
import click

@click.command()
def health():
    """Check system health."""

    checks = {
        "database": check_database(),
        "openai_api": check_openai_api(),
        "disk_space": check_disk_space(),
        "last_run": check_last_run()
    }

    for name, status in checks.items():
        icon = "✓" if status["healthy"] else "✗"
        click.echo(f"{icon} {name}: {status['message']}")

    # Exit code: 0 if all healthy, 1 otherwise
    sys.exit(0 if all(c["healthy"] for c in checks.values()) else 1)

def check_database():
    """Check database connectivity."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
        return {"healthy": True, "message": f"OK ({size_mb:.1f} MB)"}
    except Exception as e:
        return {"healthy": False, "message": str(e)}

def check_openai_api():
    """Check OpenAI API connectivity."""
    try:
        response = openai.models.list()
        return {"healthy": True, "message": "OK"}
    except Exception as e:
        return {"healthy": False, "message": str(e)}
```

### Cost Tracking Dashboard

```python
@click.command()
@click.option("--days", default=30, help="Number of days to analyze")
def cost_report(days):
    """Generate cost report."""

    # Query API calls from database
    calls = db.query("""
        SELECT
            DATE(created_at) as date,
            module,
            SUM(cost) as daily_cost,
            SUM(total_tokens) as daily_tokens
        FROM api_calls
        WHERE created_at > datetime('now', '-{} days')
        GROUP BY DATE(created_at), module
        ORDER BY date DESC
    """.format(days))

    # Print report
    click.echo(f"\n=== Cost Report (Last {days} Days) ===\n")

    total_cost = 0
    for row in calls:
        click.echo(f"{row['date']}: ${row['daily_cost']:.2f} ({row['module']})")
        total_cost += row['daily_cost']

    avg_daily_cost = total_cost / days
    projected_monthly = avg_daily_cost * 30

    click.echo(f"\nTotal: ${total_cost:.2f}")
    click.echo(f"Average Daily: ${avg_daily_cost:.2f}")
    click.echo(f"Projected Monthly: ${projected_monthly:.2f}")

    if projected_monthly > 50:
        click.echo("\n⚠ WARNING: Projected monthly cost exceeds $50 target!")
```

### Metrics Tracking

```python
# Key metrics to track
metrics = {
    # Pipeline metrics
    "pipeline_duration_seconds": duration,
    "articles_collected": collected_count,
    "articles_filtered": filtered_count,
    "articles_scraped": scraped_count,
    "articles_summarized": summarized_count,

    # Quality metrics
    "filter_rate": filtered_count / collected_count,
    "scraping_success_rate": scraped_count / filtered_count,

    # Cost metrics
    "total_cost_usd": total_cost,
    "cost_per_article_usd": total_cost / collected_count,

    # Error metrics
    "errors_count": error_count,
    "failed_feeds_count": failed_feeds
}
```

## Backup Strategy

### Automated Daily Backups

```python
# scripts/backup_db.py
import shutil
import gzip
from datetime import datetime
from pathlib import Path

def backup_database(
    db_path: Path,
    backup_dir: Path,
    keep_days: int = 7
):
    """Create compressed database backup."""

    # Create backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"news_db_{timestamp}.db.gz"

    # Create backup directory if not exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Compress database file
    with open(db_path, 'rb') as f_in:
        with gzip.open(backup_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"Backup created: {backup_path}")

    # Cleanup old backups
    cleanup_old_backups(backup_dir, keep_days)

def cleanup_old_backups(backup_dir: Path, keep_days: int):
    """Delete backups older than keep_days."""

    cutoff = datetime.now().timestamp() - (keep_days * 86400)

    for backup_file in backup_dir.glob("news_db_*.db.gz"):
        if backup_file.stat().st_mtime < cutoff:
            backup_file.unlink()
            print(f"Deleted old backup: {backup_file}")

if __name__ == "__main__":
    backup_database(
        db_path=Path("./news.db"),
        backup_dir=Path("./backups"),
        keep_days=7
    )
```

### Restore from Backup

```bash
# Decompress and restore
gunzip -c backups/news_db_20260104_020000.db.gz > news.db
```

## Maintenance Tasks

### Database Vacuum (Weekly)

```python
# scripts/vacuum_db.py
import sqlite3

def vacuum_database(db_path: str):
    """Optimize database and reclaim space."""

    conn = sqlite3.connect(db_path)

    print("Running VACUUM...")
    conn.execute("VACUUM")

    print("Running ANALYZE...")
    conn.execute("ANALYZE")

    print("Optimizing FTS index...")
    conn.execute("INSERT INTO articles_fts(articles_fts) VALUES('optimize')")

    conn.close()
    print("Database optimization complete")

if __name__ == "__main__":
    vacuum_database("./news.db")
```

### Data Retention Cleanup

```python
# scripts/cleanup_old_data.py
def cleanup_old_articles(conn, retention_days_by_priority):
    """Delete old articles based on retention policy."""

    for priority, days in retention_days_by_priority.items():
        result = conn.execute("""
            DELETE FROM articles
            WHERE feed_priority = ?
              AND published_at < datetime('now', '-{} days')
        """.format(days), (priority,))

        print(f"Deleted {result.rowcount} old articles (priority {priority})")

    # Cleanup orphaned records
    conn.execute("DELETE FROM articles_fts WHERE rowid NOT IN (SELECT id FROM articles)")
    conn.execute("DELETE FROM processed_links WHERE processed_at < datetime('now', '-7 days')")

    conn.commit()
```

## Error Recovery

### Orphaned Article Recovery

```python
# scripts/recover_orphaned.py
def recover_orphaned_articles(conn):
    """Recover articles stuck in processing."""

    # Find articles stuck in "processing" status for >1 hour
    stuck = conn.execute("""
        SELECT id, url, pipeline_stage
        FROM articles
        WHERE processing_status = 'processing'
          AND updated_at < datetime('now', '-1 hour')
    """).fetchall()

    for article_id, url, stage in stuck:
        print(f"Recovering article {article_id} stuck at {stage}")

        # Reset to pending
        conn.execute("""
            UPDATE articles
            SET processing_status = 'pending',
                error_count = error_count + 1
            WHERE id = ?
        """, (article_id,))

    conn.commit()
    print(f"Recovered {len(stuck)} stuck articles")
```

### Manual Pipeline Resume

```bash
# Resume failed pipeline run
newsanalysis run --resume <run_id>
```

## Deployment Checklist

**Pre-Deployment**:
- [ ] Python 3.11+ installed
- [ ] Dependencies installed (pip install -e .)
- [ ] .env file configured with API keys
- [ ] Database initialized (scripts/init_db.py)
- [ ] Feed configs validated (config/feeds.yaml)
- [ ] Backup directory created
- [ ] Logs directory created

**Post-Deployment**:
- [ ] Test run successful (newsanalysis run --limit 5)
- [ ] Health check passes (newsanalysis health)
- [ ] Scheduled tasks configured (cron/systemd)
- [ ] Monitoring alerts configured
- [ ] Backup automation tested
- [ ] Documentation updated

## Troubleshooting

### Common Issues

**1. OpenAI API Rate Limit**:
```
Error: Rate limit exceeded

Solution:
- Enable batch processing (ENABLE_BATCH_API=true)
- Reduce concurrent requests
- Add delays between calls
```

**2. Database Locked**:
```
Error: database is locked

Solution:
- Enable WAL mode (PRAGMA journal_mode=WAL)
- Reduce concurrent connections
- Check for long-running transactions
```

**3. Out of Memory**:
```
Error: MemoryError

Solution:
- Reduce MAX_ITEMS_PER_FEED
- Process in smaller batches
- Add memory limits (systemd MemoryLimit)
```

## Next Steps

- Review technology stack (10-technology-stack.md)
- Set up deployment environment
- Configure monitoring and alerts
