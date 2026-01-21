# Expand News Sources with Regional Feeds and Fix Scraping

## Summary

Added 20 Minuten and Blick news sources including business-specific and regional feeds for local business coverage. Fixed scraping issues caused by TLS fingerprinting bot protection (Akamai/Cloudflare) by integrating `curl_cffi` library. Added `--fresh-start-today` CLI flag for development workflows.

## Context / Problem

1. **Missing popular Swiss news sources:** 20 Minuten and Blick (two of Switzerland's most-read news sites) were not being collected
2. **Scraping blocked by bot protection:** Blick uses Akamai TLS fingerprinting which blocked all requests with 403 Forbidden errors
3. **Old articles appearing in digest:** The `--reset digest` command was incorrectly resetting ALL historical articles instead of just today's
4. **No regional coverage:** Missing local business news (bankruptcies, store closings, acquisitions) that don't make national headlines
5. **No clean development reset:** No way to clear today's data and start fresh during testing

## What Changed

### 1. TLS Fingerprint Bypass (`curl_cffi` integration)

Added `curl_cffi` library which impersonates Chrome's TLS fingerprint to bypass Akamai/Cloudflare bot protection.

**Files modified:**
- `pyproject.toml` - Added `curl_cffi>=0.7.0` dependency
- `src/newsanalysis/pipeline/scrapers/trafilatura_scraper.py` - Primary fetch method now uses `curl_cffi` with Chrome impersonation, falls back to `httpx`

```python
# Uses Chrome TLS fingerprint impersonation
response = curl_requests.get(url, impersonate="chrome", timeout=self.timeout)
```

### 2. New RSS Feeds Added

**Business Feeds:**
- 20 Minuten Wirtschaft (`partner-feeds.20min.ch/rss/20minuten/wirtschaft`)
- Blick Wirtschaft (`blick.ch/wirtschaft/rss.xml`)

**Regional Feeds (local business news):**
- 20 Minuten Zürich (`partner-feeds.20min.ch/rss/20minuten/regionen/zuerich`)
- 20 Minuten Basel (`partner-feeds.20min.ch/rss/20minuten/regionen/basel`)
- 20 Minuten Bern (`partner-feeds.20min.ch/rss/20minuten/regionen/bern`)
- 20 Minuten Ostschweiz (`partner-feeds.20min.ch/rss/20minuten/regionen/ostschweiz`)
- 20 Minuten Zentralschweiz (`partner-feeds.20min.ch/rss/20minuten/regionen/zentralschweiz`)
- Blick Zürich (`blick.ch/schweiz/zuerich/rss.xml`)

**Fixed Feeds:**
- 20 Minuten main feed URL changed from sitemap to proper RSS

**Files modified:**
- `config/feeds.yaml`

### 3. Fixed `--reset digest` Bug

The reset command was using `WHERE pipeline_stage = 'digested' OR included_in_digest = TRUE` which reset ALL historical articles. Changed to only reset articles with `digest_date = today`.

**Files modified:**
- `src/newsanalysis/cli/commands/run.py` - `_reset_articles()` function

### 4. Added `--fresh-start-today` CLI Flag

New command to delete all data from today and run fresh:
```bash
python -m newsanalysis.cli.main run --fresh-start-today
```

Deletes: articles, digests, pipeline_runs, api_calls, cache_stats, classification_cache (all from today only).

Fixed foreign key constraint issue by deleting from child tables first (duplicate_members, duplicate_groups, article_images) before deleting articles.

**Files modified:**
- `src/newsanalysis/cli/commands/run.py` - Added `--fresh-start-today` flag and `_fresh_start_today()` function

## How to Test

```bash
# Test fresh start (clears today's data and runs full pipeline)
python -m newsanalysis.cli.main run --fresh-start-today

# Verify new feeds are being collected
python -c "
import sqlite3
conn = sqlite3.connect('news.db')
cursor = conn.execute('''
    SELECT source, COUNT(*) as total
    FROM articles
    WHERE DATE(collected_at) = DATE('now')
    GROUP BY source ORDER BY total DESC
''')
for row in cursor:
    print(f'{row[0]}: {row[1]} articles')
"

# Verify Blick scraping works (should not get 403 errors)
# Check logs for successful curl_cffi fetches
```

## Risk / Rollback Notes

- **Risk:** `curl_cffi` requires native compilation. If installation fails on some systems, the scraper falls back to `httpx` automatically.
- **Risk:** Regional feeds may have lower business relevance on some days. The AI filter correctly rejects non-business content.
- **Rollback:** Set `enabled: false` on individual feeds in `config/feeds.yaml` or remove `curl_cffi` from dependencies.
