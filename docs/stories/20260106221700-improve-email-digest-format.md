# Improve Email Digest Format

## Summary

Updated the email digest to display shorter article summaries with better visual layout, including Outlook-compatible spacing and relevance-based ordering.

## Context / Problem

The email digest was displaying long article summaries (150-200 words) that made the email too verbose and hard to scan. The formatting also had issues with article spacing in Outlook and missing source attribution.

## What Changed

- **config/prompts/summarization.yaml**: Changed summary prompt from "150-200 words" to "1-2 sentences, max 50 words"; reduced key points from 2-8 to 2-3 items
- **src/newsanalysis/pipeline/summarizers/article_summarizer.py**: Updated Pydantic model descriptions to match new shorter format
- **src/newsanalysis/services/digest_formatter.py**:
  - Added filtering for "Analysis unavailable" placeholders
  - Added sorting by confidence/relevance score
  - Added fallback truncation for legacy long summaries
  - Switched from markdown to structured JSON for article data
- **src/newsanalysis/templates/email_digest.html**:
  - Added Outlook-compatible spacer rows (20px) between articles
  - Moved source to separate line below title
  - Adjusted font sizes and line heights for compact display
- **tests/unit/test_email_service.py**: Updated tests for new key_points limit (2 instead of 3)

## How to Test

```bash
# Clear summary cache to regenerate with new prompt
python -c "import sqlite3; conn = sqlite3.connect('news.db'); conn.execute('DELETE FROM content_fingerprints'); conn.commit()"

# Delete old digest
python -c "import sqlite3; conn = sqlite3.connect('news.db'); conn.execute(\"DELETE FROM digests WHERE digest_date='2026-01-06'\"); conn.commit()"

# Re-summarize and regenerate digest
newsanalysis run --reset summarization --skip-collection

# Preview email
newsanalysis email --preview --recipient test@example.com
```

## Risk / Rollback Notes

- **Low risk**: Changes are cosmetic/formatting only
- **Cache dependency**: Existing cached summaries will retain old format until cache is cleared
- **Rollback**: Revert commit and clear content_fingerprints table to regenerate summaries with old prompt
