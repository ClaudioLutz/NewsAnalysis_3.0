# Fix Digest Generation Reliability and Add Automatic Email

## Summary

Fixed two critical bugs in digest generation that caused articles to be marked as "digested" without actually being included in a saved digest, and prevented multiple pipeline runs per day from generating new digests. Also added automatic email sending with support for multiple recipients.

## Context / Problem

When running the pipeline multiple times per day:

1. **Articles marked digested before digest saved**: The `generate_digest()` method marked articles as `digested` BEFORE the digest was saved to the database. If `save_digest()` failed (e.g., due to unique constraint violation), articles remained marked as "digested" but were not in any actual digest - creating orphaned articles.

2. **Hardcoded version=1**: The orchestrator passed `incremental=False` to `generate_digest()`, which always created version 1. When a digest for the current date already existed, the INSERT would fail with a `UNIQUE(digest_date, version)` constraint violation.

3. **Silent failure**: The digest generation exception was caught and swallowed in the orchestrator, so the pipeline appeared to succeed but no digest/email was generated.

4. **No automatic email**: Users had to manually run `newsanalysis email` after the pipeline to send the digest.

Result: Morning pipeline runs would find new articles, summarize them, mark them as "digested", but fail to actually create a new digest or send an email.

## What Changed

### Digest Generator (`src/newsanalysis/pipeline/generators/digest_generator.py`)

- **Removed early article marking**: No longer calls `_mark_articles_digested()` inside `generate_digest()`. Articles are now marked AFTER the digest is successfully saved.

- **Auto-detect incremental version**: Instead of using the `incremental` parameter, the generator now checks if a digest already exists for the date and automatically increments the version number.

- **Made `mark_articles_digested()` public**: Renamed from `_mark_articles_digested()` to allow the orchestrator to call it after save.

- **Removed unused `_get_next_version()` method**: Logic was inlined into `generate_digest()`.

### Orchestrator (`src/newsanalysis/pipeline/orchestrator.py`)

- **Call mark_articles_digested AFTER save**: Added call to `digest_generator.mark_articles_digested()` after `save_digest()` succeeds, ensuring data consistency.

- **New Stage 6: Email Sending**: Added `_run_email_sending()` method that automatically sends the digest email after successful digest generation when `EMAIL_AUTO_SEND=true`.

### Configuration (`src/newsanalysis/core/config.py`)

- **`email_recipients`**: Comma-separated list of email recipients (replaces single `email_recipient`)
- **`email_auto_send`**: Boolean flag to enable automatic email after digest generation
- **`email_recipient_list`**: Property that parses comma-separated recipients into a list

### Email Service (`src/newsanalysis/services/email_service.py`)

- **Multiple recipients support**: `send_html_email()` now accepts `str | list[str]` for the `to` parameter

### Email Command (`src/newsanalysis/cli/commands/email.py`)

- Updated to use `email_recipient_list` from config
- Works with multiple recipients

### Environment Configuration (`.env`)

New variables:
```bash
EMAIL_RECIPIENTS=user1@example.com,user2@example.com
EMAIL_AUTO_SEND=true
```

## How to Test

1. Configure email in `.env`:
   ```bash
   EMAIL_RECIPIENTS=your@email.com
   EMAIL_AUTO_SEND=true
   ```

2. Run pipeline:
   ```bash
   newsanalysis run --mode full
   ```

3. Verify email was sent (check logs for `stage_email_sending_complete`)

4. Verify multiple digest versions work:
   ```bash
   python -c "
   import sqlite3
   conn = sqlite3.connect('news.db')
   cursor = conn.execute('SELECT id, digest_date, version, article_count FROM digests ORDER BY generated_at DESC')
   for row in cursor:
       print(row)
   "
   ```

5. Manual email test with multiple recipients:
   ```bash
   newsanalysis email --preview
   ```

## Risk / Rollback Notes

**Low risk** - Changes improve reliability without breaking existing functionality:

- Existing digests remain valid
- Version auto-increment is backward compatible
- Article marking happens in same transaction boundary (just moved later in sequence)
- Email sending is optional and controlled by `EMAIL_AUTO_SEND`

To rollback:
- Revert `digest_generator.py` to restore `_mark_articles_digested()` call inside `generate_digest()`
- Revert `orchestrator.py` to remove post-save `mark_articles_digested()` call and email stage
- Set `EMAIL_AUTO_SEND=false` to disable automatic emails

## Files Changed

- `src/newsanalysis/core/config.py` - Add `email_recipients`, `email_auto_send`, `email_recipient_list`
- `src/newsanalysis/pipeline/generators/digest_generator.py` - Move article marking out, auto-increment version
- `src/newsanalysis/pipeline/orchestrator.py` - Call mark_articles_digested after save, add email stage
- `src/newsanalysis/services/email_service.py` - Support multiple recipients
- `src/newsanalysis/cli/commands/email.py` - Use recipient list from config
- `.env.example` - Add email configuration section
- `.env` - Add `EMAIL_RECIPIENTS` and `EMAIL_AUTO_SEND`
