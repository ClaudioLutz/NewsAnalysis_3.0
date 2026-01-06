---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/analysis/brainstorming-session-20260106-email-feature.md
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Outlook Email Automation for NewsAnalysis 3.0'
research_goals: 'Understand pywin32/win32com for Outlook automation, security considerations, HTML email formatting, and Windows Task Scheduler integration'
user_name: 'Claudio'
date: '2026-01-06'
web_research_enabled: true
source_verification: true
---

# Technical Research Report: Outlook Email Automation

**Date:** 2026-01-06
**Author:** Claudio
**Research Type:** Technical

---

## Research Overview

This technical research supports the implementation of an email digest feature for NewsAnalysis 3.0, as defined in the brainstorming session. The research focuses on:

1. **pywin32/win32com Outlook COM automation** - Sending HTML emails programmatically
2. **Outlook security settings** - Avoiding trust prompts and security dialogs
3. **HTML email formatting** - Best practices for corporate email clients
4. **Windows Task Scheduler integration** - Reliable scheduled execution with Python

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Outlook Email Automation for NewsAnalysis 3.0
**Research Goals:** Understand pywin32/win32com for Outlook automation, security considerations, HTML email formatting, and Windows Task Scheduler integration

**Technical Research Scope:**

- Architecture Analysis - COM automation patterns, Outlook object model, Python-Windows integration
- Implementation Approaches - pywin32/win32com code patterns, email composition, HTML body handling
- Technology Stack - pywin32, win32com.client, Outlook COM API, Python scheduling
- Integration Patterns - CLI command integration, error handling, fallback strategies
- Performance Considerations - Outlook availability detection, retry logic, Task Scheduler reliability

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-01-06

---

## Technology Stack Analysis

### Core Library: pywin32 / win32com

**[High Confidence]** The pywin32 package remains the standard approach for Windows COM automation with Python through 2025-2026.

| Component | Details |
|-----------|---------|
| **Package** | `pywin32` (install via `pip install pywin32`) |
| **Module** | `win32com.client` |
| **Purpose** | Access Windows COM (Component Object Model) APIs |
| **Requirement** | Microsoft Outlook must be installed locally |

**Key Capability:** win32com allows Python to control Outlook as if clicking through the UI manually - but faster and without errors. It can send emails, read inbox, process attachments, and manage folders.

**Documentation Note:** The library is notoriously poorly documented, but once configured correctly, it works reliably without the "hit-and-miss randomness" of VBA automation.

_Sources:_
- [Automating Microsoft Outlook and Excel with Python's win32com (Aug 2025)](https://medium.com/@ajeet214/automating-microsoft-outlook-and-excel-with-pythons-win32com-86d830d1fc4a)
- [Practical Business Python - Automating Windows Applications Using COM](https://pbpython.com/windows-com.html)

### Basic Email Sending Pattern

```python
import win32com.client as win32

outlook = win32.Dispatch('outlook.application')
mail = outlook.CreateItem(0)  # 0 = MailItem
mail.To = 'recipient@example.com'
mail.Subject = 'Message subject'
mail.HTMLBody = '<html><body><h1>HTML content</h1></body></html>'
mail.Send()
```

**Best Practices for HTMLBody:**
- Use `mail.HTMLBody` for HTML-formatted emails (not `mail.Body`)
- Use `mail.Display(True)` for preview/testing before sending
- Use `mail.Recipients.Add(recipient)` in a loop for multiple recipients
- Attachments: `mail.Attachments.Add(file_path)`

_Sources:_
- [Send email with Outlook and Python](https://win32com.goermezer.de/microsoft/ms-office/send-email-with-outlook-and-python.html)
- [How to Automate Outlook Emails With Python](https://www.makeuseof.com/send-outlook-emails-using-python/)

### Outlook Security: Programmatic Access Settings

**[High Confidence]** Outlook includes security prompts ("A program is trying to send an email on your behalf") that must be configured for unattended automation.

#### Trust Center Settings
Navigate to: **File → Options → Trust Center → Trust Center Settings → Programmatic Access**

**Note:** Must run Outlook as Administrator to change these settings. Settings may be greyed out due to security restrictions.

#### Registry Configuration (Office 2016/365)

**User-level registry path:**
```
HKEY_CURRENT_USER\Software\Policies\Microsoft\Office\16.0\outlook\security
```

| DWORD Value | Setting |
|-------------|---------|
| `PromptOOMSend` | 2 |
| `AdminSecurityMode` | 3 |
| `promptoomaddressinformationaccess` | 2 |
| `promptoomaddressbookaccess` | 2 |

**Machine-level (if user-level insufficient):**
```
HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\16.0\Outlook\Security
ObjectModelGuard = 2 (DWORD)
```

**For Microsoft 365 Click-to-Run:**
```
HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Office\ClickToRun\REGISTRY\MACHINE\Software\Microsoft\Office\16.0\Outlook\Security
ObjectModelGuard = 2 (DWORD)
```

**Security Warning:** Disabling these prompts removes a security check. Only perform on trusted automation environments, not general-use desktops.

_Sources:_
- [Slipstick Systems - Change Outlook's Programmatic Access Options](https://www.slipstick.com/developer/change-programmatic-access-options/)
- [Microsoft Learn - Program is trying to send email on your behalf](https://learn.microsoft.com/en-us/troubleshoot/outlook/security/a-program-is-trying-to-send-an-email-message-on-your-behalf)
- [Disabling Outlook Programmatic Access Security Prompts](https://mariobienaime.com/permanently-disabling-outlook-programmatic-access-security-prompts/)

### Windows Task Scheduler + Python

**[High Confidence]** Standard approach for scheduling Python scripts on Windows.

#### Basic Setup
1. **Program/script:** Full path to Python executable (e.g., `C:\Python311\python.exe`)
2. **Add arguments:** Full path to script (e.g., `C:\Scripts\newsanalysis_email.py`)
3. **Start in:** Script's directory (for relative path dependencies)

#### Best Practices

| Practice | Recommendation |
|----------|----------------|
| **Use Full Paths** | Always use absolute paths for Python and scripts |
| **Test First** | Run exact command outside Task Scheduler before scheduling |
| **Environment Variables** | Task Scheduler has minimal environment; set explicitly |
| **Logging** | Redirect stdout/stderr: `script.py > logfile.log 2>&1` |
| **Run Without Login** | Enable "Run whether user is logged on or not" |
| **Virtual Environments** | Point directly to venv's python.exe or use wrapper .bat |
| **Least Privilege** | Use dedicated service account, not SYSTEM |

#### Virtual Environment Approach
```batch
@echo off
cd /d C:\Codes\news_analysis_3.0
call .venv\Scripts\activate.bat
python -m newsanalysis email >> logs\email.log 2>&1
```

#### Command-Line Alternative
```cmd
schtasks /Create /SC DAILY /TN "NewsAnalysis Email 0830" /TR "C:\Codes\news_analysis_3.0\.venv\Scripts\python.exe -m newsanalysis email" /ST 08:30
```

_Sources:_
- [DataToFish - Schedule Python Script using Windows Task Scheduler](https://datatofish.com/python-script-windows-scheduler/)
- [GeeksforGeeks - Schedule Python Script using Windows Scheduler](https://www.geeksforgeeks.org/python/schedule-python-script-using-windows-scheduler/)
- [JC Chouinard - How to Automate Python Scripts with Task Scheduler](https://www.jcchouinard.com/python-automation-using-task-scheduler/)

---

## Integration Patterns Analysis

### COM Error Handling Patterns

**[High Confidence]** Proper error handling is critical for robust Outlook automation.

#### Exception Types

| Exception | Module | Use Case |
|-----------|--------|----------|
| `pywintypes.com_error` | pywintypes | COM-specific errors |
| `pywintypes.error` | pywintypes | General Win32 errors |
| `pythoncom.com_error` | pythoncom | Alternative COM error access |

#### Error Handling Pattern

```python
import win32com.client
import pywintypes

def send_email_safe(to, subject, html_body):
    try:
        outlook = win32com.client.Dispatch('Outlook.Application')
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.Subject = subject
        mail.HTMLBody = html_body
        mail.Send()
        return True, "Email sent successfully"
    except pywintypes.com_error as e:
        error_code = e.args[0]
        error_msg = e.args[2]
        return False, f"COM Error {error_code}: {error_msg}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
```

#### Differentiating Errors by Code

Access error details via `e.args[0]` for error code and `e.args[2]` for message. Common patterns:
- Check specific error codes to handle known failure modes
- Log full exception details for debugging
- Provide user-friendly error messages

_Sources:_
- [Tim Golden - com_error Object](https://timgolden.me.uk/pywin32-docs/com_error.html)
- [Python Examples of pywintypes.com_error](https://www.programcreek.com/python/example/13100/pywintypes.com_error)

### Outlook Availability Detection

**[High Confidence]** Different approaches for checking Outlook availability.

#### Dispatch vs GetActiveObject

| Method | Behavior |
|--------|----------|
| `Dispatch('Outlook.Application')` | Connects to running instance OR launches Outlook |
| `GetActiveObject('Outlook.Application')` | Only connects if already running; raises error otherwise |

#### Check-Before-Connect Pattern

```python
import win32com.client

def get_outlook(require_running=False):
    """Get Outlook application instance.

    Args:
        require_running: If True, only connect to running instance.
                        If False, launch Outlook if needed.
    """
    if require_running:
        try:
            return win32com.client.GetActiveObject('Outlook.Application')
        except:
            raise RuntimeError("Outlook is not running")
    else:
        return win32com.client.Dispatch('Outlook.Application')
```

**Important Caveats:**
- Modal dialogs (activation wizards, security prompts) block COM calls
- For unattended automation, ensure Outlook is pre-configured and running
- Consider fallback to SMTP if Outlook unavailable

_Sources:_
- [How to Automate Outlook Emails With Python](https://www.makeuseof.com/send-outlook-emails-using-python/)
- [Automating Microsoft Outlook and Excel with Python's win32com](https://medium.com/@ajeet214/automating-microsoft-outlook-and-excel-with-pythons-win32com-86d830d1fc4a)

### CLI Integration with Typer

**[High Confidence]** Typer is the modern choice for Python CLI applications, built on Click.

#### Why Typer for NewsAnalysis

| Feature | Benefit |
|---------|---------|
| Type hints | Automatic argument parsing and validation |
| Auto-documentation | `--help` generated from docstrings |
| Testing support | `typer.testing.CliRunner` for unit tests |
| Click compatibility | Can integrate with existing Click code |

#### CLI Command Pattern

```python
import typer
from typing import Optional
from typing_extensions import Annotated

app = typer.Typer()

@app.command()
def email(
    preview: Annotated[bool, typer.Option("--preview", "-p",
        help="Preview email without sending")] = False,
    recipient: Annotated[Optional[str], typer.Option("--to",
        help="Override default recipient")] = None,
):
    """Send the news digest email via Outlook."""
    if preview:
        # Display email in Outlook without sending
        send_digest(preview=True, recipient=recipient)
    else:
        send_digest(preview=False, recipient=recipient)
```

#### Subcommand Integration

```python
# In main CLI app
from newsanalysis.commands import email

app = typer.Typer()
app.add_typer(email.app, name="email")

# Usage: newsanalysis email --preview
# Usage: newsanalysis email --to someone@example.com
```

_Sources:_
- [Typer Documentation - Commands](https://typer.tiangolo.com/tutorial/commands/)
- [Building Powerful Command-Line Interfaces with Click and Typer](https://procodebase.com/article/building-powerful-command-line-interfaces-with-click-and-typer-in-python)

### HTML Email Rendering in Outlook

**[Critical]** Outlook uses Microsoft Word as its rendering engine, not a browser.

#### Key Limitations

| Feature | Outlook Support |
|---------|-----------------|
| `<div>` styling | ❌ Ignored (widths, padding) |
| `<table>` layout | ✅ Required for structure |
| External CSS | ❌ Only 21% of clients support |
| Inline CSS | ✅ Required for styling |
| CSS Grid | ❌ Not supported |
| Flexbox | ⚠️ Limited (84% of clients) |
| Hover effects | ❌ Not supported |
| Custom fonts | ⚠️ Limited; use web-safe fonts |

#### Best Practices for Outlook-Compatible HTML

1. **Use table-based layouts** - Outlook ignores `<div>` styling
2. **Inline all CSS** - External stylesheets stripped
3. **Set explicit image dimensions** - Use HTML `width`/`height` attributes
4. **Use web-safe fonts** - Arial, Verdana, Georgia with fallbacks
5. **Use padding over margins** - Margins render inconsistently
6. **Use MSO properties** - Special Microsoft Office CSS properties

#### Recommended HTML Structure

```html
<html>
<head>
  <meta charset="UTF-8">
  <!--[if mso]>
  <style type="text/css">
    table { border-collapse: collapse; }
  </style>
  <![endif]-->
</head>
<body width="100%" style="margin: 0; padding: 0 !important; mso-line-height-rule: exactly;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center" style="padding: 20px;">
        <!-- Content tables here -->
      </td>
    </tr>
  </table>
</body>
</html>
```

#### Conditional Comments for Outlook

```html
<!--[if mso]>
  <p>This content only shows in Outlook</p>
<![endif]-->

<!--[if !mso]><!-->
  <p>This content shows everywhere except Outlook</p>
<!--<![endif]-->
```

_Sources:_
- [Designmodo - HTML and CSS in Emails: What Works in 2026](https://designmodo.com/html-css-emails/)
- [Litmus - Guide to Rendering Differences in Microsoft Outlook](https://www.litmus.com/blog/a-guide-to-rendering-differences-in-microsoft-outlook-clients)
- [Why Inline CSS Is Still Essential for HTML Emails (2025)](https://www.francescatabor.com/articles/2025/12/12/why-inline-css-is-still-essential-for-html-emails)

---

## Architectural Patterns and Design

### Module Architecture for CLI Applications

**[High Confidence]** Modern Python CLI applications follow clean architecture principles with clear separation of concerns.

#### Recommended Structure for Email Feature

```
src/newsanalysis/
├── __init__.py
├── __main__.py              # Entry point: python -m newsanalysis
├── cli.py                   # Main CLI with Typer app
├── commands/
│   ├── __init__.py
│   ├── run.py               # Existing run command
│   └── email.py             # NEW: Email command module
├── services/
│   ├── __init__.py
│   ├── email_service.py     # NEW: Email sending logic
│   └── digest_formatter.py  # NEW: HTML digest generation
├── templates/
│   └── email_digest.html    # NEW: Jinja2 email template
└── config/
    ├── __init__.py
    └── settings.py          # Configuration management
```

#### Key Architectural Principles

| Principle | Application |
|-----------|-------------|
| **Separation of Concerns** | CLI commands, business logic (services), and templates in separate modules |
| **Single Responsibility** | Each module has one clear purpose |
| **Dependency Injection** | Services receive dependencies, enabling testability |
| **Configuration Isolation** | Settings separate from code, environment-aware |

_Sources:_
- [The Cleanest Way to Structure a Python Project in 2025](https://medium.com/the-pythonworld/the-cleanest-way-to-structure-a-python-project-in-2025-4f04ccb8602f)
- [Best Practices for Structuring a Python CLI Application](https://medium.com/@ernestwinata/best-practices-for-structuring-a-python-cli-application-1bc8f8a57369)

### Email Template Architecture with Jinja2

**[High Confidence]** Jinja2 is the standard for Python template rendering, enabling separation of content from presentation.

#### Why Jinja2 for Email Templates

| Benefit | Explanation |
|---------|-------------|
| **Separation of concerns** | HTML template separate from Python code |
| **Template inheritance** | Base layout + content blocks |
| **Logic in templates** | Loops, conditionals for dynamic content |
| **Maintainability** | Non-developers can modify HTML |

#### Template Architecture Pattern

```python
from jinja2 import Environment, PackageLoader, select_autoescape

def create_template_env():
    return Environment(
        loader=PackageLoader('newsanalysis', 'templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )

def render_digest(articles, risk_signals, date):
    env = create_template_env()
    template = env.get_template('email_digest.html')
    return template.render(
        articles=articles,
        risk_signals=risk_signals,
        date=date
    )
```

#### Template with Inheritance

```html
{# templates/email_base.html #}
<html>
<head>
  <meta charset="UTF-8">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
  {% block content %}{% endblock %}
</body>
</html>

{# templates/email_digest.html #}
{% extends "email_base.html" %}
{% block content %}
<table width="100%" cellpadding="0" cellspacing="0">
  {% for article in articles %}
  <tr>
    <td style="padding: 10px;">
      <strong>{{ article.title }}</strong><br>
      {{ article.summary }}
    </td>
  </tr>
  {% endfor %}
</table>
{% endblock %}
```

_Sources:_
- [Using Jinja for HTML Email Templates in Python](https://frankcorso.dev/email-html-templates-jinja-python.html)
- [Email Templates with Jinja in Python - GeeksforGeeks](https://www.geeksforgeeks.org/python/email-templates-with-jinja-in-python/)

### Configuration Management Pattern

**[High Confidence]** Separate configuration from code, supporting multiple environments.

#### Recommended Approach: YAML + Environment Variables

For NewsAnalysis, given its existing YAML-based configuration, extend the pattern:

```yaml
# config/email.yaml
email:
  recipient: "claudio@example.com"
  subject_template: "Bonitäts-News: {date} - {count} relevante Artikel"
  schedule:
    - "08:30"
    - "14:30"
  format: "medium"  # brief, medium, detailed
```

#### Configuration Loading Pattern

```python
from pathlib import Path
import yaml
from dataclasses import dataclass
from typing import List

@dataclass
class EmailConfig:
    recipient: str
    subject_template: str
    schedule: List[str]
    format: str

def load_email_config(config_path: Path) -> EmailConfig:
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return EmailConfig(**data['email'])
```

#### Environment Override Pattern

```python
import os

def get_recipient():
    # Environment variable overrides config file
    return os.environ.get('NEWSANALYSIS_EMAIL_RECIPIENT') or config.recipient
```

_Sources:_
- [Configuring Python Projects with INI, TOML, YAML, and ENV files](https://hackersandslackers.com/simplify-your-python-projects-configuration/)
- [Python YAML configuration with environment variables parsing](https://dev.to/mkaranasou/python-yaml-configuration-with-environment-variables-parsing-2ha6)

### Logging Architecture

**[High Confidence]** Structured logging with rotation for reliable automation.

#### Logging Configuration for Email Feature

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_email_logging(log_dir: Path):
    logger = logging.getLogger('newsanalysis.email')
    logger.setLevel(logging.DEBUG)

    # Rotating file handler - 5MB max, keep 3 backups
    file_handler = RotatingFileHandler(
        log_dir / 'email.log',
        maxBytes=5_000_000,
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler for interactive use
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Structured format for parsing
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

#### Log Events for Email Feature

| Event | Level | Information |
|-------|-------|-------------|
| Email send attempt | INFO | Recipient, article count |
| Email sent success | INFO | Message ID, timestamp |
| Email send failure | ERROR | Error code, message |
| Template render | DEBUG | Template name, context size |
| Outlook connection | DEBUG | Connection method used |

_Sources:_
- [Python Logging Best Practices: Complete Guide 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/)
- [10 Best Practices for Logging in Python](https://betterstack.com/community/guides/logging/python/python-logging-best-practices/)

### Service Layer Pattern

**[High Confidence]** Encapsulate business logic in service classes for testability and reuse.

#### Email Service Architecture

```python
# services/email_service.py
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

@dataclass
class EmailResult:
    success: bool
    message: str
    message_id: Optional[str] = None

class OutlookEmailService:
    """Service for sending emails via Outlook COM automation."""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._outlook = None

    def connect(self) -> bool:
        """Establish connection to Outlook."""
        try:
            import win32com.client
            self._outlook = win32com.client.Dispatch('Outlook.Application')
            self.logger.debug("Connected to Outlook")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Outlook: {e}")
            return False

    def send_html_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        preview: bool = False
    ) -> EmailResult:
        """Send an HTML email via Outlook."""
        if not self._outlook:
            if not self.connect():
                return EmailResult(False, "Could not connect to Outlook")

        try:
            mail = self._outlook.CreateItem(0)
            mail.To = to
            mail.Subject = subject
            mail.HTMLBody = html_body

            if preview:
                mail.Display(True)
                return EmailResult(True, "Email displayed for preview")
            else:
                mail.Send()
                return EmailResult(True, "Email sent successfully")

        except Exception as e:
            return EmailResult(False, str(e))
```

#### Digest Formatter Service

```python
# services/digest_formatter.py
from jinja2 import Environment, PackageLoader
from typing import List, Dict

class DigestFormatter:
    """Formats news articles into email digest HTML."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader('newsanalysis', 'templates'),
            autoescape=True
        )

    def format_digest(
        self,
        articles: List[Dict],
        risk_signals: List[str],
        date: str
    ) -> str:
        """Generate HTML digest from articles."""
        template = self.env.get_template('email_digest.html')
        return template.render(
            articles=articles,
            risk_signals=risk_signals,
            date=date
        )
```

_Sources:_
- [Real Python - Python Application Layouts](https://realpython.com/python-application-layouts/)
- [The Hitchhiker's Guide to Python - Structuring Your Project](https://docs.python-guide.org/writing/structure/)

---

## Implementation Approaches and Technology Adoption

### Dependency Management

**[High Confidence]** pywin32 is a Windows-only dependency that must be handled with platform markers.

#### requirements.txt Entry

```
# Platform-specific: only install on Windows
pywin32>=306;sys_platform == 'win32'
Jinja2>=3.0
```

#### pyproject.toml Entry

```toml
[project]
dependencies = [
    "pywin32>=306; platform_system=='Windows'",
    "Jinja2>=3.0",
]
```

#### Installation Verification

```python
def check_outlook_available():
    """Check if Outlook automation is available on this system."""
    try:
        import win32com.client
        return True
    except ImportError:
        return False
```

_Sources:_
- [pywin32 on PyPI](https://pypi.org/project/pywin32/)
- [How to Install pywin32 on Windows - GeeksforGeeks](https://www.geeksforgeeks.org/installation-guide/how-to-install-pywin32-on-windows/)

### Testing Strategy

**[High Confidence]** Mock COM objects to enable testing without Outlook dependency.

#### Mocking win32com for Tests

```python
# tests/test_email_service.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_outlook():
    """Create a mock Outlook application."""
    with patch('win32com.client.Dispatch') as mock_dispatch:
        mock_app = MagicMock()
        mock_mail = MagicMock()
        mock_app.CreateItem.return_value = mock_mail
        mock_dispatch.return_value = mock_app
        yield {
            'dispatch': mock_dispatch,
            'app': mock_app,
            'mail': mock_mail
        }

def test_send_email_success(mock_outlook):
    """Test successful email sending."""
    from newsanalysis.services.email_service import OutlookEmailService

    service = OutlookEmailService()
    result = service.send_html_email(
        to='test@example.com',
        subject='Test',
        html_body='<p>Test</p>'
    )

    assert result.success
    mock_outlook['mail'].Send.assert_called_once()

def test_send_email_preview_mode(mock_outlook):
    """Test preview mode displays email without sending."""
    from newsanalysis.services.email_service import OutlookEmailService

    service = OutlookEmailService()
    result = service.send_html_email(
        to='test@example.com',
        subject='Test',
        html_body='<p>Test</p>',
        preview=True
    )

    assert result.success
    mock_outlook['mail'].Display.assert_called_once()
    mock_outlook['mail'].Send.assert_not_called()
```

#### Integration Test (Manual)

```python
# tests/integration/test_outlook_integration.py
import pytest
import sys

@pytest.mark.skipif(sys.platform != 'win32', reason="Windows only")
@pytest.mark.manual  # Requires manual verification
def test_outlook_preview_integration():
    """Integration test: Preview email in actual Outlook."""
    from newsanalysis.services.email_service import OutlookEmailService

    service = OutlookEmailService()
    result = service.send_html_email(
        to='test@example.com',
        subject='[TEST] NewsAnalysis Integration Test',
        html_body='<h1>Test Email</h1><p>Verify this displays correctly.</p>',
        preview=True  # Opens in Outlook, doesn't send
    )
    assert result.success
```

_Sources:_
- [pytest-mock Tutorial - DataCamp](https://www.datacamp.com/tutorial/pytest-mock)
- [Common Mocking Problems & How To Avoid Them](https://pytest-with-eric.com/mocking/pytest-common-mocking-problems/)

### Development Workflow

**[High Confidence]** Recommended development approach for the email feature.

#### Development Phases

| Phase | Activities | Validation |
|-------|------------|------------|
| **1. Setup** | Add pywin32 dependency, create module structure | Import test |
| **2. Core Service** | Implement OutlookEmailService class | Unit tests with mocks |
| **3. Template** | Create Jinja2 email template | Template render test |
| **4. CLI Command** | Add `email` command to CLI | CLI integration test |
| **5. Integration** | Connect digest data to email formatter | Preview mode test |
| **6. Scheduling** | Configure Windows Task Scheduler | Manual scheduled test |

#### Git Branch Strategy

```
main
└── feature/email-digest
    ├── feat/email-service       # Core service implementation
    ├── feat/email-template      # Jinja2 template
    └── feat/email-cli           # CLI command integration
```

### Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Outlook not installed | Low | High | Check at runtime, clear error message |
| Security prompt blocks automation | Medium | High | Document registry settings in README |
| Task Scheduler fails silently | Medium | Medium | Implement logging, email-on-failure |
| HTML renders incorrectly | Medium | Low | Use table-based layout, test in Outlook |
| Network/Exchange unavailable | Low | Medium | Retry logic, queue for later |

### Operational Considerations

#### Monitoring

```batch
REM Check if email was sent today
schtasks /Query /TN "NewsAnalysis Email 0830" /FO LIST /V
```

#### Log Review

```powershell
# Check recent email logs
Get-Content C:\Codes\news_analysis_3.0\logs\email.log -Tail 50
```

#### Failure Notification

Consider adding Windows Event Log integration for failures:

```python
def log_to_windows_event(message, event_type='error'):
    """Log critical failures to Windows Event Log."""
    import win32evtlogutil
    import win32evtlog

    win32evtlogutil.ReportEvent(
        'NewsAnalysis',
        1,  # Event ID
        eventType=win32evtlog.EVENTLOG_ERROR_TYPE,
        strings=[message]
    )
```

---

## Technical Research Summary and Recommendations

### Implementation Roadmap

| Step | Component | Priority | Complexity |
|------|-----------|----------|------------|
| 1 | Add pywin32 dependency | High | Low |
| 2 | Create OutlookEmailService class | High | Medium |
| 3 | Create Jinja2 email template | High | Medium |
| 4 | Implement CLI `email` command | High | Low |
| 5 | Add email configuration to config.yaml | Medium | Low |
| 6 | Write unit tests with mocked COM | Medium | Medium |
| 7 | Configure Windows Task Scheduler | Medium | Low |
| 8 | Configure Outlook security (if needed) | Low | Low |

### Technology Stack Recommendations

| Component | Recommendation | Rationale |
|-----------|----------------|-----------|
| **Email Sending** | pywin32 + win32com | Only option for Outlook COM automation |
| **Template Engine** | Jinja2 | Industry standard, already common in Python |
| **CLI Framework** | Typer | Modern, type-hint based, good DX |
| **Configuration** | YAML (existing) | Consistent with project's current approach |
| **Logging** | Python logging + RotatingFileHandler | Standard library, reliable |

### Key Technical Decisions

1. **Outlook COM over SMTP**: Required for corporate email compliance and authentication
2. **Table-based HTML**: Necessary for Outlook rendering compatibility
3. **Jinja2 templates**: Separation of concerns, maintainable HTML
4. **Service layer pattern**: Enables unit testing through mocking
5. **Windows Task Scheduler**: Native, reliable, no additional dependencies

### Success Criteria Alignment

| Brainstorming Criteria | Technical Solution |
|------------------------|-------------------|
| Email arrives at 08:30 and 14:30 | Windows Task Scheduler with batch wrapper |
| Format scannable in ~2 minutes | Jinja2 template with "Medium" format |
| Contains top stories with summaries | DigestFormatter service pulls from existing data |
| Highlights risk signals clearly | Dedicated section in email template |
| Links to original sources work | Full URLs in template, HTML anchor tags |

### Next Steps After Research

1. **Create Tech Spec** - Detailed implementation specification based on this research
2. **Implement MVP** - Basic email sending with hardcoded content
3. **Template Development** - Create the "Medium" format HTML template
4. **CLI Integration** - Add `newsanalysis email` command
5. **Testing** - Unit tests with mocked COM, manual integration test
6. **Scheduling** - Configure Task Scheduler tasks

---

## Research Metadata

- **Total Research Topics**: 4 (Technology Stack, Integration Patterns, Architecture, Implementation)
- **Web Sources Cited**: 25+
- **Confidence Level**: High across all sections
- **Research Date**: 2026-01-06
- **Estimated Implementation Effort**: Small feature (1-2 days for experienced developer)
