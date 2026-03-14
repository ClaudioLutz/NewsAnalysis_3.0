# Split Email Sending: Separate Official and BCC Emails

## Summary

Changed email sending to dispatch two separate emails instead of one: the first email goes to the official TO recipients (without BCC), and the second email goes to the sender's own address with BCC recipients in the BCC field. This ensures BCC recipients cannot see each other and are fully isolated from the official recipient list.

## Context / Problem

Previously, a single email was sent with both TO and BCC recipients. The requirement is to send two distinct emails: one for the official distribution list and one for the BCC distribution list. This provides cleaner separation and allows different handling of each group.

## What Changed

- **`src/newsanalysis/core/config.py`**: Added `EMAIL_SENDER` config field — used as the TO address for the BCC-only email.
- **`src/newsanalysis/pipeline/orchestrator.py`**: `_run_email_sending()` now sends two emails:
  1. Email 1: TO = official recipients, no BCC
  2. Email 2: TO = EMAIL_SENDER, BCC = EMAIL_BCC (only if both are configured)
- **`src/newsanalysis/cli/commands/email.py`**: Same two-email logic for the standalone `email` CLI command. BCC email is skipped when `--recipient` override is used.
- **`.env.example`**: Added `EMAIL_BCC` and `EMAIL_SENDER` example entries.

## How to Test

1. Set `EMAIL_SENDER=your@email.com` and `EMAIL_BCC=bcc1@example.com,bcc2@example.com` in `.env`
2. Run `python -m newsanalysis.cli.main email --preview` — two Outlook windows should open
3. Verify Email 1 has TO = EMAIL_RECIPIENTS, no BCC
4. Verify Email 2 has TO = EMAIL_SENDER, BCC = EMAIL_BCC list
5. Test without `EMAIL_SENDER` set — should log warning and skip BCC email
6. Test with `--recipient override@example.com` — should only send one email

## Risk / Rollback Notes

- **Low risk**: If `EMAIL_SENDER` is not configured, BCC email is simply skipped with a warning — existing behavior for the official email is unchanged.
- **Rollback**: Remove `EMAIL_SENDER` from `.env` to revert to single-email behavior.
