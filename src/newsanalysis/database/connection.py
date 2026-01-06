"""Database connection management with corruption prevention."""

import atexit
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Global registry of connections for cleanup
_active_connections: list["DatabaseConnection"] = []

# Global write lock to serialize all database writes across connections
_write_lock = threading.RLock()


def _cleanup_all_connections() -> None:
    """Cleanup all active connections on exit."""
    for conn in _active_connections[:]:
        try:
            conn.close()
        except Exception:
            pass


# Register cleanup handler
atexit.register(_cleanup_all_connections)


class DatabaseConnection:
    """SQLite database connection manager."""

    def __init__(self, db_path: Path) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection.

        Returns:
            SQLite connection object
        """
        return self.connect()

    def connect(self) -> sqlite3.Connection:
        """Get or create database connection.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            # Check database integrity before connecting
            needs_init = not self.db_path.exists()
            if self.db_path.exists():
                self._check_and_repair_database()
                # Check again - recovery might have removed it
                needs_init = not self.db_path.exists()

            # Don't use PARSE_DECLTYPES - it's deprecated in Python 3.13
            # Set timeout to 30 seconds to handle concurrent writes
            self._connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )

            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use WAL mode for better crash recovery and concurrency
            self._connection.execute("PRAGMA journal_mode = WAL")
            # Use NORMAL synchronous with WAL (safe and fast)
            self._connection.execute("PRAGMA synchronous = NORMAL")
            # Set busy timeout at SQLite level
            self._connection.execute("PRAGMA busy_timeout = 30000")
            # Enable WAL checkpointing after 1000 pages (~4MB)
            self._connection.execute("PRAGMA wal_autocheckpoint = 1000")
            # Return rows as dictionaries
            self._connection.row_factory = sqlite3.Row

            # Initialize schema if database is new
            if needs_init:
                self._initialize_schema()

            # Register for cleanup
            _active_connections.append(self)

            logger.info("database_connected", path=str(self.db_path))

        return self._connection

    def _initialize_schema(self) -> None:
        """Initialize database schema."""
        if self._connection is None:
            return
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            self._connection.executescript(schema_sql)
            logger.info("database_schema_initialized")

    def _check_and_repair_database(self) -> None:
        """Check database integrity and attempt repair if corrupted.

        Performs both standard integrity check AND FTS-specific validation,
        since FTS trigger corruption often passes standard integrity_check.
        """
        try:
            test_conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            test_conn.execute("PRAGMA journal_mode = WAL")

            # Standard integrity check
            cursor = test_conn.execute("PRAGMA quick_check")
            result = cursor.fetchone()[0]

            if result != "ok":
                test_conn.close()
                logger.warning("database_corruption_detected", result=result)
                self._attempt_recovery()
                return

            # FTS-specific corruption check - test if FTS triggers work
            # This catches trigger corruption that integrity_check misses
            if self._has_fts_tables(test_conn):
                fts_ok = self._test_fts_triggers(test_conn)
                if not fts_ok:
                    test_conn.close()
                    logger.warning("fts_trigger_corruption_detected")
                    self._attempt_recovery()
                    return

            test_conn.close()

        except sqlite3.DatabaseError as e:
            logger.error("database_error_on_check", error=str(e))
            self._attempt_recovery()

    def _has_fts_tables(self, conn: sqlite3.Connection) -> bool:
        """Check if database has FTS tables."""
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts'"
            )
            return cursor.fetchone() is not None
        except Exception:
            return False

    def _test_fts_triggers(self, conn: sqlite3.Connection) -> bool:
        """Test if FTS triggers are functional by doing a test UPDATE.

        FTS trigger corruption often passes integrity_check but fails during
        UPDATE operations with 'database disk image is malformed'.
        """
        try:
            # Find the main table that has FTS triggers
            cursor = conn.execute(
                "SELECT tbl_name FROM sqlite_master WHERE type='trigger' AND name LIKE '%_fts_update'"
            )
            row = cursor.fetchone()
            if not row:
                return True  # No FTS triggers to test

            table_name = row[0]

            # Get primary key column name
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            pk_col = None
            for col in cursor.fetchall():
                if col[5] == 1:  # pk column
                    pk_col = col[1]
                    break

            if not pk_col:
                pk_col = "id"  # fallback

            # Get one row to test
            cursor = conn.execute(f"SELECT {pk_col} FROM {table_name} LIMIT 1")
            test_row = cursor.fetchone()
            if not test_row:
                return True  # No data to test with

            test_id = test_row[0]

            # Try a no-op UPDATE that triggers FTS update
            # This will fail with 'database disk image is malformed' if FTS is corrupted
            conn.execute(
                f"UPDATE {table_name} SET {pk_col} = {pk_col} WHERE {pk_col} = ?",
                (test_id,),
            )
            conn.rollback()  # Don't actually commit the test

            return True

        except sqlite3.DatabaseError as e:
            if "malformed" in str(e).lower():
                logger.warning("fts_trigger_test_failed", error=str(e))
                return False
            raise

    def _attempt_recovery(self) -> None:
        """Attempt to recover from database corruption."""
        backup_path = self.db_path.with_suffix(".db.corrupted")

        logger.warning("attempting_database_recovery", backup_path=str(backup_path))

        # Backup corrupted database
        if self.db_path.exists():
            shutil.copy2(self.db_path, backup_path)
            logger.info("corrupted_db_backed_up", path=str(backup_path))

        # Try to recover data using .recover command equivalent
        try:
            # Open corrupted database
            old_conn = sqlite3.connect(str(self.db_path), timeout=5.0)

            # Create new clean database
            new_path = self.db_path.with_suffix(".db.new")
            new_conn = sqlite3.connect(str(new_path), timeout=5.0)

            # Copy schema and data
            old_conn.backup(new_conn)

            old_conn.close()
            new_conn.close()

            # Replace corrupted with recovered
            self.db_path.unlink()
            new_path.rename(self.db_path)

            logger.info("database_recovered_successfully")

        except Exception as e:
            logger.error("database_recovery_failed", error=str(e))
            # Remove corrupted database and let it be recreated
            if self.db_path.exists():
                self.db_path.unlink()
            # Remove WAL and SHM files if they exist
            wal_path = self.db_path.with_suffix(".db-wal")
            shm_path = self.db_path.with_suffix(".db-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
            logger.info("corrupted_database_removed_will_reinitialize")

    def close(self) -> None:
        """Close database connection with proper WAL checkpoint."""
        if self._connection:
            try:
                # Checkpoint WAL before closing to prevent corruption
                self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass  # Ignore checkpoint errors on close

            self._connection.close()
            self._connection = None

            # Remove from cleanup registry
            if self in _active_connections:
                _active_connections.remove(self)

            logger.info("database_closed")

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a database query with thread safety.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object
        """
        conn = self.connect()
        # Use lock for write operations to prevent corruption
        is_write = query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"))
        if is_write:
            with _write_lock:
                return conn.execute(query, params)
        return conn.execute(query, params)

    def executemany(self, query: str, params: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets (thread-safe).

        Args:
            query: SQL query string
            params: List of parameter tuples

        Returns:
            Cursor object
        """
        conn = self.connect()
        # Always lock for executemany as it's typically writes
        with _write_lock:
            return conn.executemany(query, params)

    def commit(self) -> None:
        """Commit current transaction (thread-safe)."""
        if self._connection:
            with _write_lock:
                self._connection.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()

    def __enter__(self) -> "DatabaseConnection":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Context manager exit."""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def init_database(db_path: Path) -> DatabaseConnection:
    """Initialize database with schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        DatabaseConnection object
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database connection
    db = DatabaseConnection(db_path)

    # Read schema file
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Execute schema
    conn = db.connect()
    conn.executescript(schema_sql)
    conn.commit()

    logger.info("database_initialized", path=str(db_path))

    return db
