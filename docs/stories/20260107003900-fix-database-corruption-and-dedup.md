# Fix Database Corruption, Migration System, and Deduplication

## Summary

Fixed multiple critical pipeline issues: FTS trigger database corruption, missing schema migration system, broken semantic deduplication, and digest date filtering. The pipeline now runs reliably from start to finish.

## Context / Problem

The pipeline was failing with multiple interconnected issues:

1. **Database corruption**: "database disk image is malformed" errors during summarization stage
2. **Schema updates not applied**: New columns added to schema.sql weren't being applied to existing databases
3. **Deduplication not working**: Semantic duplicate detection silently failing, allowing duplicate articles in digest
4. **Digest generation failing**: Date mismatch causing "No summarized articles found" error

Root cause analysis revealed:
- FTS triggers firing on UPDATE operations were corrupting the FTS5 virtual table
- No migration system existed to update existing databases when schema changed
- DeepSeek API requires "json" keyword in prompt for JSON response format
- DeepSeek returning different field names than expected (`duplicate` vs `is_duplicate`)
- Digest generator filtering by `published_at` date missed articles published yesterday

## What Changed

### Schema Version System
- **Modified**: `src/newsanalysis/database/schema.sql`
  - Added `schema_info` table to track schema version
  - Updated to schema version 3
  - Disabled FTS triggers (cause of corruption)

### Migration System
- **New**: `src/newsanalysis/database/migrations.py`
  - Added `CURRENT_SCHEMA_VERSION` constant
  - Added `get_schema_version()`, `set_schema_version()` functions
  - Added `migrate_v1_to_v2()` for deduplication columns
  - Added `migrate_v2_to_v3()` to drop FTS triggers
  - Added `run_migrations()` to apply pending migrations

- **Modified**: `src/newsanalysis/database/connection.py`
  - Added import for `run_migrations`
  - Call `run_migrations()` on connect for existing databases

- **Modified**: `src/newsanalysis/database/__init__.py`
  - Export `run_migrations`

### Deduplication Fixes
- **Modified**: `config/prompts/deduplication.yaml`
  - Added "You must respond with a JSON object" to system prompt (DeepSeek requirement)
  - Added explicit field name instructions in user prompt (`is_duplicate`, `confidence`, `reason`)

### Digest Generation Fix
- **Modified**: `src/newsanalysis/pipeline/generators/digest_generator.py`
  - Removed date filtering in `_get_digest_articles()`
  - Now gets all summarized articles not yet included in a digest

## How to Test

1. Delete existing database:
   ```bash
   rm -f news.db news.db-wal news.db-shm
   ```

2. Run full pipeline:
   ```bash
   newsanalysis run --mode full
   ```

3. Verify:
   - No "database disk image is malformed" errors
   - Deduplication finds duplicate groups (check logs for "duplicate_group_found")
   - Digest generated with deduplicated article count
   - Email preview works: `newsanalysis email --preview -r test@example.com`

4. Test migration on existing database:
   ```bash
   # Create v2 database, then run pipeline - should migrate to v3
   python -c "import sqlite3; c=sqlite3.connect('news.db'); c.execute('CREATE TABLE IF NOT EXISTS schema_info(id INTEGER PRIMARY KEY, version INTEGER, applied_at TIMESTAMP, description TEXT)'); c.execute('INSERT INTO schema_info(version,applied_at) VALUES(2, datetime())')"
   newsanalysis run --mode full
   # Check logs for "applying_migration" from v2 to v3
   ```

## Risk / Rollback Notes

**Low risk** - Changes are additive and backward-compatible:
- Migration system handles databases at any version
- FTS table preserved (only triggers disabled)
- Prompt changes improve reliability

To rollback:
- Revert schema.sql to re-enable FTS triggers (not recommended)
- Revert deduplication.yaml to original prompts
- Revert digest_generator.py to date-based filtering

Potential issues:
- FTS full-text search will not work until triggers re-enabled or index manually rebuilt
- Old databases need migration run at least once

## Files Changed

- `src/newsanalysis/database/schema.sql` - Schema v3 with disabled FTS triggers
- `src/newsanalysis/database/migrations.py` - New migration system
- `src/newsanalysis/database/connection.py` - Run migrations on connect
- `src/newsanalysis/database/__init__.py` - Export migrations
- `config/prompts/deduplication.yaml` - Fixed DeepSeek prompts
- `src/newsanalysis/pipeline/generators/digest_generator.py` - Removed date filter
