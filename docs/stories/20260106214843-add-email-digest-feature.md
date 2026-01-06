# Add Email Digest Feature

## Summary

Implemented an email digest CLI command that sends daily news digests via Microsoft Outlook COM automation. Users can now receive their credit risk news analysis directly in their inbox instead of reading local files.

## Context / Problem

The NewsAnalysis pipeline generates digests as local files, requiring manual access. Claudio needs the digest delivered to his inbox for:
1. Smoother personal consumption workflow
2. Future expansion to leadership distribution
3. Foundation for broader distribution within Creditreform Schweiz

## What Changed

- **src/newsanalysis/core/config.py**: Added `email_recipient` and `email_subject_template` configuration fields
- **src/newsanalysis/services/email_service.py** (NEW): Created `OutlookEmailService` class using pywin32/win32com for Outlook COM automation
- **src/newsanalysis/services/digest_formatter.py** (NEW): Created `HtmlEmailFormatter` service using Jinja2 for HTML email generation
- **src/newsanalysis/templates/email_digest.html** (NEW): Created Outlook-compatible HTML template with table-based layout
- **src/newsanalysis/cli/commands/email.py** (NEW): Created `email` CLI command with `--preview`, `--date`, and `--recipient` options
- **src/newsanalysis/cli/commands/__init__.py**: Registered email command export
- **src/newsanalysis/cli/main.py**: Added email command to CLI
- **tests/unit/test_email_service.py** (NEW): Added 13 unit tests for email service and formatter

## How to Test

1. **Prerequisites:**
   - Windows with Outlook installed
   - pywin32 installed: `pip install ".[email]"`

2. **Verify CLI registration:**
   ```bash
   newsanalysis --help  # Should show 'email' command
   newsanalysis email --help  # Should show options
   ```

3. **Test preview mode (recommended first):**
   ```bash
   newsanalysis email --preview
   ```
   This opens the email in Outlook without sending.

4. **Test actual send:**
   ```bash
   # Set recipient in .env: EMAIL_RECIPIENT=your@email.com
   newsanalysis email
   ```

5. **Run unit tests:**
   ```bash
   pytest tests/unit/test_email_service.py -v
   ```

## Risk / Rollback Notes

**Risks:**
- Outlook security prompts may block unattended automation (registry settings may be needed)
- pywin32 is Windows-only dependency (platform-gated in pyproject.toml)
- Template rendering issues in Outlook's Word-based HTML engine

**Rollback:**
1. Remove `cli.add_command(email)` from main.py
2. Remove email import from commands/__init__.py
3. Delete new files: email.py, email_service.py, digest_formatter.py, email_digest.html, test_email_service.py
4. Remove email config fields from config.py
