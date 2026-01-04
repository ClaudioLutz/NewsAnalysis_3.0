"""Database migration script for Phase 5 optimizations.

This script adds:
- Classification cache table
- Content fingerprints table
- Cache stats table
- Composite indexes for better performance
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str):
    """Run Phase 5 database migrations.

    Args:
        db_path: Path to the database file
    """
    print(f"Running Phase 5 migrations on: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # 1. Create classification_cache table
        print("Creating classification_cache table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classification_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                is_match BOOLEAN NOT NULL,
                confidence REAL NOT NULL,
                topic TEXT NOT NULL,
                reason TEXT,
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_hit_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_cache_key ON classification_cache(cache_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_cache_created_at ON classification_cache(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_cache_expires_at ON classification_cache(expires_at)")

        # 2. Create content_fingerprints table
        print("Creating content_fingerprints table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL UNIQUE,
                content_length INTEGER NOT NULL,
                summary_title TEXT,
                summary TEXT,
                key_points TEXT,
                entities TEXT,
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_hit_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_fingerprints_hash ON content_fingerprints(content_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_fingerprints_created_at ON content_fingerprints(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_fingerprints_expires_at ON content_fingerprints(expires_at)")

        # 3. Create cache_stats table
        print("Creating cache_stats table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                cache_type TEXT NOT NULL,
                requests INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0,
                hit_rate REAL DEFAULT 0.0,
                api_calls_saved INTEGER DEFAULT 0,
                cost_saved REAL DEFAULT 0.0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, cache_type)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_date ON cache_stats(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_type ON cache_stats(cache_type)")

        # 4. Add composite indexes to articles table
        print("Adding composite indexes to articles table...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_stage_status ON articles(pipeline_stage, processing_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_match_stage ON articles(is_match, pipeline_stage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_created_stage ON articles(created_at, pipeline_stage)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_digest_included ON articles(digest_date, included_in_digest)")

        # Commit changes
        conn.commit()

        print("✓ Migration completed successfully!")

        # Display statistics
        cursor.execute("SELECT COUNT(*) FROM classification_cache")
        cache_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM content_fingerprints")
        content_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cache_stats")
        stats_count = cursor.fetchone()[0]

        print(f"\nCache Statistics:")
        print(f"  Classification cache entries: {cache_count}")
        print(f"  Content fingerprint entries: {content_count}")
        print(f"  Cache stats records: {stats_count}")

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    # Default database path
    db_path = "news.db"

    # Allow custom path via command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    # Check if database exists
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        print("Usage: python scripts/migrate_phase5.py [database_path]")
        sys.exit(1)

    run_migration(db_path)
