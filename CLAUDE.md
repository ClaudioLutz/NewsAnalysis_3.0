# NewsAnalysis 3.0

AI-powered Swiss news analysis pipeline for credit risk intelligence (Creditreform Switzerland).
Collects articles from 30+ RSS feeds, classifies them via LLM, scrapes content, deduplicates, summarizes in German, and delivers a daily HTML email digest via Outlook.

### Key Features

- **3-level credit impact classification**: negative (specific company affected), neutral (default), positive (specific company benefits)
- **Stakes-first summarization**: Summaries lead with creditworthiness impact, then state what happened (Bloomberg/Reuters style)
- **Non-redundant key points**: 0-4 variable key points per article containing only new facts not in the summary
- **Topic icons**: Each topic category has a BMP Unicode icon (Outlook-safe) in the email header
- **Relevance-based topic ordering**: Email topics sorted by average article relevance score (highest first)
- **Multi-email delivery**: VIP group receives one shared email (all in TO, see each other); remaining recipients each get an individual email (cannot see anyone else)
- **Content fingerprint cache**: SHA-256 based summary cache with 90-day TTL (must be cleared to force re-summarization)

---

## Tech Stack

- **Python** >= 3.11 (target 3.11 in tooling)
- **CLI**: Click
- **Models**: Pydantic v2
- **Database**: SQLAlchemy 2.0 + SQLite (`news.db`)
- **LLM Providers**: DeepSeek (classification), Gemini (summarization/digest), OpenAI (fallback)
- **Scraping**: Trafilatura + Playwright (JS-heavy sites with OneTrust consent)
- **Email**: Outlook COM via pywin32 (Windows only)
- **Logging**: structlog (dual output: colorized console + JSON log files)
- **Templating**: Jinja2

---

## Development Setup

```bash
# Install all dependencies (including dev tools)
pip install -e ".[dev,playwright,email]"

# Install Playwright browsers (needed for JS-heavy sites)
playwright install chromium
```

Environment variables are in `.env` (see `.env.example` for template).

---

## Code Quality

All settings are in `pyproject.toml`.

```bash
# Linting (ruff)
ruff check src/

# Auto-fix lint issues
ruff check src/ --fix

# Formatting (ruff, double quotes, 100 char line length)
ruff format src/

# Type checking (mypy, strict mode)
mypy src/
```

### Conventions

- **Line length**: 100 characters
- **Quotes**: double quotes
- **Indent**: spaces (not tabs)
- **Type hints**: required on all function signatures (`disallow_untyped_defs = true`)
- **Imports**: sorted by isort rules (via ruff `I` rule)

---

## Testing

```bash
# Run all tests with coverage
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run a specific test file
pytest tests/unit/test_models.py
```

- Tests live in `tests/` (unit, integration, e2e)
- Coverage target: 80%+
- Coverage report: `htmlcov/index.html` (generated automatically)
- Markers: `unit`, `integration`, `slow`

---

## Project Structure

```
src/newsanalysis/
  cli/            # Click CLI commands (run, export, stats, cost-report, health, email)
  core/           # Domain models (Article, Config, Digest, Enums)
  database/       # SQLite connection, repositories, migrations
  integrations/   # LLM provider clients (DeepSeek, Gemini, OpenAI)
  pipeline/       # Processing stages: collectors, filters, scrapers, dedup,
                  #   summarizers, generators, extractors, formatters, orchestrator
  services/       # Email, digest formatting, image cache, metrics tracking
  templates/      # Jinja2 email template
  utils/          # Logging, exceptions, date/text utilities
config/           # YAML configs: feeds.yaml, topics.yaml, prompts/
docs/stories/     # Change documentation (see below)
scripts/          # Utility scripts (backup, deploy, image extraction, etc.)
tests/            # pytest test suite
```

---

## Change Documentation (required)

For every change that modifies behavior, adds/removes features, changes dependencies, alters configuration, or impacts performance/security:

* Create **one** new Markdown file under `docs/stories/` in the **same PR/commit** as the code change.

### Filename format

* `docs/stories/YYYYMMddHHmmss-topic-of-the-code-change.md`
* `YYYYMMddHHmmss` is a **14-digit timestamp** (recommend **UTC** to avoid timezone ambiguity).
* `topic-of-the-code-change` is a short **kebab-case** slug (ASCII, no spaces, no underscores).

Examples:

* `docs/stories/20251228143005-fix-dedup-merge-logic.md`
* `docs/stories/20251228160219-add-address-normalization-step.md`

### Required sections

Each story file must include these sections:

#### Summary

1-3 sentences describing the change.

#### Context / Problem

Why this change is needed (bug, requirement, refactor driver).

#### What Changed

Bulleted list of key implementation changes (include modules/components touched).

#### How to Test

Exact commands and/or manual steps to validate.

#### Risk / Rollback Notes

What could go wrong, and how to revert/mitigate.

### Documentation updates (required)

In addition to the story file, **every behavioral change must also update**:

* **`CLAUDE.md`** — if the change affects pipeline behavior, configuration, CLI options, key features, or development workflows
* **`README.md`** — if the change affects user-facing features, setup instructions, environment variables, or architecture
* **`.env.example`** — if new environment variables are added

These updates must be in the **same commit** as the code change. Do not defer documentation to a separate PR.

### When a story is NOT required

* Pure formatting (whitespace), typo fixes in comments/docs, or non-functional refactors that do not change behavior.

  * If in doubt, create a story.

---

## Pipeline Operations

### Running the Pipeline

**Standard daily run** (collects new articles, processes them, sends email):
```bash
python -m newsanalysis.cli.main run
```

### Re-running When No New Articles

When you need to re-process existing articles or regenerate outputs **without collecting new articles**, use these commands:

#### Regenerate Digest Only
Re-creates the digest from existing summarized articles and sends email:
```bash
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

#### Reprocess Today's Articles (SAFE)
Reprocesses only today's articles through filtering, scraping, summarization, and digest:
```bash
python -m newsanalysis.cli.main run --reset all-today --skip-collection
```

#### Re-summarize Today's Articles (SAFE)
Re-summarizes only today's articles:
```bash
python -m newsanalysis.cli.main run --reset summarization-today --skip-collection
```

**Note:** If articles have unchanged content, the content fingerprint cache will return old summaries.
To force re-summarization with a new prompt, clear today's cache first:
```bash
python -c "import sqlite3; c=sqlite3.connect('news.db'); c.execute(\"DELETE FROM content_fingerprints WHERE created_at >= 'YYYY-MM-DD'\"); c.commit()"
```

#### Reprocess ALL Articles (DANGEROUS)
Completely reprocesses ALL articles in the database. Requires confirmation or `-y` flag:
```bash
python -m newsanalysis.cli.main run --reset all --skip-collection
```
**Warning:** This resets ALL articles, not just today's. Will prompt for confirmation.

#### Extract Missing Images
If articles don't have images extracted, run the retroactive image extraction script:
```bash
python scripts/extract_missing_images.py
```
Then regenerate the digest to include the new images:
```bash
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

### Pipeline Command Options

| Option | Description |
|--------|-------------|
| `--skip-collection` | Skip collecting new articles from RSS feeds |
| `--skip-filtering` | Skip AI filtering stage |
| `--skip-scraping` | Skip content scraping stage |
| `--skip-summarization` | Skip article summarization stage |
| `--skip-digest` | Skip digest generation stage |
| `--reset digest` | Re-generate today's digest from existing summaries |
| `--reset summarization-today` | Re-summarize today's articles only (SAFE) |
| `--reset all-today` | Full reprocess today's articles only (SAFE) |
| `--reset summarization` | Re-summarize ALL articles (DANGEROUS - prompts for confirmation) |
| `--reset all` | Full reprocess ALL articles (DANGEROUS - prompts for confirmation) |
| `--yes`, `-y` | Skip confirmation prompts (for automation) |
| `--limit N` | Process only N articles (for testing) |
| `--today-only` | Only include articles collected today in digest (for testing) |

### Typical Workflows

**Daily automated run:**
```bash
python -m newsanalysis.cli.main run
```

**Quick test with limited articles:**
```bash
python -m newsanalysis.cli.main run --limit 5
```

**Fix missing images then send email:**
```bash
python scripts/extract_missing_images.py
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

**Re-send today's email with updated digest:**
```bash
python -m newsanalysis.cli.main run --reset digest --skip-collection
```

**Test with only today's articles (smaller digest for layout testing):**
```bash
python -m newsanalysis.cli.main run --reset digest --skip-collection --today-only
```

**Re-run today's failed pipeline (e.g., after API balance recharged):**
```bash
python -m newsanalysis.cli.main run --reset all-today --skip-collection
```

### Safe Production Re-Run (4-Step Workflow)

When the daily pipeline fails and you need to re-run on production **with manual verification before sending emails**:

```powershell
# Step 1: Process articles (filter, scrape, summarize) — no digest, no email
python -m newsanalysis.cli.main run --reset all-today --skip-collection --skip-digest

# Step 2: Generate digest WITHOUT sending email
$env:EMAIL_AUTO_SEND="false"; python -m newsanalysis.cli.main run --reset digest --skip-collection

# Step 3: Preview in Outlook (opens email without sending)
python -m newsanalysis.cli.main email --preview

# Step 4: If everything looks good, send
python -m newsanalysis.cli.main email
```

**Note:** Production uses PowerShell. Use `$env:VAR="value"` for env vars, not `set` or `export`.

### Other CLI Commands

```bash
# Export articles to JSON/Markdown
python -m newsanalysis.cli.main export

# Show pipeline statistics
python -m newsanalysis.cli.main stats

# Show API cost report
python -m newsanalysis.cli.main cost-report

# Health check
python -m newsanalysis.cli.main health
```
