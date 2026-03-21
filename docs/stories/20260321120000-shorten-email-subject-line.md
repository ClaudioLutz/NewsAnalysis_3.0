# E-Mail-Betreff kürzen — max. 60 Zeichen

## Summary

E-Mail-Betreff wurde von ~78 auf max. 60 Zeichen gekürzt, damit er in Outlook nicht mehr abgeschnitten wird. Prefix von `Creditreform News-Digest:` auf `News-Digest:` verkürzt.

## Context / Problem

Der Betreff `Creditreform News-Digest: {top_title}` war mit bis zu 78 Zeichen zu lang für Outlook. Je nach Ansicht zeigt Outlook nur 50–80 Zeichen an, sodass der Betreff häufig mit "..." abgeschnitten wurde und Empfänger den relevanten Teil (den Artikel-Titel) nicht sahen.

## What Changed

- **`src/newsanalysis/pipeline/orchestrator.py`** — Prefix auf `News-Digest: ` gekürzt, Titel-Limit dynamisch berechnet (60 - Prefix-Länge = 47 Zeichen)
- **`src/newsanalysis/cli/commands/email.py`** — Gleiche Änderung im Email-CLI-Befehl
- **`docs/Ideen/verbesserungen-brainstorming.md`** — Dokumentation aktualisiert

### Vorher/Nachher

| | Prefix | Titel max. | Total max. |
|---|--------|-----------|------------|
| Vorher | `Creditreform News-Digest: ` (28 Z.) | 50 Z. | ~78 Z. |
| Nachher | `News-Digest: ` (13 Z.) | 47 Z. | 60 Z. |

## How to Test

1. Pipeline ausführen oder Digest neu generieren:
   ```bash
   python -m newsanalysis.cli.main run --reset digest --skip-collection
   ```
2. Prüfen, dass der Betreff in Outlook vollständig sichtbar ist (max. 60 Zeichen)
3. Tests: `pytest tests/ -x -q` — alle Tests müssen bestehen

## Risk / Rollback Notes

- **Risiko:** Gering — rein kosmetische Änderung am Betreff
- **Rollback:** Prefix zurück auf `Creditreform News-Digest: ` setzen und `max_length=50` wiederherstellen
