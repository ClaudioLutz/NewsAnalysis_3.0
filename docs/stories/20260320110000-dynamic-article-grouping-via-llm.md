# Dynamische Themengruppierung via LLM-Redakteur-Pass

## Summary

Die Email-Digest gruppiert Artikel neu in 3-10 dynamische Themencluster statt in 13 statische Kategorien. Die bestehende Meta-Analysis-LLM-Abfrage wird erweitert, um alle Artikel thematisch zu clustern. Verwandte Artikel landen in derselben Gruppe, auch wenn sie verschiedene statische Topics haben.

## Context / Problem

Zwei Probleme mit der statischen Themengruppierung:

1. **Thematisch zusammengehörende Artikel landen in verschiedenen Kategorien**: z.B. "Marti Bau Konkurs" unter Insolvenzen, "Bausektor 15% mehr Pleiten" unter Konjunktur, "CEO von Implenia tritt zurück" unter Personalien — obwohl alle drei zur Baubranche gehören.
2. **Zu viele kleine Kategorien**: 13 statische Topics führen zu vielen Ein-Artikel-Sektionen, die das Mail unübersichtlich machen.

## What Changed

- **`src/newsanalysis/core/digest.py`**:
  - Neues Pydantic-Model `ArticleGroup` (label, icon, article_indices)
  - Neues Feld `article_groups: List[ArticleGroup]` auf `MetaAnalysis` (default=[], max=10)

- **`config/prompts/meta_analysis.yaml`**:
  - System-Prompt: Neue ARTICLE GROUPING Sektion mit Anweisungen für 3-10 Cluster
  - User-Prompt: JSON-Format um `article_groups` erweitert
  - Output-Schema: `article_groups` Array hinzugefügt

- **`src/newsanalysis/pipeline/generators/digest_generator.py`**:
  - Neue Methode `_validate_article_groups()`: validiert Indices, entfernt Duplikate, erstellt Catch-all-Gruppe
  - `_build_articles_summary()`: Hinweis am Ende für LLM-Indexierung
  - Import von `ArticleGroup` hinzugefügt

- **`src/newsanalysis/services/digest_formatter.py`**:
  - Refactoring: `_parse_article_dict()` extrahiert aus `_parse_articles()` (keine Duplikation)
  - Neue Methode `_regroup_by_llm_groups()`: gruppiert Artikel nach LLM-Clustern
  - Neue Hilfsmethoden: `_sort_articles_in_groups()`, `_sort_groups_by_confidence()`
  - `format()` und `format_with_images()` nutzen dynamische Gruppierung mit Fallback

- **`src/newsanalysis/templates/email_digest.html`**:
  - Topic-Header: dynamisches Label + LLM-Icon bei `use_dynamic_groups`
  - Statistik-Footer: dynamische Labels statt `TOPIC_TRANSLATIONS` Lookup

## How to Test

```bash
# Tests
pytest tests/ -x

# Digest neu generieren (benötigt API-Zugang)
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Prüfpunkte:
# 1. Email hat 3-10 Themengruppen (nicht 13 statische)
# 2. Verwandte Artikel sind zusammen gruppiert
# 3. Jede Gruppe hat ein Icon und ein deutsches Label
# 4. Alle Artikel sind einer Gruppe zugeordnet
```

## Risk / Rollback Notes

- **Rückwärtskompatibel**: `article_groups` hat `default_factory=list`, alte Digests in der DB funktionieren weiterhin mit statischer Gruppierung (Fallback).
- **Fallback eingebaut**: Wenn das LLM keine `article_groups` liefert oder die Validierung fehlschlägt, greift automatisch die statische Topic-Gruppierung.
- **Rollback**: `article_groups` Feld und Prompt-Erweiterung entfernen; Formatter fällt automatisch auf statische Gruppierung zurück.
- **Risiko**: LLM könnte suboptimale Cluster bilden (zu viele kleine Gruppen, unklare Labels). Evaluierung nach ersten Runs empfohlen.
