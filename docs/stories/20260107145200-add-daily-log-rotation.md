# Add Daily Log Rotation with 30-Day Retention

## Summary

Added file logging with daily rotation and 30-day retention. Logs are now written to the `logs/` directory in human-readable console format alongside console output.

## Context / Problem

Previously, logs were only written to stdout/console with no persistent storage. This made it difficult to review historical logs for debugging and auditing purposes.

## What Changed

- **[logging.py](src/newsanalysis/utils/logging.py)**: Added `TimedRotatingFileHandler` with:
  - Daily rotation (`when="midnight"`)
  - 30-day retention (`backupCount=30`)
  - Human-readable console format for file logs (no ANSI colors)
  - New `log_dir` parameter to `setup_logging()`

- **[config.py](src/newsanalysis/core/config.py)**:
  - Changed `log_file: Optional[Path]` to `log_dir: Path = Path("./logs")`
  - Updated `validate_paths()` to create log directory

- **CLI commands updated** to pass `log_dir` to `setup_logging()`:
  - [run.py](src/newsanalysis/cli/commands/run.py)
  - [email.py](src/newsanalysis/cli/commands/email.py)
  - [stats.py](src/newsanalysis/cli/commands/stats.py)
  - [export.py](src/newsanalysis/cli/commands/export.py)
  - [init_db.py](scripts/init_db.py)

- **[.env.example](.env.example)**: Added `LOG_DIR=./logs` documentation

## How to Test

1. Run any CLI command:
   ```bash
   newsanalysis run --limit 1
   ```

2. Verify log file is created:
   ```bash
   ls logs/
   # Should show: newsanalysis.log
   ```

3. Verify log content is human-readable:
   ```bash
   cat logs/newsanalysis.log
   # Format: 2026-01-07T15:15:27Z [info] event_name [logger] key=value
   ```

4. Rotated files will be named `newsanalysis.log.YYYY-MM-DD` after midnight rotation.

## Risk / Rollback Notes

- **Low risk**: File logging is additive; console output continues unchanged
- **Disk usage**: Logs retained for 30 days; monitor if running frequently
- **Rollback**: Set `LOG_DIR` to empty string or remove the file handler code in `logging.py`
