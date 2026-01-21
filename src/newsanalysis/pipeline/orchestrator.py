"""Pipeline orchestrator for coordinating all processing stages."""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from newsanalysis.core.config import Config, FeedConfig, PipelineConfig
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.database.digest_repository import DigestRepository
from newsanalysis.database.repository import ArticleRepository
from newsanalysis.integrations.provider_factory import ProviderFactory
from newsanalysis.core.enums import ExtractionMethod
from newsanalysis.pipeline.collectors import create_collector
from newsanalysis.pipeline.dedup import DuplicateDetector
from newsanalysis.pipeline.filters.ai_filter import AIFilter
from newsanalysis.pipeline.formatters import (
    GermanReportFormatter,
    JSONFormatter,
    MarkdownFormatter,
)
from newsanalysis.pipeline.generators import DigestGenerator
from newsanalysis.pipeline.scrapers import create_scraper
from newsanalysis.pipeline.summarizers import ArticleSummarizer
from newsanalysis.pipeline.extractors.image_extractor import ImageExtractor
from newsanalysis.services.cache_service import CacheService
from newsanalysis.services.config_loader import ConfigLoader, load_feeds_config
from newsanalysis.services.digest_formatter import HtmlEmailFormatter
from newsanalysis.services.email_service import OutlookEmailService
from newsanalysis.services.image_cache import ImageCache
from newsanalysis.services.image_download_service import ImageDownloadService
from newsanalysis.services.metrics_tracker import MetricsTracker
from newsanalysis.utils.exceptions import PipelineError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the news analysis pipeline.

    Coordinates: Collection → Filtering → (Scraping → Summarization → Digest)
    """

    def __init__(
        self,
        config: Config,
        db: DatabaseConnection,
        pipeline_config: Optional[PipelineConfig] = None,
    ):
        """Initialize pipeline orchestrator.

        Args:
            config: Application configuration.
            db: Database connection.
            pipeline_config: Pipeline execution configuration.
        """
        self.config = config
        self.db = db
        self.pipeline_config = pipeline_config or PipelineConfig()

        # Generate run ID
        self.run_id = self._generate_run_id()

        # Initialize repositories
        self.repository = ArticleRepository(db)
        self.digest_repository = DigestRepository(db)

        # Initialize cache service
        self.cache_service = CacheService(db.conn)

        # Initialize config loader
        self.config_loader = ConfigLoader(Path("config"))

        # Initialize provider factory
        self.provider_factory = ProviderFactory(
            config=config,
            db=db,
            run_id=self.run_id,
        )

        # Initialize AI filter with classification client (DeepSeek by default)
        classification_client = self.provider_factory.get_classification_client()
        self.ai_filter = AIFilter(
            llm_client=classification_client,
            config=config,
            cache_service=self.cache_service,
        )

        # Initialize scrapers
        self.trafilatura_scraper = create_scraper(
            method=ExtractionMethod.TRAFILATURA,
            timeout=config.request_timeout_sec,
        )
        self.playwright_scraper = create_scraper(
            method=ExtractionMethod.PLAYWRIGHT,
            timeout=config.request_timeout_sec,
        )

        # Initialize duplicate detector with classification client (DeepSeek - cheap)
        dedup_client = self.provider_factory.get_classification_client()
        self.duplicate_detector = DuplicateDetector(
            llm_client=dedup_client,
            confidence_threshold=0.75,
            time_window_hours=48,
        )

        # Initialize summarizer with summarization client (Gemini by default)
        summarization_client = self.provider_factory.get_summarization_client()
        self.summarizer = ArticleSummarizer(
            llm_client=summarization_client,
            cache_service=self.cache_service,
        )

        # Initialize digest generator with digest client (Gemini by default)
        digest_client = self.provider_factory.get_digest_client()
        self.digest_generator = DigestGenerator(
            llm_client=digest_client,
            article_repo=self.repository,
            digest_repo=self.digest_repository,
            config_loader=self.config_loader,
        )

        # Initialize formatters
        self.json_formatter = JSONFormatter()
        self.markdown_formatter = MarkdownFormatter()
        self.german_formatter = GermanReportFormatter()

        # Initialize image extraction services
        self.image_extractor = ImageExtractor(
            timeout=config.request_timeout_sec,
            max_images=5,
        )
        self.image_cache = ImageCache(
            cache_root=Path("cache"),
            days_to_keep=30,
        )

        # Initialize metrics tracker
        self.metrics = MetricsTracker()

        logger.info("pipeline_initialized", run_id=self.run_id, mode=self.pipeline_config.mode)

    async def run(self) -> Dict[str, int]:
        """Run the pipeline.

        Returns:
            Statistics dict with counts for each stage.

        Raises:
            PipelineError: If pipeline execution fails.
        """
        logger.info("pipeline_starting", run_id=self.run_id)

        # Start metrics tracking
        self.metrics.start_pipeline()

        # Track pipeline run
        self._start_pipeline_run()

        try:
            stats = {
                "collected": 0,
                "filtered": 0,
                "matched": 0,
                "rejected": 0,
                "scraped": 0,
                "images_extracted": 0,
                "images_downloaded": 0,
                "deduplicated": 0,
                "duplicates_found": 0,
                "summarized": 0,
                "digested": 0,
            }

            # Stage 1: Collection
            if not self.pipeline_config.skip_collection:
                collected_count = await self._run_collection()
                stats["collected"] = collected_count

            # Stage 2: Filtering
            if not self.pipeline_config.skip_filtering:
                filter_stats = await self._run_filtering()
                stats["filtered"] = filter_stats["total"]
                stats["matched"] = filter_stats["matched"]
                stats["rejected"] = filter_stats["rejected"]

            # Stage 3: Scraping
            if not self.pipeline_config.skip_scraping:
                scraped_count = await self._run_scraping()
                stats["scraped"] = scraped_count

            # Stage 3.5: Image Extraction and Download
            if not self.pipeline_config.skip_scraping:
                image_stats = await self._run_image_extraction()
                stats["images_extracted"] = image_stats["extracted"]
                stats["images_downloaded"] = image_stats["downloaded"]

            # Stage 3.6: Semantic Deduplication
            if not self.pipeline_config.skip_summarization:
                dedup_stats = await self._run_deduplication()
                stats["deduplicated"] = dedup_stats["checked"]
                stats["duplicates_found"] = dedup_stats["duplicates"]

            # Stage 4: Summarization
            if not self.pipeline_config.skip_summarization:
                summarized_count = await self._run_summarization()
                stats["summarized"] = summarized_count

            # Stage 5: Digest Generation
            if not self.pipeline_config.skip_digest:
                digest_count = await self._run_digest_generation()
                stats["digested"] = digest_count

                # Stage 6: Email Sending (if enabled and digest was generated)
                if digest_count > 0 and self.config.email_auto_send:
                    email_sent = await self._run_email_sending(pipeline_stats=stats)
                    stats["email_sent"] = 1 if email_sent else 0

            # Complete pipeline run
            self._complete_pipeline_run(stats, success=True)

            # Log comprehensive metrics
            self.metrics.log_metrics_summary()

            # Check health status
            health = self.metrics.check_health()
            logger.info("pipeline_health_check", health_status=health["status"], warnings=health["warnings"], errors=health["errors"])

            # Log detailed run summary (deduplication, scrape failures, image issues)
            self._log_run_summary()

            logger.info("pipeline_completed", run_id=self.run_id, stats=stats)

            return stats

        except Exception as e:
            logger.error("pipeline_failed", run_id=self.run_id, error=str(e))
            self._complete_pipeline_run({}, success=False, error=str(e))

            # Log metrics even on failure
            self.metrics.log_metrics_summary()

            raise PipelineError(f"Pipeline execution failed: {e}") from e

    async def _run_collection(self) -> int:
        """Run news collection stage.

        Returns:
            Number of articles collected.
        """
        logger.info("stage_collection_starting")

        # Load feed configurations
        feeds = load_feeds_config(Path("config"))

        # Filter enabled feeds
        enabled_feeds = [f for f in feeds if f.enabled]

        logger.info("feeds_loaded", total=len(feeds), enabled=len(enabled_feeds))

        # Collect from all feeds
        total_collected = 0
        total_saved = 0

        for feed in enabled_feeds:
            try:
                # Create collector for feed type
                collector = create_collector(feed, timeout=self.config.request_timeout_sec)

                # Collect articles
                articles = await collector.collect()

                # Apply limit if configured
                if self.pipeline_config.limit:
                    articles = articles[: self.pipeline_config.limit]

                # Save to database
                saved_count = self.repository.save_collected_articles(articles, self.run_id)

                total_collected += len(articles)
                total_saved += saved_count

                # Rate limiting
                if feed.rate_limit_seconds > 0:
                    await asyncio.sleep(feed.rate_limit_seconds)

            except Exception as e:
                logger.error(
                    "feed_collection_failed",
                    feed_name=feed.name,
                    error=str(e),
                )
                # Continue with other feeds

        logger.info(
            "stage_collection_complete",
            collected=total_collected,
            saved=total_saved,
            duplicates=total_collected - total_saved,
        )

        return total_saved

    async def _run_filtering(self) -> Dict[str, int]:
        """Run AI filtering stage.

        Returns:
            Statistics dict with total, matched, rejected counts.
        """
        logger.info("stage_filtering_starting")

        # Get articles that need filtering (no limit - process all collected articles)
        articles = self.repository.get_pending_articles("collected", limit=None)

        if not articles:
            logger.info("no_articles_to_filter")
            return {"total": 0, "matched": 0, "rejected": 0}

        logger.info("articles_to_filter", count=len(articles))

        # Filter articles
        classifications = await self.ai_filter.filter_articles(articles)

        # Update database with classifications
        matched = 0
        rejected = 0

        for article, classification in zip(articles, classifications):
            self.repository.update_classification(article.url_hash, classification)

            if classification.is_match:
                matched += 1
            else:
                rejected += 1

        logger.info(
            "stage_filtering_complete",
            total=len(articles),
            matched=matched,
            rejected=rejected,
        )

        return {
            "total": len(articles),
            "matched": matched,
            "rejected": rejected,
        }

    async def _run_scraping(self) -> int:
        """Run content scraping stage.

        Returns:
            Number of articles scraped successfully.
        """
        logger.info("stage_scraping_starting")

        # Get articles that need scraping (matched articles from filtering - no limit)
        articles = self.repository.get_articles_for_scraping(limit=None)

        if not articles:
            logger.info("no_articles_to_scrape")
            return 0

        logger.info("articles_to_scrape", count=len(articles))

        scraped_count = 0
        failed_count = 0

        for article in articles:
            try:
                # Try Trafilatura first (faster)
                scraped_content = await self.trafilatura_scraper.extract(str(article.url))

                # Fall back to Playwright if Trafilatura fails
                if not scraped_content:
                    logger.info("trafilatura_failed_trying_playwright", url=str(article.url))
                    scraped_content = await self.playwright_scraper.extract(str(article.url))

                if scraped_content:
                    # Update database
                    self.repository.update_scraped_content(article.url_hash, scraped_content)
                    scraped_count += 1
                else:
                    # Mark as failed
                    self.repository.mark_article_failed(
                        article.url_hash,
                        "Content extraction failed with both methods",
                    )
                    failed_count += 1

            except Exception as e:
                logger.error(
                    "article_scraping_failed",
                    url=str(article.url),
                    error=str(e),
                )
                self.repository.mark_article_failed(
                    article.url_hash,
                    f"Scraping error: {str(e)[:200]}",
                )
                failed_count += 1

        logger.info(
            "stage_scraping_complete",
            total=len(articles),
            scraped=scraped_count,
            failed=failed_count,
        )

        return scraped_count

    async def _run_image_extraction(self) -> Dict[str, int]:
        """Run image extraction and download stage.

        Returns:
            Statistics dict with extracted and downloaded counts.
        """
        logger.info("stage_image_extraction_starting")

        # Start timer for image extraction stage
        self.metrics.start_timer("image_extraction")

        # Get articles that have been scraped
        articles = self.repository.get_articles_for_deduplication(limit=None)

        if not articles:
            logger.info("no_articles_for_image_extraction")
            self.metrics.record_stage_metrics("image_extraction", {
                "articles_processed": 0,
                "images_extracted": 0,
                "images_downloaded": 0,
                "duration_seconds": self.metrics.stop_timer("image_extraction"),
            })
            return {"extracted": 0, "downloaded": 0}

        logger.info("articles_for_image_extraction", count=len(articles))

        total_extracted = 0
        total_downloaded = 0
        total_failed = 0
        total_cached = 0

        # Use ImageDownloadService as context manager
        async with ImageDownloadService(
            image_cache=self.image_cache,
            timeout=self.config.request_timeout_sec,
            max_concurrent=10,
            max_retries=3,
        ) as download_service:
            for article in articles:
                try:
                    # Extract image URLs
                    images = await self.image_extractor.extract_images(
                        url=str(article.url),
                        html_content=None,  # Will be fetched by extractor
                    )

                    if images:
                        total_extracted += len(images)

                        # Set article_id on images
                        for img in images:
                            img.article_id = article.id

                        # Download images
                        downloaded_images = await download_service.download_article_images(
                            article=article,
                            images=images,
                        )

                        if downloaded_images:
                            total_downloaded += len(downloaded_images)

                            # Count cached vs new downloads
                            for img in downloaded_images:
                                if img.local_path and Path(img.local_path).exists():
                                    total_cached += 1

                            # Save to database
                            self.repository.save_article_images(downloaded_images)

                            logger.info(
                                "article_images_processed",
                                article_id=article.id,
                                extracted=len(images),
                                downloaded=len(downloaded_images),
                            )

                except Exception as e:
                    total_failed += 1
                    logger.error(
                        "image_extraction_failed",
                        article_id=article.id,
                        url=str(article.url),
                        error=str(e),
                        exc_info=True,
                    )
                    # Continue with other articles - don't fail pipeline

        # Stop timer and record stage metrics
        duration = self.metrics.stop_timer("image_extraction")

        # Update global metrics
        self.metrics.set_metric("images_extracted_count", total_extracted)
        self.metrics.set_metric("images_downloaded_count", total_downloaded)
        self.metrics.set_metric("images_failed_count", total_failed)
        self.metrics.set_metric("images_cached_count", total_cached)

        # Record stage-specific metrics
        self.metrics.record_stage_metrics("image_extraction", {
            "articles_processed": len(articles),
            "images_extracted": total_extracted,
            "images_downloaded": total_downloaded,
            "images_failed": total_failed,
            "images_cached": total_cached,
            "duration_seconds": round(duration, 2),
        })

        logger.info(
            "stage_image_extraction_complete",
            articles=len(articles),
            extracted=total_extracted,
            downloaded=total_downloaded,
            failed=total_failed,
            cached=total_cached,
            duration_seconds=round(duration, 2),
        )

        return {
            "extracted": total_extracted,
            "downloaded": total_downloaded,
        }

    async def _run_deduplication(self) -> Dict[str, int]:
        """Run semantic deduplication stage.

        Detects articles from different sources that cover the same news story.
        Marks duplicates so they are skipped during summarization.

        Returns:
            Statistics dict with checked and duplicates counts.
        """
        logger.info("stage_deduplication_starting")

        # Get articles that need deduplication check
        articles = self.repository.get_articles_for_deduplication(limit=None)

        if len(articles) < 2:
            logger.info("insufficient_articles_for_deduplication", count=len(articles))
            return {"checked": len(articles), "duplicates": 0}

        logger.info("articles_to_deduplicate", count=len(articles))

        try:
            # Run duplicate detection
            duplicate_groups, duplicate_hashes = await self.duplicate_detector.detect_duplicates(
                articles=articles,
                max_concurrent=10,
            )

            # Save duplicate groups to database
            if duplicate_groups:
                self.repository.save_duplicate_groups(duplicate_groups, self.run_id)

            logger.info(
                "stage_deduplication_complete",
                checked=len(articles),
                groups=len(duplicate_groups),
                duplicates=len(duplicate_hashes),
            )

            return {
                "checked": len(articles),
                "duplicates": len(duplicate_hashes),
            }

        except Exception as e:
            logger.error("deduplication_failed", error=str(e))
            # Don't fail the pipeline - deduplication is optional
            return {"checked": len(articles), "duplicates": 0}

    async def _run_summarization(self) -> int:
        """Run article summarization stage.

        Returns:
            Number of articles summarized successfully.
        """
        logger.info("stage_summarization_starting")

        # Get articles that need summarization (scraped articles - no limit)
        articles = self.repository.get_articles_for_summarization(limit=None)

        if not articles:
            logger.info("no_articles_to_summarize")
            return 0

        logger.info("articles_to_summarize", count=len(articles))

        summarized_count = 0
        failed_count = 0

        for article in articles:
            try:
                # Generate summary
                summary = await self.summarizer.summarize(
                    title=article.title,
                    source=article.source,
                    content=article.content or "",
                    url=str(article.url),
                )

                if summary:
                    # Update database
                    self.repository.update_summary(article.url_hash, summary)
                    summarized_count += 1
                else:
                    # Mark as failed
                    self.repository.mark_article_failed(
                        article.url_hash,
                        "Summarization failed",
                    )
                    failed_count += 1

            except Exception as e:
                logger.error(
                    "article_summarization_failed",
                    url=str(article.url),
                    error=str(e),
                )
                self.repository.mark_article_failed(
                    article.url_hash,
                    f"Summarization error: {str(e)[:200]}",
                )
                failed_count += 1

        logger.info(
            "stage_summarization_complete",
            total=len(articles),
            summarized=summarized_count,
            failed=failed_count,
        )

        return summarized_count

    async def _run_digest_generation(self) -> int:
        """Run digest generation stage.

        Returns:
            Number of digests generated (0 or 1).
        """
        logger.info("stage_digest_generation_starting")

        try:
            # Get today's date for digest
            digest_date = datetime.now().date()

            # Generate digest
            digest = await self.digest_generator.generate_digest(
                digest_date=digest_date,
                run_id=self.run_id,
                incremental=False,
                today_only=self.pipeline_config.today_only,
            )

            logger.info(
                "digest_generated",
                date=str(digest_date),
                version=digest.version,
                articles=digest.article_count,
            )

            # Format outputs
            json_output = self.json_formatter.format(digest)
            markdown_output = self.markdown_formatter.format(digest)
            german_report = self.german_formatter.format(digest)

            logger.info("digest_formatted", formats=3)

            # Save digest to database
            digest_id = self.digest_repository.save_digest(
                digest=digest,
                json_output=json_output,
                markdown_output=markdown_output,
                german_report=german_report,
            )

            # Digest saved successfully - from here on, we consider it a success
            # even if post-save operations fail
            digest_saved = True

            # Mark articles as digested AFTER successful save
            # This ensures we don't have orphaned "digested" articles if save fails
            try:
                await self.digest_generator.mark_articles_digested(
                    digest.articles, digest.date, digest.version
                )
            except Exception as e:
                logger.error("mark_articles_digested_failed", error=str(e))
                # Continue - digest is still valid

            # Write outputs to files
            try:
                await self._write_digest_outputs(
                    digest_date, json_output, german_report
                )
            except Exception as e:
                logger.error("digest_file_write_failed", error=str(e))
                # Continue - digest is still valid

            logger.info("stage_digest_generation_complete", digest_id=digest_id)

            return 1

        except Exception as e:
            logger.error("digest_generation_failed", error=str(e))
            # Don't fail the entire pipeline - digest generation is optional
            return 0

    async def _write_digest_outputs(
        self,
        digest_date,
        json_output: str,
        german_report: str,
    ) -> None:
        """Write digest outputs to files.

        Args:
            digest_date: Date of the digest.
            json_output: JSON formatted output.
            german_report: German report output.
        """
        try:
            # Ensure output directory exists
            digest_dir = self.config.output_dir / "digests"
            digest_dir.mkdir(parents=True, exist_ok=True)

            # Use run_id timestamp for unique filenames (avoids overwriting)
            # run_id format: YYYYMMDD_HHMMSS_uuid -> extract YYYYMMDD_HHMMSS
            timestamp = "_".join(self.run_id.split("_")[:2])

            # Write JSON
            json_path = digest_dir / f"bonitaets_analyse_{digest_date}_{timestamp}.json"
            json_path.write_text(json_output, encoding="utf-8")
            logger.info("digest_file_written", file=str(json_path))

            # Write German report (primary output)
            german_path = digest_dir / f"bonitaets_analyse_{digest_date}_{timestamp}.md"
            german_path.write_text(german_report, encoding="utf-8")
            logger.info("digest_file_written", file=str(german_path))

        except Exception as e:
            logger.error("digest_file_write_failed", error=str(e))
            # Don't raise - files are secondary to database

    async def _run_email_sending(self, pipeline_stats: Optional[Dict[str, int]] = None) -> bool:
        """Send digest email to configured recipients.

        Args:
            pipeline_stats: Optional dict with collected, filtered, rejected, deduplicated counts.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        logger.info("stage_email_sending_starting")

        recipients = self.config.email_recipient_list
        if not recipients:
            logger.warning("email_skipped", reason="No recipients configured")
            return False

        try:
            # Get today's digest
            digest_date = datetime.now().date()
            digest_data = self.digest_repository.get_digest_by_date(digest_date)

            if not digest_data:
                logger.warning("email_skipped", reason="No digest found for today")
                return False

            # Query feed stats for today
            feed_stats = self._get_feed_stats()

            # Format as HTML with images
            formatter = HtmlEmailFormatter(article_repository=self.repository)
            html_body, image_cid_mapping = formatter.format_with_images(
                digest_data,
                include_images=True,
                pipeline_stats=pipeline_stats,
                feed_stats=feed_stats,
            )

            # Create dynamic subject line with top article title
            top_title = formatter.get_top_article_title(digest_data, max_length=50)

            if top_title:
                subject = f"Creditreform News-Digest: {top_title}"
            else:
                # Fallback to date-based subject when no articles
                subject = f"Creditreform News-Digest: {digest_date.strftime('%d.%m.%Y')}"

            # Send email with images
            with OutlookEmailService() as email_service:
                if not email_service.is_available():
                    logger.warning("email_skipped", reason="Outlook not available")
                    return False

                result = email_service.send_html_email_with_images(
                    to=recipients,
                    subject=subject,
                    html_body=html_body,
                    image_attachments=image_cid_mapping,
                    bcc=self.config.email_bcc_list,
                    preview=False,
                )

                if result.success:
                    logger.info(
                        "stage_email_sending_complete",
                        recipients=", ".join(recipients),
                        images_attached=len(image_cid_mapping),
                    )
                    return True
                else:
                    logger.error("email_send_failed", error=result.message)
                    return False

        except Exception as e:
            logger.error("email_send_failed", error=str(e))
            return False

    def _get_feed_stats(self) -> List[Dict[str, Any]]:
        """Get article statistics grouped by feed source for today.

        Returns:
            List of dicts with source, total, matched, rejected counts.
        """
        try:
            query = """
                SELECT
                    source,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_match = 1 THEN 1 ELSE 0 END) as matched,
                    SUM(CASE WHEN is_match = 0 THEN 1 ELSE 0 END) as rejected
                FROM articles
                WHERE DATE(collected_at) = DATE('now')
                GROUP BY source
                ORDER BY total DESC
            """
            cursor = self.db.execute(query)
            rows = cursor.fetchall()

            return [
                {
                    "source": row[0] or "Unknown",
                    "total": row[1] or 0,
                    "matched": row[2] or 0,
                    "rejected": row[3] or 0,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("feed_stats_query_failed", error=str(e))
            return []

    def _generate_run_id(self) -> str:
        """Generate unique run ID.

        Returns:
            Run ID string (UUID + timestamp).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{timestamp}_{short_uuid}"

    def _start_pipeline_run(self) -> None:
        """Record pipeline run start in database."""
        try:
            query = """
                INSERT INTO pipeline_runs (
                    run_id, mode, started_at, status
                ) VALUES (?, ?, ?, ?)
            """

            params = (
                self.run_id,
                self.pipeline_config.mode,
                datetime.now(),
                "running",
            )

            self.db.execute(query, params)
            self.db.commit()

        except Exception as e:
            logger.error("failed_to_record_pipeline_start", error=str(e))

    def _complete_pipeline_run(
        self,
        stats: Dict[str, int],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record pipeline run completion in database.

        Args:
            stats: Pipeline statistics.
            success: Whether pipeline succeeded.
            error: Error message if failed.
        """
        try:
            completed_at = datetime.now()

            # Calculate duration
            start_result = self.db.execute(
                "SELECT started_at FROM pipeline_runs WHERE run_id = ?",
                (self.run_id,)
            )
            started_at_row = start_result.fetchone()
            duration_seconds = None
            if started_at_row:
                started_at = datetime.fromisoformat(started_at_row[0])
                duration_seconds = (completed_at - started_at).total_seconds()

            # Calculate total cost and tokens from api_calls
            cost_result = self.db.execute(
                """
                SELECT COALESCE(SUM(cost), 0.0), COALESCE(SUM(total_tokens), 0)
                FROM api_calls
                WHERE run_id = ?
                """,
                (self.run_id,)
            )
            cost_row = cost_result.fetchone()
            total_cost = cost_row[0] if cost_row else 0.0
            total_tokens = cost_row[1] if cost_row else 0

            query = """
                UPDATE pipeline_runs
                SET completed_at = ?,
                    status = ?,
                    collected_count = ?,
                    filtered_count = ?,
                    scraped_count = ?,
                    summarized_count = ?,
                    digested_count = ?,
                    duration_seconds = ?,
                    total_cost = ?,
                    total_tokens = ?,
                    error_message = ?
                WHERE run_id = ?
            """

            params = (
                completed_at,
                "completed" if success else "failed",
                stats.get("collected", 0),
                stats.get("filtered", 0),
                stats.get("scraped", 0),
                stats.get("summarized", 0),
                stats.get("digested", 0),
                duration_seconds,
                total_cost,
                total_tokens,
                error,
                self.run_id,
            )

            self.db.execute(query, params)
            self.db.commit()

        except Exception as e:
            logger.error("failed_to_record_pipeline_completion", error=str(e))

    def _log_run_summary(self) -> None:
        """Log detailed summary of what happened to articles in this run.

        Logs information about:
        - Semantic deduplication (which articles were marked as duplicates)
        - Scrape failures (which articles failed to scrape and why)
        - Image extraction issues
        """
        try:
            self._log_deduplication_summary()
            self._log_scrape_failures_summary()
            self._log_image_issues_summary()
        except Exception as e:
            logger.warning("run_summary_logging_failed", error=str(e))

    def _log_deduplication_summary(self) -> None:
        """Log detailed summary of deduplicated articles."""
        try:
            # Query duplicate groups from this run
            query = """
                SELECT
                    dg.canonical_url_hash,
                    dg.confidence,
                    dg.duplicate_count,
                    ca.title as canonical_title,
                    ca.source as canonical_source
                FROM duplicate_groups dg
                JOIN articles ca ON dg.canonical_url_hash = ca.url_hash
                WHERE dg.run_id = ?
                ORDER BY dg.duplicate_count DESC
            """
            cursor = self.db.execute(query, (self.run_id,))
            groups = cursor.fetchall()

            if not groups:
                logger.info("dedup_summary", message="No semantic duplicates detected in this run")
                return

            # Log summary header
            total_duplicates = sum(row[2] for row in groups)
            logger.info(
                "dedup_summary",
                total_groups=len(groups),
                total_duplicates=total_duplicates,
                message=f"Found {len(groups)} duplicate groups with {total_duplicates} duplicate articles"
            )

            # Log each duplicate group with its members
            for row in groups:
                canonical_hash, confidence, dup_count, canonical_title, canonical_source = row

                # Get the duplicate articles in this group
                member_query = """
                    SELECT
                        a.title,
                        a.source,
                        a.url
                    FROM duplicate_members dm
                    JOIN articles a ON dm.duplicate_url_hash = a.url_hash
                    JOIN duplicate_groups dg ON dm.group_id = dg.id
                    WHERE dg.canonical_url_hash = ?
                    ORDER BY a.collected_at
                """
                member_cursor = self.db.execute(member_query, (canonical_hash,))
                members = member_cursor.fetchall()

                # Truncate titles for readability
                canonical_title_short = (canonical_title[:60] + "...") if len(canonical_title) > 60 else canonical_title

                logger.info(
                    "dedup_group_detail",
                    canonical_title=canonical_title_short,
                    canonical_source=canonical_source,
                    duplicate_count=dup_count,
                    confidence=round(confidence, 2),
                )

                # Log each duplicate in the group
                for member in members:
                    member_title, member_source, member_url = member
                    member_title_short = (member_title[:60] + "...") if len(member_title) > 60 else member_title
                    logger.info(
                        "dedup_duplicate_article",
                        title=member_title_short,
                        source=member_source,
                        status="skipped (duplicate of above)",
                    )

        except Exception as e:
            logger.warning("dedup_summary_failed", error=str(e))

    def _log_scrape_failures_summary(self) -> None:
        """Log detailed summary of articles that failed to scrape."""
        try:
            # Query articles that failed scraping in this run
            query = """
                SELECT
                    title,
                    source,
                    url,
                    error_message,
                    error_count
                FROM articles
                WHERE run_id = ?
                  AND processing_status = 'failed'
                  AND pipeline_stage IN ('filtered', 'scraped')
                ORDER BY source, title
            """
            cursor = self.db.execute(query, (self.run_id,))
            failures = cursor.fetchall()

            if not failures:
                logger.info("scrape_failures_summary", message="No scrape failures in this run")
                return

            # Log summary header
            logger.info(
                "scrape_failures_summary",
                total_failures=len(failures),
                message=f"{len(failures)} articles failed to scrape"
            )

            # Log each failure
            for row in failures:
                title, source, url, error_message, error_count = row
                title_short = (title[:60] + "...") if len(title) > 60 else title

                # Extract key error type from message
                error_type = "Unknown"
                if error_message:
                    if "timeout" in error_message.lower():
                        error_type = "Timeout"
                    elif "403" in error_message or "forbidden" in error_message.lower():
                        error_type = "Blocked (403)"
                    elif "404" in error_message or "not found" in error_message.lower():
                        error_type = "Not Found (404)"
                    elif "connection" in error_message.lower():
                        error_type = "Connection Error"
                    elif "both methods" in error_message.lower():
                        error_type = "Content Extraction Failed"
                    else:
                        error_type = error_message[:50] if len(error_message) > 50 else error_message

                logger.info(
                    "scrape_failure_detail",
                    title=title_short,
                    source=source,
                    error_type=error_type,
                    attempts=error_count,
                )

        except Exception as e:
            logger.warning("scrape_failures_summary_failed", error=str(e))

    def _log_image_issues_summary(self) -> None:
        """Log detailed summary of image extraction issues."""
        try:
            # Query articles that were scraped but have no images
            query_no_images = """
                SELECT
                    a.title,
                    a.source,
                    a.url
                FROM articles a
                LEFT JOIN article_images ai ON a.id = ai.article_id
                WHERE a.run_id = ?
                  AND a.pipeline_stage IN ('scraped', 'summarized', 'digested')
                  AND a.processing_status = 'completed'
                  AND ai.id IS NULL
                ORDER BY a.source, a.title
            """
            cursor = self.db.execute(query_no_images, (self.run_id,))
            no_images = cursor.fetchall()

            # Query images that failed to download (have url but no local_path)
            query_failed_images = """
                SELECT
                    a.title,
                    a.source,
                    ai.image_url
                FROM article_images ai
                JOIN articles a ON ai.article_id = a.id
                WHERE a.run_id = ?
                  AND (ai.local_path IS NULL OR ai.local_path = '')
                ORDER BY a.source, a.title
            """
            cursor = self.db.execute(query_failed_images, (self.run_id,))
            failed_downloads = cursor.fetchall()

            # Query successful image extractions for context
            query_success = """
                SELECT COUNT(DISTINCT a.id) as article_count, COUNT(ai.id) as image_count
                FROM articles a
                JOIN article_images ai ON a.id = ai.article_id
                WHERE a.run_id = ?
                  AND ai.local_path IS NOT NULL
                  AND ai.local_path != ''
            """
            cursor = self.db.execute(query_success, (self.run_id,))
            success_row = cursor.fetchone()
            articles_with_images = success_row[0] if success_row else 0
            total_images = success_row[1] if success_row else 0

            # Log summary
            logger.info(
                "image_extraction_summary",
                articles_with_images=articles_with_images,
                total_images_downloaded=total_images,
                articles_without_images=len(no_images),
                failed_downloads=len(failed_downloads),
            )

            # Log articles without images (if any)
            if no_images:
                logger.info(
                    "image_issues_no_images",
                    count=len(no_images),
                    message=f"{len(no_images)} articles have no images extracted"
                )
                for row in no_images[:10]:  # Limit to first 10 to avoid spam
                    title, source, url = row
                    title_short = (title[:50] + "...") if len(title) > 50 else title
                    logger.debug(
                        "article_no_image",
                        title=title_short,
                        source=source,
                    )
                if len(no_images) > 10:
                    logger.info("image_issues_truncated", remaining=len(no_images) - 10)

            # Log failed image downloads (if any)
            if failed_downloads:
                logger.info(
                    "image_issues_failed_downloads",
                    count=len(failed_downloads),
                    message=f"{len(failed_downloads)} images failed to download"
                )
                for row in failed_downloads[:10]:  # Limit to first 10
                    title, source, image_url = row
                    title_short = (title[:40] + "...") if len(title) > 40 else title
                    # Extract domain from image URL
                    try:
                        from urllib.parse import urlparse
                        image_domain = urlparse(image_url).netloc
                    except Exception:
                        image_domain = "unknown"

                    logger.debug(
                        "image_download_failed",
                        article_title=title_short,
                        source=source,
                        image_domain=image_domain,
                    )
                if len(failed_downloads) > 10:
                    logger.info("image_failures_truncated", remaining=len(failed_downloads) - 10)

        except Exception as e:
            logger.warning("image_issues_summary_failed", error=str(e))
