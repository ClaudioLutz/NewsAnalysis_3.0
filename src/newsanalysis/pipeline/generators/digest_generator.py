"""Digest generator for creating daily news digests."""

from datetime import date
from typing import List, Optional

from newsanalysis.core.article import Article
from newsanalysis.core.digest import DailyDigest, MetaAnalysis
from newsanalysis.database.digest_repository import DigestRepository
from newsanalysis.database.repository import ArticleRepository
from newsanalysis.integrations.provider_factory import LLMClient
from newsanalysis.services.config_loader import ConfigLoader
from newsanalysis.utils.exceptions import PipelineError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class DigestGenerator:
    """Generator for creating daily news digests with meta-analysis."""

    def __init__(
        self,
        llm_client: LLMClient,
        article_repo: ArticleRepository,
        digest_repo: DigestRepository,
        config_loader: ConfigLoader,
    ):
        """Initialize digest generator.

        Args:
            llm_client: LLM client for API calls (Gemini, OpenAI, etc.).
            article_repo: Article repository.
            digest_repo: Digest repository.
            config_loader: Configuration loader for prompts.
        """
        self.llm_client = llm_client
        self.article_repo = article_repo
        self.digest_repo = digest_repo
        self.config_loader = config_loader

        # Load meta-analysis prompt configuration
        try:
            self.prompt_config = config_loader.load_prompt_config("meta_analysis")
            logger.info("meta_analysis_prompt_loaded")
        except Exception as e:
            logger.warning("meta_analysis_prompt_load_failed", error=str(e))
            self.prompt_config = None

    async def generate_digest(
        self,
        digest_date: date,
        run_id: str,
        incremental: bool = False,
    ) -> DailyDigest:
        """Generate daily digest with meta-analysis.

        Args:
            digest_date: Date for the digest.
            run_id: Pipeline run ID.
            incremental: Whether to create incremental update (version > 1).

        Returns:
            Daily digest object.

        Raises:
            PipelineError: If digest generation fails.
        """
        logger.info(
            "generating_digest",
            date=str(digest_date),
            incremental=incremental,
            run_id=run_id,
        )

        try:
            # Get summarized articles for the date
            articles = await self._get_digest_articles(digest_date)

            if not articles:
                logger.warning("no_articles_for_digest", date=str(digest_date))
                raise PipelineError(f"No summarized articles found for {digest_date}")

            logger.info("articles_retrieved", count=len(articles))

            # Generate meta-analysis
            meta_analysis = await self._generate_meta_analysis(articles, run_id)

            # Determine version
            version = self._get_next_version(digest_date, incremental)

            # Create digest
            digest = DailyDigest(
                date=digest_date,
                version=version,
                articles=articles,
                article_count=len(articles),
                cluster_count=None,  # TODO: Implement deduplication/clustering
                meta_analysis=meta_analysis,
                run_id=run_id,
            )

            # Mark articles as included in digest
            await self._mark_articles_digested(articles, digest_date, version)

            logger.info(
                "digest_generated",
                date=str(digest_date),
                version=version,
                article_count=len(articles),
            )

            return digest

        except Exception as e:
            logger.error("digest_generation_failed", error=str(e))
            raise PipelineError(f"Digest generation failed: {e}") from e

    async def _get_digest_articles(self, digest_date: date) -> List[Article]:
        """Get summarized articles for digest.

        Args:
            digest_date: Date to get articles for (used for logging only).

        Returns:
            List of summarized articles not yet included in a digest.
        """
        # Get all summarized articles not yet in a digest
        # Note: We don't filter by published_at date because:
        # 1. Articles may be published over multiple days
        # 2. The pipeline may run at midnight causing date mismatches
        # 3. What matters is: summarized + not yet digested
        cursor = self.article_repo.db.execute(
            """
            SELECT * FROM articles
            WHERE pipeline_stage = 'summarized'
            AND processing_status = 'completed'
            AND (included_in_digest = FALSE OR included_in_digest IS NULL)
            ORDER BY feed_priority ASC, confidence DESC, published_at DESC
            """,
        )

        rows = cursor.fetchall()

        # Convert to Article objects
        articles = []
        for row in rows:
            try:
                article = self.article_repo._row_to_article(row)
                articles.append(article)
            except Exception as e:
                logger.warning(
                    "article_conversion_failed", article_id=row["id"], error=str(e)
                )
                continue

        return articles

    async def _generate_meta_analysis(
        self, articles: List[Article], run_id: str
    ) -> MetaAnalysis:
        """Generate meta-analysis from articles.

        Args:
            articles: List of articles to analyze.
            run_id: Pipeline run ID.

        Returns:
            Meta-analysis object.

        Raises:
            PipelineError: If meta-analysis generation fails.
        """
        logger.info("generating_meta_analysis", article_count=len(articles))

        try:
            # Build articles summary for prompt
            articles_summary = self._build_articles_summary(articles)

            # Get prompts
            if self.prompt_config:
                system_prompt = self.prompt_config.get("system_prompt", "")
                user_template = self.prompt_config.get("user_prompt_template", "")
            else:
                # Fallback prompts
                system_prompt = "You are a senior analyst creating daily intelligence briefings."
                user_template = "Daily Articles Summary:\n{articles_summary}\n\nGenerate a meta-analysis identifying key themes, credit risk signals, regulatory updates, and market insights."

            user_prompt = user_template.format(articles_summary=articles_summary)

            # Call LLM for meta-analysis (uses Gemini by default via ProviderFactory)
            response = await self.llm_client.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                module="digest_generator",
                request_type="meta_analysis",
                response_format=MetaAnalysis,
                temperature=0.2,  # Slightly creative for analysis
            )

            # Extract MetaAnalysis from response
            meta_analysis = MetaAnalysis(**response["content"])

            logger.info(
                "meta_analysis_generated",
                themes=len(meta_analysis.key_themes),
                signals=len(meta_analysis.credit_risk_signals),
            )

            return meta_analysis

        except Exception as e:
            logger.error("meta_analysis_failed", error=str(e))
            # Return empty meta-analysis on failure
            return MetaAnalysis(
                key_themes=["Analysis unavailable"],
                credit_risk_signals=[],
                regulatory_updates=[],
                market_insights=[],
            )

    def _build_articles_summary(self, articles: List[Article]) -> str:
        """Build summary of articles for meta-analysis prompt.

        Args:
            articles: List of articles.

        Returns:
            Formatted summary string.
        """
        summaries = []

        for i, article in enumerate(articles, 1):
            summary_text = f"{i}. {article.title or article.summary_title or 'Untitled'}"

            if article.summary:
                summary_text += f"\n   Summary: {article.summary[:300]}..."

            if article.topic:
                summary_text += f"\n   Topic: {article.topic}"

            if article.entities:
                companies = article.entities.get("companies", [])
                if companies:
                    summary_text += f"\n   Companies: {', '.join(companies[:5])}"

            summaries.append(summary_text)

        return "\n\n".join(summaries)

    def _get_next_version(self, digest_date: date, incremental: bool) -> int:
        """Get next version number for digest.

        Args:
            digest_date: Date of the digest.
            incremental: Whether this is an incremental update.

        Returns:
            Version number.
        """
        if not incremental:
            return 1

        latest_version = self.digest_repo.get_latest_version(digest_date)
        return latest_version + 1

    async def _mark_articles_digested(
        self, articles: List[Article], digest_date: date, version: int
    ) -> None:
        """Mark articles as included in digest.

        Args:
            articles: Articles to mark.
            digest_date: Digest date.
            version: Digest version.
        """
        try:
            article_ids = [a.id for a in articles if a.id]

            if not article_ids:
                return

            placeholders = ",".join("?" * len(article_ids))

            self.article_repo.db.execute(
                f"""
                UPDATE articles
                SET included_in_digest = TRUE,
                    digest_date = ?,
                    digest_version = ?,
                    pipeline_stage = 'digested',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                """,
                (digest_date.isoformat(), version, *article_ids),
            )

            self.article_repo.db.commit()

            logger.info(
                "articles_marked_digested",
                count=len(article_ids),
                date=str(digest_date),
                version=version,
            )

        except Exception as e:
            self.article_repo.db.rollback()
            logger.error("mark_digested_failed", error=str(e))
            # Don't raise - this is not critical

    def get_stats(self) -> dict:
        """Get digest generation statistics.

        Returns:
            Statistics dictionary.
        """
        # TODO: Implement statistics tracking
        return {
            "total_digests_generated": 0,
            "avg_articles_per_digest": 0,
        }
