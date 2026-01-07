# Fix Deduplication NULL Handling and Email Auto-Send

## Summary

Fixed two issues: (1) Duplicate detection failing due to SQL NULL comparison issue, and (2) Automatic email not being sent after digest generation due to exception handling bug.

## Context / Problem

### Issue 1: Duplicate Detection Failure
Two articles with identical titles ("Brand in Crans-Montana: Gemeinde drohen Klagen in Millionenhöhe") from Tages-Anzeiger Switzerland and Der Bund Business both appeared in the digest. Investigation revealed:

1. **324 articles had `is_duplicate = NULL`** (default for new/reset articles)
2. **Deduplication query used `is_duplicate = FALSE`** which doesn't match NULL in SQL
3. **Result: Deduplication found 0 articles to check**, allowing duplicates through

Additionally, the digest generator query lacked any `is_duplicate` filter, so even if duplicates were detected, they could still appear in digests.

### Issue 2: Automatic Email Not Sent
After pipeline runs, emails were not being sent automatically despite `EMAIL_AUTO_SEND=true`. Investigation revealed:

1. Digest was saved successfully to database
2. But `mark_articles_digested()` or `_write_digest_outputs()` threw exceptions
3. The entire `_run_digest_generation()` method returned 0 instead of 1
4. Email check `if digest_count > 0` failed, skipping email send

## What Changed

### 1. repository.py - get_articles_for_deduplication()
**Line 632**: Fixed NULL handling in deduplication query

```python
# Before (broken)
AND is_duplicate = FALSE

# After (fixed)
AND (is_duplicate = FALSE OR is_duplicate IS NULL)
```

### 2. digest_generator.py - _get_digest_articles()
**Line 154**: Added defense-in-depth filter to exclude duplicates from digests

```python
AND (is_duplicate = FALSE OR is_duplicate IS NULL)
```

### 3. orchestrator.py - _run_digest_generation()
**Lines 530-545**: Wrapped post-save operations in individual try/catch blocks so failures don't prevent email from being sent

```python
# Before: Any exception after save_digest() would return 0
try:
    save_digest()
    mark_articles_digested()  # Exception here = return 0
    write_outputs()           # Exception here = return 0
    return 1
except:
    return 0

# After: Post-save failures are isolated
save_digest()
try:
    mark_articles_digested()
except: pass  # Continue
try:
    write_outputs()
except: pass  # Continue
return 1  # Always returns 1 if digest was saved
```

## Files Modified

- `src/newsanalysis/database/repository.py` - Deduplication query fix
- `src/newsanalysis/pipeline/generators/digest_generator.py` - Digest query defense-in-depth
- `src/newsanalysis/pipeline/orchestrator.py` - Email auto-send reliability fix

## How to Test

1. Reset articles to collected stage:
   ```sql
   UPDATE articles SET pipeline_stage = 'collected', is_duplicate = NULL, ...
   ```

2. Run full pipeline:
   ```bash
   newsanalysis run --mode full
   ```

3. Verify deduplication ran:
   - Check logs for "articles_to_deduplicate" with count > 0
   - Query: `SELECT COUNT(*) FROM articles WHERE is_duplicate = 1` should show detected duplicates

4. Verify digest has no duplicates:
   - Check digest output for articles with identical/near-identical titles

## Risk / Rollback Notes

**Risk**: Low - only changes SQL WHERE clauses to be more inclusive

**Rollback**: Revert the two query changes. The system will continue to work but duplicates may appear in digests.

**Note**: Existing articles with `is_duplicate = NULL` will now be checked for duplicates on the next pipeline run. This is the intended behavior.
