---
title: 'Email Digest Feature'
slug: 'email-digest-feature'
created: '2026-01-06'
status: 'completed'
stepsCompleted: [1, 2, 3, 4, 5]
implementation_date: '2026-01-06'
review_date: '2026-01-06'
review_notes:
  findings_total: 10
  findings_fixed: 7
  findings_skipped: 3
  resolution_approach: 'auto-fix'
tech_stack:
  - pywin32 (win32com)
  - Jinja2
  - Click (existing CLI)
files_to_modify:
  - src/newsanalysis/cli/main.py
  - src/newsanalysis/cli/commands/email.py (new)
  - src/newsanalysis/services/email_service.py (new)
  - src/newsanalysis/services/digest_formatter.py (new)
  - src/newsanalysis/templates/email_digest.html (new)
code_patterns:
  - Click command pattern (see run.py)
  - Service layer pattern
  - Jinja2 templating
test_patterns:
  - Mock win32com.client.Dispatch
  - pytest fixtures for COM objects
input_documents:
  - _bmad-output/analysis/brainstorming-session-20260106-email-feature.md
  - docs/planning-artefacts/research/technical-outlook-email-automation-research-20260106.md
---

# Tech-Spec: Email Digest Feature

**Created:** 2026-01-06

## Overview

### Problem Statement

Claudio needs the daily news digest delivered to his inbox rather than reading files on disk. The current NewsAnalysis 3.0 pipeline generates digests as local files, requiring manual access. An email delivery mechanism would enable:
1. Smoother personal consumption workflow (check email instead of files)
2. Future expansion to leadership (CEO presentation path)
3. Foundation for broader distribution within Creditreform Schweiz

### Solution

Add a `newsanalysis email` CLI command that:
1. Retrieves the latest digest from the database
2. Formats it as Outlook-compatible HTML using Jinja2 templates
3. Sends via Outlook COM automation (pywin32)
4. Supports `--preview` flag to open email in Outlook without sending

Scheduled execution via Windows Task Scheduler at 08:30 and 14:30 daily.

### Scope

**In Scope:**
- New CLI command: `newsanalysis email` and `newsanalysis email --preview`
- OutlookEmailService class using pywin32/win32com for Outlook COM automation
- DigestFormatter service using Jinja2 for HTML email generation
- Outlook-compatible HTML template (table-based layout, inline CSS)
- Email configuration (recipient, subject template) via environment variables or config
- Structured logging for email operations
- Unit tests with mocked COM objects

**Out of Scope:**
- Windows Task Scheduler configuration (manual setup, documented in README)
- Multiple recipients distribution (Phase 2)
- Confluence integration (Phase 4)
- SMTP fallback (not needed - Outlook-only environment)
- Email tracking/analytics

## Context for Development

### Codebase Patterns

**CLI Framework:** Click (not Typer)
- Commands in `src/newsanalysis/cli/commands/*.py`
- Registration in `cli/main.py` via `cli.add_command(command_name)`
- Pattern: Load config, setup logging, execute logic, display results

**Configuration:** Pydantic Settings
- Main config in `src/newsanalysis/core/config.py`
- Environment variables from `.env` file
- Email config should follow same pattern

**Digest Data Structure:**
- `DailyDigest` object contains: `articles`, `meta_analysis`, `article_count`, `date`, `version`
- `MetaAnalysis` contains: `key_themes`, `credit_risk_signals`, `regulatory_updates`, `market_insights`
- Articles have: `title`, `summary`, `summary_title`, `topic`, `entities`, `url`

**Logging:** Structured logging via `utils/logging.py`
- Use `get_logger(__name__)` pattern
- JSON format in production

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `cli/commands/run.py` | Command pattern reference (Click decorators, options, error handling) |
| `cli/main.py` | Command registration pattern |
| `pipeline/generators/digest_generator.py` | Digest data structure, how to retrieve digests |
| `database/digest_repository.py` | Database access for digests |
| `pipeline/formatters/markdown_formatter.py` | Formatter service pattern reference |
| `core/config.py` | Configuration pattern (Pydantic Settings) |
| `core/digest.py` | DailyDigest and MetaAnalysis dataclasses |

### Technical Decisions

1. **Click over Typer**: Maintain consistency with existing CLI (all commands use Click)
2. **pywin32 for Outlook**: Only option for COM automation; corporate email compliance requires Outlook
3. **Jinja2 for templates**: Standard library, separation of concerns, maintainable HTML
4. **Table-based HTML**: Required for Outlook's Word rendering engine
5. **Environment variables for config**: Consistent with existing `.env` pattern
6. **Service layer pattern**: Enables unit testing through COM mocking

## Implementation Plan

### Tasks

#### Task 1: Add Dependencies
**File:** `pyproject.toml`
**Changes:**
- Add `pywin32>=306; sys_platform == 'win32'` to dependencies
- Add `Jinja2>=3.1.0` if not present (check first)

#### Task 2: Extend Configuration
**File:** `src/newsanalysis/core/config.py`
**Changes:**
- Add email configuration fields to `Config` class:
  ```python
  # Email Settings
  email_recipient: Optional[str] = Field(default=None)
  email_subject_template: str = "Bonitäts-News: {date} - {count} relevante Artikel"
  ```

#### Task 3: Create Email Service
**File:** `src/newsanalysis/services/email_service.py` (NEW)
**Pattern:** Follow service layer pattern from research
**Class:** `OutlookEmailService`
**Methods:**
- `__init__(self, logger: Logger = None)` - Initialize with optional logger
- `connect(self) -> bool` - Connect to Outlook via `win32com.client.Dispatch('Outlook.Application')`
- `send_html_email(self, to: str, subject: str, html_body: str, preview: bool = False) -> EmailResult`
- Use `pywintypes.com_error` for proper error handling

**Return Type:**
```python
@dataclass
class EmailResult:
    success: bool
    message: str
    message_id: Optional[str] = None
```

#### Task 4: Create Digest Formatter Service
**File:** `src/newsanalysis/services/digest_formatter.py` (NEW)
**Pattern:** Follow `MarkdownFormatter` pattern from `pipeline/formatters/markdown_formatter.py`
**Class:** `HtmlEmailFormatter`
**Methods:**
- `__init__(self)` - Initialize Jinja2 environment with PackageLoader
- `format(self, digest_data: dict) -> str` - Convert digest dict from repository to HTML

**Key insight:** `DigestRepository.get_digest_by_date()` returns dict with:
- `markdown_output`: Pre-formatted markdown (can convert to HTML)
- `meta_analysis_json`: JSON string with key_themes, credit_risk_signals, etc.
- `article_count`, `digest_date`, `version`

#### Task 5: Create Email Template
**File:** `src/newsanalysis/templates/email_digest.html` (NEW)
**Pattern:** Table-based layout for Outlook compatibility (Word rendering engine)
**Structure:**
```html
- Header: "Bonitäts-News" + date
- Meta-Analysis Section:
  - Key Themes (bullet list)
  - Credit Risk Signals (highlighted)
  - Regulatory Updates
  - Market Insights
- Articles Section (from markdown_output, converted to HTML)
- Footer: Generation timestamp, version
```
**Styling:** Inline CSS only, web-safe fonts (Arial), table-based layout

#### Task 6: Create CLI Command
**File:** `src/newsanalysis/cli/commands/email.py` (NEW)
**Pattern:** Follow `run.py` Click command pattern exactly
**Command:** `@click.command()` with name `email`
**Options:**
- `--preview / -p` (flag): Open in Outlook without sending
- `--date` (optional): Specific date, defaults to today
- `--recipient` (optional): Override config recipient

**Flow:**
1. Load config via `Config()`
2. Setup logging via `setup_logging()`
3. Initialize `DatabaseConnection` and `DigestRepository`
4. Call `repo.get_digest_by_date(date)` to get digest dict
5. Format via `HtmlEmailFormatter.format(digest_data)`
6. Send via `OutlookEmailService.send_html_email()`
7. Display success/error via `click.echo()`

#### Task 7: Register CLI Command
**Files:**
- `src/newsanalysis/cli/commands/__init__.py` - Add export
- `src/newsanalysis/cli/main.py` - Add `cli.add_command(email)`

**Pattern:**
```python
# __init__.py
from newsanalysis.cli.commands.email import email
__all__ = [..., "email"]

# main.py
from newsanalysis.cli.commands import ..., email
cli.add_command(email)
```

#### Task 8: Create Unit Tests
**File:** `tests/test_email_service.py` (NEW)
**Pattern:** Mock `win32com.client.Dispatch` with pytest fixtures
**Tests:**
- `test_send_email_success` - Verify `mail.Send()` called
- `test_send_email_preview` - Verify `mail.Display()` called, `Send()` not called
- `test_send_email_com_error` - Verify error handling
- `test_html_formatter_renders_template` - Verify Jinja2 rendering

### Acceptance Criteria

#### AC1: Dependencies Installed
- [ ] `pywin32>=306` installed successfully on Windows
- [ ] `Jinja2>=3.1.0` available in environment
- [ ] `pip install -e .` completes without errors
- [ ] Import test passes: `python -c "import win32com.client; import jinja2"`

#### AC2: Configuration Working
- [ ] `EMAIL_RECIPIENT` environment variable recognized
- [ ] `EMAIL_SUBJECT_TEMPLATE` environment variable recognized
- [ ] Default values work when env vars not set
- [ ] Config validation passes: `newsanalysis health` shows no email config errors

#### AC3: Email Service Functional
- [ ] `OutlookEmailService` connects to Outlook without errors
- [ ] `send_html_email()` with `preview=True` opens email in Outlook
- [ ] `send_html_email()` with `preview=False` sends email successfully
- [ ] COM errors are caught and returned as `EmailResult(success=False, message=...)`
- [ ] Structured logging captures send attempts and outcomes

#### AC4: HTML Formatter Working
- [ ] `HtmlEmailFormatter.format()` accepts digest dict from repository
- [ ] Output is valid HTML with table-based layout
- [ ] Meta-analysis sections (key_themes, credit_risk_signals, etc.) render correctly
- [ ] Article summaries display with clickable source links
- [ ] Inline CSS applied (no external stylesheets)

#### AC5: Email Template Renders Correctly
- [ ] Template loads via Jinja2 `PackageLoader`
- [ ] Date displays in German format (e.g., "6. Januar 2026")
- [ ] Article count shows in header
- [ ] Credit risk signals highlighted visually (bold or colored)
- [ ] Footer shows generation timestamp and version
- [ ] HTML renders correctly in Outlook (manual verification)

#### AC6: CLI Command Works
- [ ] `newsanalysis email --help` displays usage information
- [ ] `newsanalysis email --preview` opens email in Outlook without sending
- [ ] `newsanalysis email` sends email to configured recipient
- [ ] `newsanalysis email --date 2026-01-05` sends digest for specific date
- [ ] `newsanalysis email --recipient other@example.com` overrides recipient
- [ ] Missing digest for date shows clear error message
- [ ] Missing Outlook shows clear error message

#### AC7: CLI Registration Complete
- [ ] `email` command appears in `newsanalysis --help` output
- [ ] Import in `__init__.py` works without circular dependency
- [ ] Command accessible via `python -m newsanalysis email`

#### AC8: Tests Pass
- [ ] Unit tests run without Outlook installed (mocked COM)
- [ ] `test_send_email_success` passes
- [ ] `test_send_email_preview` passes
- [ ] `test_send_email_com_error` passes
- [ ] `test_html_formatter_renders_template` passes
- [ ] `pytest tests/test_email_service.py` exits with code 0

#### AC9: End-to-End Validation (Manual)
- [ ] Run `newsanalysis run` to generate today's digest
- [ ] Run `newsanalysis email --preview` to preview email
- [ ] Verify email displays correctly in Outlook:
  - Header with date and article count
  - Meta-analysis sections visible
  - Articles with summaries and links
  - Links clickable and working
- [ ] Run `newsanalysis email` to send actual email
- [ ] Verify email arrives in inbox within 1 minute

## Additional Context

### Dependencies

**New Dependencies:**
- `pywin32>=306` (Windows-only, platform marker required)
- `Jinja2>=3.0` (may already be installed)

**pyproject.toml addition:**
```toml
"pywin32>=306; sys_platform == 'win32'",
```

### Testing Strategy

1. **Unit Tests (mocked COM):**
   - Mock `win32com.client.Dispatch` to return MagicMock
   - Test email service send/preview logic
   - Test template rendering with sample data

2. **Integration Test (manual):**
   - `newsanalysis email --preview` opens actual email in Outlook
   - Verify HTML renders correctly
   - Verify links work

### Notes

- Research document contains detailed code patterns for COM error handling, HTML email best practices
- Outlook security prompts may need registry configuration for unattended automation
- Task Scheduler setup is documented but out of scope for this spec
