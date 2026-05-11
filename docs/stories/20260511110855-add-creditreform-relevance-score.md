# Add Creditreform-Relevance Score (`cr_relevance`)

## Summary

Adds a per-article integer score 1–10 (`cr_relevance`) that captures how important an article is for Creditreform Switzerland's business — independent of the LLM's classification confidence. The classifier emits this score in the same call (no extra LLM round-trip), it is persisted on `articles` and in the classification cache, and the email digest now uses it both to order topic sections and to pick the subject-line article. Subject is no longer "first article of highest-confidence topic" but "globally highest `cr_relevance` article".

## Context / Problem

Production digest on 2026-05-08 chose the subject "Creditreform News-Digest: SECO aktualisiert Sanktionsliste Sudan – ...". This article has high LLM-classification confidence (clear topic fit, official source) but **low business relevance** for a Swiss credit bureau — it is an international compliance notice with no named Swiss company affected. Investigation showed the digest formatter's `get_top_article_title` ranks topics by average `confidence` (= LLM's certainty about the topic label), not by business importance. There was no field anywhere that captured "how important is this for Creditreform" — only `confidence`, `topic`, and a 3-level `credit_impact` enum.

User priority order: Swiss legal/regulatory changes (revDSG, SchKG, Inkassogesetz) > federal court / EDÖB / FINMA decisions > Swiss bankruptcies of named firms > sector crises > general CH economic news > international regulation with CH spillover > international sanctions/insolvencies without CH ties > general international > politics/sport/culture.

## What Changed

- `config/prompts/classification.yaml` — added a CREDITREFORM RELEVANCE SCORE section with 10 anchored levels and explicit rules of thumb. `user_prompt_template` and `output_schema` now require `cr_relevance: integer 1-10`.
- `src/newsanalysis/pipeline/filters/ai_filter.py` — `ClassificationResponse` gains `cr_relevance: int (ge=1, le=10)`; `_classify_article` writes it to `ClassificationResult` (defensive: `.get("cr_relevance")` so older cached responses still parse).
- `src/newsanalysis/core/article.py` — `ClassificationResult.cr_relevance: Optional[int]` (1-10, nullable for legacy); `Article.cr_relevance: Optional[int]`.
- `src/newsanalysis/database/migrations.py` — bumped `CURRENT_SCHEMA_VERSION` 6→7. New `migrate_v6_to_v7` adds nullable `cr_relevance INTEGER` to both `articles` and `classification_cache` (only if the cache table already exists).
- `src/newsanalysis/database/schema.sql` — added `cr_relevance INTEGER` to `classification_cache` for fresh databases.
- `src/newsanalysis/database/repository.py` — `update_classification` writes `cr_relevance`; `_row_to_article` reads it defensively (`if "cr_relevance" in row.keys()`).
- `src/newsanalysis/services/cache_service.py` — `get_cached_classification` selects + returns `cr_relevance`; `cache_classification` inserts it.
- `src/newsanalysis/pipeline/formatters/json_formatter.py` — emits `"cr_relevance"` in the per-article JSON, so the digest formatter sees it via the digest's `json_output` blob.
- `src/newsanalysis/services/digest_formatter.py`:
  - `_parse_article_dict` extracts `cr_relevance` into the parsed dict.
  - `_sort_articles_in_groups` now sorts within a topic by `(credit_impact, -cr_relevance, -confidence)` — `cr_relevance` is the new primary tiebreaker after `credit_impact`.
  - `_sort_groups_by_confidence` replaced by `_sort_groups_by_relevance`, which orders topics by avg `cr_relevance` and falls back to avg `confidence` when all values are NULL.
  - `get_top_article_title` rewritten to pick the **single article** with the highest `cr_relevance` across **all topics** (tie-breaks: `credit_impact` priority, then `confidence`). Previously it returned the first article of the highest-confidence topic.
- `tests/unit/test_email_service.py` — three new unit tests: subject picks highest `cr_relevance` globally; subject falls back to `credit_impact`+`confidence` when no `cr_relevance` is present; topic ordering follows avg `cr_relevance`.
- `pyproject.toml` — version 3.7.1 → 3.8.0 (MINOR: new feature, schema migration, no breaking config change since `EMAIL_DELIVERY_MODE` and other env vars are unchanged).
- `CLAUDE.md` and `README.md` — documented the new score, the subject-selection change, and the legacy-row handling (Variant C).

## How to Test

Schema + migration (fresh + upgrade path):
```bash
# Fresh DB: schema.sql now contains cr_relevance in classification_cache
python -c "from newsanalysis.database.connection import DatabaseConnection; DatabaseConnection('test_fresh.db'); print('OK')"

# Upgrade an existing v6 DB: migration v6→v7 adds the column
python -c "from newsanalysis.database.connection import DatabaseConnection; DatabaseConnection('news.db'); print('OK')"
```

Unit tests:
```bash
pytest tests/unit/test_email_service.py -k "top_article or topic_groups" -v
pytest tests/unit/test_email_service.py tests/unit/test_email_with_images.py
```

End-to-end (production-like) — pick any small batch:
```powershell
python -m newsanalysis.cli.main run --limit 10
# Then inspect the digest:
python -c "from newsanalysis.database.connection import DatabaseConnection; from newsanalysis.database.digest_repository import DigestRepository; from datetime import date; import json; d = DigestRepository(DatabaseConnection('news.db')).get_digest_by_date(date.today()); arts = json.loads(d['json_output'])['articles']; print(sorted([(a.get('cr_relevance'), a['title'][:60]) for a in arts], reverse=True))"
```

Subject-selection check on today's digest:
```bash
python -c "from newsanalysis.services.digest_formatter import HtmlEmailFormatter; from newsanalysis.database.connection import DatabaseConnection; from newsanalysis.database.digest_repository import DigestRepository; from datetime import date; d = DigestRepository(DatabaseConnection('news.db')).get_digest_by_date(date.today()); print(HtmlEmailFormatter().get_top_article_title(d))"
```

## Risk / Rollback Notes

- **Cost impact:** ~5 extra output tokens per classified article. At 375 articles/day on DeepSeek, well under 1¢/day.
- **Score quality risk:** LLMs on 1-10 scales tend to mode-cluster (5-7). The prompt addresses this with explicit anchors per level and "do NOT default to the middle" instructions. If real-world output drifts toward the middle, the anchors can be sharpened in `classification.yaml` without code changes.
- **Variant C — legacy rows:** existing articles classified before v7 keep `cr_relevance = NULL`. In sort logic, NULL is treated as 0, so they sink to the bottom. No backfill is run. If a digest contains only legacy articles, the top-article fallback (avg confidence + credit_impact) keeps the previous behavior.
- **Cache invalidation:** the classification cache schema also got the new column. Cached entries from before this change have NULL `cr_relevance` and will return without it until they expire (90-day TTL) and are re-classified. To force fresh classification immediately: `DELETE FROM classification_cache;`.
- **Subject behavior change:** subject is no longer always from the largest topic. A single high-`cr_relevance` article in a small topic can now win. This is the intended behavior; flag if any user-facing communication relies on the old grouping.
- **Rollback:** revert this commit and downgrade `CURRENT_SCHEMA_VERSION` to 6. The `cr_relevance` column on `articles` and `classification_cache` is nullable and harmless if left in place; SQLite cannot DROP COLUMN cleanly on older versions, so leave it.
