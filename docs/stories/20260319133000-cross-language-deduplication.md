# Cross-Language Deduplication for FR/IT Articles

## Summary

Added a second deduplication pass that compares French and Italian articles against German canonical articles using LLM, bypassing the entity pre-filter which cannot match cross-language terms (SNB vs BNS, Leitzins vs taux directeur).

## Context / Problem

French and Italian articles covering the same story as German articles were not being detected as duplicates. Example: SNB interest rate decision appeared three times in the digest — once in German (Blick), once in French (Le Temps), and once in Italian (RSI Economia). The entity pre-filter requires shared entities between titles, but cross-language entity matching fails for translated terms (SNB/BNS, Leitzins/taux directeur/tasso guida).

## What Changed

- **`config/feeds.yaml`**: Added `language: fr` to 5 French feeds (Tribune de Genève, 24 heures, Le Temps x3) and `language: it` to 7 Italian feeds (RSI x3, LaRegione x4)
- **`src/newsanalysis/core/config.py`**: Added `language` field to `FeedConfig` model (default: `de`)
- **`src/newsanalysis/core/article.py`**: Added `language` field to `ArticleMetadata` and `Article` models
- **`src/newsanalysis/pipeline/collectors/rss.py`**: Propagates `language` from feed config to collected articles
- **`src/newsanalysis/database/repository.py`**: Persists and loads `language` column
- **`src/newsanalysis/database/migrations.py`**: Added v5→v6 migration adding `language` column (default: `de`)
- **`src/newsanalysis/pipeline/dedup/duplicate_detector.py`**: New `detect_cross_language_duplicates()` method — compares FR/IT articles against DE canonicals without entity pre-filter
- **`src/newsanalysis/pipeline/orchestrator.py`**: Integrated second dedup pass after regular dedup — separates articles by language, runs cross-language comparison
- **`tests/unit/test_duplicate_detector.py`**: 4 new tests for cross-language dedup

## How to Test

```bash
# Run unit tests
pytest tests/unit/test_duplicate_detector.py -v --no-cov

# Verify migration runs
python -c "import sqlite3; c=sqlite3.connect('news.db'); c.execute('SELECT language FROM articles LIMIT 1'); print('OK')"

# Full pipeline run (will apply migration + use cross-language dedup)
python -m newsanalysis.cli.main run
```

## Risk / Rollback Notes

- **Risk**: Cross-language dedup sends more pairs to the LLM (no pre-filter), increasing API costs slightly. Bounded by: ~5-15 FR/IT articles × ~15-25 DE canonicals = max ~375 additional DeepSeek calls per run (~$0.01)
- **Risk**: False positives possible if LLM incorrectly matches unrelated cross-language articles. Mitigated by same 0.75 confidence threshold.
- **Rollback**: `git revert <commit>`. Existing articles retain `language` column (harmless). Cross-language duplicates would need manual un-marking: `UPDATE articles SET is_duplicate=0 WHERE language IN ('fr','it') AND is_duplicate=1`
