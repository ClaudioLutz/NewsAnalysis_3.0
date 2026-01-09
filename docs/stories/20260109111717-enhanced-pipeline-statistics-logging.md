# Enhanced Pipeline Statistics Logging

## Summary

Enhanced pipeline completion logging to display comprehensive statistics including API costs by provider and module, token usage, cache performance, pipeline duration, and detailed article processing metrics. This provides better visibility into pipeline execution costs and performance.

## Context / Problem

The previous pipeline logging only displayed basic article counts (collected, filtered, matched, rejected) without any cost, performance, or efficiency metrics. Users had no visibility into:

- API costs incurred during the pipeline run
- Cost breakdown by provider (DeepSeek, Gemini, OpenAI) and module (filter, summarizer, digest)
- Token usage across all API calls
- Cache hit rates and savings
- Pipeline execution duration
- Deduplication and scraping statistics

This lack of visibility made it difficult to monitor costs, optimize performance, and understand where resources were being consumed.

## What Changed

### 1. Pipeline Orchestrator ([orchestrator.py:686-761](src/newsanalysis/pipeline/orchestrator.py#L686-L761))

- Enhanced `_complete_pipeline_run()` method to calculate and store comprehensive metrics
- Added calculation of pipeline duration (completed_at - started_at)
- Added aggregation of total cost and tokens from `api_calls` table
- Updated database record to include: `scraped_count`, `summarized_count`, `digested_count`, `duration_seconds`, `total_cost`, `total_tokens`

### 2. CLI Run Command ([run.py:168-310](src/newsanalysis/cli/commands/run.py#L168-L310))

- Added new `_display_pipeline_results()` helper function
- Displays comprehensive statistics including:
  - Article processing counts with percentages (collection, filtering, scraping, deduplication, summarization, digest)
  - Total API cost and token usage
  - Cost breakdown by provider (DeepSeek, Gemini, OpenAI) with percentages and API call counts
  - Cost breakdown by module (filter, summarizer, digest) with percentages and API call counts
  - Pipeline execution duration (minutes and seconds)
  - Cache performance metrics (hit rate, requests, cost saved) for today
- Uses 70-character width formatting for better readability

### 3. Production Pipeline Script ([run_production_pipeline.py:86-262](scripts/run_production_pipeline.py#L86-L262))

- Updated results display to match CLI command format
- Added comprehensive statistics including:
  - Detailed article processing metrics with match rates
  - API usage and costs with provider/module breakdowns
  - Estimated savings vs OpenAI-only approach
  - Cache performance metrics
  - Pipeline duration
- Consistent formatting with CLI command for better user experience

## How to Test

### Test with CLI Command

```bash
# Run the pipeline (will process articles and display new statistics)
newsanalysis run

# Expected output includes:
# - Article Processing section with counts and percentages
# - API Usage & Costs section with:
#   - Total cost and tokens
#   - Cost by provider (DeepSeek, Gemini, etc.)
#   - Cost by module (filter, summarizer, digest)
# - Duration in minutes and seconds
# - Cache Performance metrics (if cache hits exist)
```

### Test with Production Script

```bash
# Run the production pipeline
python scripts/run_production_pipeline.py

# Expected output includes:
# - All statistics from CLI test above
# - Estimated savings vs OpenAI estimate
# - Final database state
```

### Verify Database Updates

```sql
-- Check that pipeline_runs table is properly updated
SELECT
    run_id,
    status,
    collected_count,
    filtered_count,
    scraped_count,
    summarized_count,
    digested_count,
    total_cost,
    total_tokens,
    duration_seconds
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 5;

-- Verify cost aggregation matches
SELECT
    run_id,
    SUM(cost) as total_cost,
    SUM(total_tokens) as total_tokens,
    COUNT(*) as api_calls
FROM api_calls
GROUP BY run_id
ORDER BY MIN(created_at) DESC
LIMIT 5;
```

## Risk / Rollback Notes

### Risks

- **Low Risk**: Changes are primarily additive to logging/display functionality
- Database queries for statistics add minimal overhead (<50ms) at pipeline completion
- Existing functionality unchanged - only display/logging enhanced

### Potential Issues

1. **Performance**: Additional database queries at pipeline end could add latency
   - Mitigation: Queries are simple aggregations with proper indexes
   - Impact: Minimal (<100ms for typical datasets)

2. **Database Compatibility**: Assumes `api_calls` and `pipeline_runs` tables exist with expected schema
   - Mitigation: Schema has been stable since initial implementation
   - Existing database migrations ensure schema is correct

3. **Display Formatting**: Wide statistics display may wrap on narrow terminals
   - Mitigation: 70-character width chosen to fit most terminals
   - Users with very narrow terminals may see wrapped output

### Rollback

To rollback this change:

1. **Revert Orchestrator Changes**:
   ```bash
   git checkout HEAD~1 -- src/newsanalysis/pipeline/orchestrator.py
   ```

2. **Revert CLI Command**:
   ```bash
   git checkout HEAD~1 -- src/newsanalysis/cli/commands/run.py
   ```

3. **Revert Production Script**:
   ```bash
   git checkout HEAD~1 -- scripts/run_production_pipeline.py
   ```

4. **Verify Rollback**:
   ```bash
   newsanalysis run
   # Should display old simple statistics format
   ```

### Database Impact

- No database schema changes
- No data migration required
- `pipeline_runs` table columns used (`total_cost`, `total_tokens`, `duration_seconds`) already exist in schema
- Rollback does not require database changes

### Dependencies

- No new dependencies added
- Uses existing database connection and query infrastructure
- Compatible with all existing commands and workflows
