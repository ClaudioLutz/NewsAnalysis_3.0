"""Database migration system for schema updates.

This module handles schema versioning and migrations to ensure existing
databases get updated when new columns or tables are added.

Schema Version History:
- v1: Initial schema (articles, processed_links, etc.)
- v2: Added semantic deduplication (is_duplicate, canonical_url_hash columns,
      duplicate_groups and duplicate_members tables)
"""

import sqlite3
from pathlib import Path
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)

# Current schema version - increment when adding migrations
CURRENT_SCHEMA_VERSION = 4

# Type alias for migration functions
MigrationFunc = Callable[[sqlite3.Connection], None]


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database.

    Args:
        conn: SQLite connection

    Returns:
        Schema version number (0 if not tracked yet)
    """
    try:
        cursor = conn.execute(
            "SELECT version FROM schema_info ORDER BY applied_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        # schema_info table doesn't exist - database predates versioning
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Record schema version in database.

    Args:
        conn: SQLite connection
        version: Version number to record
    """
    conn.execute(
        """
        INSERT INTO schema_info (version, applied_at)
        VALUES (?, CURRENT_TIMESTAMP)
        """,
        (version,),
    )


def ensure_schema_info_table(conn: sqlite3.Connection) -> None:
    """Create schema_info table if it doesn't exist.

    Args:
        conn: SQLite connection
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_schema_info_version
        ON schema_info(version)
        """
    )


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table.

    Args:
        conn: SQLite connection
        table: Table name
        column: Column name

    Returns:
        True if column exists
    """
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists.

    Args:
        conn: SQLite connection
        table: Table name

    Returns:
        True if table exists
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


# ============================================================================
# Migration Functions
# ============================================================================


def migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migration v1 -> v2: Add semantic deduplication support.

    Adds:
    - is_duplicate column to articles
    - canonical_url_hash column to articles
    - duplicate_groups table
    - duplicate_members table
    - Related indexes
    """
    logger.info("applying_migration", from_version=1, to_version=2)

    # Add is_duplicate column if missing
    if not column_exists(conn, "articles", "is_duplicate"):
        conn.execute(
            """
            ALTER TABLE articles
            ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE
            """
        )
        logger.info("migration_added_column", table="articles", column="is_duplicate")

    # Add canonical_url_hash column if missing
    if not column_exists(conn, "articles", "canonical_url_hash"):
        conn.execute(
            """
            ALTER TABLE articles
            ADD COLUMN canonical_url_hash TEXT
            """
        )
        logger.info(
            "migration_added_column", table="articles", column="canonical_url_hash"
        )

    # Create duplicate_groups table if missing
    if not table_exists(conn, "duplicate_groups"):
        conn.execute(
            """
            CREATE TABLE duplicate_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_url_hash TEXT NOT NULL,
                confidence REAL NOT NULL,
                duplicate_count INTEGER NOT NULL,
                detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                run_id TEXT NOT NULL,
                FOREIGN KEY (canonical_url_hash) REFERENCES articles(url_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_duplicate_groups_canonical
            ON duplicate_groups(canonical_url_hash)
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_duplicate_groups_run_id
            ON duplicate_groups(run_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_duplicate_groups_detected_at
            ON duplicate_groups(detected_at)
            """
        )
        logger.info("migration_created_table", table="duplicate_groups")

    # Create duplicate_members table if missing
    if not table_exists(conn, "duplicate_members"):
        conn.execute(
            """
            CREATE TABLE duplicate_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                duplicate_url_hash TEXT NOT NULL,
                comparison_confidence REAL,
                FOREIGN KEY (group_id) REFERENCES duplicate_groups(id) ON DELETE CASCADE,
                FOREIGN KEY (duplicate_url_hash) REFERENCES articles(url_hash),
                UNIQUE(group_id, duplicate_url_hash)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_duplicate_members_group
            ON duplicate_members(group_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_duplicate_members_hash
            ON duplicate_members(duplicate_url_hash)
            """
        )
        logger.info("migration_created_table", table="duplicate_members")

    # Create indexes on articles for deduplication queries
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_is_duplicate ON articles(is_duplicate)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_canonical_hash ON articles(canonical_url_hash)"
        )
    except sqlite3.OperationalError:
        pass  # Indexes might already exist

    logger.info("migration_complete", version=2)


def migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Migration v2 -> v3: Disable FTS triggers to prevent corruption.

    FTS triggers were causing "database disk image is malformed" errors
    during concurrent UPDATE operations in the pipeline.

    Drops:
    - articles_fts_insert trigger
    - articles_fts_update trigger
    - articles_fts_delete trigger
    """
    logger.info("applying_migration", from_version=2, to_version=3)

    # Drop FTS triggers that cause corruption
    triggers_to_drop = [
        "articles_fts_insert",
        "articles_fts_update",
        "articles_fts_delete",
    ]

    for trigger_name in triggers_to_drop:
        try:
            conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            logger.info("migration_dropped_trigger", trigger=trigger_name)
        except sqlite3.OperationalError as e:
            # Trigger might not exist, that's fine
            logger.debug("trigger_drop_skipped", trigger=trigger_name, reason=str(e))

    logger.info("migration_complete", version=3)


def migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Migration v3 -> v4: Add image extraction support.

    Adds:
    - article_images table for storing image metadata
    - Related indexes for performance
    """
    logger.info("applying_migration", from_version=3, to_version=4)

    # Create article_images table if missing
    if not table_exists(conn, "article_images"):
        conn.execute(
            """
            CREATE TABLE article_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                local_path TEXT,
                image_width INTEGER,
                image_height INTEGER,
                format TEXT,
                file_size INTEGER,
                extraction_quality TEXT,
                is_featured BOOLEAN DEFAULT 0,
                extraction_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                UNIQUE(article_id, image_url)
            )
            """
        )
        logger.info("migration_created_table", table="article_images")

        # Create indexes for article_images
        conn.execute(
            """
            CREATE INDEX idx_article_images_article_id
            ON article_images(article_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX idx_article_images_featured
            ON article_images(is_featured)
            """
        )
        logger.info("migration_created_indexes", table="article_images")

    logger.info("migration_complete", version=4)


# Registry of migrations: version -> migration function
MIGRATIONS: dict[int, MigrationFunc] = {
    2: migrate_v1_to_v2,
    3: migrate_v2_to_v3,
    4: migrate_v3_to_v4,
}


def run_migrations(conn: sqlite3.Connection) -> bool:
    """Run any pending migrations to bring database up to current version.

    Args:
        conn: SQLite connection

    Returns:
        True if any migrations were applied
    """
    # Ensure we can track versions
    ensure_schema_info_table(conn)

    current_version = get_schema_version(conn)

    if current_version >= CURRENT_SCHEMA_VERSION:
        logger.debug(
            "schema_up_to_date",
            version=current_version,
            target=CURRENT_SCHEMA_VERSION,
        )
        return False

    # Special case: if version is 0 but tables exist, it's an old database
    if current_version == 0 and table_exists(conn, "articles"):
        # Database predates versioning, set to v1
        set_schema_version(conn, 1)
        current_version = 1
        conn.commit()
        logger.info("schema_version_initialized", version=1)

    migrations_applied = False

    # Apply each migration in sequence
    for target_version in range(current_version + 1, CURRENT_SCHEMA_VERSION + 1):
        if target_version in MIGRATIONS:
            migration_func = MIGRATIONS[target_version]
            try:
                migration_func(conn)
                set_schema_version(conn, target_version)
                conn.commit()
                migrations_applied = True
                logger.info(
                    "migration_applied",
                    from_version=target_version - 1,
                    to_version=target_version,
                )
            except Exception as e:
                conn.rollback()
                logger.error(
                    "migration_failed",
                    target_version=target_version,
                    error=str(e),
                )
                raise

    return migrations_applied
