"""Article repository for database operations."""

import json
from datetime import datetime
from typing import List, Optional

from newsanalysis.core.article import (
    Article,
    ArticleImage,
    ArticleMetadata,
    ArticleSummary,
    ClassificationResult,
    ScrapedContent,
)
from newsanalysis.pipeline.dedup.duplicate_detector import DuplicateGroup
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.utils.exceptions import DatabaseError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime string from SQLite.

    Args:
        value: ISO format datetime string or None

    Returns:
        datetime object or None
    """
    if not value:
        return None
    try:
        # Handle ISO format with or without timezone
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


class ArticleRepository:
    """Repository for article database operations."""

    def __init__(self, db: DatabaseConnection):
        """Initialize repository.

        Args:
            db: Database connection instance.
        """
        self.db = db

    def save_collected_articles(self, articles: List[ArticleMetadata], run_id: str) -> int:
        """Save collected articles to database.

        Args:
            articles: List of article metadata from collection.
            run_id: Pipeline run identifier.

        Returns:
            Number of articles saved (excluding duplicates).

        Raises:
            DatabaseError: If database operation fails.
        """
        logger.info("saving_articles", count=len(articles), run_id=run_id)

        try:
            saved_count = 0

            for article in articles:
                # Check if article already exists by URL hash
                if self._article_exists(article.url_hash):
                    logger.debug("article_already_exists", url_hash=article.url_hash)
                    continue

                # Insert article
                query = """
                    INSERT INTO articles (
                        url, normalized_url, url_hash, title, source,
                        published_at, collected_at, feed_priority,
                        pipeline_stage, processing_status, run_id,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    str(article.url),
                    article.normalized_url,
                    article.url_hash,
                    article.title,
                    article.source,
                    article.published_at,
                    article.collected_at,
                    article.feed_priority,
                    "collected",
                    "pending",
                    run_id,
                    datetime.now(),
                    datetime.now(),
                )

                self.db.execute(query, params)
                saved_count += 1

            self.db.commit()

            logger.info("articles_saved", saved=saved_count, duplicates=len(articles) - saved_count)

            return saved_count

        except Exception as e:
            self.db.rollback()
            logger.error("save_articles_failed", error=str(e))
            raise DatabaseError(f"Failed to save articles: {e}") from e

    def update_classification(
        self,
        url_hash: str,
        classification: ClassificationResult,
    ) -> bool:
        """Update article with classification result.

        Args:
            url_hash: Article URL hash.
            classification: Classification result from AI filter.

        Returns:
            True if updated successfully, False if article not found.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                UPDATE articles
                SET is_match = ?,
                    confidence = ?,
                    topic = ?,
                    classification_reason = ?,
                    filtered_at = ?,
                    pipeline_stage = 'filtered',
                    processing_status = 'completed',
                    updated_at = ?
                WHERE url_hash = ?
            """

            params = (
                classification.is_match,
                classification.confidence,
                classification.topic,
                classification.reason,
                classification.filtered_at,
                datetime.now(),
                url_hash,
            )

            cursor = self.db.execute(query, params)
            self.db.commit()

            return cursor.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error("update_classification_failed", url_hash=url_hash, error=str(e))
            raise DatabaseError(f"Failed to update classification: {e}") from e

    def update_scraped_content(
        self,
        url_hash: str,
        scraped: ScrapedContent,
    ) -> bool:
        """Update article with scraped content.

        Args:
            url_hash: Article URL hash.
            scraped: Scraped content data.

        Returns:
            True if updated successfully, False if article not found.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                UPDATE articles
                SET content = ?,
                    author = ?,
                    content_length = ?,
                    extraction_method = ?,
                    extraction_quality = ?,
                    scraped_at = ?,
                    pipeline_stage = 'scraped',
                    processing_status = 'completed',
                    updated_at = ?
                WHERE url_hash = ?
            """

            params = (
                scraped.content,
                scraped.author,
                scraped.content_length,
                scraped.extraction_method.value,
                scraped.extraction_quality,
                scraped.scraped_at,
                datetime.now(),
                url_hash,
            )

            cursor = self.db.execute(query, params)
            self.db.commit()

            return cursor.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error("update_scraped_content_failed", url_hash=url_hash, error=str(e))
            raise DatabaseError(f"Failed to update scraped content: {e}") from e

    def update_summary(
        self,
        url_hash: str,
        summary: ArticleSummary,
    ) -> bool:
        """Update article with AI-generated summary.

        Args:
            url_hash: Article URL hash.
            summary: Article summary data.

        Returns:
            True if updated successfully, False if article not found.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            # Convert entities and key_points to JSON
            entities_json = json.dumps(
                {
                    "companies": summary.entities.companies,
                    "people": summary.entities.people,
                    "locations": summary.entities.locations,
                    "topics": summary.entities.topics,
                }
            )
            key_points_json = json.dumps(summary.key_points)

            query = """
                UPDATE articles
                SET summary_title = ?,
                    summary = ?,
                    key_points = ?,
                    entities = ?,
                    topic = ?,
                    summarized_at = ?,
                    pipeline_stage = 'summarized',
                    processing_status = 'completed',
                    updated_at = ?
                WHERE url_hash = ?
            """

            params = (
                summary.summary_title,
                summary.summary,
                key_points_json,
                entities_json,
                summary.topic.value,
                summary.summarized_at,
                datetime.now(),
                url_hash,
            )

            cursor = self.db.execute(query, params)
            self.db.commit()

            return cursor.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error("update_summary_failed", url_hash=url_hash, error=str(e))
            raise DatabaseError(f"Failed to update summary: {e}") from e

    def mark_article_failed(
        self,
        url_hash: str,
        error_message: str,
    ) -> bool:
        """Mark article as failed and increment error count.

        Args:
            url_hash: Article URL hash.
            error_message: Error message to store.

        Returns:
            True if updated successfully, False if article not found.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                UPDATE articles
                SET processing_status = 'failed',
                    error_message = ?,
                    error_count = error_count + 1,
                    updated_at = ?
                WHERE url_hash = ?
            """

            params = (
                error_message,
                datetime.now(),
                url_hash,
            )

            cursor = self.db.execute(query, params)
            self.db.commit()

            return cursor.rowcount > 0

        except Exception as e:
            self.db.rollback()
            logger.error("mark_article_failed_failed", url_hash=url_hash, error=str(e))
            raise DatabaseError(f"Failed to mark article as failed: {e}") from e

    def get_articles_for_scraping(self, limit: Optional[int] = None) -> List[Article]:
        """Get articles that passed filtering and need content scraping.

        Args:
            limit: Maximum number of articles to return.

        Returns:
            List of articles ready for scraping.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                SELECT * FROM articles
                WHERE pipeline_stage = 'filtered'
                  AND is_match = 1
                  AND processing_status = 'completed'
                ORDER BY feed_priority ASC, published_at DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.execute(query)
            rows = cursor.fetchall()

            articles = [self._row_to_article(row) for row in rows]

            logger.info("articles_fetched_for_scraping", count=len(articles))

            return articles

        except Exception as e:
            logger.error("fetch_articles_for_scraping_failed", error=str(e))
            raise DatabaseError(f"Failed to fetch articles for scraping: {e}") from e

    def get_articles_for_summarization(self, limit: Optional[int] = None) -> List[Article]:
        """Get articles that have been scraped and need summarization.

        Excludes articles marked as duplicates - only canonical articles are summarized.

        Args:
            limit: Maximum number of articles to return.

        Returns:
            List of articles ready for summarization.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                SELECT * FROM articles
                WHERE pipeline_stage = 'scraped'
                  AND processing_status = 'completed'
                  AND (is_duplicate = FALSE OR is_duplicate IS NULL)
                ORDER BY feed_priority ASC, published_at DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.execute(query)
            rows = cursor.fetchall()

            articles = [self._row_to_article(row) for row in rows]

            logger.info("articles_fetched_for_summarization", count=len(articles))

            return articles

        except Exception as e:
            logger.error("fetch_articles_for_summarization_failed", error=str(e))
            raise DatabaseError(f"Failed to fetch articles for summarization: {e}") from e

    def get_pending_articles(self, stage: str, limit: Optional[int] = None) -> List[Article]:
        """Get articles at a specific pipeline stage.

        Args:
            stage: Pipeline stage (collected, filtered, scraped, summarized).
            limit: Maximum number of articles to return.

        Returns:
            List of articles at the specified stage.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                SELECT * FROM articles
                WHERE pipeline_stage = ?
                  AND processing_status IN ('pending', 'failed')
                  AND error_count < 3
                ORDER BY feed_priority ASC, published_at DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.execute(query, (stage,))
            rows = cursor.fetchall()

            articles = [self._row_to_article(row) for row in rows]

            return articles

        except Exception as e:
            logger.error("fetch_pending_articles_failed", stage=stage, error=str(e))
            raise DatabaseError(f"Failed to fetch pending articles: {e}") from e

    def find_by_url_hash(self, url_hash: str) -> Optional[Article]:
        """Find article by URL hash.

        Args:
            url_hash: Article URL hash.

        Returns:
            Article if found, None otherwise.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = "SELECT * FROM articles WHERE url_hash = ?"
            cursor = self.db.execute(query, (url_hash,))
            row = cursor.fetchone()

            if row:
                return self._row_to_article(row)

            return None

        except Exception as e:
            logger.error("find_by_url_hash_failed", url_hash=url_hash, error=str(e))
            raise DatabaseError(f"Failed to find article: {e}") from e

    def _article_exists(self, url_hash: str) -> bool:
        """Check if article with URL hash exists.

        Args:
            url_hash: Article URL hash.

        Returns:
            True if article exists, False otherwise.
        """
        query = "SELECT COUNT(*) FROM articles WHERE url_hash = ?"
        cursor = self.db.execute(query, (url_hash,))
        count = cursor.fetchone()[0]
        return count > 0

    def _row_to_article(self, row) -> Article:
        """Convert database row to Article object.

        Args:
            row: SQLite row object.

        Returns:
            Article object.
        """
        # Parse JSON fields
        key_points = None
        if row["key_points"]:
            key_points = json.loads(row["key_points"])

        entities = None
        if row["entities"]:
            entities = json.loads(row["entities"])

        return Article(
            id=row["id"],
            url=row["url"],
            normalized_url=row["normalized_url"],
            url_hash=row["url_hash"],
            title=row["title"],
            source=row["source"],
            published_at=_parse_datetime(row["published_at"]),
            collected_at=_parse_datetime(row["collected_at"]),
            feed_priority=row["feed_priority"],
            is_match=row["is_match"],
            confidence=row["confidence"],
            topic=row["topic"],
            classification_reason=row["classification_reason"],
            filtered_at=_parse_datetime(row["filtered_at"]),
            content=row["content"],
            author=row["author"],
            content_length=row["content_length"],
            extraction_method=row["extraction_method"],
            extraction_quality=row["extraction_quality"],
            scraped_at=_parse_datetime(row["scraped_at"]),
            summary_title=row["summary_title"],
            summary=row["summary"],
            key_points=key_points,
            entities=entities,
            summarized_at=_parse_datetime(row["summarized_at"]),
            pipeline_stage=row["pipeline_stage"],
            processing_status=row["processing_status"],
            error_message=row["error_message"],
            error_count=row["error_count"],
            is_duplicate=row["is_duplicate"] if row["is_duplicate"] is not None else False,
            canonical_url_hash=row["canonical_url_hash"],
            run_id=row["run_id"],
            created_at=_parse_datetime(row["created_at"]),
            updated_at=_parse_datetime(row["updated_at"]),
        )

    def save_duplicate_groups(
        self,
        groups: List[DuplicateGroup],
        run_id: str,
    ) -> int:
        """Save duplicate groups to database and mark duplicate articles.

        Args:
            groups: List of DuplicateGroup objects from detector.
            run_id: Pipeline run identifier.

        Returns:
            Number of articles marked as duplicates.

        Raises:
            DatabaseError: If database operation fails.
        """
        if not groups:
            return 0

        logger.info("saving_duplicate_groups", count=len(groups), run_id=run_id)

        try:
            total_duplicates = 0

            for group in groups:
                # Insert duplicate group record
                group_query = """
                    INSERT INTO duplicate_groups (
                        canonical_url_hash, confidence, duplicate_count,
                        detected_at, run_id
                    ) VALUES (?, ?, ?, ?, ?)
                """

                group_params = (
                    group.canonical_url_hash,
                    group.confidence,
                    len(group.duplicate_url_hashes),
                    group.detected_at,
                    run_id,
                )

                cursor = self.db.execute(group_query, group_params)
                group_id = cursor.lastrowid

                # Insert duplicate members and update articles
                for dup_hash in group.duplicate_url_hashes:
                    # Insert member record
                    member_query = """
                        INSERT INTO duplicate_members (
                            group_id, duplicate_url_hash, comparison_confidence
                        ) VALUES (?, ?, ?)
                    """
                    self.db.execute(member_query, (group_id, dup_hash, group.confidence))

                    # Mark article as duplicate
                    update_query = """
                        UPDATE articles
                        SET is_duplicate = TRUE,
                            canonical_url_hash = ?,
                            updated_at = ?
                        WHERE url_hash = ?
                    """
                    self.db.execute(
                        update_query,
                        (group.canonical_url_hash, datetime.now(), dup_hash),
                    )
                    total_duplicates += 1

            self.db.commit()

            logger.info(
                "duplicate_groups_saved",
                groups=len(groups),
                duplicates_marked=total_duplicates,
            )

            return total_duplicates

        except Exception as e:
            self.db.rollback()
            logger.error("save_duplicate_groups_failed", error=str(e))
            raise DatabaseError(f"Failed to save duplicate groups: {e}") from e

    def get_articles_for_deduplication(self, limit: Optional[int] = None) -> List[Article]:
        """Get scraped articles that need semantic deduplication.

        Args:
            limit: Maximum number of articles to return.

        Returns:
            List of articles ready for deduplication check.

        Raises:
            DatabaseError: If database operation fails.
        """
        try:
            query = """
                SELECT * FROM articles
                WHERE pipeline_stage = 'scraped'
                  AND processing_status = 'completed'
                  AND (is_duplicate = FALSE OR is_duplicate IS NULL)
                ORDER BY published_at DESC, feed_priority ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.db.execute(query)
            rows = cursor.fetchall()

            articles = [self._row_to_article(row) for row in rows]

            logger.info("articles_fetched_for_deduplication", count=len(articles))

            return articles

        except Exception as e:
            logger.error("fetch_articles_for_deduplication_failed", error=str(e))
            raise DatabaseError(f"Failed to fetch articles for deduplication: {e}") from e

    def save_article_images(self, images: List[ArticleImage]) -> int:
        """Save article images to database.

        Args:
            images: List of ArticleImage objects to save

        Returns:
            Number of images saved

        Raises:
            DatabaseError: If database operation fails
        """
        if not images:
            return 0

        try:
            saved_count = 0

            for image in images:
                # Skip if no article_id
                if not image.article_id:
                    logger.warning("image_missing_article_id", url=image.image_url)
                    continue

                # Insert or ignore (UNIQUE constraint on article_id + image_url)
                query = """
                    INSERT OR IGNORE INTO article_images (
                        article_id, image_url, local_path, image_width, image_height,
                        format, file_size, extraction_quality, is_featured,
                        extraction_method, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                params = (
                    image.article_id,
                    image.image_url,
                    image.local_path,
                    image.image_width,
                    image.image_height,
                    image.format,
                    image.file_size,
                    image.extraction_quality,
                    1 if image.is_featured else 0,
                    image.extraction_method,
                    image.created_at,
                )

                self.db.execute(query, params)
                saved_count += 1

            self.db.commit()

            logger.info("article_images_saved", count=saved_count)

            return saved_count

        except Exception as e:
            self.db.rollback()
            logger.error("save_article_images_failed", error=str(e))
            raise DatabaseError(f"Failed to save article images: {e}") from e

    def get_article_images(self, article_id: int) -> List[ArticleImage]:
        """Get images for an article.

        Args:
            article_id: Article database ID

        Returns:
            List of ArticleImage objects

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = """
                SELECT
                    id, article_id, image_url, local_path, image_width, image_height,
                    format, file_size, extraction_quality, is_featured,
                    extraction_method, created_at
                FROM article_images
                WHERE article_id = ?
                ORDER BY is_featured DESC, id ASC
            """

            cursor = self.db.execute(query, (article_id,))
            rows = cursor.fetchall()

            images = []
            for row in rows:
                image = ArticleImage(
                    id=row[0],
                    article_id=row[1],
                    image_url=row[2],
                    local_path=row[3],
                    image_width=row[4],
                    image_height=row[5],
                    format=row[6],
                    file_size=row[7],
                    extraction_quality=row[8],
                    is_featured=bool(row[9]),
                    extraction_method=row[10],
                    created_at=_parse_datetime(row[11]) or datetime.now(),
                )
                images.append(image)

            logger.debug("article_images_fetched", article_id=article_id, count=len(images))

            return images

        except Exception as e:
            logger.error("fetch_article_images_failed", article_id=article_id, error=str(e))
            raise DatabaseError(f"Failed to fetch article images: {e}") from e

    def delete_article_images(self, article_id: int) -> int:
        """Delete all images for an article.

        Args:
            article_id: Article database ID

        Returns:
            Number of images deleted

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = "DELETE FROM article_images WHERE article_id = ?"
            cursor = self.db.execute(query, (article_id,))
            deleted_count = cursor.rowcount

            self.db.commit()

            logger.info("article_images_deleted", article_id=article_id, count=deleted_count)

            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error("delete_article_images_failed", article_id=article_id, error=str(e))
            raise DatabaseError(f"Failed to delete article images: {e}") from e
