# Crediweb Company Links im Email-Digest

## Summary

Firmennamen im Email-Digest werden automatisch gegen die Creditreform Pool_Adresse-Datenbank (MSSQL) gematcht. Bei einem Treffer wird der Firmenname zu einem klickbaren Link auf crediweb.ch, der direkt zur Firmensuche mit der CrefoID führt.

## Context / Problem

Im Email-Digest erscheinen extrahierte Firmennamen orange/fett unter den Artikeltiteln — bisher als reiner Text. Die Empfänger (Creditreform-Mitarbeiter) mussten manuell auf crediweb.ch nach der Firma suchen. Durch automatisches Matching und Verlinkung wird der Workflow deutlich vereinfacht.

## What Changed

- **`src/newsanalysis/services/company_matcher.py`** (NEU): CompanyMatcher-Service mit zweistufigem Matching (exakt → LIKE fallback) gegen `Pool_Adresse.Pa_S_Firma` in der CNC Report DB (MSSQL via pyodbc/ODBC). In-Memory Session-Cache verhindert redundante Queries.
- **`src/newsanalysis/core/config.py`**: Neue Config-Felder `db_server`, `db_database`, `db_driver` für MSSQL-Verbindung.
- **`src/newsanalysis/services/digest_formatter.py`**: `HtmlEmailFormatter` akzeptiert optionalen `CompanyMatcher`. In `_parse_article_dict()` werden Firmennamen zu `{name, url}`-Dicts aufgelöst.
- **`src/newsanalysis/templates/email_digest.html`**: Firmennamen-Anzeige von plain text auf conditional links umgestellt (dotted underline, gleiche orange Farbe).
- **`src/newsanalysis/pipeline/orchestrator.py`**: CompanyMatcher wird im Email-Sending-Stage erstellt, an Formatter übergeben und nach Versand geschlossen.
- **`pyproject.toml`**: Version 3.4.1 → 3.5.0, neue optionale Dependency `pyodbc>=5.0` unter `[crediweb]`.
- **`.env.example`**: CNC Report DB-Felder dokumentiert.

## How to Test

```bash
# 1. Linting & Formatting
ruff check src/ && ruff format --check src/

# 2. Unit Tests
pytest tests/unit/

# 3. Manueller Integrationstest (Company Matcher)
python -c "
from newsanalysis.services.company_matcher import CompanyMatcher
m = CompanyMatcher('prodsvcreport.svc.ch', 'CAG_Analyse')
m.connect()
print(m.resolve_companies(['UBS', 'Novartis', 'Fantasiefirma']))
m.close()
"

# 4. Digest mit Links generieren (Preview ohne Versand)
$env:EMAIL_AUTO_SEND='false'
python -m newsanalysis.cli.main run --reset digest --skip-collection
python -m newsanalysis.cli.main email --preview
```

## Risk / Rollback Notes

- **Graceful Fallback**: Wenn `DB_SERVER` nicht konfiguriert oder DB nicht erreichbar ist, werden Firmennamen wie bisher als plain text angezeigt — kein Fehler.
- **Performance**: Pro Pipeline-Run typischerweise 20-50 unique Firmennamen = 20-50 DB-Queries (Session-Cache). Kein relevanter Performance-Impact.
- **Rollback**: `DB_SERVER` aus `.env` entfernen → Feature ist deaktiviert.
