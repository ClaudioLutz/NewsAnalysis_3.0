# Add Semantic Duplicate Detection

## Summary

Added LLM-powered semantic duplicate detection to prevent summarizing the same news story from different sources. The system detects when multiple articles cover the same event (e.g., Tesla earnings reported by Reuters, Bloomberg, and CNBC) and only summarizes the canonical article from the highest-priority source.

## Context / Problem

The news analysis pipeline collects articles from multiple news sources. When a major event occurs, it's often reported by many outlets with different titles and wording. Previously, each article would be summarized separately, leading to:

- Redundant API costs (paying to summarize the same story multiple times)
- Cluttered digests with duplicate information
- Wasted processing time

Example: "Tesla Q4 Earnings Beat Expectations" (Reuters), "Tesla Reports Strong Fourth Quarter Results" (Bloomberg), and "Elon Musk's Tesla Exceeds Analyst Forecasts" (CNBC) are all the same story.

## What Changed

### New Components

1. **DuplicateDetector class** (`src/newsanalysis/pipeline/dedup/duplicate_detector.py`)
   - Uses LLM (DeepSeek, cheapest option) to compare article title pairs
   - Groups articles by time window (48h default) before comparing
   - Uses Union-Find algorithm for transitive clustering (A=B, B=C → A=B=C)
   - Selects canonical article based on feed priority (1=govt > 2=financial > 3=general)

2. **Deduplication prompt config** (`config/prompts/deduplication.yaml`)
   - System prompt explaining duplicate detection criteria
   - User prompt template for comparing two articles

3. **Database schema updates** (`src/newsanalysis/database/schema.sql`)
   - Added `is_duplicate` and `canonical_url_hash` columns to `articles` table
   - Added `duplicate_groups` table to track duplicate clusters
   - Added `duplicate_members` table to track group membership

4. **Repository methods** (`src/newsanalysis/database/repository.py`)
   - `save_duplicate_groups()`: Persists duplicate clusters and marks duplicates
   - `get_articles_for_deduplication()`: Fetches scraped articles for checking
   - Updated `get_articles_for_summarization()`: Excludes duplicates

5. **Article model update** (`src/newsanalysis/core/article.py`)
   - Added `is_duplicate: bool` and `canonical_url_hash: Optional[str]` fields

6. **Pipeline orchestrator integration** (`src/newsanalysis/pipeline/orchestrator.py`)
   - Added Stage 3.5 (deduplication) between scraping and summarization
   - Added `deduplicated` and `duplicates_found` stats tracking

7. **Unit tests** (`tests/unit/test_duplicate_detector.py`)
   - Tests for response models, time windowing, clustering, and detection

### Pipeline Flow (Updated)

```
Collection → Filtering → Scraping → [NEW] Deduplication → Summarization → Digest
```

## How to Test

1. **Run unit tests:**
   ```bash
   pytest tests/unit/test_duplicate_detector.py -v
   ```

2. **Run full pipeline with duplicate articles:**
   ```bash
   python -m newsanalysis.cli run --mode full
   ```
   Check logs for `stage_deduplication_complete` with `groups` and `duplicates` counts.

3. **Verify in database:**
   ```sql
   -- Check marked duplicates
   SELECT title, source, is_duplicate, canonical_url_hash
   FROM articles
   WHERE is_duplicate = TRUE;

   -- Check duplicate groups
   SELECT dg.*, COUNT(dm.id) as member_count
   FROM duplicate_groups dg
   LEFT JOIN duplicate_members dm ON dg.id = dm.group_id
   GROUP BY dg.id;
   ```

4. **Manual verification:**
   - Collect articles from multiple sources covering the same story
   - Verify only canonical article is summarized
   - Verify duplicate articles have `canonical_url_hash` pointing to canonical

## Risk / Rollback Notes

### Risks

1. **False positives**: LLM might incorrectly mark different stories as duplicates
   - Mitigated by: 0.75 confidence threshold, strict prompt instructions
   - Monitor: Check duplicate groups for obviously different articles

2. **False negatives**: Same story might not be detected as duplicate
   - Acceptable: Better to summarize twice than miss information
   - Monitor: Check digest for obviously duplicate summaries

3. **Increased API costs in short term**: More LLM calls during deduplication
   - Expected: Cost savings from avoided summarization should outweigh
   - Monitor: Track `api_calls` table for `module='dedup'`

4. **Database migration needed**: New columns and tables
   - SQLite will auto-create on schema initialization
   - Existing articles won't have `is_duplicate` set (defaults to FALSE)

### Rollback

1. Remove deduplication stage from orchestrator:
   ```python
   # Comment out in orchestrator.py:
   # if not self.pipeline_config.skip_summarization:
   #     dedup_stats = await self._run_deduplication()
   ```

2. Update `get_articles_for_summarization()` to remove duplicate check:
   ```sql
   -- Remove this condition:
   AND (is_duplicate = FALSE OR is_duplicate IS NULL)
   ```

3. Database cleanup (optional):
   ```sql
   UPDATE articles SET is_duplicate = FALSE, canonical_url_hash = NULL;
   DROP TABLE IF EXISTS duplicate_members;
   DROP TABLE IF EXISTS duplicate_groups;
   ```
