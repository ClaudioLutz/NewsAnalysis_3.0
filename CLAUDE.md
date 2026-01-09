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

#### Reprocess All Articles
Completely reprocesses all articles through filtering, scraping, summarization, and digest:
```bash
python -m newsanalysis.cli.main run --reset all --skip-collection
```
**Note:** This may fail with schema errors on older databases. Use with caution.

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
| `--reset digest` | Re-generate digest from existing summaries |
| `--reset summarization` | Re-summarize all articles |
| `--reset all` | Full reprocess from scratch |
| `--limit N` | Process only N articles (for testing) |

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