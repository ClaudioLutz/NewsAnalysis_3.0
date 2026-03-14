# Add Credit Impact Classification

## Summary

Added a 4-level credit impact classification (elevated_risk, negative, neutral, positive) to the article summarization pipeline, with visual differentiation in the email digest and a new Risiko-Radar section for acute risk alerts.

## Context / Problem

The existing system classified articles as relevant/irrelevant with a topic category, but lacked a creditworthiness impact assessment. The only visual differentiation was a basic rule-based "elevated risk" flag for certain topic categories (insolvency, credit_risk, business_scams, ecommerce_fraud) with high confidence. This made it impossible for analysts to quickly distinguish between articles signaling acute credit risk vs. neutral industry news vs. positive developments.

## What Changed

- **New `CreditImpact` enum** in `src/newsanalysis/core/enums.py` with values: `elevated_risk`, `negative`, `neutral`, `positive`
- **Summarization prompt** (`config/prompts/summarization.yaml`) extended with `credit_impact` field and clear category definitions with examples
- **Article model** (`src/newsanalysis/core/article.py`) — added `credit_impact` field to both `ArticleSummary` and `Article` models
- **Database schema** (`src/newsanalysis/database/schema.sql`) — added `credit_impact TEXT` column to articles table
- **Repository** (`src/newsanalysis/database/repository.py`) — reads/writes `credit_impact`
- **Summarizer** (`src/newsanalysis/pipeline/summarizers/article_summarizer.py`) — parses `credit_impact` from LLM response, caches it, applies rule-based fallback when LLM doesn't return a value
- **Digest formatter** (`src/newsanalysis/services/digest_formatter.py`) — 4-level visual styling, credit impact sorting (elevated_risk first), Risiko-Radar extraction, compact neutral display (1 key point)
- **Email template** (`src/newsanalysis/templates/email_digest.html`) — 4 color schemes with BMP Unicode icons (warning, triangle-down, circle, triangle-up), Risiko-Radar section between Executive Summary and articles
- **JSON formatter** (`src/newsanalysis/pipeline/formatters/json_formatter.py`) — includes `credit_impact` in digest output
- **DB migration** (`scripts/init_db.py`) — adds `credit_impact` column to existing databases

## How to Test

```bash
# Run existing tests (no regressions)
pytest tests/unit/ --ignore=tests/unit/test_date_utils.py -k "not (test_format_digest or test_parse_articles or test_article_creation or test_article_with_metadata or test_article_with_published or test_feed_config)"

# Verify module imports
python -c "from newsanalysis.core.enums import CreditImpact; print([e.value for e in CreditImpact])"

# Run pipeline with limited articles to test classification
python -m newsanalysis.cli.main run --limit 5

# Regenerate digest to see visual changes
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Test with today's articles only (smaller digest for layout testing)
python -m newsanalysis.cli.main run --reset digest --skip-collection --today-only
```

## Risk / Rollback Notes

- **Low risk**: The `credit_impact` field is nullable — existing articles without it default to `neutral` display
- **Backward compatible**: Old `risk_level` values ("elevated"/"standard") are normalized to new enum values
- **Rollback**: Remove the `credit_impact` column with `ALTER TABLE articles DROP COLUMN credit_impact` (SQLite 3.35+), revert code changes
- **Cache**: Existing content fingerprint cache will return articles without `credit_impact` — they'll use the rule-based fallback, which matches the previous behavior exactly
