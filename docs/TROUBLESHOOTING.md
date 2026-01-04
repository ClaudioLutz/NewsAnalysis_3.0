# NewsAnalysis 2.0 - Troubleshooting Guide

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Problems](#configuration-problems)
3. [Pipeline Errors](#pipeline-errors)
4. [Performance Issues](#performance-issues)
5. [Cost Management](#cost-management)
6. [Database Problems](#database-problems)
7. [API Integration Issues](#api-integration-issues)

## Installation Issues

### Python Version Error

**Problem**: `python: command not found` or version mismatch

**Solution**:
```bash
# Check Python version
python3 --version

# Should be 3.11+
# If not, install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv

# Use specific version
python3.11 -m venv venv
```

### Pip Install Fails

**Problem**: `ERROR: Could not find a version that satisfies the requirement...`

**Solution**:
```bash
# Update pip
pip install --upgrade pip setuptools wheel

# Install with verbose output
pip install -e ".[dev]" -v

# If specific package fails, install separately
pip install pydantic==2.5.0
```

### Playwright Installation Issues

**Problem**: `playwright install` fails or browsers not found

**Solution**:
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2

# Reinstall Playwright browsers
playwright install chromium --with-deps
```

## Configuration Problems

### OpenAI API Key Invalid

**Problem**: `AuthenticationError: Incorrect API key`

**Solution**:
```bash
# Verify API key format
echo $OPENAI_API_KEY  # Should start with 'sk-'

# Check .env file
cat .env | grep OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Generate new key at: https://platform.openai.com/api-keys
```

### Configuration File Not Found

**Problem**: `FileNotFoundError: config/feeds.yaml not found`

**Solution**:
```bash
# Check current directory
pwd  # Should be in project root

# Verify config files exist
ls -la config/

# If missing, copy from examples
cp config/feeds.yaml.example config/feeds.yaml
cp config/topics.yaml.example config/topics.yaml

# Check file permissions
chmod 644 config/*.yaml
```

### Database Initialization Fails

**Problem**: `sqlite3.OperationalError: table articles already exists`

**Solution**:
```bash
# Option 1: Backup and recreate
mv news.db news_backup_$(date +%Y%m%d).db
python scripts/init_db.py

# Option 2: Run migration
python scripts/migrate_phase5.py

# Option 3: Manual fix
sqlite3 news.db < src/newsanalysis/database/schema.sql
```

## Pipeline Errors

### Collection Stage Fails

**Problem**: `No articles collected` or `ConnectionError`

**Diagnostics**:
```bash
# Test feed URLs manually
curl -I https://www.nzz.ch/recent.rss

# Check feed configuration
cat config/feeds.yaml

# Test with single feed
newsanalysis run --limit 1
```

**Solutions**:
- Check internet connectivity
- Verify feed URLs are accessible
- Temporarily disable problematic feeds in `config/feeds.yaml`
- Check for rate limiting (503 errors)

### Filtering Stage Fails

**Problem**: `OpenAI API rate limit exceeded`

**Solution**:
```bash
# Check current usage
newsanalysis cost-report

# Wait for rate limit reset (typically 1 minute)
sleep 60 && newsanalysis run

# Reduce batch size in code if persistent
# Or upgrade OpenAI API tier
```

**Problem**: `All articles rejected by filter`

**Solution**:
```bash
# Lower confidence threshold
# Edit .env:
CONFIDENCE_THRESHOLD=0.50

# Review classification prompt
cat config/prompts/classification.yaml

# Test with known relevant article
newsanalysis run --limit 1
```

### Scraping Stage Fails

**Problem**: `Extraction failed: timeout`

**Solution**:
```bash
# Increase timeout (in code)
# Or skip problematic sites temporarily

# Test Playwright installation
playwright install chromium --with-deps

# Check for blocked IPs
# Add user agent or use proxy
```

**Problem**: `Content too short` errors

**Solution**:
- Site may have paywalls
- JavaScript rendering required (Playwright fallback)
- Content extraction rules may need adjustment

### Summarization Stage Fails

**Problem**: `JSONDecodeError: Expecting value`

**Solution**:
```bash
# OpenAI returned non-JSON response
# Check prompt format in config/prompts/summarization.yaml

# Verify structured output format
# Add error handling and retry logic

# Check API response in logs
grep "OpenAI response" logs/pipeline.log
```

## Performance Issues

### Slow Pipeline Execution

**Problem**: Pipeline takes >10 minutes for 100 articles

**Diagnostics**:
```bash
# Check cache hit rates
newsanalysis cost-report --cache-only

# Monitor system resources
top
df -h
```

**Solutions**:

1. **Enable caching** (should be automatic):
   ```bash
   # Verify cache tables exist
   sqlite3 news.db ".tables" | grep cache
   ```

2. **Reduce concurrent operations**:
   ```python
   # In code: Adjust max_concurrent in filters/summarizers
   max_concurrent = 5  # Lower for slower systems
   ```

3. **Optimize database**:
   ```bash
   bash scripts/maintenance.sh
   ```

4. **Reduce article limit**:
   ```bash
   newsanalysis run --limit 50
   ```

### High Memory Usage

**Problem**: Python process using >2 GB RAM

**Solution**:
```bash
# Monitor memory
ps aux | grep newsanalysis

# Reduce batch sizes in code
# Clear old database records
bash scripts/maintenance.sh

# Restart pipeline periodically
```

### Database Growing Too Large

**Problem**: Database >1 GB

**Solution**:
```bash
# Run maintenance
bash scripts/maintenance.sh

# Adjust retention period (default 90 days)
RETENTION_DAYS=30 bash scripts/maintenance.sh

# Manual cleanup
sqlite3 news.db "DELETE FROM articles WHERE created_at < datetime('now', '-30 days')"
sqlite3 news.db "VACUUM"
```

## Cost Management

### Exceeding Budget

**Problem**: Daily costs >$10

**Diagnostics**:
```bash
# Check cost breakdown
newsanalysis cost-report --detailed

# Identify expensive modules
sqlite3 news.db "
SELECT module, COUNT(*), SUM(cost)
FROM api_calls
WHERE created_at >= date('now')
GROUP BY module
"
```

**Solutions**:

1. **Improve cache hit rates**:
   ```bash
   # Target >70% hit rate
   newsanalysis cost-report --cache-only
   ```

2. **Reduce article volume**:
   ```bash
   # Edit .env:
   MAX_AGE_HOURS=24  # From 48
   ```

3. **Optimize prompts**:
   - Shorter prompts = lower cost
   - Review config/prompts/*.yaml
   - Remove unnecessary examples

4. **Use batch API** (50% savings):
   - Currently implemented for compatible operations
   - Adds 24-hour latency

5. **Lower confidence threshold**:
   ```bash
   # More aggressive filtering
   CONFIDENCE_THRESHOLD=0.80  # From 0.70
   ```

### Low Cache Hit Rate

**Problem**: Cache hit rate <50%

**Diagnostics**:
```bash
# Check cache stats
sqlite3 news.db "SELECT * FROM cache_stats WHERE date >= date('now', '-7 days')"
```

**Solutions**:
- Articles may be truly unique (expected)
- Verify cache is enabled
- Check cache TTL settings
- Review URL normalization logic

## Database Problems

### Database Locked

**Problem**: `sqlite3.OperationalError: database is locked`

**Solution**:
```bash
# Check for other processes
ps aux | grep newsanalysis

# Kill stale processes
pkill -f newsanalysis

# If persistent, restart
sudo systemctl restart newsanalysis.service
```

### Corruption Detected

**Problem**: `sqlite3.DatabaseError: database disk image is malformed`

**Solution**:
```bash
# Try integrity check
sqlite3 news.db "PRAGMA integrity_check"

# Attempt recovery
sqlite3 news.db ".recover" | sqlite3 news_recovered.db

# Restore from backup
cp backups/news_backup_latest.db.gz .
gunzip news_backup_latest.db.gz
mv news_backup_latest.db news.db

# Prevent future corruption
# - Use proper shutdown procedures
# - Enable WAL mode (in schema.sql)
```

### Query Performance Degraded

**Problem**: Queries taking >5 seconds

**Solution**:
```bash
# Run ANALYZE
sqlite3 news.db "ANALYZE"

# Check indexes
sqlite3 news.db ".schema articles"

# Run maintenance
bash scripts/maintenance.sh

# Check query plan
sqlite3 news.db "EXPLAIN QUERY PLAN SELECT * FROM articles WHERE..."
```

## API Integration Issues

### OpenAI API Timeout

**Problem**: `ReadTimeout: Read timed out`

**Solution**:
```bash
# Check internet connectivity
ping api.openai.com

# Increase timeout in code
# Default: 30 seconds -> 60 seconds

# Check OpenAI status
curl https://status.openai.com/api/v2/status.json
```

### Rate Limiting

**Problem**: `RateLimitError: Rate limit exceeded`

**Solution**:
```bash
# Wait for reset (typically 1 minute for requests, 1 day for tokens)
# Reduce concurrent requests in code
# Upgrade OpenAI API tier

# Check current tier limits
curl https://api.openai.com/v1/organization/limits \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Unexpected API Responses

**Problem**: Classification or summary quality poor

**Solution**:
1. **Review prompts**:
   ```bash
   cat config/prompts/classification.yaml
   cat config/prompts/summarization.yaml
   ```

2. **Check model version**:
   - Ensure using `gpt-4o-mini` or `gpt-4o`
   - Avoid deprecated models

3. **Adjust temperature**:
   ```yaml
   # In prompt config:
   temperature: 0.0  # More deterministic
   ```

4. **Add examples** (few-shot learning):
   - Add high-quality examples to prompts
   - Improves consistency

## Common Error Messages

### "No module named 'newsanalysis'"

**Cause**: Package not installed or wrong virtual environment

**Solution**:
```bash
# Activate correct venv
source venv/bin/activate

# Reinstall package
pip install -e .
```

### "Permission denied"

**Cause**: File permissions issue

**Solution**:
```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/newsanalysis

# Fix permissions
chmod +x scripts/*.sh
chmod 644 config/*.yaml
```

### "No space left on device"

**Cause**: Disk full

**Solution**:
```bash
# Check disk space
df -h

# Clean old backups
rm backups/news_backup_2025*.db.gz

# Clean old logs
rm logs/*.log.gz

# Run maintenance
bash scripts/maintenance.sh
```

## Getting Help

### Diagnostic Commands

```bash
# Full health check
newsanalysis health --verbose

# Check logs for errors
grep -i error logs/pipeline.log | tail -20

# Check last pipeline run
sqlite3 news.db "
SELECT * FROM pipeline_runs
ORDER BY created_at DESC
LIMIT 1
"

# System info
python --version
sqlite3 --version
uname -a
df -h
free -h
```

### Reporting Issues

When reporting issues, include:
1. Error message (full stack trace)
2. Output of `newsanalysis health --verbose`
3. Relevant log entries
4. Configuration (remove API keys)
5. Steps to reproduce

### Emergency Recovery

```bash
# Stop all processes
sudo systemctl stop newsanalysis.timer
sudo systemctl stop newsanalysis.service
pkill -f newsanalysis

# Backup database
cp news.db news_emergency_backup.db

# Restore from last backup
cp backups/news_backup_$(date +%Y%m%d)*.db.gz .
gunzip news_backup_*.db.gz
mv news_backup_*.db news.db

# Reinitialize if needed
mv news.db news_old.db
python scripts/init_db.py

# Restart
sudo systemctl start newsanalysis.timer
```

## Preventive Maintenance

### Weekly Tasks

```bash
# Run health check
newsanalysis health

# Review costs
newsanalysis cost-report

# Check logs
tail -100 logs/pipeline.log
```

### Monthly Tasks

```bash
# Database maintenance
bash scripts/maintenance.sh

# Review cache performance
newsanalysis cost-report --cache-only

# Clean old backups
find backups/ -name "*.gz" -mtime +90 -delete

# Update dependencies
pip list --outdated
```

### Best Practices

1. **Regular backups**: Automated daily via cron
2. **Monitor costs**: Check weekly
3. **Review logs**: Check for warnings
4. **Test changes**: Use `--limit 5` for testing
5. **Keep updated**: Update dependencies monthly
6. **Document changes**: Note any configuration modifications

## Additional Resources

- [User Guide](USER_GUIDE.md)
- [Technical Documentation](implementation_plan/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Trafilatura Documentation](https://trafilatura.readthedocs.io/)
