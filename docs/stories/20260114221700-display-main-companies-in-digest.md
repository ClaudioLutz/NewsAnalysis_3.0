# Display Main Companies in Email Digest

## Summary

Added company name display below article titles in the email digest, limited to the 1-3 main companies the article is primarily about.

## Context / Problem

Users wanted to quickly identify which companies an article is about without having to read the full summary. The existing entity extraction was capturing all mentioned companies (including competitors, market peers, etc.), which resulted in cluttered displays with many irrelevant company names.

## What Changed

### 1. Digest Formatter (`src/newsanalysis/services/digest_formatter.py`)
- Extract `companies` from article entities in `_parse_articles()` method
- Pass company list to email template context

### 2. Email Template (`src/newsanalysis/templates/email_digest.html`)
- Added company display in orange (`#cc6600`) below article titles
- Limited display to first 3 companies using Jinja2 slice: `article.companies[:3]`
- Style: 12px bold font for visibility

### 3. Summarization Prompt (`config/prompts/summarization.yaml`)
- Updated entity extraction instructions to extract only "1-3 MAIN companies the article is ABOUT (not all mentioned)"
- Added `maxItems: 3` constraint to schema
- Updated description to clarify extraction scope

## How to Test

1. Re-run summarization for today's articles:
   ```bash
   python -m newsanalysis.cli.main run --reset summarization --skip-collection --today-only
   ```

2. Preview the email digest:
   ```bash
   python -m newsanalysis.cli.main email --preview --today-only
   ```

3. Verify company names appear in orange below article titles and are limited to main companies only.

## Risk / Rollback Notes

- **Risk**: Existing articles retain old entity extraction until re-summarized
- **Rollback**: Remove the company display block from email template or set `companies` to empty list in formatter
