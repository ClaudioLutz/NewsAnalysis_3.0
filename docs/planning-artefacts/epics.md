---
stepsCompleted: [step-01-validate, step-02-design-epics, step-03-create-stories]
inputDocuments:
  - 'docs/planning-artefacts/prd.md'
  - 'docs/project-documentation/architecture.md'
  - 'docs/project-documentation/data-models.md'
  - '_bmad-output/analysis/brainstorming-session-20260314.md'
---

# Credit Impact Classification — Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the Credit Impact Classification feature, decomposing the PRD requirements into implementable stories. This is a brownfield feature addition to NewsAnalysis 3.0.

## Requirements Inventory

### Functional Requirements

```
FR-1.1: The system can classify each summarized article with a credit_impact value of elevated_risk, negative, neutral, or positive based on the article's impact on the creditworthiness of affected companies.
FR-1.2: The system can include credit_impact as a field in the LLM summarization prompt's JSON output schema with clear category definitions and examples.
FR-1.3: The system can fall back to rule-based credit impact determination when the LLM does not return a credit_impact value.
FR-1.4: The system can cache credit_impact alongside other summary fields in the content fingerprint cache.
FR-2.1: The system can store credit_impact as a column on the articles table in the database.
FR-2.2: The system can read and write credit_impact through the ArticleRepository.
FR-2.3: The system can represent credit_impact as a Python enum (CreditImpact) in the domain model.
FR-2.4: The system can include credit_impact in the digest JSON output for downstream consumption.
FR-3.1: The system can render each article in the email digest with a visual style (border color, background color, icon, label) corresponding to its credit_impact value.
FR-3.2: The system can display all four credit impact categories with distinct, Outlook-compatible visual styling using BMP Unicode icons.
FR-3.3: The system can sort articles within each topic group by credit_impact priority (elevated_risk first) before sorting by confidence.
FR-4.1: The system can display a Risiko-Radar section at the top of the email digest listing all articles classified as elevated_risk.
FR-4.2: Each Risiko-Radar entry can show the company name(s), a short description, and the topic category.
FR-4.3: The system can hide the Risiko-Radar section or display an appropriate message when no elevated_risk articles exist.
FR-5.1: The system can process articles that were summarized before credit_impact was introduced (treating missing values as neutral or applying fallback logic).
FR-5.2: The system can maintain existing pipeline behavior for all stages not directly modified by this feature.
```

### Non-Functional Requirements

```
NFR-1: Adding credit_impact to the summarization prompt must not increase pipeline execution time by more than 5%.
NFR-2: The email digest generation time must not increase noticeably (< 1 second additional).
NFR-3: The email template must render correctly in Outlook Desktop (Word rendering engine), Outlook Web (OWA), and Outlook Mobile.
NFR-4: All Unicode icons used must be from the Basic Multilingual Plane (BMP) to ensure cross-client compatibility.
NFR-5: The feature must support dark mode rendering via existing @media (prefers-color-scheme: dark) styles.
NFR-6: The credit impact category definitions must be configurable in the summarization YAML prompt file, not hardcoded in Python.
NFR-7: The fallback logic must be clearly separated from the LLM-based classification logic.
NFR-8: Existing articles without credit_impact must not cause errors in digest generation or email rendering.
NFR-9: The credit_impact field must be nullable in the database to support backward compatibility.
```

### Additional Requirements (from Architecture & Codebase)

```
AR-1: Summarization uses Gemini 2.0 Flash — prompt changes go to config/prompts/summarization.yaml
AR-2: Article model uses Pydantic v2 — new fields added to src/newsanalysis/core/article.py
AR-3: Database uses SQLAlchemy 2.0 + SQLite — schema changes in schema.sql, migration in init_db.py
AR-4: Email template uses Jinja2 with table-based layout for Outlook — modifications to email_digest.html
AR-5: Content fingerprint cache must include credit_impact to avoid re-classification on cache hits
AR-6: Existing _determine_risk_level() in digest_formatter.py becomes the fallback mechanism
AR-7: Digest JSON output in json_formatter.py must include credit_impact for downstream consumption
```

### FR Coverage Map

| FR | Epic | Story |
|----|------|-------|
| FR-1.1, FR-1.2, FR-1.3, FR-1.4 | Epic 1 | Story 1.1 |
| FR-2.1, FR-2.2, FR-2.3 | Epic 1 | Story 1.2 |
| FR-2.4, FR-5.1, FR-5.2 | Epic 1 | Story 1.3 |
| FR-3.1, FR-3.2 | Epic 2 | Story 2.1 |
| FR-3.3 | Epic 2 | Story 2.2 |
| FR-4.1, FR-4.2, FR-4.3 | Epic 2 | Story 2.3 |

## Epic List

1. **Epic 1: Credit Impact Intelligence** — Analysts receive articles with LLM-assessed creditworthiness impact, stored and cached for all downstream use
2. **Epic 2: Visual Credit Risk Communication** — Analysts see credit impact at a glance through color-coded articles, smart sorting, and a Risiko-Radar overview

---

## Epic 1: Credit Impact Intelligence

**Goal:** Enable the system to classify each article's creditworthiness impact using the LLM during summarization, store it persistently, and make it available throughout the pipeline. After this epic, every new article has a `credit_impact` value — the foundation for all visual and analytical features.

**FRs covered:** FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-5.1, FR-5.2
**Priority:** Highest — Must be completed first
**Effort:** Small-Medium

---

### Story 1.1: LLM Credit Impact Classification

As a **system operator**,
I want **the summarization LLM to classify each article's impact on creditworthiness**,
So that **every article receives an accurate, content-based credit impact assessment**.

**Acceptance Criteria:**

**Given** an article with scraped content is sent to the summarization LLM
**When** the summarization prompt is executed
**Then** the LLM response includes a `credit_impact` field with one of: `elevated_risk`, `negative`, `neutral`, `positive`
**And** the prompt contains clear definitions and examples for each category:
  - `elevated_risk`: Acute threat to solvency (bankruptcy, debt enforcement, license revocation, criminal proceedings)
  - `negative`: Deterioration of creditworthiness (revenue decline, layoffs, rating downgrade, regulatory warning)
  - `neutral`: No impact on creditworthiness (industry news, personnel changes without impact)
  - `positive`: Improvement of creditworthiness (revenue growth, new investment, rating upgrade, regulatory relief)

**Given** the LLM does not return a `credit_impact` value (malformed response, timeout)
**When** the summarization result is processed
**Then** the system applies rule-based fallback logic:
  - Topic in `{insolvency_bankruptcy, credit_risk, business_scams, ecommerce_fraud}` AND confidence ≥ 0.85 → `elevated_risk`
  - Otherwise → `neutral`
**And** the fallback logic is clearly separated from the LLM classification code

**Given** an article's content matches a cached content fingerprint
**When** the cache is retrieved
**Then** the cached `credit_impact` value is returned along with the cached summary
**And** no additional LLM call is made

**Technical Notes:**
- Modify `config/prompts/summarization.yaml` — add `credit_impact` to JSON output schema with enum values and descriptions
- Modify `src/newsanalysis/pipeline/summarizers/article_summarizer.py` — parse `credit_impact` from LLM response, apply fallback
- Modify `src/newsanalysis/services/cache_service.py` — include `credit_impact` in content fingerprint cache read/write
- Add `CreditImpact` enum to `src/newsanalysis/core/enums.py`
- Add `credit_impact` field to `SummaryResponse` Pydantic model

**Files:**
- `config/prompts/summarization.yaml`
- `src/newsanalysis/core/enums.py`
- `src/newsanalysis/pipeline/summarizers/article_summarizer.py`
- `src/newsanalysis/services/cache_service.py`

---

### Story 1.2: Credit Impact Data Persistence

As a **system operator**,
I want **the credit impact classification to be stored in the database**,
So that **the value is available for digest generation, statistics, and future analytics**.

**Acceptance Criteria:**

**Given** the database schema
**When** the migration is applied
**Then** the `articles` table has a new nullable `credit_impact` TEXT column
**And** existing articles without `credit_impact` have NULL values (no errors)

**Given** an article is summarized with a `credit_impact` value
**When** the summary is saved via `ArticleRepository.update_summary()`
**Then** the `credit_impact` value is persisted to the database
**And** the value can be read back via `ArticleRepository` queries

**Given** the Article Pydantic model
**When** an article is loaded from the database
**Then** the `credit_impact` field is populated (or None for legacy articles)
**And** the field uses the `CreditImpact` enum type

**Technical Notes:**
- Add `credit_impact TEXT` column to `articles` table in `schema.sql`
- Add migration logic in `scripts/init_db.py` for existing databases
- Add `credit_impact: Optional[CreditImpact]` to Article model in `article.py`
- Update `ArticleRepository.update_summary()` to write `credit_impact`
- Update `ArticleRepository._row_to_article()` to read `credit_impact`

**Files:**
- `src/newsanalysis/database/schema.sql`
- `scripts/init_db.py`
- `src/newsanalysis/core/article.py`
- `src/newsanalysis/database/repository.py`

---

### Story 1.3: Credit Impact in Digest Pipeline

As a **system operator**,
I want **credit impact to flow through the digest generation pipeline**,
So that **the email formatter and any export format can access the classification**.

**Acceptance Criteria:**

**Given** articles are loaded for digest generation
**When** the digest JSON output is created
**Then** each article object includes a `credit_impact` field
**And** articles without `credit_impact` (legacy) default to `null` in JSON output

**Given** the digest formatter processes articles
**When** an article has `credit_impact = null` (legacy article)
**Then** the system treats it as `neutral` for display purposes
**And** no errors occur during formatting or rendering

**Technical Notes:**
- Update `src/newsanalysis/pipeline/formatters/json_formatter.py` — include `credit_impact` in article serialization
- Update `src/newsanalysis/services/digest_formatter.py` — replace `_determine_risk_level()` usage with `credit_impact` (keeping old logic as fallback)
- Handle null/missing `credit_impact` gracefully throughout

**Files:**
- `src/newsanalysis/pipeline/formatters/json_formatter.py`
- `src/newsanalysis/services/digest_formatter.py`

---

## Epic 2: Visual Credit Risk Communication

**Goal:** Enable analysts to instantly see the credit risk landscape in the daily email digest through color-coded articles, directional icons, smart sorting, and a Risiko-Radar overview of acute risks. After this epic, the email digest is a visual credit intelligence tool.

**FRs covered:** FR-3.1, FR-3.2, FR-3.3, FR-4.1, FR-4.2, FR-4.3
**Priority:** High — Immediately after Epic 1
**Effort:** Medium
**Dependency:** Epic 1 (credit_impact values must be available)

---

### Story 2.1: 4-Level Visual Article Styling

As a **credit analyst**,
I want **each article in the email digest to be visually styled according to its credit impact**,
So that **I can instantly distinguish between acute risks, negative signals, neutral news, and positive developments**.

**Acceptance Criteria:**

**Given** an article with `credit_impact = elevated_risk`
**When** the email is rendered
**Then** the article displays with:
  - Left border: 4px solid `#cc0000` (red)
  - Background: `#fff5f5` (light red)
  - Label: `&#9888; ERHÖHTES RISIKO` in `#cc0000`
  - Title link color: `#990000`

**Given** an article with `credit_impact = negative`
**When** the email is rendered
**Then** the article displays with:
  - Left border: 4px solid `#e67e00` (orange)
  - Background: `#fff8f0` (light orange)
  - Label: `&#9660; Negativ` in `#e67e00`

**Given** an article with `credit_impact = neutral`
**When** the email is rendered
**Then** the article displays with:
  - Left border: 3px solid `#888888` (grey)
  - Background: `#ffffff` (white)
  - Label: `&#9679; Neutral` in `#888888`
  - Only 1 key point displayed (instead of 2)

**Given** an article with `credit_impact = positive`
**When** the email is rendered
**Then** the article displays with:
  - Left border: 4px solid `#2e7d32` (green)
  - Background: `#f0f8f0` (light green)
  - Label: `&#9650; Positiv` in `#2e7d32`

**Given** the email is viewed in Outlook Desktop (Word rendering engine)
**When** Unicode icons are rendered
**Then** all icons (⚠ ▼ ● ▲) display correctly as BMP characters
**And** colors render through inline CSS styles

**Technical Notes:**
- Modify `email_digest.html` — expand `{% if article.risk_level %}` from 2 to 4 cases using `article.credit_impact`
- Replace `risk_level` property with `credit_impact` in template variables
- Update `digest_formatter.py` `_parse_articles()` to pass `credit_impact` instead of `risk_level`
- Limit key_points to 1 for neutral articles: `article.key_points[:1]` vs `[:2]`
- Add dark mode support for new background colors in `<style>` block

**Files:**
- `src/newsanalysis/templates/email_digest.html`
- `src/newsanalysis/services/digest_formatter.py`

---

### Story 2.2: Credit Impact Sorting

As a **credit analyst**,
I want **articles within each topic sorted by credit impact severity**,
So that **the most critical articles always appear first**.

**Acceptance Criteria:**

**Given** a topic group with articles of mixed credit impact levels
**When** the digest is generated
**Then** articles are sorted by:
  1. `credit_impact` priority: `elevated_risk` → `negative` → `neutral` → `positive`
  2. Then by `confidence` descending (existing behavior)
**And** an `elevated_risk` article with 0.75 confidence appears before a `neutral` article with 0.95 confidence

**Technical Notes:**
- Modify `digest_formatter.py` `_parse_articles()` — change sort key to use credit_impact priority map, then confidence
- Define priority map: `{"elevated_risk": 0, "negative": 1, "neutral": 2, "positive": 3}`

**Files:**
- `src/newsanalysis/services/digest_formatter.py`

---

### Story 2.3: Risiko-Radar Section

As a **credit analyst**,
I want **a Risiko-Radar section at the top of the email listing all elevated-risk articles**,
So that **I can see the most critical credit risk signals within 5 seconds of opening the email**.

**Acceptance Criteria:**

**Given** a daily digest with 2 or more articles classified as `elevated_risk`
**When** the email is rendered
**Then** a "⚠ Erhöhte Risiken" section appears between the Executive Summary and the topic-grouped articles
**And** each entry shows: ⚠ icon + company name(s) + short description (summary_title) + topic category in parentheses
**And** entries link to the full article URL

**Given** a daily digest with exactly 1 article classified as `elevated_risk`
**When** the email is rendered
**Then** the Risiko-Radar section still appears with the single entry

**Given** a daily digest with no articles classified as `elevated_risk`
**When** the email is rendered
**Then** the Risiko-Radar section is not displayed (hidden, not "empty")

**Given** an elevated risk article about a company with entities.companies populated
**When** the Risiko-Radar entry is rendered
**Then** the company name(s) appear prominently before the description
**And** format is: `⚠ [Company] — [Summary Title] (Topic)`

**Technical Notes:**
- Modify `digest_formatter.py` — extract `elevated_risk` articles into a separate list for the template
- Pass `risiko_radar_articles` to template context in `format_with_images()`
- Add new template section in `email_digest.html` between Executive Summary and topic articles
- Style consistently with the elevated_risk article styling (red theme)
- Use `{% if risiko_radar_articles %}` to conditionally show/hide

**Files:**
- `src/newsanalysis/templates/email_digest.html`
- `src/newsanalysis/services/digest_formatter.py`

---

## Implementation Order

### Phase 1: Intelligence Layer (Epic 1)

1. **Story 1.1:** LLM Credit Impact Classification (enum, prompt, parser, cache)
2. **Story 1.2:** Credit Impact Data Persistence (DB, model, repository)
3. **Story 1.3:** Credit Impact in Digest Pipeline (JSON output, formatter integration)

**Validation:** Run pipeline with `--limit 5`, verify `credit_impact` values in DB and digest JSON.

### Phase 2: Visual Layer (Epic 2)

4. **Story 2.1:** 4-Level Visual Article Styling (template, 4 color schemes)
5. **Story 2.2:** Credit Impact Sorting (sort priority change)
6. **Story 2.3:** Risiko-Radar Section (new template section, data extraction)

**Validation:** Run `--reset digest --skip-collection`, send test email, verify Outlook rendering.

---

*Generated via BMAD Create Epics & Stories Workflow — 2026-03-14*
