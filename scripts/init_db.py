#!/usr/bin/env python
"""Initialize NewsAnalysis database."""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from newsanalysis.core.config import Config
from newsanalysis.database.connection import init_database
from newsanalysis.utils.logging import setup_logging


def main() -> None:
    """Initialize database with schema."""
    # Load configuration
    try:
        config = Config()  # type: ignore
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Please ensure .env file exists with required settings.")
        sys.exit(1)

    # Setup logging
    setup_logging(log_level=config.log_level, log_dir=config.log_dir)

    # Initialize database
    print(f"Initializing database at: {config.db_path}")

    try:
        db = init_database(config.db_path)
        print(f"✓ Database initialized successfully at {config.db_path}")

        # Run migrations for existing databases
        _migrate_credit_impact(db)


        # Verify tables were created
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            if not table.startswith("sqlite_"):
                print(f"  - {table}")

        db.close()

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


def _migrate_credit_impact(db) -> None:
    """Add credit_impact column to articles table if it doesn't exist."""
    try:
        cursor = db.execute("PRAGMA table_info(articles)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "credit_impact" not in columns:
            db.execute("ALTER TABLE articles ADD COLUMN credit_impact TEXT")
            db.commit()
            print("  ✓ Migration: added credit_impact column to articles table")
        else:
            print("  ✓ credit_impact column already exists")
    except Exception as e:
        print(f"  ⚠ Migration warning: {e}")


if __name__ == "__main__":
    main()
