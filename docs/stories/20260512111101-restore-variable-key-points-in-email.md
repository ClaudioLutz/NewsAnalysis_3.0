# Restore variable 0–4 key points in email digest

## Summary

The HTML email formatter capped article bullet points at 1 (for `neutral` credit
impact) or 2 (for `negative`/`positive`), overriding the LLM's complexity-based
0–4 output. The cap is removed so the email reflects what the summarization
prompt produces. Version bumped to **3.8.1**.

## Context / Problem

`CLAUDE.md` and `README.md` document the feature as
*"0–4 variable key points per article containing only new facts not in the summary"*,
and the summarization prompt (`config/prompts/summarization.yaml`) instructs the
LLM to emit 0–4 key points scaled to article complexity (`minItems: 0`,
`maxItems: 4`).

The formatter, however, still contained an older slice from commit `0376f10`
("feat: add 3-level credit impact classification…", 14.03.2026):

```python
# Neutral articles show 1 key point, others show 2
max_key_points = 1 if credit_impact == "neutral" else 2
"key_points": article.get("key_points", [])[:max_key_points],
```

When the prompt was rewritten later that day in commit `5a42940`
("feat: improve summarization prompt — stakes-first, non-redundant, variable
key points") to the 0–4 / complexity-based model, the formatter was not
updated. As a result, complex regulatory or multi-impact articles routinely
lost 1–3 of their bullet points before reaching the recipient.

Confirmed visually by the user: today's digest shows exactly one bullet per
article across topics, regardless of complexity.

Decision (with user, 12.05.2026): drive the bullet count purely from article
complexity (the prompt's existing axis), not from `credit_impact`. Every
article that reaches the digest is by definition Creditreform-relevant, so
forcing neutral articles to be more compact discards substance.

## What Changed

- `src/newsanalysis/services/digest_formatter.py`
  - Removed the `max_key_points` computation in `_parse_article_dict`.
  - Replaced `article.get("key_points", [])[:max_key_points]` with
    `article.get("key_points", [])`, so all 0–4 LLM-produced bullets reach
    the template unchanged.
- `pyproject.toml`: version `3.8.0` → `3.8.1`.

No prompt change, no schema change, no template change. The Jinja template
already iterates over `article.key_points` without any limit.

## How to Test

Verification happens with the next scheduled daily run — no test email is sent
today (today's digest has already gone out).

On the next run, in the delivered email check:

- Articles whose LLM output contained ≥2 `key_points` now show all of them
  (up to 4) — previously only 1–2 were rendered.
- Articles whose LLM output is `[]` show no bullets at all (expected).
- Mix of `credit_impact` values: bullet count no longer correlates with
  `negative`/`neutral`/`positive` — it correlates with article complexity
  as judged by the LLM.
- Spot-check a complex regulatory article (e.g. FINMA-Konsultation,
  Eigenkapital-Debatte) — expect 2–4 bullets if the LLM emitted them.

If a dry verification before the next run is desired later, the safest path is
without sending:

```powershell
$env:EMAIL_DELIVERY_MODE="draft"; python -m newsanalysis.cli.main run --reset digest --skip-collection --today-only
```

This places the digest in the Outlook Drafts folder for inspection.

## Risk / Rollback Notes

- **Low risk.** No data model, schema, prompt, cache, or template change.
  The LLM was already producing the larger lists; only the display was
  clipping them. Cached summaries from before 14.03.2026 may have ≤3
  `key_points` per the older prompt — those simply display whatever was
  stored, which is the desired behavior.
- **Visual impact:** emails will sometimes be longer per article (more
  bullets). If the recipient feedback signals "too verbose", revisit by
  tightening the prompt's complexity thresholds rather than re-introducing
  a hard slice in the formatter.
- **Rollback:** revert this commit. The previous behavior (`neutral` → 1,
  others → 2) is restored as-is. No migration or cache invalidation needed.
