---
title: 'Topic Classification for Email Digest'
slug: 'topic-classification-email-digest'
created: '2026-01-08'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.11', 'Pydantic 2.x', 'Jinja2', 'Gemini API', 'SQLite', 'pytest']
files_to_modify: ['config/prompts/summarization.yaml', 'src/newsanalysis/core/article.py', 'src/newsanalysis/core/enums.py', 'src/newsanalysis/pipeline/summarizers/article_summarizer.py', 'src/newsanalysis/pipeline/formatters/german_formatter.py', 'src/newsanalysis/templates/email_digest.html', 'src/newsanalysis/services/digest_formatter.py', 'config/topics.yaml', 'src/newsanalysis/pipeline/generators/digest_generator.py', 'src/newsanalysis/pipeline/orchestrator.py', 'docs/stories/']
code_patterns: ['Pydantic BaseModel with Field validators', 'str Enum pattern', 'Jinja2 template loops with conditionals', 'JSON serialization for cache storage', 'async/await for LLM calls']
test_patterns: ['pytest with @pytest.mark.unit decorator', 'ValidationError testing for Pydantic', 'Test classes grouped by model']
---

# Tech-Spec: Topic Classification for Email Digest

**Created:** 2026-01-08

## Overview

### Problem Statement

The email digest displays articles in a flat chronological list without topic organization. This makes it harder for credit analysts to quickly scan and find relevant sections. The current classification stage only returns generic "creditreform_insights" instead of granular topic categories, leaving the existing `topic` field underutilized.

### Solution

Add a `topic` field to the Gemini summarization output (zero additional API cost by piggybacking on existing summarization) and restructure the HTML email template to group articles by topic sections. Leverage the existing `articles_by_topic` infrastructure in the German formatter as a pattern.

### Scope

**In Scope:**
- Add `topic` enum field to summarization prompt and output schema
- Update `ArticleSummary` and `SummaryResponse` Pydantic models
- Implement 12-topic taxonomy (11 business categories + "other")
- Add new topic: `board_changes` (Mutationen Gremien)
- Update HTML email template with topic-grouped sections
- Update `digest_formatter.py` to group articles by topic
- Add missing German translations for new topics
- Handle cached entries gracefully (default to "other")
- Fixed priority ordering of topic sections (risk-critical first)

**Out of Scope:**
- Multi-label classification (single primary topic only)
- Topic filtering/subscription per user
- Analytics dashboard for topic trends
- Changes to the initial relevance classification stage (DeepSeek)
- Database schema migrations (topic stored in existing JSON fields)

## Context for Development

### Codebase Patterns

- **Pydantic Models**: All domain models use Pydantic 2.x with `BaseModel`, `Field` validators, and `field_validator` decorators
- **Enums**: String enums inherit from `(str, Enum)` pattern in `core/enums.py`
- **LLM Integration**: Uses `response_format=SummaryResponse` for structured output validation
- **Caching**: Content fingerprints stored in SQLite with JSON serialization for complex fields
- **Templates**: Jinja2 with `{% for %}` loops and `{% if %}` conditionals, table-based HTML for Outlook compatibility
- **German Formatter**: Groups articles by topic using `articles_by_topic` dict with `_translate_topic()` method

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `src/newsanalysis/core/enums.py` | Add `ArticleTopic` enum here (follows existing `ExtractionMethod` pattern) |
| `src/newsanalysis/core/article.py:92-109` | `ArticleSummary` model - add `topic` field |
| `src/newsanalysis/pipeline/summarizers/article_summarizer.py:28-43` | `SummaryResponse` model - add `topic` field |
| `src/newsanalysis/pipeline/summarizers/article_summarizer.py:156-163` | Parse response - extract topic |
| `src/newsanalysis/services/cache_service.py:133-190` | Cache get/set - handle topic in entities JSON |
| `src/newsanalysis/pipeline/formatters/german_formatter.py:85-116` | `_build_context()` - topic grouping pattern to reuse |
| `src/newsanalysis/pipeline/formatters/german_formatter.py:118-144` | `_translate_topic()` - add new translations |
| `src/newsanalysis/services/digest_formatter.py:98-146` | `_parse_articles()` - add topic grouping |
| `src/newsanalysis/templates/email_digest.html:119-159` | Articles section - restructure for topic groups |
| `config/prompts/summarization.yaml:20-31` | Output schema - add topic enum |
| `config/topics.yaml` | Add `board_changes` focus area |

### Technical Decisions

- **Single topic per article**: Cleaner email layout, no article duplication
- **Allow "other" category**: Prevents forced misclassification
- **Fixed priority ordering**: Risk-critical topics (Insolvenzen, Bonität) appear first
- **Hide empty sections**: Cleaner email without visual noise
- **Enum constraint in prompt**: Guarantees valid topic values from LLM
- **Store topic in entities JSON**: No database migration required, backwards compatible
- **Default missing cached topics to "other"**: Graceful degradation for existing cache entries
- **Override Article.topic during summarization**: Reuse existing field, German formatter already reads it

## Implementation Plan

### Tasks

#### Task 1: Add ArticleTopic Enum
- **File:** `src/newsanalysis/core/enums.py`
- **Action:** Add new `ArticleTopic(str, Enum)` class with 12 values after `PipelineMode` class
- **Code:**
```python
class ArticleTopic(str, Enum):
    """Article topic classification for digest grouping.

    NOTE: Enum member order has no functional meaning.
    Display priority is controlled by TOPIC_PRIORITY list in german_formatter.py
    """
    INSOLVENCY_BANKRUPTCY = "insolvency_bankruptcy"
    CREDIT_RISK = "credit_risk"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    KYC_AML_SANCTIONS = "kyc_aml_sanctions"
    PAYMENT_BEHAVIOR = "payment_behavior"
    DEBT_COLLECTION = "debt_collection"
    BOARD_CHANGES = "board_changes"
    COMPANY_LIFECYCLE = "company_lifecycle"
    ECONOMIC_INDICATORS = "economic_indicators"
    MARKET_INTELLIGENCE = "market_intelligence"
    ECOMMERCE_FRAUD = "ecommerce_fraud"
    OTHER = "other"
```

#### Task 2: Update ArticleSummary Model
- **File:** `src/newsanalysis/core/article.py`
- **Action:** Import `ArticleTopic` and add `topic` field to `ArticleSummary` class (after line 98)
- **Code:**
```python
from newsanalysis.core.enums import ExtractionMethod, ArticleTopic

class ArticleSummary(BaseModel):
    """AI-generated article summary."""
    summary_title: str = Field(..., max_length=200)
    summary: str = Field(...)
    key_points: List[str] = Field(...)
    entities: EntityData
    topic: ArticleTopic = Field(default=ArticleTopic.OTHER)  # NEW
    summarized_at: datetime = Field(default_factory=datetime.now)
```

#### Task 3: Update SummaryResponse Model
- **File:** `src/newsanalysis/pipeline/summarizers/article_summarizer.py`
- **Action:** Import `ArticleTopic` and add `topic` field to `SummaryResponse` class (line 28-43)
- **Code:**
```python
from newsanalysis.core.enums import ArticleTopic

class SummaryResponse(BaseModel):
    """Structured response from OpenAI for summarization."""
    title: str = Field(..., description="Normalized article title")
    summary: str = Field(..., description="Brief summary (1-2 sentences, max 50 words)")
    key_points: List[str] = Field(..., description="Concise key bullet points (2-3 items)")
    entities: EntityList = Field(default_factory=EntityList)
    topic: ArticleTopic = Field(default=ArticleTopic.OTHER, description="Primary topic")  # NEW
```

#### Task 4: Update Summarization Prompt
- **File:** `config/prompts/summarization.yaml`
- **Action A:** Update `user_prompt_template` to include topic field in JSON example (insert after "entities" block, before closing braces)
- **Action B:** Add `topic` to `output_schema` and `required` list
- **Full user_prompt_template structure with topic:**
```yaml
user_prompt_template: |
  Article Title: {title}
  Source: {source}
  Content: {content}

  Create a structured summary in JSON format:
  {{
    "title": "Normalized title (max 150 chars)",
    "summary": "1-2 sentence summary (max 50 words) focusing on the key message",
    "key_points": ["short bullet point 1", "short bullet point 2"],
    "entities": {{
      "companies": ["company names mentioned"],
      "people": ["key people mentioned"],
      "locations": ["locations mentioned"],
      "topics": ["main topics/themes"]
    }},
    "topic": "Primary topic - exactly ONE of: insolvency_bankruptcy, credit_risk, regulatory_compliance, kyc_aml_sanctions, payment_behavior, debt_collection, board_changes, company_lifecycle, economic_indicators, market_intelligence, ecommerce_fraud, other"
  }}
```
- **Add to output_schema (after entities section):**
```yaml
    topic:
      type: string
      enum: [insolvency_bankruptcy, credit_risk, regulatory_compliance, kyc_aml_sanctions, payment_behavior, debt_collection, board_changes, company_lifecycle, economic_indicators, market_intelligence, ecommerce_fraud, other]
      description: "Primary topic classification"
  required:
    - title
    - summary
    - key_points
    - entities
    - topic
```

#### Task 5: Update Summarizer to Extract Topic
- **File:** `src/newsanalysis/pipeline/summarizers/article_summarizer.py`
- **Action:** Update `summarize()` method to extract topic from response (around line 156-172)
- **Code:**
```python
# After parsing entities (around line 163)
topic_str = content_dict.get("topic", "other")
try:
    topic = ArticleTopic(topic_str)
except ValueError:
    logger.warning("invalid_topic_fallback", topic=topic_str)
    topic = ArticleTopic.OTHER

# Update ArticleSummary creation
summary = ArticleSummary(
    summary_title=content_dict["title"],
    summary=content_dict["summary"],
    key_points=content_dict["key_points"],
    entities=entities,
    topic=topic,  # NEW
    summarized_at=datetime.now(),
)
```

#### Task 6: Update Cache Storage (Summarizer Side)
- **File:** `src/newsanalysis/pipeline/summarizers/article_summarizer.py`
- **Action:** Include topic INSIDE the entities JSON when caching (NO schema change needed)
- **Rationale:** The `content_fingerprints` table stores `entities` as JSON. We add topic to this JSON object rather than adding a new column.
- **Code for cache storage (around line 175-187):**
```python
# Include topic in entities JSON for cache storage
self.cache_service.cache_summary(
    content=content,
    summary_title=summary.summary_title,
    summary=summary.summary,
    key_points=json.dumps(summary.key_points),
    entities=json.dumps({
        "companies": entities.companies,
        "people": entities.people,
        "locations": entities.locations,
        "topics": entities.topics,
        "topic": summary.topic.value,  # NEW - store topic inside entities JSON
    }),
)
```

#### Task 7: Update Cache Retrieval (Summarizer Side)
- **File:** `src/newsanalysis/pipeline/summarizers/article_summarizer.py`
- **Action:** Extract topic from entities JSON when reading from cache (around line 107-128)
- **Code for cache retrieval:**
```python
# Parse cached JSON data
entities_dict = json.loads(cached_summary["entities"])
entities = EntityData(
    companies=entities_dict.get("companies", []),
    people=entities_dict.get("people", []),
    locations=entities_dict.get("locations", []),
    topics=entities_dict.get("topics", []),
)

# Extract topic from entities JSON (backwards compatible)
topic_str = entities_dict.get("topic", "other")
try:
    topic = ArticleTopic(topic_str)
except ValueError:
    topic = ArticleTopic.OTHER

return ArticleSummary(
    summary_title=cached_summary["summary_title"],
    summary=cached_summary["summary"],
    key_points=json.loads(cached_summary["key_points"]),
    entities=entities,
    topic=topic,  # NEW
    summarized_at=datetime.now(),
)
```
- **Notes:** No changes needed to `cache_service.py` - the existing `entities` column stores the JSON with topic included

#### Task 8: Add Topic Priority and Translations Constants
- **File:** `src/newsanalysis/pipeline/formatters/german_formatter.py`
- **Action:** Add constants after `GERMAN_MONTHS` (line 26)
- **Code:**
```python
TOPIC_PRIORITY = [
    "insolvency_bankruptcy", "credit_risk", "regulatory_compliance",
    "kyc_aml_sanctions", "payment_behavior", "debt_collection",
    "board_changes", "company_lifecycle", "economic_indicators",
    "market_intelligence", "ecommerce_fraud", "other",
]

TOPIC_TRANSLATIONS = {
    "insolvency_bankruptcy": "Insolvenzen",
    "credit_risk": "Bonität",
    "regulatory_compliance": "Regulierung",
    "kyc_aml_sanctions": "Sanktionen & Compliance",
    "payment_behavior": "Zahlungsverhalten",
    "debt_collection": "Inkasso",
    "board_changes": "Mutationen Gremien",
    "company_lifecycle": "Fusionen & Übernahmen",
    "economic_indicators": "Wirtschaftsindikatoren",
    "market_intelligence": "Marktentwicklungen",
    "ecommerce_fraud": "Betrug & Cyberkriminalität",
    "other": "Sonstige",
}
```

#### Task 9: Update German Formatter _translate_topic
- **File:** `src/newsanalysis/pipeline/formatters/german_formatter.py`
- **Action:** Replace hardcoded dict in `_translate_topic()` with `TOPIC_TRANSLATIONS`
- **Code:**
```python
def _translate_topic(self, topic: str) -> str:
    return TOPIC_TRANSLATIONS.get(topic, topic)
```

#### Task 10: Update Digest Formatter for Topic Grouping
- **File:** `src/newsanalysis/services/digest_formatter.py`
- **Action A:** Import constants at top of file
```python
from newsanalysis.pipeline.formatters.german_formatter import TOPIC_PRIORITY, TOPIC_TRANSLATIONS
```
- **Action B:** Update `_parse_articles()` to return `Dict[str, List[Dict]]` grouped by topic
- **Action C:** Update `format()` to pass `articles_by_topic` and `topic_translations` to template
- **Code for _parse_articles (complete implementation):**
```python
def _parse_articles(self, json_output: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Parse articles from JSON output and group by topic."""
    if not json_output:
        return {}
    try:
        data = json.loads(json_output)
        articles = data.get("articles", [])

        # Group by topic
        articles_by_topic: Dict[str, List[Dict[str, Any]]] = {}
        for article in articles:
            topic = article.get("topic", "other")
            if topic not in articles_by_topic:
                articles_by_topic[topic] = []

            # Build article dict with all required fields
            summary = article.get("summary", "")
            if len(summary) > 200:
                summary = summary[:197] + "..."

            articles_by_topic[topic].append({
                "title": article.get("summary_title") or article.get("title", "Untitled"),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "summary": summary,
                "key_points": article.get("key_points", []),
                "topic": topic,
            })

        # Sort by priority, filter empty topics
        sorted_by_topic = {
            t: articles_by_topic[t]
            for t in TOPIC_PRIORITY
            if t in articles_by_topic and articles_by_topic[t]
        }
        return sorted_by_topic
    except json.JSONDecodeError:
        return {}
```
- **Code for format() method - pass new template variables:**
```python
html = template.render(
    # ... existing variables ...
    articles_by_topic=articles_by_topic,  # NEW - replaces flat articles list
    topic_translations=TOPIC_TRANSLATIONS,  # NEW
)
```

#### Task 11: Update Email Template for Topic Sections
- **File:** `src/newsanalysis/templates/email_digest.html`
- **Action:** Replace flat article list (lines 119-159) with topic-grouped sections
- **Code (with edge case handling for empty articles):**
```html
<!-- Articles by Topic -->
<tr>
  <td style="padding: 20px 30px;">
    {% if articles_by_topic %}
      {% for topic, topic_articles in articles_by_topic.items() %}
      <h2 style="margin: 20px 0 10px 0; color: #003366; font-size: 16px; font-weight: bold; border-bottom: 2px solid #003366; padding-bottom: 5px;">
        {{ topic_translations.get(topic, topic) }}
      </h2>
      {% for article in topic_articles %}
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-left: 3px solid #003366; margin-bottom: 12px;">
        <tr>
          <td style="padding-left: 12px;">
            <p style="margin: 0 0 2px 0; font-size: 13px; font-weight: bold;">
              {% if article.url %}<a href="{{ article.url }}" style="color: #003366; text-decoration: none;">{{ article.title }}</a>{% else %}{{ article.title }}{% endif %}
            </p>
            {% if article.source %}
            <p style="margin: 0 0 4px 0; color: #888888; font-size: 11px;">{{ article.source }}</p>
            {% endif %}
            {% if article.summary %}
            <p style="margin: 0 0 4px 0; color: #555555; font-size: 12px; line-height: 1.3;">{{ article.summary }}</p>
            {% endif %}
          </td>
        </tr>
      </table>
      {% endfor %}
      {% endfor %}
    {% else %}
      <p style="color: #666666; font-style: italic;">Keine relevanten Artikel heute.</p>
    {% endif %}
  </td>
</tr>
```

#### Task 12: Update Orchestrator to Set Article Topic
- **File:** `src/newsanalysis/pipeline/orchestrator.py`
- **Action:** After summarization success, copy `summary.topic.value` to `article.topic`
- **Location:** Around line 453-477 in `_run_summarization()`
- **Code:**
```python
if summary:
    article.summary_title = summary.summary_title
    article.summary = summary.summary
    article.key_points = summary.key_points
    article.entities = summary.entities
    article.topic = summary.topic.value  # NEW - override classification topic
    article.summarized_at = summary.summarized_at
```

#### Task 13: Ensure Topic Flows to Digest JSON
- **File:** `src/newsanalysis/pipeline/generators/digest_generator.py`
- **Action:** Verify that when building the digest JSON, the `topic` field from each Article is included
- **Context:** The digest generator reads Article objects from the database. After Task 12, each Article has `article.topic` set. The generator must include this in the JSON output that gets passed to digest_formatter.
- **Verification Code (check existing implementation):**
```python
# In digest_generator.py, ensure article serialization includes topic:
article_data = {
    "title": article.title,
    "summary_title": article.summary_title,
    "summary": article.summary,
    "url": str(article.url),
    "source": article.source,
    "topic": article.topic,  # VERIFY THIS EXISTS
    # ...
}
```
- **Notes:** If not present, add `"topic": article.topic` to the article dict serialization

#### Task 14: Add board_changes to topics.yaml
- **File:** `config/topics.yaml`
- **Action:** Add new focus area after `ecommerce_fraud` section
- **Code:**
```yaml
board_changes:
  - Verwaltungsrat
  - Geschäftsleitung
  - CEO
  - CFO
  - VR-Präsident
  - Ernennung
  - Rücktritt
  - Mutation
  - Personalie
  - Management
```

#### Task 15: Create Story Documentation
- **File:** `docs/stories/YYYYMMddHHmmss-topic-classification-email-digest.md`
- **Action:** Create story documentation per CLAUDE.md requirements
- **Template:**
```markdown
## Summary
Add topic classification to email digest for professional layout with grouped sections.

## Context / Problem
Email digest displayed articles in flat chronological list. Credit analysts needed faster scanning by topic.

## What Changed
- Added ArticleTopic enum with 12 categories
- Updated summarization prompt to classify articles by topic
- Restructured HTML email template with topic-grouped sections
- Added German translations for topic headers

## How to Test
1. Run pipeline: `newsanalysis run`
2. Send email: `newsanalysis email --send`
3. Verify topic sections appear in correct priority order

## Risk / Rollback Notes
- Rollback: Revert to previous flat article template
- Topic classification depends on Gemini accuracy
```

### Acceptance Criteria

#### AC1: Topic Enum Validation
- **Given** a valid topic string "insolvency_bankruptcy"
- **When** creating an ArticleTopic enum
- **Then** the enum is created successfully with value "insolvency_bankruptcy"

#### AC2: Invalid Topic Fallback
- **Given** an invalid topic string "unknown_topic"
- **When** the summarizer parses the LLM response
- **Then** the topic defaults to ArticleTopic.OTHER

#### AC3: Summarization Returns Contextually Correct Topic
- **Given** an article with title "UBS meldet Konkurs an" about company bankruptcy
- **When** the article is summarized by Gemini
- **Then** the ArticleSummary.topic equals ArticleTopic.INSOLVENCY_BANKRUPTCY (not OTHER)

#### AC4: Cache Stores and Retrieves Topic
- **Given** a new article summary with topic="credit_risk"
- **When** the summary is cached and later retrieved
- **Then** the cached ArticleSummary has topic=ArticleTopic.CREDIT_RISK

#### AC5: Cache Backwards Compatibility
- **Given** a cached summary without topic field (legacy entry)
- **When** retrieving from cache
- **Then** the topic defaults to ArticleTopic.OTHER

#### AC6: Email Groups by Topic
- **Given** a digest with articles in topics: credit_risk (2), insolvency_bankruptcy (1), other (1)
- **When** the HTML email is generated
- **Then** articles appear in 3 separate sections with German headers

#### AC7: Topic Sections Ordered by Priority
- **Given** articles in topics: other, credit_risk, insolvency_bankruptcy
- **When** the email is generated
- **Then** sections appear in order: Insolvenzen, Bonität, Sonstige

#### AC8: Empty Sections Hidden
- **Given** no articles in the "ecommerce_fraud" topic
- **When** the email is generated
- **Then** no "Betrug & Cyberkriminalität" section appears

#### AC9: German Topic Headers Display Correctly
- **Given** articles with topic "board_changes"
- **When** the email is generated
- **Then** the section header displays "Mutationen Gremien"

#### AC10: Article.topic Updated in Database
- **Given** an article passes through the full pipeline
- **When** summarization completes
- **Then** the article record has topic set to the granular summarization topic

#### AC11: German Markdown Report Still Works
- **Given** the german_formatter.py uses TOPIC_TRANSLATIONS constant
- **When** generating the German markdown report
- **Then** topics are correctly translated and articles grouped (no regression)

#### AC12: Zero Articles Handled Gracefully
- **Given** no articles pass the relevance filter
- **When** the HTML email is generated
- **Then** the template displays "Keine relevanten Artikel heute." instead of empty sections

## Additional Context

### Dependencies

| Dependency | Type | Notes |
|------------|------|-------|
| Gemini API | Existing | No new costs - topic added to existing summarization call |
| Pydantic 2.x | Existing | Schema validation for ArticleTopic enum |
| Jinja2 | Existing | Template rendering with topic loops |
| SQLite | Existing | No schema migration - topic stored in JSON |

### Testing Strategy

#### Unit Tests (`tests/unit/test_models.py`)
- Test ArticleTopic enum creation with valid values
- Test ArticleTopic enum rejects invalid values
- Test ArticleSummary with topic field
- Test ArticleSummary default topic is OTHER

#### Unit Tests (`tests/unit/test_cache_service.py`)
- Test cache_summary stores topic
- Test get_cached_summary returns topic
- Test backwards compatibility (missing topic returns "other")

#### Integration Tests (`tests/integration/test_pipeline.py`)
- Test full pipeline assigns topic to articles
- Test summarized articles have valid topic values

#### Manual Testing
1. Run pipeline: `newsanalysis run`
2. Check `out/digest-*.json` - verify articles have `topic` field
3. Send test email: `newsanalysis email --send`
4. Open in Outlook - verify topic sections with German headers
5. Verify priority ordering (Insolvenzen before Bonität)
6. Verify no empty sections appear

### Notes

#### Pre-Mortem Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gemini returns invalid topic | Low | Low | Enum validation + fallback to OTHER |
| Existing cache entries lack topic | Certain | Low | Default to OTHER, degrades gracefully |
| Outlook HTML rendering issues | Medium | Medium | Table-based layout, manual testing |
| Topic classification inconsistency | Medium | Low | Keywords in prompt guide LLM |

#### Known Limitations
- Single topic per article (no multi-label support)
- Topic accuracy depends on Gemini's German business context understanding
- Legacy cached entries appear in "Sonstige" until cache expires (90 days)

#### Architecture Notes
- **Constants Location:** `TOPIC_PRIORITY` and `TOPIC_TRANSLATIONS` are defined in `german_formatter.py` and imported by `digest_formatter.py`. This creates a coupling between formatters. Future refactor could move these to a shared `constants.py` module, but current approach is acceptable for now.

#### Rollback Plan
If topic classification causes issues in production:
1. **Quick rollback (template only):** Revert `email_digest.html` to flat article list - keeps topic data but displays flat
2. **Full rollback:** Revert all 15 tasks - articles display without topic grouping
3. **Selective rollback:** Keep topic in data, disable grouping via config flag (requires additional work)

**Monitoring:** Watch for excessive articles in "Sonstige" section (indicates poor classification)

#### Future Considerations (Out of Scope)
- Topic-based filtering per subscriber
- Topic trend analytics dashboard
- Confidence scores for topic classification
- Secondary topic support for multi-topic articles
- Move TOPIC_PRIORITY/TOPIC_TRANSLATIONS to shared constants module

### Source Documents
- Brainstorming session: `_bmad-output/analysis/brainstorming-session-20260108-topic-classification.md`
