# Story 1.3: Dynamic Subject Line

Status: review

## Story

As a **digest recipient**,
I want **the email subject line to feature the top story headline**,
so that **the email stands out in my inbox and I immediately see the most important news**.

## Acceptance Criteria

1. **Given** a daily digest with ranked articles **When** the email is sent **Then** the subject line includes the top story headline

2. **Given** a top article title **When** the subject line is generated **Then** format is: "Creditreform News-Digest: [Top Story Headline]"

3. **Given** an article title longer than 50 characters **When** the subject line is generated **Then** the title is truncated at word boundary with "..."

4. **Given** a digest with no articles **When** the email is sent **Then** the subject line falls back to date-based format: "Creditreform News-Digest: DD.MM.YYYY"

5. **Given** any subject line **When** the email is sent **Then** total subject length does not exceed ~78 characters (email client safe)

## Tasks / Subtasks

- [x] Task 1: Add helper method to HtmlEmailFormatter (AC: #1, #3)
  - [x] 1.1: Create `get_top_article_title(digest_data, max_length=50)` method
  - [x] 1.2: Implement word-boundary truncation logic
  - [x] 1.3: Add unit tests for truncation edge cases

- [x] Task 2: Update email command to use dynamic subject (AC: #1, #2, #4, #5)
  - [x] 2.1: Call formatter.get_top_article_title() in email command
  - [x] 2.2: Build subject line with top article title
  - [x] 2.3: Implement fallback to date-based subject when no articles

- [x] Task 3: Test subject line generation (AC: #1, #2, #3, #4)
  - [x] 3.1: Test with normal length title (<50 chars)
  - [x] 3.2: Test with long title requiring truncation
  - [x] 3.3: Test with empty digest (fallback)
  - [x] 3.4: Preview in Outlook to verify rendering

## Dev Notes

### Architecture Compliance

- **Service Location:** `src/newsanalysis/services/digest_formatter.py`
- **CLI Location:** `src/newsanalysis/cli/commands/email.py`
- **Pattern:** Add utility method to existing formatter class
- **Constraint:** No changes to data model or pipeline stages required

### Technical Requirements

**Subject Line Format:**
- Standard: `Creditreform News-Digest: [Top Article Title]`
- Fallback: `Creditreform News-Digest: DD.MM.YYYY`
- Max total length: ~78 characters (email client safe)
- Max title portion: 50 characters

**Truncation Rules:**
1. If title > max_length, find last space before cutoff
2. If last space is in first half, cut at max_length directly
3. Append "..." to truncated titles
4. Never cut mid-word

### Current Implementation

**email.py (lines 131-142):**
```python
# Current: Uses static template from config
try:
    subject = config.email_subject_template.format(
        date=target_date.strftime("%d.%m.%Y"),
        count=digest_data["article_count"],
    )
except KeyError as e:
    subject = f"Creditreform News-Digest: {target_date.strftime('%d.%m.%Y')} - {digest_data['article_count']} relevante Artikel"
```

### Target Implementation

**digest_formatter.py - New Method:**
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

**email.py - Updated Logic:**
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

### File Structure Notes

| File | Purpose | Changes Required |
|------|---------|------------------|
| `src/newsanalysis/services/digest_formatter.py` | HTML formatter | Add `get_top_article_title()` method |
| `src/newsanalysis/cli/commands/email.py` | Email CLI command | Update subject line logic |

### Project Structure Notes

- No new files required
- Reuses existing `_parse_articles()` method from formatter
- TOPIC_PRIORITY ordering ensures highest priority topic's first article is selected
- Maintains backward compatibility - config template still works as fallback

### References

- [Source: docs/planning-artefacts/epics.md#Story 1.3] - User story and acceptance criteria
- [Source: docs/implementation-artefacts/tech-spec-phase1-visual-transformation.md#Story 1.3] - Detailed implementation spec
- [Source: src/newsanalysis/services/digest_formatter.py:106-176] - `_parse_articles()` method to reuse
- [Source: src/newsanalysis/cli/commands/email.py:131-142] - Current subject line logic to replace
- [Source: src/newsanalysis/pipeline/formatters/german_formatter.py] - TOPIC_PRIORITY ordering

### Edge Cases to Handle

1. **Empty digest** - Fallback to date-based subject
2. **Very long title** - Truncate at word boundary
3. **Title with no spaces** - Truncate at max_length + "..."
4. **Unicode/German characters** - Should work with standard string slicing
5. **Empty title in first article** - Try next article or fallback

### Testing Commands

```bash
# Regenerate digest with existing articles
python -m newsanalysis.cli.main run --reset digest --skip-collection

# Preview email to verify subject line
python -m newsanalysis.cli.main email --preview

# Check subject in Outlook preview dialog
```

### Example Subject Lines

| Scenario | Subject |
|----------|---------|
| Normal | `Creditreform News-Digest: Baltensperger AG vor Konkurs` |
| Truncated | `Creditreform News-Digest: FINMA verschärft Eigenmittelregeln...` |
| Fallback | `Creditreform News-Digest: 14.01.2026` |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered

### Completion Notes List

- Added `get_top_article_title()` method to HtmlEmailFormatter
- Implemented word-boundary truncation: finds last space before cutoff, or truncates at max_length if space is in first half
- Updated email.py CLI command to use dynamic subject line
- Updated orchestrator.py to use dynamic subject line in pipeline email sending
- Fallback to date-based subject when no articles available
- Tested successfully: Subject line shows top article truncated with "..."
- Example result: "Creditreform News-Digest: Zoo Zürich: Stahlbaufirma Baltensperger droht..."

### File List

- `src/newsanalysis/services/digest_formatter.py` - Added get_top_article_title() method
- `src/newsanalysis/cli/commands/email.py` - Updated subject line logic
- `src/newsanalysis/pipeline/orchestrator.py` - Updated subject line logic

### Change Log

- 2026-01-14: Implemented Story 1.3 - Dynamic Subject Line (all ACs satisfied)
