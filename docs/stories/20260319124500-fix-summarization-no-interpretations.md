# Fix: Summarization prompt — remove model interpretations

## Summary

Fixed contradictory instructions in the summarization prompt that caused the LLM to add its own risk assessments and creditworthiness judgments instead of reporting only facts from the article.

## Context / Problem

The summarization prompt contained a contradiction:
- **CRITICAL RULES** (lines 8-10): "Only include facts explicitly stated in the article. Do NOT make assumptions or interpretations."
- **SUMMARY RULES** (line 16): "Lead with the impact/stakes: what does this mean for creditworthiness?"

The "stakes-first" instruction forced the model to generate interpretive openings like:
- "Keine unmittelbaren Auswirkungen auf die Kreditwürdigkeit" (not stated in article)
- "Erhöhtes Risiko durch steigende Energiepreise" (model's own assessment)
- "Mangelhafte Rückrufaktion birgt Reputationsrisiko für Danone" (interpretation)

## What Changed

- **`config/prompts/summarization.yaml`**:
  - Replaced "Lead with impact/stakes" with "Lead with the most important fact. Only mention creditworthiness if the article explicitly states a concrete impact."
  - Added CRITICAL RULE: "Do NOT start summaries with risk assessments or creditworthiness judgments unless the article explicitly makes that assessment"
  - Updated user_prompt_template summary field to match
  - Updated output_schema description to match
  - Added BAD EXAMPLE 3 and 4 showing interpretation anti-patterns with corrections

## How to Test

1. Wait for the next pipeline run (daily at 07:00)
2. Check summaries for interpretive openings: `python -c "import sqlite3; c=sqlite3.connect('news.db'); [print(r[0][:120]) for r in c.execute(\"SELECT summary FROM articles WHERE date(collected_at) = date('now') AND summary IS NOT NULL\")]"`
3. Summaries should start with facts, not risk assessments

## Risk / Rollback Notes

- **Risk**: Low — only changes prompt text, no code changes
- **Rollback**: `git revert <commit>` to restore previous prompt
- **Note**: Existing summaries are not affected (cached by content fingerprint). Only new articles will use the updated prompt.
