# Duplicate Detection Analysis: Intra-Day Runs

This document analyzes how the news analysis pipeline handles duplicate articles across multiple same-day runs (e.g., 8:30 AM and 1:00 PM).

## Overview

The pipeline uses a **two-level deduplication strategy**:

1. **URL-based deduplication** (fast, exact-match) - Prevents the same URL from being collected twice
2. **Semantic/LLM-based deduplication** (comprehensive) - Groups articles covering the same story from different sources

## Level 1: URL-Based Deduplication

### How It Works

When articles are collected from RSS feeds, each article URL goes through normalization and hashing:

```
Original URL → Normalized URL → SHA-256 Hash (url_hash)
```

**Normalization removes** ([text_utils.py](../src/newsanalysis/utils/text_utils.py)):
- UTM tracking parameters (`utm_source`, `utm_medium`, etc.)
- Social media tracking (`fbclid`, `gclid`, etc.)
- URL fragments (`#section`)
- Trailing slashes
- Case normalization (domain lowercased)

**Example:**
```
https://Reuters.com/article/tesla?utm_source=twitter&ref=homepage#comments
    ↓ normalized ↓
https://reuters.com/article/tesla
    ↓ SHA-256 ↓
a7f3b2c1d4e5... (64-char hash)
```

### Database Constraint

The `url_hash` column has a `UNIQUE` constraint in the articles table:

```sql
url_hash TEXT UNIQUE NOT NULL
```

### Collection Logic

In [repository.py:72-74](../src/newsanalysis/database/repository.py#L72-L74):

```python
# Check if article already exists by URL hash
if self._article_exists(article.url_hash):
    logger.debug("article_already_exists", url_hash=article.url_hash)
    continue  # Skip - already in database
```

### Intra-Day Run Behavior

| Scenario | 8:30 AM Run | 1:00 PM Run |
|----------|-------------|-------------|
| New article appears in RSS | Collected & saved | Skipped (url_hash exists) |
| Same article, URL unchanged | Collected & saved | Skipped (url_hash exists) |
| Same article, new tracking params | Collected & saved | Skipped (normalized hash matches) |
| New article from same source | Collected & saved | Collected & saved |

**Key insight**: URL-based dedup is **immediate** - the second run never re-collects articles from the first run if URLs match.

---

## Level 2: Semantic/LLM-Based Deduplication

### Purpose

Detect when **different sources** publish articles about the **same story** with different headlines and URLs.

**Example:**
```
Reuters:   "Tesla Q4 Earnings Beat Expectations"    → url_hash: abc123
Bloomberg: "Tesla Reports Strong Q4 Results"       → url_hash: def456
CNBC:      "Elon Musk's Tesla Exceeds Forecasts"   → url_hash: ghi789
```

All three are about the same event but have different URLs.

### How It Works

The `DuplicateDetector` ([duplicate_detector.py](../src/newsanalysis/pipeline/dedup/duplicate_detector.py)) runs after scraping:

1. **Time Grouping**: Articles within a 48-hour window are grouped together
2. **Pairwise Comparison**: All article pairs within a time group are compared via LLM
3. **Clustering**: Uses Union-Find algorithm to transitively group duplicates
4. **Canonical Selection**: Picks one article per group (lowest `feed_priority`)
5. **Marking**: Non-canonical articles marked with `is_duplicate = TRUE`

### LLM Comparison

The DeepSeek LLM compares article titles and returns structured JSON:

```json
{
  "is_duplicate": true,
  "confidence": 0.92,
  "reason": "Both articles report Tesla's Q4 earnings beating expectations"
}
```

**Threshold**: Articles are only marked as duplicates if `confidence >= 0.75`

### Canonical Article Selection

Within a duplicate group, the **canonical** article is selected by:
1. **Lowest `feed_priority`** (1 = government > 2 = financial > 3 = general)
2. **Earliest `collected_at`** as tiebreaker

Only the canonical article gets summarized; duplicates are skipped.

### Database Schema

```sql
-- In articles table:
is_duplicate BOOLEAN DEFAULT FALSE,
canonical_url_hash TEXT,  -- Points to canonical article if duplicate

-- Tracking tables:
duplicate_groups (
    canonical_url_hash TEXT,
    confidence REAL,
    duplicate_count INTEGER,
    detected_at TIMESTAMP,
    run_id TEXT
)

duplicate_members (
    group_id INTEGER,
    duplicate_url_hash TEXT,
    comparison_confidence REAL
)
```

---

## Intra-Day Run Scenarios

### Scenario 1: Same Article, Same URL (Both Runs)

**8:30 AM:**
- Reuters article "Tesla Earnings" collected
- URL hash: `abc123`
- Article saved to database

**1:00 PM:**
- Same Reuters article still in RSS feed
- URL hash: `abc123` computed
- `_article_exists(abc123)` returns `True`
- **Article skipped** - no duplicate

**Result**: Single article in database, no dedup needed

---

### Scenario 2: Same Story, Different Sources (Same Run)

**8:30 AM:**
- Reuters "Tesla Earnings" collected (hash: `abc123`)
- Bloomberg "Tesla Q4 Results" collected (hash: `def456`)
- Both saved to database
- Semantic dedup runs:
  - Compares Reuters vs Bloomberg
  - LLM returns `confidence: 0.88`
  - Reuters selected as canonical (priority 2, earlier)
  - Bloomberg marked as `is_duplicate = TRUE`

**Result**: Only Reuters gets summarized

---

### Scenario 3: Same Story, Different Sources (Different Runs)

**8:30 AM:**
- Reuters "Tesla Earnings" collected (hash: `abc123`)
- Scraped, summarized, digested

**1:00 PM:**
- Bloomberg "Tesla Q4 Results" collected (hash: `def456`)
- Scraped
- Semantic dedup runs:
  - Compares Bloomberg vs Reuters
  - LLM returns `confidence: 0.85`
  - Reuters already exists, has higher priority
  - **Bloomberg marked as duplicate** → skipped for summarization

**Result**: Bloomberg not re-summarized, links to Reuters as canonical

---

### Scenario 4: Different Stories About Same Company

**8:30 AM:**
- "Tesla Q4 Earnings Beat Expectations" (hash: `abc123`)

**1:00 PM:**
- "Tesla Recalls 500,000 Vehicles" (hash: `xyz789`)

**Semantic dedup:**
- LLM compares titles
- Returns `is_duplicate: false, confidence: 0.95`
- Reason: "Different events - earnings vs recall"

**Result**: Both articles summarized independently

---

## Time Window Behavior

The 48-hour time window affects which articles are compared:

```
Day 1 08:00 - Article A collected
Day 1 13:00 - Article B collected (within 48h → compared with A)
Day 2 09:00 - Article C collected (within 48h → compared with A and B)
Day 3 10:00 - Article D collected (outside 48h from A → NOT compared with A)
```

### Edge Case: Article Revived After Gap

If a story is revived weeks later with fresh coverage, the 48-hour window means old articles **won't** be compared with new ones. This is intentional - old and new coverage may have meaningful differences.

---

## Query: Articles Skipped Due to Deduplication

To see which articles were marked as duplicates:

```sql
SELECT
    a.title,
    a.source,
    a.collected_at,
    a.canonical_url_hash,
    c.title as canonical_title,
    c.source as canonical_source
FROM articles a
LEFT JOIN articles c ON a.canonical_url_hash = c.url_hash
WHERE a.is_duplicate = TRUE
ORDER BY a.collected_at DESC;
```

To see duplicate groups for a specific run:

```sql
SELECT
    dg.canonical_url_hash,
    dg.confidence,
    dg.duplicate_count,
    a.title as canonical_title,
    a.source as canonical_source
FROM duplicate_groups dg
JOIN articles a ON dg.canonical_url_hash = a.url_hash
WHERE dg.run_id = '20260121_083000_abc12345'
ORDER BY dg.detected_at;
```

---

## Summary: What Happens in Two Runs

| Time | Event | Action |
|------|-------|--------|
| 08:30 | Run starts | Pipeline run #1 begins |
| 08:30 | RSS collection | 50 articles found |
| 08:30 | URL dedup | 45 new, 5 already exist → 45 saved |
| 08:31 | Filtering | 30 matched, 15 rejected |
| 08:35 | Scraping | 28 scraped, 2 failed |
| 08:40 | Semantic dedup | 3 duplicate groups found, 5 articles marked as dupes |
| 08:45 | Summarization | 23 articles summarized |
| 08:50 | Digest | Email sent |
| | | |
| 13:00 | Run starts | Pipeline run #2 begins |
| 13:00 | RSS collection | 55 articles found |
| 13:00 | URL dedup | **10 new** (45 from AM already exist) → 10 saved |
| 13:01 | Filtering | 7 matched, 3 rejected |
| 13:05 | Scraping | 6 scraped, 1 failed |
| 13:08 | Semantic dedup | 2 new groups found, **1 article matches AM canonical** |
| 13:12 | Summarization | 4 articles summarized |
| 13:15 | Digest | Updated digest sent |

---

## Performance Considerations

### URL Deduplication
- **O(1)** lookup per article (hash index)
- Negligible overhead

### Semantic Deduplication
- **O(n²)** comparisons within time groups
- Each comparison = 1 LLM API call
- Uses DeepSeek (cost-efficient)
- Max 10 concurrent calls

### Mitigation
- Time grouping reduces comparisons (only compare within 48h window)
- Union-Find provides O(α(n)) amortized union operations
- Results cached in database (same pairs not re-compared)

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Confidence threshold | 0.75 | `orchestrator.py:105` |
| Time window | 48 hours | `orchestrator.py:106` |
| Max concurrent LLM calls | 10 | `orchestrator.py:557` |
| Feed priority values | 1-3 | `config/feeds/*.yaml` |

---

## Logging

The pipeline logs deduplication events at these points:

- `detecting_duplicates`: Number of articles being checked
- `comparing_candidate_pairs`: Number of pairs to compare
- `articles_compared`: Individual comparison results (DEBUG level)
- `duplicate_group_found`: Groups detected with confidence
- `duplicate_detection_complete`: Summary statistics
- `duplicate_groups_saved`: Database persistence

Example log output:
```
INFO  duplicate_detection_complete groups_found=3 duplicates_found=5 articles_to_summarize=23
INFO  duplicate_group_found canonical_title="Tesla Q4..." canonical_source=Reuters duplicate_count=2 avg_confidence=0.89
```
