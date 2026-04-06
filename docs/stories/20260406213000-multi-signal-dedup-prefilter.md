# Multi-Signal Dedup Pre-Filter (v3.6.0)

## Summary

Der Duplikaterkennung wurde von einem Entity-only Pre-Filter auf ein Multi-Signal-System umgestellt, das 5 unabhängige Signale kombiniert. Zusätzlich erhält das LLM nun Content-Snippets für bessere Entscheidungen. Cross-Language Dedup nutzt nun multilingual Embeddings statt Brute-Force.

## Context / Problem

Die bisherige Deduplizierung hatte mehrere Schwachstellen:
- **Nur Entity-Overlap als Pre-Filter** — Paare ohne gemeinsame Eigennamen wurden nie verglichen
- **Nur Titel-Vergleich beim LLM** — gleiche Story mit anderem Titel konnte durchrutschen
- **Cross-Language teuer** — alle FR/IT × DE Paare gingen an LLM (kein Pre-Filter)
- **Kein Content-Vergleich** — identischer Content mit leicht anderem Text nicht erkannt
- **Kein URL-Pattern-Matching** — syndizierte Artikel nicht erkannt

## What Changed

- **`src/newsanalysis/pipeline/dedup/duplicate_detector.py`**: Kompletter Umbau des Pre-Filters
  - Neuer `_multi_signal_pre_filter()` ersetzt `_pre_filter_candidates()`
  - Signal 1: URL-Slug Jaccard-Similarity (>= 0.50) für syndizierte Inhalte
  - Signal 2: Multilingual Embedding Cosine-Similarity (>= 0.65, bzw. 0.40 cross-language)
  - Signal 3: Entity-Overlap (bestehend, unverändert)
  - Signal 4: Title-Token Jaccard-Similarity (>= 0.30)
  - Signal 5: Content SimHash — 64-Bit Locality-Sensitive Hash, Hamming-Distanz <= 15
  - `_compare_articles()` sendet nun Content-Snippet (erste 300 Zeichen) an LLM
  - Cross-Language Dedup nutzt ebenfalls Multi-Signal mit niedrigerem Embedding-Threshold
- **`src/newsanalysis/pipeline/dedup/embedding_service.py`** (NEU): Singleton-Service für multilingual Sentence-Embeddings (`paraphrase-multilingual-MiniLM-L12-v2`), Batch-Encoding, Cosine-Similarity-Matrix
- **`config/prompts/deduplication.yaml`**: Prompt erweitert um optionale Content-Preview-Felder und Cross-Language-Hinweis
- **`pyproject.toml`**: `numpy` als explizite Dependency, Version → 3.6.0
- **`tests/unit/test_duplicate_detector.py`**: Tests aktualisiert + neue Testklassen für URL-Slug, Jaccard, SimHash (35 Tests, alle grün)

## How to Test

```bash
# Unit Tests
pytest tests/unit/test_duplicate_detector.py -v

# Linting
ruff check src/newsanalysis/pipeline/dedup/

# E2E: Pipeline neu laufen lassen
python -m newsanalysis.cli.main run --reset all-today --skip-collection
```

## Risk / Rollback Notes

- **Graceful Fallback**: Wenn `sentence-transformers` nicht installiert ist, wird der Embedding-Signal übersprungen — die anderen 4 Signale funktionieren weiterhin
- **Mehr Kandidaten möglich**: Das Multi-Signal-System ist permissiver als der alte Entity-Filter → mehr LLM-Calls möglich. Aber da der Pre-Filter weiterhin viele Paare eliminiert und DeepSeek sehr günstig ist, ist der Kostenzuwachs minimal
- **Cross-Language günstiger**: Embedding-Pre-Filter reduziert die Anzahl Cross-Language LLM-Calls deutlich
- **Rollback**: `git revert` auf den vorherigen Commit
