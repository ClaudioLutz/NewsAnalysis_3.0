# Email Delivery Mode Options (send | preview | draft)

## Summary

Adds a configurable email delivery mode so the daily pipeline can either auto-send emails (existing behavior), open them in Outlook for manual review/send, or save them as Outlook drafts. Configurable via `EMAIL_DELIVERY_MODE` in `.env` and overridable per CLI invocation.

## Context / Problem

The pipeline previously had a hardcoded `preview=False` in the orchestrator's email stage, so once `EMAIL_AUTO_SEND=true` was set, emails were always sent immediately. There was no way to make the daily run prepare emails for manual review without disabling auto-send entirely and re-running the `email` CLI command. Users wanted a single config knob so the same scheduled run can be flipped between immediate-send, open-and-let-me-click-Send, and save-to-drafts.

The `email` CLI command exposed a single `--preview` flag, with no draft option.

## What Changed

- `src/newsanalysis/services/email_service.py`
  - Replaced `preview: bool = False` parameter with `delivery_mode: Literal["send","preview","draft"] = "send"` on both `send_html_email()` and `send_html_email_with_images()`.
  - Added `"draft"` branch that calls `mail.Save()` (saves to Outlook Drafts folder, no window opens).
  - Exported a `DeliveryMode` type alias.
- `src/newsanalysis/core/config.py`
  - Added `email_delivery_mode: Literal["send","preview","draft"] = "send"` (env var `EMAIL_DELIVERY_MODE`).
- `src/newsanalysis/pipeline/orchestrator.py`
  - `_run_email_sending()` now reads `self.config.email_delivery_mode` once and passes it to both VIP and individual `send_html_email_with_images` calls. Removed hardcoded `preview=False`.
- `src/newsanalysis/cli/commands/email.py`
  - Added `--mode send|preview|draft` option, `--draft` shortcut flag, kept `--preview` shortcut. The three are mutually exclusive (Click aborts with an error if combined). When none are passed, the command falls back to `config.email_delivery_mode`.
  - Updated CLI status messages (`Mode:`, action verbs) to reflect the chosen mode.
- `tests/unit/test_email_service.py`
  - Updated existing `preview=...` calls to `delivery_mode=...`. Added `test_send_email_draft_mode` verifying `mail.Save()` is called and `Send`/`Display` are not.
- `tests/unit/test_email_with_images.py`
  - Updated `preview=True` calls to `delivery_mode="preview"`. Added `test_send_html_email_with_images_draft_mode`.
- `.env.example` — added `EMAIL_DELIVERY_MODE=send` with documenting comment.
- `README.md` — added "Email delivery modes" section with mode table; documented CLI override flags.
- `CLAUDE.md` — added the feature to the key-features list and a "Manual-send mode for the daily run" subsection under the production workflow.
- `pyproject.toml` — bumped version `3.6.0` → `3.7.0` (MINOR: new feature, no breaking change since default is `send`).

## How to Test

Unit tests:
```bash
pytest tests/unit/test_email_service.py tests/unit/test_email_with_images.py
```

Lint/format:
```bash
ruff check src/
ruff format --check src/
```

Manual smoke test (requires Windows + Outlook):
```powershell
# Default (send) — should send normally
$env:EMAIL_DELIVERY_MODE="send"; python -m newsanalysis.cli.main email --date 2026-05-08

# Preview — should open VIP email + one window per BCC recipient
$env:EMAIL_DELIVERY_MODE="preview"; python -m newsanalysis.cli.main email --date 2026-05-08
# OR shortcut:
python -m newsanalysis.cli.main email --preview --date 2026-05-08

# Draft — no window, check Outlook Drafts folder
$env:EMAIL_DELIVERY_MODE="draft"; python -m newsanalysis.cli.main email --date 2026-05-08
# OR shortcut:
python -m newsanalysis.cli.main email --draft --date 2026-05-08

# CLI mutual exclusion guard — should abort
python -m newsanalysis.cli.main email --preview --draft
```

End-to-end pipeline run with manual-send mode:
```powershell
$env:EMAIL_AUTO_SEND="true"; $env:EMAIL_DELIVERY_MODE="preview"; python -m newsanalysis.cli.main run
```
Expect: VIP email window opens, then one window per individual recipient.

## Risk / Rollback Notes

- **Default unchanged:** `EMAIL_DELIVERY_MODE` defaults to `"send"`, so existing production behavior is preserved without any config change.
- **Signature change:** `OutlookEmailService.send_html_email[*]` no longer accepts `preview`. Any external caller that passed `preview=True/False` as a keyword would break — only internal callers (orchestrator, CLI, tests) use these, and all were updated in this commit.
- **Many BCC recipients in `preview` mode:** opens N+1 Outlook windows. If that's unwieldy, switch to `draft` mode and approve from the Drafts folder.
- **Rollback:** revert this commit. No DB migrations, no schema changes, no breaking config (the env var is optional and ignored on older versions).
