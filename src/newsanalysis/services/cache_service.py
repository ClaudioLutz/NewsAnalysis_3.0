"""Cache service for classification and content caching.

This module provides caching functionality to reduce API costs by:
1. Caching classification results for identical title+URL combinations
2. Caching content fingerprints to avoid re-summarizing identical content
3. Tracking cache hit rates and cost savings
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from newsanalysis.core.article import ClassificationResult, EntityData
from newsanalysis.utils.date_utils import now_utc
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Service for caching classification and content results."""

    def __init__(self, db_connection: sqlite3.Connection):
        """Initialize cache service.

        Args:
            db_connection: Database connection
        """
        self.conn = db_connection
        self._classification_ttl_days = 30  # Classification cache TTL
        self._content_ttl_days = 90  # Content cache TTL

    # Classification Cache Methods

    def get_cached_classification(
        self, title: str, url: str
    ) -> Optional[ClassificationResult]:
        """Get cached classification result for title+URL combination.

        Args:
            title: Article title
            url: Article URL

        Returns:
            ClassificationResult if cache hit, None if cache miss
        """
        cache_key = self._generate_classification_key(title, url)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT is_match, confidence, topic, reason
            FROM classification_cache
            WHERE cache_key = ?
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """,
            (cache_key,),
        )
        row = cursor.fetchone()

        if row:
            # Update hit count and last_hit_at
            cursor.execute(
                """
                UPDATE classification_cache
                SET hit_count = hit_count + 1,
                    last_hit_at = CURRENT_TIMESTAMP
                WHERE cache_key = ?
                """,
                (cache_key,),
            )
            self.conn.commit()

            # Track cache hit
            self._track_cache_stat("classification", hit=True)

            logger.debug(
                "classification_cache_hit",
                cache_key=cache_key[:16],
                title=title[:50],
            )

            return ClassificationResult(
                is_match=bool(row[0]),
                confidence=float(row[1]),
                topic=row[2],
                reason=row[3] or "",
            )

        # Track cache miss
        self._track_cache_stat("classification", hit=False)
        logger.debug("classification_cache_miss", title=title[:50])
        return None

    def cache_classification(
        self, title: str, url: str, result: ClassificationResult
    ) -> None:
        """Cache classification result for title+URL combination.

        Args:
            title: Article title
            url: Article URL
            result: Classification result to cache
        """
        cache_key = self._generate_classification_key(title, url)
        expires_at = now_utc() + timedelta(days=self._classification_ttl_days)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO classification_cache
            (cache_key, title, url, is_match, confidence, topic, reason, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                cache_key,
                title,
                url,
                result.is_match,
                result.confidence,
                result.topic,
                result.reason,
                expires_at.isoformat(),
            ),
        )
        self.conn.commit()

        logger.debug("classification_cached", cache_key=cache_key[:16])

    # Content Fingerprint Cache Methods

    def get_cached_summary(
        self, content: str
    ) -> Optional[dict]:
        """Get cached summary for content fingerprint.

        Args:
            content: Article content

        Returns:
            Dictionary with summary data if cache hit, None if cache miss
        """
        content_hash = self._generate_content_hash(content)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT summary_title, summary, key_points, entities
            FROM content_fingerprints
            WHERE content_hash = ?
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """,
            (content_hash,),
        )
        row = cursor.fetchone()

        if row:
            # Update hit count and last_hit_at
            cursor.execute(
                """
                UPDATE content_fingerprints
                SET hit_count = hit_count + 1,
                    last_hit_at = CURRENT_TIMESTAMP
                WHERE content_hash = ?
                """,
                (content_hash,),
            )
            self.conn.commit()

            # Track cache hit
            self._track_cache_stat("content", hit=True)

            logger.debug(
                "content_cache_hit",
                content_hash=content_hash[:16],
                content_length=len(content),
            )

            return {
                "summary_title": row[0],
                "summary": row[1],
                "key_points": row[2],  # JSON string
                "entities": row[3],  # JSON string
            }

        # Track cache miss
        self._track_cache_stat("content", hit=False)
        logger.debug("content_cache_miss", content_length=len(content))
        return None

    def cache_summary(
        self,
        content: str,
        summary_title: str,
        summary: str,
        key_points: str,
        entities: str,
    ) -> None:
        """Cache summary for content fingerprint.

        Args:
            content: Article content
            summary_title: Summary title
            summary: Summary text
            key_points: Key points (JSON string)
            entities: Entities (JSON string)
        """
        content_hash = self._generate_content_hash(content)
        expires_at = now_utc() + timedelta(days=self._content_ttl_days)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO content_fingerprints
            (content_hash, content_length, summary_title, summary, key_points, entities, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                content_hash,
                len(content),
                summary_title,
                summary,
                key_points,
                entities,
                expires_at.isoformat(),
            ),
        )
        self.conn.commit()

        logger.debug("content_cached", content_hash=content_hash[:16])

    # Cache Statistics Methods

    def get_cache_stats(self, date: Optional[str] = None) -> dict:
        """Get cache statistics for a specific date.

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Dictionary with cache statistics by cache type
        """
        if not date:
            date = now_utc().date().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT cache_type, requests, hits, misses, hit_rate, api_calls_saved, cost_saved
            FROM cache_stats
            WHERE date = ?
            """,
            (date,),
        )

        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                "requests": row[1],
                "hits": row[2],
                "misses": row[3],
                "hit_rate": row[4],
                "api_calls_saved": row[5],
                "cost_saved": row[6],
            }

        return stats

    def get_cache_summary(self) -> dict:
        """Get overall cache summary statistics.

        Returns:
            Dictionary with cache summary data
        """
        cursor = self.conn.cursor()

        # Classification cache stats
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits_per_entry
            FROM classification_cache
            WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
            """
        )
        class_row = cursor.fetchone()

        # Content cache stats
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_entries,
                SUM(hit_count) as total_hits,
                AVG(hit_count) as avg_hits_per_entry
            FROM content_fingerprints
            WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
            """
        )
        content_row = cursor.fetchone()

        # Recent cache stats (last 7 days)
        cursor.execute(
            """
            SELECT
                cache_type,
                SUM(hits) as total_hits,
                SUM(misses) as total_misses,
                SUM(api_calls_saved) as total_api_calls_saved,
                SUM(cost_saved) as total_cost_saved
            FROM cache_stats
            WHERE date >= date('now', '-7 days')
            GROUP BY cache_type
            """
        )
        recent_stats = {row[0]: {
            "hits": row[1] or 0,
            "misses": row[2] or 0,
            "api_calls_saved": row[3] or 0,
            "cost_saved": row[4] or 0.0,
        } for row in cursor.fetchall()}

        return {
            "classification_cache": {
                "entries": class_row[0] or 0,
                "total_hits": class_row[1] or 0,
                "avg_hits_per_entry": class_row[2] or 0.0,
                "recent_7days": recent_stats.get("classification", {}),
            },
            "content_cache": {
                "entries": content_row[0] or 0,
                "total_hits": content_row[1] or 0,
                "avg_hits_per_entry": content_row[2] or 0.0,
                "recent_7days": recent_stats.get("content", {}),
            },
        }

    def cleanup_expired_cache(self) -> dict:
        """Remove expired cache entries.

        Returns:
            Dictionary with cleanup statistics
        """
        cursor = self.conn.cursor()

        # Clean classification cache
        cursor.execute(
            """
            DELETE FROM classification_cache
            WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """
        )
        classification_deleted = cursor.rowcount

        # Clean content fingerprints
        cursor.execute(
            """
            DELETE FROM content_fingerprints
            WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """
        )
        content_deleted = cursor.rowcount

        self.conn.commit()

        logger.info(
            "cache_cleanup_completed",
            classification_deleted=classification_deleted,
            content_deleted=content_deleted,
        )

        return {
            "classification_deleted": classification_deleted,
            "content_deleted": content_deleted,
        }

    # Private Helper Methods

    def _generate_classification_key(self, title: str, url: str) -> str:
        """Generate cache key for classification.

        Args:
            title: Article title
            url: Article URL

        Returns:
            SHA-256 hash of normalized title + URL
        """
        # Normalize title and URL for consistent caching
        normalized_title = title.lower().strip()
        normalized_url = url.lower().strip()
        combined = f"{normalized_title}|{normalized_url}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content fingerprint.

        Args:
            content: Article content

        Returns:
            SHA-256 hash of normalized content
        """
        # Normalize content (remove extra whitespace)
        normalized = " ".join(content.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _track_cache_stat(self, cache_type: str, hit: bool) -> None:
        """Track cache hit/miss statistics.

        Args:
            cache_type: Type of cache ("classification" or "content")
            hit: Whether this was a cache hit
        """
        date = now_utc().date().isoformat()

        cursor = self.conn.cursor()

        # Estimate cost saved per cache hit
        # Classification: ~$0.0001 per call (gpt-4o-mini)
        # Content: ~$0.001 per call (gpt-4o-mini summarization)
        cost_per_hit = 0.0001 if cache_type == "classification" else 0.001

        if hit:
            cursor.execute(
                """
                INSERT INTO cache_stats (date, cache_type, requests, hits, misses, api_calls_saved, cost_saved)
                VALUES (?, ?, 1, 1, 0, 1, ?)
                ON CONFLICT(date, cache_type) DO UPDATE SET
                    requests = requests + 1,
                    hits = hits + 1,
                    api_calls_saved = api_calls_saved + 1,
                    cost_saved = cost_saved + ?,
                    hit_rate = CAST(hits AS REAL) / requests,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (date, cache_type, cost_per_hit, cost_per_hit),
            )
        else:
            cursor.execute(
                """
                INSERT INTO cache_stats (date, cache_type, requests, hits, misses)
                VALUES (?, ?, 1, 0, 1)
                ON CONFLICT(date, cache_type) DO UPDATE SET
                    requests = requests + 1,
                    misses = misses + 1,
                    hit_rate = CAST(hits AS REAL) / requests,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (date, cache_type),
            )

        self.conn.commit()
