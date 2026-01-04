"""Digest repository for database operations."""

import json
from datetime import date, datetime
from typing import List, Optional

from newsanalysis.core.digest import DailyDigest, MetaAnalysis
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.exceptions import DatabaseError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class DigestRepository:
    """Repository for digest database operations."""

    def __init__(self, db: DatabaseConnection):
        """Initialize repository.

        Args:
            db: Database connection instance.
        """
        self.db = db

    def save_digest(
        self,
        digest: DailyDigest,
        json_output: Optional[str] = None,
        markdown_output: Optional[str] = None,
        german_report: Optional[str] = None,
    ) -> int:
        """Save digest to database.

        Args:
            digest: Daily digest object.
            json_output: JSON formatted output (optional).
            markdown_output: Markdown formatted output (optional).
            german_report: German rating report (optional).

        Returns:
            Digest database ID.

        Raises:
            DatabaseError: If database operation fails.
        """
        logger.info(
            "saving_digest",
            date=str(digest.date),
            version=digest.version,
            article_count=digest.article_count,
        )

        try:
            # Prepare article IDs list
            article_ids = [a.id for a in digest.articles if a.id]
            articles_json = json.dumps(article_ids)

            # Prepare meta-analysis JSON
            meta_analysis_json = digest.meta_analysis.model_dump_json()

            cursor = self.db.execute(
                """
                INSERT INTO digests (
                    digest_date, version, articles_json, meta_analysis_json,
                    json_output, markdown_output, german_report,
                    article_count, cluster_count, generated_at, run_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    digest.date.isoformat(),
                    digest.version,
                    articles_json,
                    meta_analysis_json,
                    json_output,
                    markdown_output,
                    german_report,
                    digest.article_count,
                    digest.cluster_count,
                    digest.generated_at.isoformat(),
                    digest.run_id,
                ),
            )

            self.db.commit()
            digest_id = cursor.lastrowid

            logger.info("digest_saved", digest_id=digest_id)
            return digest_id

        except Exception as e:
            self.db.rollback()
            logger.error("digest_save_failed", error=str(e))
            raise DatabaseError(f"Failed to save digest: {e}") from e

    def get_digest_by_date(
        self, digest_date: date, version: Optional[int] = None
    ) -> Optional[dict]:
        """Get digest by date.

        Args:
            digest_date: Date of the digest.
            version: Version number (defaults to latest).

        Returns:
            Digest dictionary or None if not found.
        """
        try:
            if version:
                cursor = self.db.execute(
                    """
                    SELECT * FROM digests
                    WHERE digest_date = ? AND version = ?
                    """,
                    (digest_date.isoformat(), version),
                )
            else:
                # Get latest version for the date
                cursor = self.db.execute(
                    """
                    SELECT * FROM digests
                    WHERE digest_date = ?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (digest_date.isoformat(),),
                )

            row = cursor.fetchone()
            if not row:
                return None

            return self._row_to_dict(row)

        except Exception as e:
            logger.error("digest_fetch_failed", error=str(e))
            raise DatabaseError(f"Failed to fetch digest: {e}") from e

    def get_latest_version(self, digest_date: date) -> int:
        """Get the latest version number for a date.

        Args:
            digest_date: Date of the digest.

        Returns:
            Latest version number (0 if no digest exists).
        """
        try:
            cursor = self.db.execute(
                """
                SELECT MAX(version) as max_version
                FROM digests
                WHERE digest_date = ?
                """,
                (digest_date.isoformat(),),
            )

            row = cursor.fetchone()
            if row and row["max_version"]:
                return row["max_version"]
            return 0

        except Exception as e:
            logger.error("version_fetch_failed", error=str(e))
            raise DatabaseError(f"Failed to fetch version: {e}") from e

    def list_digests(self, limit: int = 10) -> List[dict]:
        """List recent digests.

        Args:
            limit: Maximum number of digests to return.

        Returns:
            List of digest dictionaries.
        """
        try:
            cursor = self.db.execute(
                """
                SELECT * FROM digests
                ORDER BY digest_date DESC, version DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error("digests_list_failed", error=str(e))
            raise DatabaseError(f"Failed to list digests: {e}") from e

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary.

        Args:
            row: Database row.

        Returns:
            Dictionary representation.
        """
        return {
            "id": row["id"],
            "digest_date": row["digest_date"],
            "version": row["version"],
            "articles_json": row["articles_json"],
            "meta_analysis_json": row["meta_analysis_json"],
            "json_output": row["json_output"],
            "markdown_output": row["markdown_output"],
            "german_report": row["german_report"],
            "article_count": row["article_count"],
            "cluster_count": row["cluster_count"],
            "generated_at": row["generated_at"],
            "run_id": row["run_id"],
        }
