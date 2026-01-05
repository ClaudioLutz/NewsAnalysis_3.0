## Summary

Adversarial code review fixes addressing 12 issues identified in the multi-provider LLM implementation. Removed OpenAI dependencies entirely, fixed critical bugs, added retry logic with exponential backoff, and improved German language output.

## Context / Problem

Code review of the multi-provider LLM implementation (commits 1e657f8, a2b5f84) identified several issues:

1. **CRITICAL**: DigestGenerator hardcoded `model="gpt-4o-mini"` when using Gemini client
2. **CRITICAL**: Provider factory caching bug caused fallback client to be cached under wrong provider key
3. **CRITICAL**: No runtime retry/fallback on 429/5xx errors
4. **MEDIUM**: German date formatting used English month names (system locale dependent)
5. **MEDIUM**: No retry logic in DeepSeek/Gemini clients for transient failures
6. **MEDIUM**: Gemini API system instruction handling was suboptimal (concatenated into user message)
7. **MEDIUM**: Variable naming inconsistency (`openai_client` vs `llm_client`)
8. **LOW**: Import placement, empty response checks, style issues

Additionally, OpenAI is no longer used as a provider, so all OpenAI fallback references needed removal.

## What Changed

### Critical Fixes

- **digest_generator.py**:
  - Renamed `self.openai_client` to `self.llm_client`
  - Removed hardcoded `model="gpt-4o-mini"` parameter (uses client's default)

- **provider_factory.py**:
  - Removed `LLMProvider.OPENAI` enum value
  - Changed fallbacks: DeepSeek ↔ Gemini (no OpenAI)
  - Fixed caching bug: now caches under `actual_provider` not requested provider

### Retry Logic

- **deepseek_client.py**:
  - Added `MAX_RETRIES = 3` and `RETRY_DELAY_BASE = 1.0` constants
  - Moved `json` import to top of file
  - Added exponential backoff retry loop for 429/5xx errors

- **gemini_client.py**:
  - Added same retry configuration
  - Added retry logic to both new and old API paths
  - Added empty response checks before JSON parsing
  - Fixed system instruction handling: now uses `config_dict["system_instruction"]` properly

### German Language Fixes

- **german_formatter.py**:
  - Added `GERMAN_MONTHS` dict with German month names (Januar, Februar, etc.)
  - Changed date formatting to use German months (locale-independent)

### OpenAI Removal

- **orchestrator.py**:
  - Removed `OpenAIClient` import
  - Removed OpenAI client initialization

## How to Test

```bash
# Run linting
ruff check src/newsanalysis/integrations/ src/newsanalysis/pipeline/

# Run type checking
mypy src/newsanalysis/integrations/ src/newsanalysis/pipeline/

# Test pipeline (requires API keys)
newsanalysis run --limit 5

# Verify German date output
newsanalysis export --format german

# Verify retry logging (simulate rate limit by running concurrent requests)
# Check logs for "deepseek_retry" or "gemini_retry" messages
```

## Risk / Rollback Notes

- **Low risk**: Changes are bug fixes and improvements, no new features
- **Retry logic**: Uses conservative settings (3 retries, 1-4s delays)
- **German dates**: Locale-independent, won't break on different server configurations
- **OpenAI removal**: Ensure DeepSeek and Gemini API keys are configured before deploying

To rollback:
- Revert this commit
- Re-add `LLMProvider.OPENAI` if OpenAI fallback is needed
