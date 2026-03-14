## Summary

Improved LLM summarization prompt to produce stakes-first, non-redundant summaries with variable key point count (0-4) based on article complexity. Tightened credit_impact classification to require concrete company impact.

## Context / Problem

Article summaries and key points had three quality issues: (1) key points frequently repeated information from the summary, (2) fixed 2-3 key points forced padding for simple articles, (3) credit_impact was too broadly classified as "negative" for general market trends without specific company impact.

## What Changed

- `config/prompts/summarization.yaml`: Rewrote system prompt with stakes-first writing rules, anti-redundancy instructions, telegraphic style guidance, variable key point count (0-4), bad/good examples, and stricter credit_impact definition requiring concrete company impact
- `src/newsanalysis/pipeline/summarizers/article_summarizer.py`: Updated `SummaryResponse` model to allow 0 key points (`default_factory=list`)
- `src/newsanalysis/core/article.py`: Changed `validate_key_points` from "at least 2 required" to "0-4 allowed"
- `src/newsanalysis/services/digest_formatter.py`: Increased `_truncate_summary` max_length from 200 to 300 characters to accommodate stakes-first summaries

## How to Test

```bash
# Clear today's summary cache and re-run
python -c "import sqlite3; c=sqlite3.connect('news.db'); c.execute(\"DELETE FROM content_fingerprints WHERE created_at >= '2026-03-14'\"); c.commit()"
python -m newsanalysis.cli.main run --reset summarization-today --skip-collection
```

Verify in the email digest:
- Summaries lead with credit impact/stakes, not event description
- Key points contain only new facts not in the summary
- Simple articles may have 0 key points
- credit_impact is "negative" only when a specific named company is directly affected

## Risk / Rollback Notes

- Prompt changes affect all future summarizations; old cached summaries remain unchanged
- Content fingerprint cache must be cleared for existing articles to get new summaries
- Rollback: revert `summarization.yaml` to previous version
