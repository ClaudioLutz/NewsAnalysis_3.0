---
stepsCompleted: [1]
inputDocuments:
  - '_bmad-output/analysis/brainstorming-session-20260114.md'
  - 'docs/project-documentation/architecture.md'
constraints:
  - 'SQL Server company data enrichment uses mock data (no connection available)'
---

# Creditreform News-Digest Enhancement - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for enhancing the Creditreform News-Digest, transforming it from a "news aggregator" into a "credit intelligence product" for CEO demo.

**The Vision:** "This automatically monitors 35 Swiss news sources, filters for credit-relevant signals, and enriches each article with our own company data."

## Requirements Inventory

### Functional Requirements

```
FR1: Display articles in 2-column newspaper layout (900px container, ~430px columns)
FR2: Show odd articles in full-width format for visual variety
FR3: Generate "Heute in 30 Sekunden" summary with 3 concrete sentences naming specific companies and impacts
FR4: Dynamic email subject line featuring the top story headline
FR5: Enrich articles with Creditreform company data (credit score, payment behavior, watchlist status)
FR6: Display company data chip showing Score, trend arrow, payment days, and CHE UID
FR7: Group articles by company entity when company is identified
FR8: Show "Früher berichtet" links to previous articles about the same company
FR9: Bold company names within summary text using existing entities.companies data
FR10: Add visual hierarchy (colored borders/backgrounds) for high-stakes articles based on severity
FR11: Make source links clickable with "→ Originalartikel" format
FR12: Order topics dynamically by article severity (critical first)
FR13: Hide empty topic categories instead of showing "keine Artikel"
FR14: Show relevance reasoning line ("→ Relevant: Konkursrisiko, Bausektor-Lieferkette")
FR15: Implement cross-day deduplication to avoid duplicate stories across consecutive days
FR16: Normalize company names during summarization for reliable matching
FR17: Support multiple companies per article with compact inline chips (top 3 + "+N more")
```

### Non-Functional Requirements

```
NFR1: Email must render correctly in Outlook (B2B desktop audience)
NFR2: Mobile responsiveness is NOT required (desktop-only audience)
NFR3: Container width: 900px (increased from 600px)
NFR4: Maintain existing pipeline performance (<5 min total processing)
NFR5: Company data enrichment must gracefully handle missing/unavailable data
NFR6: All text output in German (Hochdeutsch)
NFR7: Mock data implementation must be easily replaceable with real SQL Server integration
```

### Additional Requirements (from Architecture)

```
AR1: Email template uses Jinja2 - modifications go to templates/ folder
AR2: Digest generation in Stage 5 (DigestGenerator) - logic changes go there
AR3: Summarization in Stage 4 uses Gemini - prompt changes for entity normalization
AR4: Existing entities.companies field available for company identification
AR5: Classification caching (30-day TTL) must not be broken
AR6: Multi-provider LLM strategy (DeepSeek/Gemini) must be preserved
```

### Cleanup Requirements (Technical Debt)

```
CR1: Remove FTS5 full-text search (dead code with corruption warnings)
CR2: Eliminate express mode (redundant with --skip-X flags)
CR3: Improve summary prompt structure: "Sentence 1: What happened. Sentence 2: Why it matters for credit risk."
```

## FR Coverage Map

| FR | Epic | Story |
|----|------|-------|
| FR1, FR2 | Epic 1 | Story 1.1 |
| FR3 | Epic 1 | Story 1.2 |
| FR4 | Epic 1 | Story 1.3 |
| FR5, FR6, FR16, FR17 | Epic 2 | Story 2.1 |
| FR7, FR8 | Epic 2 | Story 2.2 |
| FR9 | Epic 3 | Story 3.1 |
| FR10, FR12, FR13 | Epic 3 | Story 3.2 |
| FR11 | Epic 3 | Story 3.3 |
| FR14 | Epic 3 | Story 3.4 |
| FR15 | Epic 3 | Story 3.5 |
| CR1, CR2, CR3 | Epic 3 | Story 3.6 |

## Epic List

1. **Epic 1: Look Impressive** - Visual transformation for CEO demo (Hours)
2. **Epic 2: Be Impressive** - Company intelligence integration (Days, mock data)
3. **Epic 3: Polish & Cleanup** - Refinements and technical debt (Hours)

---

## Epic 1: Look Impressive

**Goal:** Transform the digest from "notification feed" into "professional publication" through visual improvements that create immediate "wow" factor for CEO demo.

**Priority:** Highest - This week
**Effort:** Hours

### Story 1.1: 2-Column Newspaper Layout

As a **digest reader**,
I want **articles displayed in a professional 2-column newspaper layout**,
So that **I can scan more content efficiently and the digest feels like a curated publication rather than a feed**.

**Acceptance Criteria:**

**Given** a daily digest with multiple articles
**When** the email is rendered in Outlook
**Then** articles display in 2-column layout (900px container, ~430px columns)
**And** odd-numbered articles within a category span full width
**And** images display as 100px thumbnails in 2-col, 120px in full-width
**And** the layout degrades gracefully if images are missing

**Technical Notes:**
- Modify Jinja2 email template
- Container: 900px (up from 600px)
- Use HTML tables for Outlook compatibility
- Test in Outlook desktop client

---

### Story 1.2: Executive Summary - "Heute in 30 Sekunden"

As an **executive reader**,
I want **a 3-sentence summary at the top naming specific companies and impacts**,
So that **I can decide in 5 seconds whether to read further**.

**Acceptance Criteria:**

**Given** a daily digest with summarized articles
**When** the digest is generated
**Then** a "Heute in 30 Sekunden" section appears at the top
**And** it contains exactly 3 concrete sentences
**And** each sentence names a specific company and specific impact
**And** sentences are actionable (not generic category descriptions)

**Example:**
```
Heute in 30 Sekunden:
1. Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen
2. FINMA verschärft Eigenmittelregeln für Retailbanken
3. Nestlé-Rückruf: Reputationsschaden, aber Finanzen stabil
```

**Technical Notes:**
- Modify DigestGenerator (Stage 5)
- Update meta-analysis prompt to generate specific sentences
- Update email template to display new section

---

### Story 1.3: Dynamic Subject Line

As a **digest recipient**,
I want **the email subject line to feature the top story headline**,
So that **the email stands out in my inbox and I immediately see the most important news**.

**Acceptance Criteria:**

**Given** a daily digest with ranked articles
**When** the email is sent
**Then** the subject line includes the top story headline
**And** format is: "Creditreform News-Digest: [Top Story Headline]"
**And** subject line is truncated appropriately for email clients (~60 chars)

**Technical Notes:**
- Modify email generation logic
- Extract top article title from digest
- Truncate intelligently (don't cut mid-word)

---

## Epic 2: Be Impressive

**Goal:** Integrate Creditreform company intelligence to create unique value proposition - "Our data + news = nobody else has this."

**Priority:** High - Next sprint
**Effort:** Days
**Constraint:** SQL Server uses mock data for this implementation

### Story 2.1: Company Data Enrichment (Mock Implementation)

As a **credit analyst**,
I want **each article enriched with Creditreform company data**,
So that **I can immediately see the credit risk context without manual lookup**.

**Acceptance Criteria:**

**Given** an article mentioning a company in entities.companies
**When** the digest is generated
**Then** a company data chip displays: Score, trend arrow (↑↓), payment days, CHE UID
**And** watchlist flag (⚠) displays if applicable
**And** if company data unavailable, chip shows "Keine Daten" gracefully
**And** multiple companies display as compact chips (top 3 + "+N more" if 4+)

**Mock Data Structure:**
```python
{
    "company_name": "Baltensperger AG",
    "che_uid": "CHE-123.456.789",
    "credit_score": 284,
    "score_trend": -12,  # negative = down
    "payment_days": 67,
    "watchlist": True
}
```

**Technical Notes:**
- Create mock company data service with ~10 sample companies
- Add company lookup during digest generation
- Design service interface for easy replacement with real SQL Server
- Normalize company names using existing entities.companies + fuzzy matching

---

### Story 2.2: Company-Centric Grouping with History

As a **credit analyst**,
I want **articles grouped by company with links to previous coverage**,
So that **I can see developing stories rather than isolated news events**.

**Acceptance Criteria:**

**Given** an article about a company with previous coverage
**When** the digest is rendered
**Then** articles are grouped under company header (if company identified)
**And** "Früher berichtet" section shows previous article headlines with dates
**And** links navigate to previous digest entries (if available)
**And** articles without identified companies display in current format

**Technical Notes:**
- Query historical articles by company name
- Group articles by primary company in digest generation
- Store company associations for historical lookup
- Limit history to last 30 days / 5 articles

---

## Epic 3: Polish & Cleanup

**Goal:** Refine the digest with smaller improvements and eliminate technical debt.

**Priority:** Medium - Future sprint
**Effort:** Hours per story

### Story 3.1: Bold Company Names in Summaries

As a **digest reader**,
I want **company names bolded within summary text**,
So that **I can quickly scan for companies I recognize**.

**Acceptance Criteria:**

**Given** a summary containing company names from entities.companies
**When** the email is rendered
**Then** each company name is wrapped in `<strong>` tags
**And** company names match the normalized form (not original text variations)

**Technical Notes:**
- Post-process summaries in template or digest generation
- Use entities.companies list for matching
- Handle case variations

---

### Story 3.2: Visual Hierarchy for High-Stakes Articles

As a **digest reader**,
I want **critical articles to visually stand out**,
So that **I notice elevated risks immediately**.

**Acceptance Criteria:**

**Given** an article with high severity (bankruptcy, major lawsuit, etc.)
**When** the digest is rendered
**Then** the article displays with visual emphasis (red border, "ELEVATED RISK" label)
**And** high-severity articles float to top of their category
**And** topics with high-severity articles appear before topics without

**Technical Notes:**
- Use confidence score + sentiment from summarization
- Add severity field to article model
- Update template for conditional styling

---

### Story 3.3: Clickable Source Links

As a **digest reader**,
I want **source links to be clickable**,
So that **I can easily access the original article**.

**Acceptance Criteria:**

**Given** an article in the digest
**When** the email is rendered
**Then** source displays as: "NZZ → [Originalartikel](link)"
**And** link opens in new tab/window

**Technical Notes:**
- Template change only
- Ensure link is the original article URL

---

### Story 3.4: Relevance Reasoning Line

As a **digest reader**,
I want **to see why each article was included**,
So that **I understand the filtering logic and trust the selection**.

**Acceptance Criteria:**

**Given** an article in the digest
**When** the email is rendered
**Then** a "→ Relevant:" line shows the classification reasoning
**And** reasoning lists 2-3 keywords (e.g., "Konkursrisiko, Bausektor-Lieferkette")

**Technical Notes:**
- Classification result already includes topic/reasoning
- Expose this in digest model
- Update template to display

---

### Story 3.5: Cross-Day Deduplication

As a **digest reader**,
I want **duplicate stories filtered across consecutive days**,
So that **I don't see the same story from different sources on multiple days**.

**Acceptance Criteria:**

**Given** a story covered yesterday from Source A
**When** Source B publishes the same story today
**Then** Source B's article is marked as duplicate
**And** only genuinely new developments pass through

**Technical Notes:**
- Extend deduplication window beyond single run
- Query recent articles before dedup stage
- May require title similarity check across days

---

### Story 3.6: Technical Debt Cleanup

As a **developer**,
I want **dead code removed and prompts improved**,
So that **the codebase is maintainable and outputs are higher quality**.

**Acceptance Criteria:**

**Given** the current codebase
**When** cleanup is complete
**Then** FTS5 full-text search tables and triggers are removed
**And** express mode is eliminated (--skip-X flags remain)
**And** summary prompt is structured: "Sentence 1: What happened. Sentence 2: Why it matters."

**Technical Notes:**
- Schema migration to drop FTS5
- Remove express mode from CLI
- Update summarization.yaml prompt

---

## Implementation Order

### Phase 1: Look Impressive (CEO Demo - This Week)
1. Story 1.1: 2-Column Newspaper Layout
2. Story 1.3: Dynamic Subject Line
3. Story 1.2: Executive Summary

### Phase 2: Be Impressive (Next Sprint)
4. Story 2.1: Company Data Enrichment (Mock)
5. Story 2.2: Company-Centric Grouping

### Phase 3: Polish (Future)
6. Story 3.1 - 3.6 (prioritize as needed)

---

*Generated via BMAD Create Epics & Stories Workflow*
