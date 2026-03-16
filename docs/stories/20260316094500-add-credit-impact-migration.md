## Summary

Added missing database migration (v4 → v5) to create the `credit_impact` column on the `articles` table. Without this migration, the pipeline crashed with "No item with that key" when reading articles from an existing database.

## Context / Problem

The credit impact classification feature was added on 2026-03-14 (code + schema.sql), but no migration was included for existing databases. New databases got the column from schema.sql, but the production database (created before v5) lacked it. The `_row_to_article` method tried to access `row["credit_impact"]`, which raised a KeyError, aborting the entire pipeline after collection.

## What Changed

- `src/newsanalysis/database/migrations.py`:
  - Added `migrate_v4_to_v5()` — adds `credit_impact TEXT` column to `articles` table
  - Bumped `CURRENT_SCHEMA_VERSION` from 4 to 5
  - Updated schema version history in module docstring

## How to Test

```bash
# Verify migration runs on existing database
python -c "
import sqlite3
from newsanalysis.database.migrations import run_migrations, get_schema_version
conn = sqlite3.connect('news.db')
run_migrations(conn)
print('Version:', get_schema_version(conn))
cursor = conn.execute('PRAGMA table_info(articles)')
cols = [r[1] for r in cursor.fetchall()]
print('credit_impact exists:', 'credit_impact' in cols)
conn.close()
"

# Run pipeline to confirm it no longer crashes
python -m newsanalysis.cli.main run --limit 5
```

## Risk / Rollback Notes

- Low risk: `ALTER TABLE ADD COLUMN` is safe in SQLite and does not affect existing data (new column defaults to NULL).
- Rollback: The column can be left in place harmlessly; no data depends on it yet.
