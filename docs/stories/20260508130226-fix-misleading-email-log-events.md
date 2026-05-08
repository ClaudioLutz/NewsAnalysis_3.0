# Fix Misleading Email Log Events for Preview/Draft Modes

## Summary

In v3.7.0 the orchestrator's email-stage log events were still hardcoded to `email_official_sent` / `email_bcc_sent` regardless of the active `EMAIL_DELIVERY_MODE`. With `draft` (or `preview`) this read as if mails had been sent, when in fact they had been saved to Drafts (or opened in Outlook). The event names now reflect the actual delivery action: `email_official_drafted` / `email_official_displayed` / `email_official_sent` (and the same for the BCC counterpart).

## Context / Problem

After flipping the live config to `EMAIL_DELIVERY_MODE=draft`, a real production run produced log lines like:

```
{"event": "email_official_sent", ...}
{"event": "email_bcc_sent": 6, ...}
```

This made it look like the pipeline had auto-sent the digest, when in reality `mail.Save()` was invoked and the mails ended up in the Outlook Drafts folder (a separate UI-refresh issue made the drafts initially invisible until F9 was pressed). The misleading event names cost real diagnosis time.

## What Changed

- `src/newsanalysis/pipeline/orchestrator.py` — `_run_email_sending()` now derives a verb from `delivery_mode` (`send→sent`, `preview→displayed`, `draft→drafted`) and uses it in:
  - `email_official_{verb}` (success)
  - `email_official_{verb}_failed` (error)
  - `email_bcc_{verb}` (summary)
  - `email_bcc_{verb}_failed` (per-recipient error)
  - All these events now also include a `delivery_mode` field for unambiguous filtering.
- `bcc_sent` counter renamed to `bcc_done` so it does not imply "sent" in non-send modes.
- `pyproject.toml` — version bumped 3.7.0 → 3.7.1 (PATCH: observability fix, no behavior change).

## How to Test

Run the pipeline with each mode and grep the log:

```powershell
$env:EMAIL_DELIVERY_MODE="draft"; python -m newsanalysis.cli.main run --reset digest --skip-collection
```

Then:
```bash
grep -E "email_(official|bcc)_" logs/newsanalysis.log | tail -10
```

Expect events ending in `_drafted` (not `_sent`). Switch to `preview` → expect `_displayed`. Switch to `send` → expect `_sent` (unchanged behavior).

## Risk / Rollback Notes

- **Pure observability change.** No functional difference in what is sent, opened, or saved.
- **Breaking for log consumers** that grep specifically for `email_official_sent` or `email_bcc_sent` literals — those will now match only when running in `send` mode. If any downstream log parser exists (none known in-repo), update its filter.
- **Rollback:** revert the orchestrator hunk; no schema or config changes touched.
