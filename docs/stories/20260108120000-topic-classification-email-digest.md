## Summary

Add topic classification to email digest for professional layout with grouped sections. Articles are now classified into 12 topic categories during Gemini summarization and displayed in priority-ordered topic sections in HTML emails.

## Context / Problem

Email digest displayed articles in flat chronological list. Credit analysts needed faster scanning by topic area. The existing `topic` field was only populated with generic "creditreform_insights" from the initial DeepSeek classification, leaving topic grouping underutilized.

## What Changed

- Added `ArticleTopic` enum with 12 categories in `core/enums.py`
- Updated `ArticleSummary` and `SummaryResponse` Pydantic models with topic field
- Extended summarization prompt to request topic classification (zero additional API cost)
- Updated cache storage/retrieval to include topic in entities JSON (backwards compatible)
- Added `TOPIC_PRIORITY` and `TOPIC_TRANSLATIONS` constants to `german_formatter.py`
- Updated `digest_formatter.py` to group articles by topic with priority ordering
- Restructured `email_digest.html` template with topic sections and German headers
- Updated `repository.update_summary()` to persist topic to database
- Added `board_changes` focus area to `topics.yaml`

### Files Modified

- `src/newsanalysis/core/enums.py` - Added ArticleTopic enum
- `src/newsanalysis/core/article.py` - Added topic field to ArticleSummary
- `src/newsanalysis/pipeline/summarizers/article_summarizer.py` - Topic extraction, cache handling, logging
- `config/prompts/summarization.yaml` - Added topic to prompt and schema
- `src/newsanalysis/pipeline/formatters/german_formatter.py` - Topic constants and translations
- `src/newsanalysis/services/digest_formatter.py` - Topic grouping, confidence sorting, smart truncation
- `src/newsanalysis/templates/email_digest.html` - Topic-grouped layout with key_points
- `src/newsanalysis/database/repository.py` - Topic persistence
- `config/topics.yaml` - Added board_changes focus area
- `tests/unit/test_models.py` - Unit tests for ArticleTopic and ArticleSummary

## How to Test

1. Run pipeline: `newsanalysis run`
2. Check `out/digests/*.json` - verify articles have `topic` field with valid enum values
3. Send test email: `newsanalysis email --send`
4. Open in Outlook - verify topic sections with German headers (e.g., "Insolvenzen", "Bonität")
5. Verify priority ordering (risk-critical topics appear first)
6. Verify no empty sections appear

## Risk / Rollback Notes

- **Low Risk**: Topic classification piggybacks on existing Gemini call, no new API costs
- **Backwards Compatible**: Legacy cached entries default to "other" topic
- **Rollback**: Revert template to flat article list if topic grouping causes issues
- **Monitoring**: Watch for excessive articles in "Sonstige" section (indicates poor classification)
