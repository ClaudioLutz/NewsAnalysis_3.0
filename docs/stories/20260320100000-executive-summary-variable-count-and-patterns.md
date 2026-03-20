# Executive Summary: Variable Anzahl & Mustererkennung

## Summary

Die "Heute in 30 Sekunden"-Sektion verwendet neu 1–5 variable Sätze statt fix 3, und das LLM wird angewiesen, thematisch verwandte Artikel zu Muster-Sätzen zu kombinieren statt einzelne Artikel zu paraphrasieren.

## Context / Problem

Zwei Probleme mit der bisherigen Executive Summary:

1. **Fix 3 Sätze**: An ruhigen Tagen wurden Füllsätze über Routinenachrichten generiert. An hektischen Tagen fehlten wichtige Themen.
2. **Artikelparaphrasen statt Muster**: Jeder Satz paraphrasierte einen einzelnen Artikel — den der Leser 10 Sekunden später nochmal im Detail sah. Kein Mehrwert gegenüber den Einzelartikeln.

## What Changed

- **`config/prompts/meta_analysis.yaml`**:
  - Schema: `minItems: 1, maxItems: 5` statt `minItems: 3, maxItems: 3`
  - System-Prompt: Neue Anweisung zur variablen Länge (1–2 bei ruhigen Tagen, bis 5 bei viel Bewegung)
  - System-Prompt: Explizite Mustererkennungs-Anweisung (verwandte Artikel in einem Satz kombinieren)
  - System-Prompt: Good/Bad-Beispiele für Muster-Sätze vs. Einzelartikel-Paraphrasen
  - User-Prompt: Kommentar bei executive_summary aktualisiert
- **`src/newsanalysis/core/digest.py`**:
  - `MetaAnalysis.executive_summary`: `max_length=5` statt `max_length=3`, neue Description

## How to Test

```bash
# Digest neu generieren und Output prüfen
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Prüfen: executive_summary hat 1-5 Sätze (nicht immer genau 3)
# Prüfen: Verwandte Artikel werden in einem Satz gruppiert
```

## Risk / Rollback Notes

- **Risiko gering**: Nur Prompt- und Schema-Änderung, kein Code-Logik-Change.
- **Rollback**: Schema auf `minItems: 3, maxItems: 3` und Prompt-Text zurücksetzen.
- Das LLM könnte anfangs trotzdem 3 Sätze generieren (gelerntes Muster). Ggf. nach ersten Runs evaluieren.
