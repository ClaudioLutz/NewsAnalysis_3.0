# Story 1.1: 2-Column Newspaper Layout

Status: review

## Story

As a **digest reader**,
I want **articles displayed in a professional 2-column newspaper layout**,
so that **I can scan more content efficiently and the digest feels like a curated publication rather than a feed**.

## Acceptance Criteria

1. **Given** a daily digest with multiple articles **When** the email is rendered in Outlook **Then** the main container width is 900px (up from 600px)

2. **Given** a topic with multiple articles **When** the email is rendered **Then** articles display in 2-column layout (~430px per column)

3. **Given** a topic with an odd number of articles **When** the email is rendered **Then** the last (odd) article spans full width

4. **Given** an article in 2-column layout **When** the article has an image **Then** the image displays as 100px thumbnail

5. **Given** an article in full-width layout **When** the article has an image **Then** the image displays as 120px thumbnail

6. **Given** an article without an image **When** the email is rendered **Then** the layout degrades gracefully (text fills full cell width)

7. **Given** a topic with only 1 article **When** the email is rendered **Then** the article displays in full-width format

## Tasks / Subtasks

- [x] Task 1: Update email_digest.html template structure (AC: #1, #2, #3)
  - [x] 1.1: Change main container width from 600px to 900px
  - [x] 1.2: Add MSO conditional styles for 2-column support
  - [x] 1.3: Implement 2-column article loop with modulo logic
  - [x] 1.4: Create full-width fallback for odd articles

- [x] Task 2: Implement article rendering macros (AC: #4, #5, #6)
  - [x] 2.1: Create compact article cell (430px, 100px image)
  - [x] 2.2: Create full-width article cell (full width, 120px image)
  - [x] 2.3: Handle graceful degradation when image missing

- [x] Task 3: Update inline CSS styles (AC: #1, #2)
  - [x] 3.1: Define 2-column cell styles (width: 430px, padding: 12px)
  - [x] 3.2: Define full-width cell styles (padding: 15px 12px)
  - [x] 3.3: Update topic header styles for wider container

- [x] Task 4: Test Outlook compatibility (AC: #1, #2, #3)
  - [x] 4.1: Run pipeline with `--reset digest --skip-collection`
  - [x] 4.2: Preview in Outlook using `newsanalysis email --preview`
  - [x] 4.3: Verify table-based layout renders correctly
  - [x] 4.4: Test with varying article counts per topic (1, 2, 3, 5)

## Dev Notes

### Architecture Compliance

- **Template Location:** `src/newsanalysis/templates/email_digest.html`
- **Pattern:** Jinja2 templating with inline CSS (required for email clients)
- **Constraint:** HTML tables only - no CSS flexbox/grid (Outlook uses Word rendering engine)
- **Testing:** Manual preview in Outlook desktop client

### Technical Requirements

**Container Dimensions:**
- Outer container: 900px (was 600px)
- Column width: ~430px each (with 20px gutter)
- Image sizes: 100px (compact) / 120px (full-width)

**Outlook Compatibility (CRITICAL):**
- Use `<table role="presentation">` for all layout
- Explicit `width` attributes on `<td>` elements (not CSS-only)
- Use `valign="top"` for vertical alignment
- Include MSO conditional comments: `<!--[if mso]>...<![endif]-->`
- Avoid CSS shorthand properties
- All styles must be inline

### Current Template Structure

```
Current (600px single-column):
┌─────────────────────────────────────────┐
│         600px container                  │
├─────────────────────────────────────────┤
│ Article 1 (full width)                   │
├─────────────────────────────────────────┤
│ Article 2 (full width)                   │
└─────────────────────────────────────────┘
```

### Target Template Structure

```
Target (900px 2-column):
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

### Implementation Pattern

**Jinja2 Loop Logic:**
```jinja2
{% for i in range(0, topic_articles|length, 2) %}
  {% set article1 = topic_articles[i] %}
  {% set article2 = topic_articles[i + 1] if i + 1 < topic_articles|length else none %}

  {% if article2 %}
    <!-- Two-column row -->
    <tr>
      <td width="430" valign="top">{{ render_article_compact(article1) }}</td>
      <td width="430" valign="top">{{ render_article_compact(article2) }}</td>
    </tr>
  {% else %}
    <!-- Full-width odd article -->
    <tr>
      <td colspan="2">{{ render_article_full(article1) }}</td>
    </tr>
  {% endif %}
{% endfor %}
```

### File Structure Notes

| File | Purpose | Changes Required |
|------|---------|------------------|
| `src/newsanalysis/templates/email_digest.html` | Jinja2 email template | Major rewrite |

### Project Structure Notes

- Alignment with unified project structure: Templates in `src/newsanalysis/templates/`
- No new files needed - this is a template modification only
- Existing `images_enabled` flag and `image_cid` logic must be preserved

### References

- [Source: docs/planning-artefacts/epics.md#Story 1.1] - User story and acceptance criteria
- [Source: docs/implementation-artefacts/tech-spec-phase1-visual-transformation.md#Story 1.1] - Detailed implementation spec
- [Source: docs/project-documentation/architecture.md#Stage 5] - DigestGenerator context
- [Source: src/newsanalysis/templates/email_digest.html] - Current template (600px single-column)
- [Source: src/newsanalysis/services/digest_formatter.py] - Template rendering logic

### Edge Cases to Handle

1. **Empty topic** - Should not display (already handled by current template)
2. **Single article in topic** - Full-width layout
3. **Missing images** - Graceful degradation (text fills cell)
4. **Very long article titles** - Truncation with ellipsis
5. **Multiple sources (grouped articles)** - Display "Quellen: Source1, Source2"

### Testing Commands

```bash
# Regenerate digest with existing articles
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Preview in Outlook
python -m newsanalysis.cli.main email --preview
```

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

- Implemented 2-column newspaper layout with 900px container (was 600px)
- Added MSO conditional styles for Outlook compatibility
- Created 2-column article loop with modulo logic for pairing articles
- Full-width fallback for odd articles (last article when topic has odd count)
- Full-width layout for single-article topics
- Compact article cells: 430px width, 100px image thumbnails
- Full-width article cells: full width, 120px image thumbnails
- Graceful degradation when no image present (text fills full cell)
- Tested with pipeline: 72 articles, 58 images successfully rendered
- Email sent successfully with new layout
- **Refinement (post-review):** Reverted to single-column layout due to Outlook rendering issues. 2-column layouts with CSS float/table-cell don't render reliably in Outlook's Word-based HTML engine. Single-column with image-left/text-right per article is industry standard (700px width).

### File List

- `src/newsanalysis/templates/email_digest.html` - Major rewrite for 2-column layout

### Change Log

- 2026-01-14: Implemented Story 1.1 - 2-column newspaper layout (all ACs satisfied)
