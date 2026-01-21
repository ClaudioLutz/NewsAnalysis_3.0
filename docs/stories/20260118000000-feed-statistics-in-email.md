# Add Feed Statistics to Email Digest and CLI Output

## Summary

Added per-feed statistics showing collected/matched/rejected article counts to both the CLI pipeline output and the email digest footer. This provides visibility into which news sources are providing relevant business content.

## Context / Problem

After adding multiple new RSS feeds (20 Minuten, Blick, regional feeds), there was no easy way to see:
- Which feeds were successfully collecting articles
- Which feeds were providing business-relevant content (passing AI filter)
- Whether new feeds were worth keeping or should be removed

This information was only available by querying the database manually.

## What Changed

### 1. CLI Pipeline Output

Added a "By Feed (Today)" table to the pipeline results displayed after each run:

```
By Feed (Today):
  Source                         | Total | Match | Reject
  --------------------------------------------------------
  Blick                          |    48 |     0 |     48
  NZZ Recent                     |    26 |     1 |     25
  Tages-Anzeiger Front           |    23 |     2 |     21
  20 Minuten Wirtschaft          |     1 |     1 |      0
  ...
```

**Files modified:**
- `src/newsanalysis/cli/commands/run.py` - Added feed breakdown query and display in `_display_pipeline_results()`

### 2. Email Digest Footer

Added a "Nach Quelle (Heute)" table to the email footer showing the same statistics:
- Source name
- Total articles collected
- Matched (highlighted in green when > 0)
- Rejected

**Files modified:**
- `src/newsanalysis/services/digest_formatter.py` - Added `feed_stats` parameter to `format_with_images()`
- `src/newsanalysis/templates/email_digest.html` - Added feed breakdown table section
- `src/newsanalysis/pipeline/orchestrator.py` - Added `_get_feed_stats()` method and pass to formatter

### Database Query

Both CLI and email use the same query pattern:
```sql
SELECT
    source,
    COUNT(*) as total,
    SUM(CASE WHEN is_match = 1 THEN 1 ELSE 0 END) as matched,
    SUM(CASE WHEN is_match = 0 THEN 1 ELSE 0 END) as rejected
FROM articles
WHERE DATE(collected_at) = DATE('now')
GROUP BY source
ORDER BY total DESC
```

## How to Test

```bash
# Run pipeline and check CLI output
python -m newsanalysis.cli.main run

# Regenerate digest email to see feed table
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

## Risk / Rollback Notes

- **Risk:** None - this is display-only and doesn't affect pipeline processing
- **Rollback:** Remove the feed_stats sections from template and formatter, or pass empty list
