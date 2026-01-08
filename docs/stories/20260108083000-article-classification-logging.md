# Add Article Classification Logging

## Summary

Changed per-article classification logs from DEBUG to INFO level so article titles and decisions appear in production logs.

## Context / Problem

The logs showed generic DeepSeek API calls (`deepseek_request`, `deepseek_response_success`) without article-specific details, making it difficult to see which articles were classified and what decisions were made.

## What Changed

- `src/newsanalysis/pipeline/filters/ai_filter.py`:
  - Line 120: Changed `logger.debug` to `logger.info` for `article_classified` event
  - Line 159: Changed `logger.debug` to `logger.info` for `using_cached_classification` event

## How to Test

1. Run the news analysis pipeline: `newsanalysis run`
2. Check logs for per-article entries:
   ```
   [info] article_classified title="..." match=True confidence=0.92
   [info] using_cached_classification title="..." match=True
   ```

## Risk / Rollback Notes

- Low risk: Only changes log verbosity, no functional changes
- May increase log volume in high-traffic scenarios
- Rollback: Revert the two lines back to `logger.debug`
