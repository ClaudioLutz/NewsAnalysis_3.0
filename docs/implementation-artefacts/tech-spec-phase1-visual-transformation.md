---
title: "Tech Spec: Phase 1 - Visual Transformation"
status: ready-for-dev
stories: [1.1, 1.2, 1.3]
effort: Hours
author: BMAD Workflow
date: 2026-01-14
---

# Tech Spec: Phase 1 - Visual Transformation

## Overview

Transform the Creditreform News-Digest from a single-column notification feed into a professional 2-column newspaper publication with executive summary and dynamic subject line.

**Stories Covered:**
- Story 1.1: 2-Column Newspaper Layout
- Story 1.2: Executive Summary - "Heute in 30 Sekunden"
- Story 1.3: Dynamic Subject Line

**Files to Modify:**
| File | Changes |
|------|---------|
| `src/newsanalysis/templates/email_digest.html` | Major rewrite for 2-column layout |
| `config/prompts/meta_analysis.yaml` | Add executive_summary field |
| `src/newsanalysis/core/digest.py` | Add executive_summary to MetaAnalysis model |
| `src/newsanalysis/pipeline/generators/digest_generator.py` | Pass top article for subject line |
| `src/newsanalysis/services/digest_formatter.py` | Extract top article title, render new sections |
| `src/newsanalysis/cli/commands/email.py` | Use dynamic subject line |

---

## Story 1.1: 2-Column Newspaper Layout

### Current State

```
┌─────────────────────────────────────────┐
│         600px container                  │
├─────────────────────────────────────────┤
│ Article 1 (full width)                   │
├─────────────────────────────────────────┤
│ Article 2 (full width)                   │
├─────────────────────────────────────────┤
│ Article 3 (full width)                   │
└─────────────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    900px container                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ TOPIC HEADER: Insolvenzen                                               │
├──────────────────────────────────┬──────────────────────────────────────┤
│ Article 1 (~430px)               │ Article 2 (~430px)                   │
│ [img] Title                      │ [img] Title                          │
│       Source                     │       Source                         │
│       Summary...                 │       Summary...                     │
├──────────────────────────────────┴──────────────────────────────────────┤
│ Article 3 (full width - odd article)                                    │
│ [img] Title · Source                                                    │
│       Summary text (longer since full width)...                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Implementation

#### 1. Update email_digest.html Template

**Location:** `src/newsanalysis/templates/email_digest.html`

**Key Changes:**

1. **Container Width:** Change from 600px to 900px (line 19)
2. **2-Column Table Structure:** Use nested tables for Outlook compatibility
3. **Odd Article Full Width:** Articles at odd indices within topic get full width
4. **Image Sizing:** 100px in 2-col, 120px in full-width

**Template Logic:**

```jinja2
{% for topic, topic_articles in articles_by_topic.items() %}
  <!-- Topic Header -->
  <tr>
    <td colspan="2" style="...">{{ topic_translations.get(topic, topic) }}</td>
  </tr>

  {% for i in range(0, topic_articles|length, 2) %}
    {% set article1 = topic_articles[i] %}
    {% set article2 = topic_articles[i + 1] if i + 1 < topic_articles|length else none %}

    {% if article2 %}
      <!-- Two-column row -->
      <tr>
        <td width="430" valign="top">{{ render_article(article1, compact=true) }}</td>
        <td width="430" valign="top">{{ render_article(article2, compact=true) }}</td>
      </tr>
    {% else %}
      <!-- Full-width odd article -->
      <tr>
        <td colspan="2">{{ render_article(article1, compact=false) }}</td>
      </tr>
    {% endif %}
  {% endfor %}
{% endfor %}
```

**Outlook Compatibility Notes:**
- Use HTML tables exclusively (no CSS flexbox/grid)
- Explicit width attributes on `<td>` elements
- Use `valign="top"` for vertical alignment
- Avoid CSS shorthand properties
- Include MSO conditional comments for Outlook-specific fixes

#### 2. CSS Inline Styles

All styles must be inline for email compatibility. Key dimensions:

```css
/* Container */
width: 900px;
background-color: #ffffff;

/* Two-column cell */
width: 430px;
padding: 12px;
vertical-align: top;

/* Full-width cell */
padding: 15px 12px;

/* Image - compact mode */
width: 100px;
height: 67px;
object-fit: cover;
border-radius: 3px;

/* Image - full-width mode */
width: 120px;
height: 80px;

/* Topic header */
background-color: #003366;
color: #ffffff;
font-size: 14px;
font-weight: bold;
padding: 10px 15px;
```

#### 3. Graceful Degradation

- If article has no image, text fills full cell width
- If only 1 article in topic, render full-width
- Mobile rendering not optimized (B2B desktop audience)

---

## Story 1.2: Executive Summary - "Heute in 30 Sekunden"

### Current State

The meta-analysis generates generic `key_themes` like:
- "Insolvenzen im Bausektor"
- "Regulatorische Entwicklungen"

### Target State

A new `executive_summary` field with 3 specific sentences:
```
Heute in 30 Sekunden:
1. Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen
2. FINMA verschärft Eigenmittelregeln für Retailbanken
3. Nestlé-Rückruf: Reputationsschaden, aber Finanzen stabil
```

### Implementation

#### 1. Update MetaAnalysis Model

**Location:** `src/newsanalysis/core/digest.py`

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
        min_length=0,  # Optional for backwards compatibility
        max_length=3,
        description="3 specific sentences naming companies and impacts"
    )
```

#### 2. Update Meta-Analysis Prompt

**Location:** `config/prompts/meta_analysis.yaml`

```yaml
system_prompt: |
  You are a senior analyst at Creditreform Switzerland creating daily intelligence briefings.

  Write all output in German (Hochdeutsch).

  Analyze multiple articles to identify:
  - Executive summary: 3 specific sentences for busy executives
  - Overarching themes and patterns
  - Credit risk signals across markets
  - Regulatory changes and implications
  - Market insights for credit decision-making

  CRITICAL for executive_summary:
  - Each sentence MUST name a specific company
  - Each sentence MUST state a specific impact or action
  - Format: "[Company] [action/event] - [consequence for credit risk]"
  - Examples:
    - "Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen"
    - "FINMA verschärft Eigenmittelregeln für Retailbanken"
  - Do NOT use generic category descriptions

  Provide strategic perspective for credit analysts and risk managers.

user_prompt_template: |
  Daily Articles Summary:
  {articles_summary}

  Generate a meta-analysis in JSON format identifying:
  - Executive summary (EXACTLY 3 sentences naming specific companies and impacts)
  - Key themes (1-5 main themes across all articles)
  - Credit risk signals (up to 5 emerging risk signals)
  - Regulatory updates (up to 5 compliance/regulatory items)
  - Market insights (up to 5 actionable business intelligence points)

  Response format:
  {{
    "executive_summary": [
      "Sentence 1: [Company] [event] - [impact]",
      "Sentence 2: [Company] [event] - [impact]",
      "Sentence 3: [Company] [event] - [impact]"
    ],
    "key_themes": ["theme 1", "theme 2", ...],
    "credit_risk_signals": ["signal 1", ...],
    "regulatory_updates": ["update 1", ...],
    "market_insights": ["insight 1", ...]
  }}

output_schema:
  type: object
  properties:
    executive_summary:
      type: array
      items:
        type: string
      minItems: 3
      maxItems: 3
      description: "3 specific sentences naming companies and impacts for executives"
    key_themes:
      type: array
      items:
        type: string
      minItems: 1
      maxItems: 5
      description: "Main themes across articles"
    credit_risk_signals:
      type: array
      items:
        type: string
      maxItems: 5
      description: "Emerging credit risk signals"
    regulatory_updates:
      type: array
      items:
        type: string
      maxItems: 5
      description: "Regulatory and compliance updates"
    market_insights:
      type: array
      items:
        type: string
      maxItems: 5
      description: "Actionable market intelligence"
  required:
    - executive_summary
    - key_themes
    - credit_risk_signals
    - regulatory_updates
    - market_insights
  additionalProperties: false
```

#### 3. Update Email Template

**Location:** `src/newsanalysis/templates/email_digest.html`

Replace the `{% if key_themes %}` section with:

```jinja2
{% if executive_summary %}
<!-- Executive Summary: Heute in 30 Sekunden -->
<tr>
  <td style="padding: 20px 30px; background-color: #f0f5fa; border-bottom: 2px solid #003366;">
    <h2 style="margin: 0 0 12px 0; color: #003366; font-size: 16px; font-weight: bold;">
      Heute in 30 Sekunden
    </h2>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
      {% for i, sentence in enumerate(executive_summary, 1) %}
      <tr>
        <td style="padding: 4px 0; color: #333333; font-size: 14px; line-height: 1.5;">
          <strong>{{ i }}.</strong> {{ sentence }}
        </td>
      </tr>
      {% endfor %}
    </table>
  </td>
</tr>
{% endif %}
```

#### 4. Update Digest Formatter

**Location:** `src/newsanalysis/services/digest_formatter.py`

In `format()` and `format_with_images()` methods, add:

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

---

## Story 1.3: Dynamic Subject Line

### Current State

Subject line from `.env` template (static):
```
Creditreform News-Digest: {date} - {count} relevante Artikel
```

### Target State

Dynamic subject featuring top story:
```
Creditreform News-Digest: Baltensperger AG vor Konkurs
```

### Implementation

#### 1. Add Helper Method to Formatter

**Location:** `src/newsanalysis/services/digest_formatter.py`

```python
def get_top_article_title(self, digest_data: Dict[str, Any], max_length: int = 50) -> Optional[str]:
    """Extract the top article title for subject line.

    Args:
        digest_data: Dictionary from DigestRepository.get_digest_by_date().
        max_length: Maximum title length before truncation.

    Returns:
        Top article title, truncated if necessary, or None if no articles.
    """
    articles_by_topic = self._parse_articles(digest_data.get("json_output"))

    if not articles_by_topic:
        return None

    # Get first article from first topic (highest priority)
    for topic_articles in articles_by_topic.values():
        if topic_articles:
            title = topic_articles[0].get("title", "")

            # Truncate at word boundary if too long
            if len(title) > max_length:
                truncated = title[:max_length]
                last_space = truncated.rfind(" ")
                if last_space > max_length // 2:
                    return truncated[:last_space] + "..."
                return truncated + "..."

            return title

    return None
```

#### 2. Update Email Command

**Location:** `src/newsanalysis/cli/commands/email.py`

Replace subject line generation (lines 131-142):

```python
# Create dynamic subject line with top story
formatter = HtmlEmailFormatter()

# Get top article for subject line
top_title = formatter.get_top_article_title(digest_data, max_length=50)

if top_title:
    subject = f"Creditreform News-Digest: {top_title}"
else:
    # Fallback to date-based subject
    subject = f"Creditreform News-Digest: {target_date.strftime('%d.%m.%Y')}"

# Format HTML body
html_body = formatter.format(digest_data)
```

#### 3. Subject Line Constraints

- Maximum total length: ~78 characters (email client safe)
- Title truncation: 50 characters max
- Truncation at word boundaries (no mid-word cuts)
- Fallback to date if no articles

---

## Testing Plan

### Manual Testing

1. **2-Column Layout**
   - [ ] Run pipeline with `--reset digest --skip-collection`
   - [ ] Preview email in Outlook (`newsanalysis email --preview`)
   - [ ] Verify 900px container width
   - [ ] Verify 2-column article layout within topics
   - [ ] Verify odd articles display full-width
   - [ ] Verify image sizing (100px compact, 120px full-width)
   - [ ] Verify layout doesn't break with 1 article per topic

2. **Executive Summary**
   - [ ] Verify "Heute in 30 Sekunden" section appears
   - [ ] Verify exactly 3 sentences displayed
   - [ ] Verify sentences name specific companies
   - [ ] Verify numbered list formatting

3. **Dynamic Subject Line**
   - [ ] Verify subject includes top article title
   - [ ] Verify truncation works for long titles
   - [ ] Verify fallback to date when no articles

### Edge Cases

- Empty topics (should not display)
- Single article in topic (full-width)
- Very long article titles (truncation)
- Missing images (graceful degradation)
- Failed meta-analysis (fallback to empty executive_summary)

---

## Implementation Order

1. **MetaAnalysis Model** - Add `executive_summary` field
2. **meta_analysis.yaml** - Update prompt for executive summary
3. **email_digest.html** - Rewrite template for 2-column + executive summary
4. **digest_formatter.py** - Add `get_top_article_title()`, pass executive_summary
5. **email.py** - Use dynamic subject line
6. **Test** - Run full pipeline and preview

---

## Rollback Plan

If issues arise:
1. Revert `email_digest.html` to previous single-column layout
2. Make `executive_summary` optional in model (already is with default_factory)
3. Revert subject line logic to static template

All changes are isolated to digest generation and email formatting - no impact on data collection, filtering, scraping, or summarization stages.

---

## Appendix: Full email_digest.html Template

See separate file: `email_digest_v2.html` (to be created during implementation)

Key structure:
```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Creditreform News-Digest - {{ date }}</title>
  <!--[if mso]>
  <style type="text/css">
    table { border-collapse: collapse; }
    .column { width: 430px !important; }
  </style>
  <![endif]-->
</head>
<body>
  <table width="100%" bgcolor="#f4f4f4">
    <tr>
      <td align="center" style="padding: 20px;">
        <!-- 900px Container -->
        <table width="900" bgcolor="#ffffff">
          <!-- Header -->
          <!-- Executive Summary (Heute in 30 Sekunden) -->
          <!-- Articles by Topic (2-column) -->
          <!-- Footer -->
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
```
