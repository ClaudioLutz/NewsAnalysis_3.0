---
stepsCompleted: [step-01-init, step-02-discovery, step-03-problem, step-04-solution, step-05-features, step-06-ux, step-07-technical, step-08-scope, step-09-metrics, step-10-risks, step-11-complete]
inputDocuments:
  - _bmad-output/analysis/brainstorming-session-20260314.md
  - docs/project-documentation/project-overview.md
  - docs/project-documentation/architecture.md
  - docs/project-documentation/data-models.md
  - docs/index.md
workflowType: 'prd'
lastStep: 11
documentCounts:
  briefs: 0
  research: 4
  brainstorming: 6
  projectDocs: 5
---

# Product Requirements Document — Credit Impact Classification

**Author:** Claudio
**Date:** 2026-03-14
**Project:** NewsAnalysis 3.0 (Creditreform Switzerland)

---

## 1. Executive Summary

NewsAnalysis 3.0 currently classifies news articles as relevant/irrelevant with a topic category, but lacks a **creditworthiness impact assessment**. Analysts receive a daily email digest where all articles look visually identical (except a basic rule-based "elevated risk" flag for certain topic categories). This makes it impossible to quickly distinguish between articles that signal acute credit risk, negative trends, neutral industry news, or positive developments.

This PRD defines the **Credit Impact Classification** feature: a 4-level creditworthiness assessment (Erhöhtes Risiko, Negativ, Neutral, Positiv) integrated into the existing summarization pipeline, with visual differentiation in the daily email digest and a new Risiko-Radar overview section.

### What Makes This Special

- **Bonität, not Sentiment:** This is explicitly a creditworthiness assessment, not general sentiment analysis. The classification answers: *"What does this article mean for the credit rating of the affected company?"*
- **Near-Zero Marginal Cost:** By integrating into the existing summarization LLM call (adding one JSON field), the feature costs practically nothing extra per article.
- **Immediate Visual Impact:** Analysts see the credit risk landscape at a glance — with color-coded articles and a Risiko-Radar section at the top of every email.

### Project Classification

| Attribute | Value |
|-----------|-------|
| **Project Type** | Feature addition (brownfield) |
| **Domain** | Credit risk intelligence / financial services |
| **Complexity** | Medium — touches multiple pipeline layers but follows established patterns |
| **Context** | Extending a production system serving Creditreform Switzerland analysts daily |

---

## 2. Success Criteria

### User Success

- Analysts can identify credit-risk-relevant articles **within 5 seconds** of opening the email digest
- All four credit impact categories are visually distinguishable without reading the full article
- The Risiko-Radar section provides a complete overview of acute risk articles at a glance

### Business Success

- Creditreform analysts report improved speed in identifying actionable credit risk signals
- Feature enables future company-level risk trend analysis (data collection begins immediately)
- No increase in operational costs (LLM API spending stays within existing budget)

### Technical Success

- `credit_impact` classification is returned by the LLM for ≥95% of summarized articles
- Rule-based fallback activates correctly when LLM does not return a value
- Email rendering is correct across Outlook Desktop (Word engine), Outlook Web, and mobile
- No regression in existing pipeline functionality (all tests pass)

### Measurable Outcomes

| Metric | Target | How to Measure |
|--------|--------|----------------|
| LLM return rate | ≥95% of articles have `credit_impact` | DB query on `credit_impact IS NOT NULL` |
| Visual correctness | 4 distinct styles render in Outlook | Manual QA on test email |
| Pipeline speed | No measurable slowdown (<5% increase) | `pipeline_runs.duration_seconds` comparison |
| API cost | ≤$0.10/month additional | `api_calls` cost tracking |

---

## 3. Product Scope

### MVP (V1) — This PRD

1. **LLM Classification** — `credit_impact` field added to summarization prompt with 4 categories
2. **Data Model** — New enum, DB column, model field, repository support
3. **Email Visual Differentiation** — 4-level color/icon system in the email template
4. **Sorting** — Articles sorted by `credit_impact` priority before confidence within topic groups
5. **Risiko-Radar** — Compact section at top of email listing all "Erhöhtes Risiko" articles

### Growth Features (V1.1)

- **Meta-Analysis Integration** — Executive Summary includes credit impact distribution ("3x Erhöhtes Risiko, 5x Negativ...")
- **Compact Neutral Display** — Neutral articles show 1 key point instead of 2 to reduce visual noise

### Vision (V2+)

- **Company Intelligence** — Aggregate credit impact per company over time; trend detection
- **Entity Deduplication** — Normalize company names ("UBS AG" = "UBS" = "UBS Group AG")
- **Analyst Feedback Loop** — Allow analysts to correct LLM assessments for continuous improvement

---

## 4. User Journeys

### Journey 1: Morning Triage (Primary Path)

A Creditreform analyst opens the daily email digest at 8:00 AM. The first thing they see is the **Risiko-Radar** at the top: "⚠ 2 Artikel mit erhöhtem Risiko" — one about a bankruptcy filing and one about a FINMA license revocation. Both show the affected company name and topic. The analyst clicks through to the bankruptcy article immediately, knowing this requires urgent attention. Below the Risiko-Radar, they scan the topic-grouped articles. Orange-bordered ▼ Negativ articles catch their eye next — a revenue decline at a mid-sized client. Green-bordered ▲ Positiv articles about a rating upgrade confirm positive developments they can note. Grey ● Neutral articles they skim quickly, knowing these are informational only.

**Capabilities revealed:** Risiko-Radar rendering, 4-level visual distinction, credit impact sorting, article linking.

### Journey 2: Edge Case — No Elevated Risk Today

On a quiet news day, there are no "Erhöhtes Risiko" articles. The Risiko-Radar section either shows "Keine erhöhten Risiken heute" or is omitted entirely. The analyst proceeds directly to the topic-grouped articles, where a few Negativ and several Neutral articles are displayed with their respective visual styling.

**Capabilities revealed:** Graceful handling of empty Risiko-Radar, consistent visual styling across all categories.

### Journey 3: LLM Fallback Scenario

An article about an insolvency filing is summarized, but the LLM response doesn't include `credit_impact` (malformed response, timeout, etc.). The system falls back to the existing rule-based logic: topic `insolvency_bankruptcy` + confidence ≥ 0.85 → `elevated_risk`. The article still appears correctly styled with the red border and ⚠ label. The analyst never notices the difference.

**Capabilities revealed:** Fallback mechanism, seamless degradation, existing behavior preserved.

### Journey Requirements Summary

| Capability Area | Revealed By |
|-----------------|-------------|
| LLM-based credit impact classification | Journeys 1, 3 |
| 4-level visual email rendering | Journeys 1, 2 |
| Risiko-Radar section | Journeys 1, 2 |
| Credit impact sorting | Journey 1 |
| Rule-based fallback | Journey 3 |
| Empty state handling | Journey 2 |

---

## 5. Data Pipeline Requirements

### Pipeline Integration Overview

| Aspect | Decision |
|--------|----------|
| **Classification stage** | Summarization (Stage 4) — full article content available |
| **LLM provider** | Gemini (existing summarization provider) |
| **API cost impact** | Near-zero — one additional JSON field in existing prompt |
| **Caching** | `credit_impact` cached in `content_fingerprints` table alongside existing summary cache |

### Credit Impact Category Definitions

These definitions are embedded in the summarization prompt to ensure LLM consistency:

| Category | Enum Value | Definition | Examples |
|----------|------------|------------|----------|
| **Erhöhtes Risiko** | `elevated_risk` | Acute, immediate threat to solvency or business operations | Bankruptcy, debt enforcement, license revocation, criminal proceedings |
| **Negativ** | `negative` | Deterioration of creditworthiness or business situation, not immediately existential | Revenue decline, layoffs, rating downgrade, regulatory warning |
| **Neutral** | `neutral` | No discernible impact on creditworthiness | Industry news, personnel changes without impact, general market reports |
| **Positiv** | `positive` | Improvement of creditworthiness, stability, or growth | Revenue growth, new investment, rating upgrade, regulatory relief |

### Fallback Logic

When the LLM does not return a `credit_impact` value:

1. Check if article topic is in `HIGH_RISK_TOPICS` (`insolvency_bankruptcy`, `credit_risk`, `business_scams`, `ecommerce_fraud`)
2. If yes AND confidence ≥ 0.85 → `elevated_risk`
3. Otherwise → `neutral` (safe default)

---

## 6. Email Presentation Requirements

### Visual Specification

| Category | Icon (HTML Entity) | Border Color | Background | Text Color | Label |
|----------|-------------------|-------------|------------|------------|-------|
| Erhöhtes Risiko | `&#9888;` (⚠) | 4px `#cc0000` | `#fff5f5` | `#cc0000` | ⚠ ERHÖHTES RISIKO |
| Negativ | `&#9660;` (▼) | 4px `#e67e00` | `#fff8f0` | `#e67e00` | ▼ Negativ |
| Neutral | `&#9679;` (●) | 3px `#888888` | `#ffffff` | `#888888` | ● Neutral |
| Positiv | `&#9650;` (▲) | 4px `#2e7d32` | `#f0f8f0` | `#2e7d32` | ▲ Positiv |

### Design Constraints

- **Outlook compatibility:** Unicode icons must be BMP (Basic Multilingual Plane) — no emoji, no ZWJ sequences
- **Color blindness:** All categories use icons + text labels as a second visual channel beyond color
- **Table-based layout:** All styling via inline CSS, no external stylesheets (Outlook Word engine)

### Risiko-Radar Section

Placed **between the Executive Summary and the topic-grouped articles**:

- Heading: "⚠ Erhöhte Risiken" (or similar)
- Lists all articles with `credit_impact = elevated_risk`
- Each entry shows: Icon + Company name + Short description + Topic category
- If no elevated risk articles: Section is hidden or shows "Keine erhöhten Risiken heute"

### Article Sorting

Within each topic group, articles are sorted by:
1. `credit_impact` priority: `elevated_risk` → `negative` → `neutral` → `positive`
2. Then by `confidence` descending (existing behavior)

---

## 7. Project Scoping & Phased Development

### MVP Strategy

The MVP focuses on **end-to-end integration** of one new field through all pipeline layers. The principle is: get `credit_impact` from LLM → store it → display it. No analytics, no aggregation, no feedback loops in V1.

### MVP Feature Set (V1)

| # | Feature | Components | Effort |
|---|---------|------------|--------|
| 1 | Summarization prompt extension | `summarization.yaml` — add `credit_impact` to JSON schema with definitions | Small |
| 2 | Data model + DB migration | `enums.py` (new enum), `article.py` (new field), `schema.sql` (new column), `repository.py` (read/write), `cache_service.py` (cache field) | Small |
| 3 | Email template — 4 visual levels | `email_digest.html` — extend `{% if article.risk_level %}` to 4 cases | Medium |
| 4 | Digest formatter — sorting + logic | `digest_formatter.py` — new `_determine_credit_impact()`, sorting logic, fallback | Medium |
| 5 | Risiko-Radar section | `email_digest.html` + `digest_formatter.py` — new section, data preparation | Small |

### Post-MVP Features

| Phase | Feature | Dependency |
|-------|---------|------------|
| V1.1 | Meta-Analysis credit impact distribution in Executive Summary | V1 data available |
| V1.1 | Compact neutral article display (1 key point) | V1 template changes |
| V2 | Company credit impact aggregation over time | V1 data accumulation + entity queries |
| V2 | Company name deduplication | Entity normalization logic |
| V3 | Analyst feedback loop for LLM correction | UI/workflow design needed |

### Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM inconsistent classification | Medium | Medium | Clear prompt definitions with examples; fallback logic |
| Outlook rendering issues | Low | High | Use proven BMP Unicode entities (already used in template); QA testing |
| Pipeline performance regression | Low | Medium | Single additional JSON field — negligible token increase |
| Breaking existing email layout | Low | High | Incremental template changes; test with `--reset digest --skip-collection` |

---

## 8. Functional Requirements

### FR Area 1: Credit Impact Classification

- **FR-1.1:** The system can classify each summarized article with a `credit_impact` value of `elevated_risk`, `negative`, `neutral`, or `positive` based on the article's impact on the creditworthiness of affected companies.
- **FR-1.2:** The system can include `credit_impact` as a field in the LLM summarization prompt's JSON output schema with clear category definitions and examples.
- **FR-1.3:** The system can fall back to rule-based credit impact determination when the LLM does not return a `credit_impact` value.
- **FR-1.4:** The system can cache `credit_impact` alongside other summary fields in the content fingerprint cache.

### FR Area 2: Data Persistence

- **FR-2.1:** The system can store `credit_impact` as a column on the `articles` table in the database.
- **FR-2.2:** The system can read and write `credit_impact` through the `ArticleRepository`.
- **FR-2.3:** The system can represent `credit_impact` as a Python enum (`CreditImpact`) in the domain model.
- **FR-2.4:** The system can include `credit_impact` in the digest JSON output for downstream consumption.

### FR Area 3: Email Visual Presentation

- **FR-3.1:** The system can render each article in the email digest with a visual style (border color, background color, icon, label) corresponding to its `credit_impact` value.
- **FR-3.2:** The system can display all four credit impact categories with distinct, Outlook-compatible visual styling using BMP Unicode icons.
- **FR-3.3:** The system can sort articles within each topic group by `credit_impact` priority (elevated_risk first, then negative, neutral, positive) before sorting by confidence.

### FR Area 4: Risiko-Radar

- **FR-4.1:** The system can display a Risiko-Radar section at the top of the email digest listing all articles classified as `elevated_risk`.
- **FR-4.2:** Each Risiko-Radar entry can show the company name(s), a short description, and the topic category.
- **FR-4.3:** The system can hide the Risiko-Radar section or display an appropriate message when no `elevated_risk` articles exist.

### FR Area 5: Backward Compatibility

- **FR-5.1:** The system can process articles that were summarized before `credit_impact` was introduced (treating missing values as `neutral` or applying fallback logic).
- **FR-5.2:** The system can maintain existing pipeline behavior for all stages not directly modified by this feature.

---

## 9. Non-Functional Requirements

### Performance

- **NFR-1:** Adding `credit_impact` to the summarization prompt must not increase pipeline execution time by more than 5%.
- **NFR-2:** The email digest generation time must not increase noticeably (< 1 second additional).

### Compatibility

- **NFR-3:** The email template must render correctly in Outlook Desktop (Word rendering engine), Outlook Web (OWA), and Outlook Mobile.
- **NFR-4:** All Unicode icons used must be from the Basic Multilingual Plane (BMP) to ensure cross-client compatibility.
- **NFR-5:** The feature must support dark mode rendering via existing `@media (prefers-color-scheme: dark)` styles.

### Maintainability

- **NFR-6:** The credit impact category definitions must be configurable in the summarization YAML prompt file, not hardcoded in Python.
- **NFR-7:** The fallback logic must be clearly separated from the LLM-based classification logic.

### Data Integrity

- **NFR-8:** Existing articles without `credit_impact` must not cause errors in digest generation or email rendering.
- **NFR-9:** The `credit_impact` field must be nullable in the database to support backward compatibility.

---

## 10. Appendix

### Input Documents

- [Brainstorming Session 2026-03-14](_bmad-output/analysis/brainstorming-session-20260314.md) — Primary design input
- [Project Architecture](docs/project-documentation/architecture.md) — System context
- [Data Models](docs/project-documentation/data-models.md) — Schema reference

### Files Affected (Implementation Reference)

| File | Change Type |
|------|------------|
| `src/newsanalysis/core/enums.py` | Add `CreditImpact` enum |
| `src/newsanalysis/core/article.py` | Add `credit_impact` field to Article model |
| `config/prompts/summarization.yaml` | Add `credit_impact` to JSON output schema |
| `src/newsanalysis/database/schema.sql` | Add `credit_impact` column to articles table |
| `src/newsanalysis/database/repository.py` | Read/write `credit_impact` |
| `src/newsanalysis/pipeline/summarizers/article_summarizer.py` | Parse `credit_impact` from LLM response |
| `src/newsanalysis/services/digest_formatter.py` | 4-level visual logic, sorting, Risiko-Radar data |
| `src/newsanalysis/templates/email_digest.html` | 4-level template, Risiko-Radar section |
| `src/newsanalysis/services/cache_service.py` | Cache `credit_impact` in content fingerprints |
| `src/newsanalysis/pipeline/formatters/json_formatter.py` | Include `credit_impact` in digest JSON |
