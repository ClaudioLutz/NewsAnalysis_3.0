# Fix Duplicate Sources Display in Email Digest

## Summary

Fixed an issue where duplicate article sources were not displayed below article titles in the email digest. When articles from multiple sources cover the same story, the "Quellen:" (sources) line now correctly shows all sources with links.

## Context / Problem

The semantic deduplication system correctly identifies duplicate articles from different sources and marks them with `is_duplicate = TRUE` and `canonical_url_hash` pointing to the canonical article. However, the email digest only showed the canonical source, not the additional sources from duplicates.

**Expected behavior**: Article from Reuters with duplicates from Bloomberg and NZZ should display:
```
Article Title
Quellen: Reuters, Bloomberg, NZZ
```

**Actual behavior**: Only showed:
```
Article Title
Reuters
```

## Root Cause Analysis

The issue was in `_get_digest_articles()` in `digest_generator.py`:

1. **Deduplication** runs before summarization and marks duplicates with `is_duplicate = TRUE`
2. **Summarization** query explicitly filters out duplicates: `AND (is_duplicate = FALSE OR is_duplicate IS NULL)`
3. Only **canonical articles** get summarized → reach `pipeline_stage = 'summarized'`
4. **Digest query** fetches only `pipeline_stage = 'summarized'` articles → **misses duplicates**
5. `_group_duplicate_articles()` receives **no duplicate articles** to group
6. **Result**: `duplicate_sources` stays empty, template shows single source only

```
Articles collected
     ↓
Articles scraped (pipeline_stage = 'scraped')
     ↓
Deduplication marks some as is_duplicate = TRUE
     ↓
Summarization SKIPS is_duplicate = TRUE articles
     ↓
Canonicals reach pipeline_stage = 'summarized'
Duplicates STAY at pipeline_stage = 'scraped'  ← Problem!
     ↓
Digest query fetches pipeline_stage = 'summarized'
     ↓
_group_duplicate_articles() gets NO duplicates to merge
```

## What Changed

### Modified File

**`src/newsanalysis/pipeline/generators/digest_generator.py`** - `_get_digest_articles()` method

The method now:
1. Fetches canonical (summarized) articles as before
2. **NEW**: Collects url_hashes of all canonical articles
3. **NEW**: Executes second query to fetch duplicate articles that point to those canonicals
4. Combines both sets before passing to `_group_duplicate_articles()`

```python
# Step 2: Fetch duplicate articles that point to these canonicals
canonical_hashes = [a.url_hash for a in canonical_articles if a.url_hash]

if canonical_hashes:
    placeholders = ",".join("?" * len(canonical_hashes))
    duplicate_query = f"""
        SELECT * FROM articles
        WHERE is_duplicate = TRUE
        AND canonical_url_hash IN ({placeholders})
    """
    # ... fetch and convert duplicates ...

# Step 3: Combine canonical and duplicate articles for grouping
all_articles = canonical_articles + duplicate_articles
```

### New Log Events

- `duplicate_articles_fetched`: Shows how many canonical and duplicate articles were fetched
- Enhanced `articles_grouped_and_clustered`: Now includes `canonical_count` and `duplicate_count`

## How to Test

1. **Regenerate digest:**
   ```bash
   python -m newsanalysis.cli.main run --reset digest --skip-collection
   ```

2. **Check logs for successful grouping:**
   ```
   "canonical_count": 20, "duplicate_count": 7, "event": "duplicate_articles_fetched"
   "canonical_count": 20, "duplicate_count": 7, "event": "duplicate_grouping_complete"
   ```

3. **Verify email displays multiple sources:**
   - Open received email
   - Find articles that had duplicates
   - Confirm "Quellen: Source1, Source2, ..." appears below title

4. **Query database to find articles with duplicates:**
   ```sql
   SELECT a1.title, a1.source as canonical_source, a2.source as duplicate_source
   FROM articles a1
   JOIN articles a2 ON a1.url_hash = a2.canonical_url_hash
   WHERE a2.is_duplicate = TRUE
   ORDER BY a1.title;
   ```

## Risk / Rollback Notes

### Risks

1. **Performance**: Additional query for duplicates
   - Mitigated: Uses IN clause with url_hashes, indexed column
   - Impact: Minimal, typically < 100 duplicates

2. **Memory**: Loading duplicate articles into memory
   - Mitigated: Duplicates are lightweight (no full content needed for display)
   - Impact: Negligible

### Rollback

Revert the changes to `_get_digest_articles()` to restore original single-query behavior:

```python
# Remove duplicate fetching logic
# Restore: all_articles = canonical_articles
```

No database changes required - this fix only affects how existing data is queried and displayed.
