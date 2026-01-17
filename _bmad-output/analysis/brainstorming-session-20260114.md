---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Improvements to news_analysis_3.0 pipeline'
session_goals: 'Generate a prioritized improvement list for CEO demo'
selected_approach: 'ai-recommended'
techniques_used: ['SCAMPER', 'Reverse Brainstorming', 'Constraint Mapping']
ideas_generated: 17
context_file: '_bmad/bmm/data/project-context-template.md'
---

# Brainstorming Session: News Analysis Pipeline Improvements

**Facilitator:** Claudio
**Date:** 2026-01-14
**Duration:** ~45 minutes
**Techniques Used:** SCAMPER, Reverse Brainstorming, Constraint Mapping

---

## Executive Summary

This session generated **17 concrete improvement ideas** for the Creditreform News-Digest, prioritized into a 2-phase implementation plan targeting a CEO demo.

**The transformation:** From "news aggregator" → "credit intelligence product"

**The CEO pitch:**
> "This automatically monitors 35 Swiss news sources, filters for credit-relevant signals, and enriches each article with our own company data. A story about Baltensperger doesn't just show the news - it shows their credit score, payment behavior, and that we've reported on them 4 times this month. No manual research needed."

---

## Phase 1: Look Impressive (Hours)

| ID | Improvement | Effort | Impact |
|----|-------------|--------|--------|
| S1 | 2-column newspaper layout | Hours | Visual "wow", professional publication feel |
| A2 | "Heute in 30 Sekunden" - 3 concrete sentences | Hours | Executives see the point in 5 seconds |
| RB4 | Dynamic subject line with top story | Minutes | Feels polished, stands out in inbox |

## Phase 2: Be Impressive (Days)

| ID | Improvement | Effort | Impact |
|----|-------------|--------|--------|
| C1 | Company data enrichment (scores, payment behavior) | Days | "Our data + news = nobody else has this" |
| R1 | Company-centric grouping with history links | Days | "It tracks the story developing. Smart." |

---

## All Ideas by Technique

### SCAMPER Method

#### S - Substitute

**S1: Replace single-column feed with 2-column newspaper layout**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Creditreform News-Digest              ← 900px        │
├─────────────────────────────────────────────────────────────────────────┤
│  Wichtige Themen          │  Regulatorische Updates                     │
├─────────────────────────────────────────────────────────────────────────┤
│                         INSOLVENZEN                                     │
├──────────────────────────────────┬──────────────────────────────────────┤
│ 📰 Title                         │ 📰 Title                             │
│ Source                           │ Source                               │
│ Summary text here...             │ Summary text here...                 │
│ • Key point                      │ • Key point                          │
├──────────────────────────────────┴──────────────────────────────────────┤
│ 📰 Title (full width - odd article)                                     │
│ Source                                                                  │
│ Summary text, can be longer since we have full width...                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Specifications:**
- Container: 900px (up from 600px)
- Columns: ~430px each
- Images: 100px thumbnails in 2-col, 120px in full-width
- Odd articles: Full width, more prominent
- Mobile: Ignore (B2B desktop/Outlook audience)

**Rationale:** "More editorial, less feed" - transforms from notification into publication. Respects reader time by enabling scanning vs. forced scrolling.

---

#### C - Combine

**C1: Combine news articles with Creditreform company intelligence**

```
┌─────────────────────────────────────────────────┐
│ 📰 Stahlbaufirma Baltensperger droht Konkurs    │
│ NZZ Recent                                      │
├─────────────────────────────────────────────────┤
│ 🏢 Baltensperger AG · CHE-123.456.789           │
│ Score: 284 (↓12) · Zahlung: 67 Tage · ⚠ Watchlist│
├─────────────────────────────────────────────────┤
│ Die Verhandlungen zwischen dem Zoo Zürich...    │
└─────────────────────────────────────────────────┘
```

**Data to expose:**
- Credit score + trend arrow (↑↓)
- Payment behavior (days)
- Watchlist flag
- CHE UID

**Multiple companies UX:** Compact inline chips, top 3 + "(+2 more)" if 4+

**Matching strategy:**
- Entity extraction already exists (`entities.companies`)
- Hybrid matching: exact → CHE UID → fuzzy → LLM normalization
- Add `normalized_companies` field during summarization

**Impact:** Transforms digest from news feed → actionable credit intelligence. Unique value proposition - competitors don't have Creditreform's proprietary data.

---

#### A - Adapt

**A1: Bold company names in summary text**

| Current | Adapted |
|---------|---------|
| Die Verhandlungen zwischen dem Zoo Zürich und der Stahlbaufirma Baltensperger sind gescheitert. | Die Verhandlungen zwischen dem Zoo Zürich und der **Baltensperger AG** sind gescheitert. |

- Readers scan for names they recognize
- Zero code change - template/prompt adjustment
- Uses existing `entities.companies` to know what to bold

---

**A2: Replace generic "Wichtige Themen" with 3 concrete sentences**

| Current | Adapted |
|---------|---------|
| Wichtige Themen:<br>• Insolvenzen im Bausektor<br>• Regulatorische Entwicklungen<br>• Zahlungsverhalten | **Heute in 30 Sekunden:**<br>1. Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen<br>2. FINMA verschärft Eigenmittelregeln für Retailbanken<br>3. Nestlé-Rückruf: Reputationsschaden, aber Finanzen stabil |

- Specific companies, specific impact, actionable
- Executive reads 3 lines → decides whether to scroll
- Newsletter DNA: Name specifics, not categories

---

#### M - Modify

**M1: Minimize key points bullets**

- **Current:** Every article has 3 bullet points that restate the summary
- **Proposal:** Drop bullets by default, only include for complex multi-fact stories
- **Impact:** Reduces vertical space, eliminates redundancy

---

**M2: Minimize meta-sections**

- **Current:** Three sections (Wichtige Themen, Regulatorische Updates, Markt-Einblicke) of generic bullets
- **Proposal:** Collapse to one "Heute in 30 Sekunden" with 3 concrete sentences (see A2)
- **Impact:** Less scrolling past filler to reach real content

---

**M3: Magnify high-stakes articles with visual hierarchy**

```
┌─────────────────────────────────────────────────────────────────┐
│ █ ELEVATED RISK                                                 │  ← Red border, bold
│ Baltensperger AG droht Konkurs                                  │
│ ...                                                             │
├─────────────────────────────────────────────────────────────────┤
│ │ Bernina prüft Verlagerung nach Thailand                       │  ← Standard blue
│ │ ...                                                           │
├─────────────────────────────────────────────────────────────────┤
│ │ Investoren warnen vor Wohnschutzinitiativen                   │  ← Standard
│ │ ...                                                           │
└─────────────────────────────────────────────────────────────────┘
```

- Use confidence score + sentiment to drive visual weight
- Border color, header weight, background tint
- **Principle:** "Not every article is equal - the digest should reflect that visually"

---

**M4: Magnify source links - make clickable**

| Current | Improved |
|---------|----------|
| NZZ Recent | NZZ → [Originalartikel](link) |

- Small change, reduces friction to original article
- Readers can skim headlines, jump to source later

---

**M5: Modify topic ordering - dynamic by severity**

- **Current:** Fixed order (Insolvenzen, Bonität, Regulierung, etc.)
- **Proposal:**
  - Topics with high-severity articles float to top
  - Empty topics hidden (not "keine Artikel")
  - Most critical article always first, regardless of category
- **Impact:** Critical information never buried by arbitrary ordering

---

#### E - Eliminate

**E1: Eliminate FTS5 full-text search**

```sql
-- Currently in schema:
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(...)
-- Triggers DISABLED, comments warn of corruption
```

- Dead code with corruption warnings
- Remove table + all related schema
- If search needed later, rebuild properly

---

**E2: Eliminate express mode**

```python
# Currently:
type=click.Choice(["full", "express", "export"])
```

- Three execution modes when `--skip-X` flags exist
- Redundant abstraction
- One way to run things > three ways to confuse

---

#### R - Reverse

**R1: Reverse organizing principle from topic-centric → entity-centric**

```
┌─────────────────────────────────────────────────┐
│ BALTENSPERGER AG                                │  ← Entity header
├─────────────────────────────────────────────────┤
│ Konkurs droht wegen fehlender liquider Mittel   │
│ NZZ · Die Verhandlungen zwischen dem Zoo...     │
├─────────────────────────────────────────────────┤
│ Früher berichtet:                               │
│ · Liquiditätsengpass bestätigt (08.01)          │
│ · Verhandlungen mit Zoo stocken (12.01)         │
└─────────────────────────────────────────────────┘
```

**Logic:**
```python
if article.entities.companies:
    show company header
    show today's article
    if past_articles_exist:
        show "Früher berichtet" links
else:
    show article only (current format)
```

**Impact:** Transforms isolated news events into developing narratives. Reader sees story arc, not just today's headline.

---

### Reverse Brainstorming

*"How would you sabotage the digest to make it fail?"*

**RB1: Bury critical news through arbitrary ordering**
- Sabotage: Alphabetize topics, insolvency buried between routine categories
- Flip: Severity-based ordering (→ M5) ✓

**RB2: Bloat summaries with unnecessary words**
- Sabotage: 150 words when 40 would do
- Flip: Enforce tight summaries with word cap

**RB3: Length constraint without structure constraint**
- Current prompt: `"summary": "1-2 sentence summary (max 50 words)"`
- Improved prompt: `"summary": "Sentence 1: What happened. Sentence 2: Why it matters for credit risk. Max 50 words total."`

**RB4: Send timing buried in the flood**
- Sabotage: Send at exactly 8:00 AM with 15 other newsletters
- Flip: Send at 8:17 AM (odd time, after the rush) or A/B test send times

**RB5: Opaque filtering erodes trust**
- Sabotage: No explanation why articles appear, seems random
- Flip: Add "→ Relevant: Arbeitsplatzabbau, Produktionsverlagerung" reasoning line

**RB6: Duplicate stories across days**
- Sabotage: Same story from different source on consecutive days
- Flip: Cross-day deduplication awareness (not just within single run)

---

### Constraint Mapping

**Constraints Identified:**

| Constraint | Status |
|------------|--------|
| Time | Side project, occasional hours |
| SQL Server access | Unblocked |
| Audience | You + colleague → CEO demo |
| Outlook rendering | Fixed constraint |
| Risk tolerance | Low risk, can break things |

**Prioritization Framework for CEO Demo:**

1. **Visual "wow"** - Looks professional, not hacked-together
2. **Unique value** - Something competitors can't do
3. **Clear story** - "This saves X hours / catches Y risks"

---

## Implementation Roadmap

### Phase 1: Look Impressive (This Week)

| Task | Effort | Files to Modify |
|------|--------|-----------------|
| 2-column newspaper layout | Hours | Email template (Jinja2) |
| Dynamic subject line with top story | Minutes | Email generation logic |
| "Heute in 30 Sekunden" summary | Hours | Digest generation, template |

### Phase 2: Be Impressive (Next Sprint)

| Task | Effort | Files to Modify |
|------|--------|-----------------|
| Company data enrichment | Days | New SQL Server integration, template |
| Entity matching logic | Days | Summarization pipeline |
| Company-centric grouping | Days | Digest generation logic |
| History links ("Früher berichtet") | Days | Query logic, template |

### Phase 3: Polish (Future)

| Task | Effort |
|------|--------|
| Visual hierarchy for high-stakes articles | Hours |
| Bold company names in summaries | Hours |
| Cross-day deduplication | Hours |
| Send time optimization | Minutes |
| Eliminate dead code (FTS5, express mode) | Hours |
| Structured summary prompt | Minutes |

---

## Master Improvement List

| ID | Improvement | Category | Effort | Phase |
|----|-------------|----------|--------|-------|
| S1 | 2-column newspaper layout | Layout | Hours | 1 |
| C1 | Company data enrichment | Integration | Days | 2 |
| A1 | Bold company names in summaries | Template | Hours | 3 |
| A2 | "Heute in 30 Sekunden" top summary | Content | Hours | 1 |
| M1 | Drop key points bullets (most articles) | Template | Hours | 3 |
| M2 | Collapse meta-sections | Template | Hours | 1 |
| M3 | Visual hierarchy for high-stakes | Template | Hours | 3 |
| M4 | Clickable source links | Template | Hours | 3 |
| M5 | Dynamic topic ordering by severity | Logic | Hours | 3 |
| E1 | Eliminate FTS5 dead code | Cleanup | Hours | 3 |
| E2 | Eliminate express mode | Cleanup | Hours | 3 |
| R1 | Company-centric grouping + history | Logic | Days | 2 |
| RB3 | Structured summary prompt | Prompt | Minutes | 3 |
| RB4 | Optimize send timing (8:17 AM) | Config | Minutes | 3 |
| RB5 | "Relevant:" reasoning line | Template | Hours | 3 |
| RB6 | Cross-day deduplication | Logic | Hours | 3 |
| - | Dynamic subject line | Template | Minutes | 1 |

---

## Design Principles Discovered

1. **"More editorial, less feed"** - Transform from notification into publication
2. **"Not every article is equal"** - Visual hierarchy should reflect importance
3. **"Name specifics, not categories"** - "Baltensperger AG vor Konkurs" > "Insolvenzen im Bausektor"
4. **"Reduce sameness, create hierarchy"** - Critical info should visually shout
5. **"If code has warnings not to use it, delete it"** - No dead code

---

## The Full Vision

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Creditreform News-Digest                    900px    │
│                        14. Januar 2026                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Heute in 30 Sekunden:                                                   │
│ 1. Baltensperger AG steht vor Konkurs - Bausektor-Lieferanten betroffen │
│ 2. FINMA verschärft Eigenmittelregeln für Retailbanken                  │
│ 3. Nestlé-Rückruf: Reputationsschaden, aber Finanzen stabil             │
├─────────────────────────────────────────────────────────────────────────┤
│ █ ELEVATED RISK                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ BALTENSPERGER AG                           CHE-123.456.789              │
│ Score: 284 (↓12) · Zahlung: 67 Tage · ⚠ Watchlist                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Konkurs droht wegen fehlender liquider Mittel                           │
│ NZZ → Originalartikel                                                   │
│                                                                         │
│ Die Verhandlungen zwischen dem Zoo Zürich und der **Baltensperger AG**  │
│ sind gescheitert. Das Unternehmen kämpft seit Monaten mit               │
│ Liquiditätsproblemen.                                                   │
│                                                                         │
│ → Relevant: Konkursrisiko, Bausektor-Lieferkette                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Früher berichtet:                                                       │
│ · Liquiditätsengpass bestätigt (08.01)                                  │
│ · Verhandlungen mit Zoo stocken (12.01)                                 │
├──────────────────────────────────┬──────────────────────────────────────┤
│ BERNINA AG                       │ SWISS LOGISTICS GMBH                 │
│ Score: 412 · Zahlung: 34 Tage    │ Score: 523 · Zahlung: 28 Tage        │
├──────────────────────────────────┼──────────────────────────────────────┤
│ Produktion wird nach Thailand    │ Expansion in deutsche Märkte         │
│ verlagert                        │ angekündigt                          │
│ NZZ → Originalartikel            │ Handelszeitung → Originalartikel     │
│                                  │                                      │
│ Bis zu 40 Mitarbeitende...       │ Das Unternehmen plant...             │
└──────────────────────────────────┴──────────────────────────────────────┘
```

---

## Session Metadata

**Techniques Applied:**
- SCAMPER Method (Substitute, Combine, Adapt, Modify, Eliminate, Reverse)
- Reverse Brainstorming (sabotage → flip)
- Constraint Mapping (prioritization for CEO demo)

**Session Outcome:** 17 improvement ideas → 2-phase implementation plan

**Next Action:** Implement Phase 1 (2-column layout, dynamic subject line, top summary)

---

*Generated via BMAD Brainstorming Workflow · 2026-01-14*
