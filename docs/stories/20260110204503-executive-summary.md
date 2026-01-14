# Story 1.2: Executive Summary - "Heute in 30 Sekunden"

Status: review

## Story

As an **executive reader**,
I want **a 3-sentence summary at the top naming specific companies and impacts**,
so that **I can decide in 5 seconds whether to read further**.

## Acceptance Criteria

1. **Given** a daily digest with summarized articles **When** the digest is generated **Then** a "Heute in 30 Sekunden" section appears at the top of the email

2. **Given** the meta-analysis is generated **When** executive_summary is requested **Then** it contains exactly 3 concrete sentences

3. **Given** each sentence in the executive summary **When** it is generated **Then** it names a specific company AND states a specific impact

4. **Given** the 3 sentences **When** displayed in the email **Then** each is numbered (1. 2. 3.) and actionable (not generic category descriptions)

5. **Given** the MetaAnalysis model **When** executive_summary is empty or unavailable **Then** the section is hidden gracefully (backwards compatibility)

## Tasks / Subtasks

- [x] Task 1: Update MetaAnalysis Pydantic model (AC: #2, #5)
  - [x] 1.1: Add `executive_summary: List[str]` field to MetaAnalysis class
  - [x] 1.2: Set default_factory=list for backwards compatibility
  - [x] 1.3: Add field constraints (max_length=3)

- [x] Task 2: Update meta_analysis.yaml prompt (AC: #2, #3, #4)
  - [x] 2.1: Add executive_summary to system_prompt instructions
  - [x] 2.2: Add CRITICAL formatting rules for company + impact pattern
  - [x] 2.3: Update user_prompt_template with executive_summary request
  - [x] 2.4: Add executive_summary to output_schema (array of 3 strings)

- [x] Task 3: Update email template (AC: #1, #4, #5)
  - [x] 3.1: Add "Heute in 30 Sekunden" section after header
  - [x] 3.2: Implement numbered list display (1. 2. 3.)
  - [x] 3.3: Style section with light blue background (#f0f5fa)
  - [x] 3.4: Add conditional check for empty executive_summary

- [x] Task 4: Update digest formatter (AC: #1)
  - [x] 4.1: Parse executive_summary from meta_analysis JSON
  - [x] 4.2: Pass executive_summary to template render

- [x] Task 5: Test executive summary generation (AC: #1, #2, #3, #4)
  - [x] 5.1: Run full pipeline to test LLM prompt
  - [x] 5.2: Verify 3 sentences with company names
  - [x] 5.3: Preview in Outlook for visual verification

## Dev Notes

### Architecture Compliance

- **Model Location:** `src/newsanalysis/core/digest.py` - MetaAnalysis class
- **Prompt Location:** `config/prompts/meta_analysis.yaml` - LLM prompt
- **Template Location:** `src/newsanalysis/templates/email_digest.html` - Display
- **Formatter Location:** `src/newsanalysis/services/digest_formatter.py` - Data passing
- **Provider:** Google Gemini (Stage 5 - DigestGenerator)

### Technical Requirements

**Executive Summary Format:**
```
Heute in 30 Sekunden:
1. Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen
2. FINMA verschärft Eigenmittelregeln für Retailbanken
3. Nestlé-Rückruf: Reputationsschaden, aber Finanzen stabil
```

**Sentence Pattern:** `[Company] [action/event] - [consequence for credit risk]`

**Critical Constraints:**
- Each sentence MUST name a specific company
- Each sentence MUST state a specific impact or action
- Do NOT use generic category descriptions
- Exactly 3 sentences (not 2, not 4)

### Current State

**MetaAnalysis model (digest.py):**
```python
class MetaAnalysis(BaseModel):
    key_themes: List[str] = Field(..., min_length=1, max_length=5)
    credit_risk_signals: List[str] = Field(default_factory=list, max_length=5)
    regulatory_updates: List[str] = Field(default_factory=list, max_length=5)
    market_insights: List[str] = Field(default_factory=list, max_length=5)
    # Missing: executive_summary
```

**Current meta_analysis.yaml key_themes output:**
- Generic themes like "Insolvenzen im Bausektor"
- No specific company names
- No actionable insights

### Target Implementation

**digest.py - Updated Model:**
```python
class MetaAnalysis(BaseModel):
    """Meta-analysis of daily articles."""

    key_themes: List[str] = Field(..., min_length=1, max_length=5)
    credit_risk_signals: List[str] = Field(default_factory=list, max_length=5)
    regulatory_updates: List[str] = Field(default_factory=list, max_length=5)
    market_insights: List[str] = Field(default_factory=list, max_length=5)

    # NEW: Executive summary for "Heute in 30 Sekunden"
    executive_summary: List[str] = Field(
        default_factory=list,
        max_length=3,
        description="3 specific sentences naming companies and impacts"
    )
```

**meta_analysis.yaml - Updated Prompt (Critical Section):**
```yaml
system_prompt: |
  CRITICAL for executive_summary:
  - Each sentence MUST name a specific company
  - Each sentence MUST state a specific impact or action
  - Format: "[Company] [action/event] - [consequence for credit risk]"
  - Examples:
    - "Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen"
    - "FINMA verschärft Eigenmittelregeln für Retailbanken"
  - Do NOT use generic category descriptions

output_schema:
  properties:
    executive_summary:
      type: array
      items:
        type: string
      minItems: 3
      maxItems: 3
      description: "3 specific sentences naming companies and impacts for executives"
```

**email_digest.html - New Section:**
```jinja2
{% if executive_summary %}
<!-- Executive Summary: Heute in 30 Sekunden -->
<tr>
  <td style="padding: 20px 30px; background-color: #f0f5fa; border-bottom: 2px solid #003366;">
    <h2 style="margin: 0 0 12px 0; color: #003366; font-size: 16px; font-weight: bold;">
      Heute in 30 Sekunden
    </h2>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      {% for sentence in executive_summary %}
      <tr>
        <td style="padding: 4px 0; color: #333333; font-size: 14px; line-height: 1.5;">
          <strong>{{ loop.index }}.</strong> {{ sentence }}
        </td>
      </tr>
      {% endfor %}
    </table>
  </td>
</tr>
{% endif %}
```

**digest_formatter.py - Updated render call:**
```python
# Parse executive summary (new field)
executive_summary = meta_analysis.get("executive_summary", [])

# Pass to template
html = template.render(
    ...
    executive_summary=executive_summary,
    ...
)
```

### File Structure Notes

| File | Purpose | Changes Required |
|------|---------|------------------|
| `src/newsanalysis/core/digest.py` | Pydantic model | Add executive_summary field |
| `config/prompts/meta_analysis.yaml` | LLM prompt | Add executive_summary instructions + schema |
| `src/newsanalysis/templates/email_digest.html` | Email template | Add "Heute in 30 Sekunden" section |
| `src/newsanalysis/services/digest_formatter.py` | Formatter | Parse and pass executive_summary |

### Project Structure Notes

- Follows existing meta-analysis pattern (key_themes, credit_risk_signals, etc.)
- Backwards compatible - default_factory=list handles missing field in old digests
- Prompt changes affect DigestGenerator (Stage 5) LLM call
- No database schema changes required (JSON stored in meta_analysis_json column)

### References

- [Source: docs/planning-artefacts/epics.md#Story 1.2] - User story and acceptance criteria
- [Source: docs/implementation-artefacts/tech-spec-phase1-visual-transformation.md#Story 1.2] - Detailed implementation spec
- [Source: src/newsanalysis/core/digest.py:11-18] - Current MetaAnalysis model
- [Source: config/prompts/meta_analysis.yaml] - Current LLM prompt
- [Source: src/newsanalysis/services/digest_formatter.py:37-86] - format() method
- [Source: src/newsanalysis/templates/email_digest.html:39-57] - Current key_themes section
- [Source: docs/project-documentation/architecture.md#Stage 5] - DigestGenerator uses Gemini

### Edge Cases to Handle

1. **Failed LLM call** - executive_summary defaults to empty list, section hidden
2. **LLM returns <3 sentences** - Display whatever was returned
3. **LLM returns generic sentences** - Prompt hardening should prevent this
4. **Old digests without executive_summary** - Graceful fallback (hidden section)
5. **No articles in digest** - LLM may struggle; prompt should handle this

### Testing Commands

```bash
# Full pipeline run to test new prompt
python -m newsanalysis.cli.main run --limit 10

# Or regenerate meta-analysis only (if articles already summarized)
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Preview to verify display
python -m newsanalysis.cli.main email --preview
```

### Quality Validation

After implementation, verify each sentence:
- [ ] Names a specific company (not "some companies" or "the market")
- [ ] States specific impact (not "may be affected")
- [ ] Is actionable for credit analyst
- [ ] Written in German (Hochdeutsch)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

- Added `executive_summary: List[str]` field to MetaAnalysis Pydantic model with default_factory=list for backwards compatibility
- Updated meta_analysis.yaml prompt with CRITICAL formatting rules for company + impact pattern
- Added executive_summary to output_schema (minItems: 3, maxItems: 3)
- Added "Heute in 30 Sekunden" section to email template with light blue background (#f0f5fa)
- Added executive_summary to JSON, Markdown, and German formatters
- Updated digest_formatter.py to pass executive_summary to template
- Tested successfully: LLM generates 3 specific sentences with company names and impacts
- Example output: "Nestlé ruft Babynahrung wegen Kontamination zurück - Reputationsschaden..."

### File List

- `src/newsanalysis/core/digest.py` - Added executive_summary field to MetaAnalysis
- `config/prompts/meta_analysis.yaml` - Updated prompt with executive_summary rules
- `src/newsanalysis/templates/email_digest.html` - Added "Heute in 30 Sekunden" section
- `src/newsanalysis/services/digest_formatter.py` - Pass executive_summary to templates
- `src/newsanalysis/pipeline/formatters/json_formatter.py` - Include executive_summary in JSON
- `src/newsanalysis/pipeline/formatters/markdown_formatter.py` - Include executive_summary in MD
- `config/templates/german_report.md.j2` - Include executive_summary in German report

### Change Log

- 2026-01-14: Implemented Story 1.2 - Executive Summary "Heute in 30 Sekunden" (all ACs satisfied)
