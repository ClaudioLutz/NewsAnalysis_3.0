## Summary

Modified LLM prompts to generate article summaries, key points, and meta-analysis in German (Hochdeutsch) instead of English. Updated digest file naming to prevent overwrites and use German naming convention.

## Context / Problem

1. The digest output was being generated in English, but the target audience (Creditreform Switzerland) requires German language output
2. Digest files were being overwritten on each pipeline run (used only date in filename)
3. File naming was English ("digest_") instead of German

## What Changed

- **config/prompts/summarization.yaml**: Added "Write all output in German (Hochdeutsch)" instruction to the system prompt
- **config/prompts/meta_analysis.yaml**: Added "Write all output in German (Hochdeutsch)" instruction to the system prompt
- **src/newsanalysis/pipeline/orchestrator.py**:
  - Changed file naming from `digest_{date}.md` to `bonitaets_analyse_{date}_{timestamp}.md`
  - Added timestamp from run_id to prevent overwriting previous digests
  - Removed English markdown file output (only German report and JSON now)
- **out/digests/demo_digest.md**: Updated demo file to reflect German output format

## How to Test

1. Run the pipeline: `newsanalysis run`
2. Check that matched/summarized articles have German summaries and key points
3. Verify new files are created in `out/digests/` with naming like `bonitaets_analyse_2026-01-04_20260104_211500.md`
4. Run pipeline again and confirm previous files are not overwritten

## Risk / Rollback Notes

- Low risk - only affects LLM prompt instructions and file naming
- To rollback prompts: Remove the "Write all output in German (Hochdeutsch)" line from both YAML files
- To rollback naming: Revert `_write_digest_outputs` method in orchestrator.py
- Note: Existing cached summaries will remain in their original language until cache expires or is cleared
