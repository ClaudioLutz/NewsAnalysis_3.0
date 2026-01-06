# Fix FTS Trigger Corruption Detection

## Summary

Added FTS-specific corruption detection to the database connection manager. Standard SQLite `integrity_check` and `quick_check` can pass while FTS triggers are corrupted, causing "database disk image is malformed" errors during UPDATE operations.

## Context / Problem

The pipeline was failing repeatedly with "database disk image is malformed" errors during the summarization stage. Despite passing standard integrity checks, UPDATE operations on the articles table were failing because the FTS5 triggers were corrupted.

Root cause analysis:
1. `PRAGMA integrity_check` returned "ok"
2. `PRAGMA quick_check` returned "ok"
3. Direct FTS table queries worked
4. Direct article table UPDATEs (non-FTS columns) worked
5. UPDATEs that triggered FTS update triggers failed with corruption error

This type of corruption is not detected by SQLite's standard integrity checks but manifests when triggers fire during UPDATE operations.

## What Changed

- **Modified**: [connection.py](../../src/newsanalysis/database/connection.py)
  - Enhanced `_check_and_repair_database()` to perform FTS-specific validation
  - Added `_has_fts_tables()` helper to detect FTS tables
  - Added `_test_fts_triggers()` to perform a test UPDATE that exercises FTS triggers
  - If FTS trigger test fails with "malformed" error, auto-recovery via SQLite backup API is triggered

The fix proactively detects FTS corruption at database connection time and automatically repairs using SQLite's `backup()` API, which creates a clean copy of the database.

## How to Test

1. Corrupt the FTS triggers manually (for testing):
   ```python
   import sqlite3
   c = sqlite3.connect('news.db')
   # Simulate corruption scenario
   ```

2. Run the pipeline:
   ```bash
   newsanalysis run
   ```

3. Verify logs show FTS corruption detection and auto-recovery:
   ```
   fts_trigger_corruption_detected
   attempting_database_recovery
   database_recovered_successfully
   ```

4. Verify pipeline completes successfully with digest generated.

## Risk / Rollback Notes

**Low risk** - This change only adds additional integrity checking and uses SQLite's built-in backup API for recovery.

Potential issues:
- If `_test_fts_triggers()` incorrectly detects corruption (false positive), it will trigger unnecessary recovery
- Recovery creates a backup file, consuming disk space

To rollback:
- Revert the changes to `connection.py`
- The database files are preserved (corrupted versions backed up with `.db.corrupted` suffix)

## Research Sources

- [SQLite Forum: FTS5 error: database disk image is malformed](https://sqlite.org/forum/forumpost/f61937c9b25e2a5e)
- [SQLite Forum: FTS5 Error after 'delete'](https://sqlite.org/forum/info/1a249403ce8eba7d)
