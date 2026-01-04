"""Database connection management."""

import sqlite3
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


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
            # Don't use PARSE_DECLTYPES - it's deprecated in Python 3.13
            # and doesn't handle timezone-aware timestamps properly
            # Set timeout to 30 seconds to handle concurrent writes
            # Use isolation_level=None for autocommit mode to prevent locking issues on Windows
            self._connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                isolation_level=None  # Autocommit mode
            )

            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
            # Use TRUNCATE journal mode instead of WAL for Windows compatibility
            self._connection.execute("PRAGMA journal_mode = TRUNCATE")
            # Use FULL synchronous mode for data integrity
            self._connection.execute("PRAGMA synchronous = FULL")
            # Set busy timeout at SQLite level as well
            self._connection.execute("PRAGMA busy_timeout = 30000")
            # Disable memory-mapped I/O which can cause corruption on Windows
            self._connection.execute("PRAGMA mmap_size = 0")
            # Return rows as dictionaries
            self._connection.row_factory = sqlite3.Row

            logger.info("database_connected", path=str(self.db_path))

        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("database_closed")

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object
        """
        conn = self.connect()
        return conn.execute(query, params)

    def executemany(self, query: str, params: list) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query string
            params: List of parameter tuples

        Returns:
            Cursor object
        """
        conn = self.connect()
        return conn.executemany(query, params)

    def commit(self) -> None:
        """Commit current transaction."""
        if self._connection:
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
