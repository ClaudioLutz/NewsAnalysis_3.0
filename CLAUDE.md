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

### Minimum required contents

Each story file must include these sections:

#### Summary

1–3 sentences describing the change.

#### Context / Problem

Why this change is needed (bug, requirement, refactor driver).

#### What Changed

Bulleted list of key implementation changes (include modules/components touched).

#### How to Test

Exact commands and/or manual steps to validate.

#### Risk / Rollback Notes

What could go wrong, and how to revert/mitigate.

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