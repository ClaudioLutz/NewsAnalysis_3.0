# Add Safe Reset Options to CLI

## Summary

Added safer `--reset` options that only affect today's articles, plus confirmation prompts for dangerous operations that reset all articles in the database.

## Context / Problem

The `--reset all` and `--reset summarization` commands were dangerous because they reset ALL articles in the database without any warning or confirmation. A user intending to reset only today's failed pipeline run could accidentally wipe summaries for thousands of historical articles, requiring expensive re-processing.

## What Changed

### src/newsanalysis/cli/commands/run.py

- Added new safe reset options:
  - `--reset all-today` - Resets only today's articles for full reprocessing
  - `--reset summarization-today` - Re-summarizes only today's articles
- Added confirmation prompts for dangerous operations:
  - `--reset all` now shows article count and requires confirmation
  - `--reset summarization` now shows article count and requires confirmation
- Added `--yes` / `-y` flag to skip confirmation (for automation)
- Updated help text and examples to recommend safe options

### CLAUDE.md

- Updated documentation to reflect new options
- Added typical workflow for re-running failed daily pipeline

## How to Test

1. Test safe reset (should work without confirmation):
   ```bash
   python -m newsanalysis.cli.main run --reset all-today --skip-collection --skip-filtering --skip-scraping --skip-summarization --skip-digest
   ```

2. Test dangerous reset (should prompt for confirmation):
   ```bash
   python -m newsanalysis.cli.main run --reset all --skip-collection --skip-filtering --skip-scraping --skip-summarization --skip-digest
   ```
   Press `n` to abort and verify it doesn't reset articles.

3. Test bypass with -y flag:
   ```bash
   python -m newsanalysis.cli.main run --reset summarization -y --skip-collection --skip-filtering --skip-scraping --skip-summarization --skip-digest
   ```

## Risk / Rollback Notes

- **Risk**: None - this change only adds safety guards
- **Rollback**: Revert the changes to run.py and CLAUDE.md
- The new options are additive; existing automation using `--reset all` will now prompt for confirmation (may break CI if not updated to use `-y`)
