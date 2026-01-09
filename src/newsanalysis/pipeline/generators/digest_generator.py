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

        Note:
            This method does NOT mark articles as digested. The caller should
            call mark_articles_digested() AFTER successfully saving the digest
            to the database to avoid orphaned "digested" articles if save fails.
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

            # Determine version - auto-increment if digest exists for this date
            existing_version = self.digest_repo.get_latest_version(digest_date)
            if existing_version > 0:
                # Digest already exists for today - create incremental version
                version = existing_version + 1
                logger.info(
                    "creating_incremental_digest",
                    existing_version=existing_version,
                    new_version=version,
                )
            else:
                version = 1

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

            # NOTE: Do NOT mark articles as digested here!
            # The orchestrator should call mark_articles_digested() AFTER
            # successfully saving the digest to avoid data inconsistency.

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
        """Get summarized articles for digest, including duplicates grouped together.

        Args:
            digest_date: Date to get articles for (used for logging only).

        Returns:
            List of summarized articles not yet included in a digest.
            Duplicate articles are grouped with their canonical article.
        """
        # Get all summarized articles not yet in a digest (including duplicates)
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
        all_articles = []
        for row in rows:
            try:
                article = self.article_repo._row_to_article(row)
                all_articles.append(article)
            except Exception as e:
                logger.warning(
                    "article_conversion_failed", article_id=row["id"], error=str(e)
                )
                continue

        # Group duplicate articles with their canonical versions
        grouped_articles = self._group_duplicate_articles(all_articles)

        # Cluster similar articles by topic and content
        clustered_articles = self._cluster_similar_articles(grouped_articles)

        logger.info(
            "articles_grouped_and_clustered",
            total_articles=len(all_articles),
            after_dedup_grouping=len(grouped_articles),
            after_clustering=len(clustered_articles),
        )

        return clustered_articles

    def _group_duplicate_articles(self, articles: List[Article]) -> List[Article]:
        """Group duplicate articles with their canonical versions.

        For articles marked as duplicates, we merge them with their canonical article
        by combining sources and keeping the canonical article's summary.

        Args:
            articles: List of all articles (including duplicates).

        Returns:
            List of canonical articles with duplicate sources merged.
        """
        # Build index of articles by url_hash
        articles_by_hash = {a.url_hash: a for a in articles if a.url_hash}

        # Separate canonical articles from duplicates
        canonical_articles = []
        duplicate_articles = []

        for article in articles:
            if article.is_duplicate and article.canonical_url_hash:
                duplicate_articles.append(article)
            else:
                canonical_articles.append(article)

        # Group duplicates with their canonical articles
        for duplicate in duplicate_articles:
            canonical = articles_by_hash.get(duplicate.canonical_url_hash)

            if canonical:
                # Initialize duplicate_sources list if not exists
                if canonical.duplicate_sources is None:
                    canonical.duplicate_sources = []

                # Add duplicate's source to the canonical article
                canonical.duplicate_sources.append({
                    "source": duplicate.source,
                    "url": str(duplicate.url),
                    "title": duplicate.title,
                })

                logger.debug(
                    "duplicate_grouped",
                    canonical_id=canonical.id,
                    duplicate_id=duplicate.id,
                    duplicate_source=duplicate.source,
                )
            else:
                # Canonical article not found - treat duplicate as standalone
                logger.warning(
                    "canonical_not_found",
                    duplicate_id=duplicate.id,
                    canonical_hash=duplicate.canonical_url_hash,
                )
                canonical_articles.append(duplicate)

        logger.info(
            "duplicate_grouping_complete",
            canonical_count=len(canonical_articles),
            duplicate_count=len(duplicate_articles),
        )

        return canonical_articles

    def _cluster_similar_articles(self, articles: List[Article]) -> List[Article]:
        """Cluster semantically similar articles by topic and title keywords.

        Groups articles about the same event that weren't caught by duplicate detection.
        Uses topic + title keyword overlap to identify related articles.

        Args:
            articles: List of articles (already grouped by duplicates).

        Returns:
            List of articles with similar articles merged as duplicate_sources.
        """
        # Group articles by topic first
        articles_by_topic = {}
        for article in articles:
            topic = article.topic or "other"
            if topic not in articles_by_topic:
                articles_by_topic[topic] = []
            articles_by_topic[topic].append(article)

        clustered = []
        total_clusters = 0

        # Within each topic, find similar articles
        for topic, topic_articles in articles_by_topic.items():
            if len(topic_articles) <= 1:
                clustered.extend(topic_articles)
                continue

            # Sort by confidence (highest first)
            topic_articles.sort(key=lambda a: a.confidence or 0, reverse=True)

            used = set()
            for i, article in enumerate(topic_articles):
                if i in used:
                    continue

                # Extract keywords from this article's title
                article_keywords = self._extract_keywords(article.summary_title or article.title or "")

                # Find similar articles in the same topic
                similar_indices = []
                for j in range(i + 1, len(topic_articles)):
                    if j in used:
                        continue

                    other = topic_articles[j]
                    other_keywords = self._extract_keywords(other.summary_title or other.title or "")

                    # Calculate keyword overlap
                    if self._is_similar(article_keywords, other_keywords):
                        similar_indices.append(j)
                        used.add(j)

                # If we found similar articles, merge them
                if similar_indices:
                    # Initialize duplicate_sources if not exists
                    if article.duplicate_sources is None:
                        article.duplicate_sources = []

                    # Add similar articles as duplicate sources
                    for idx in similar_indices:
                        similar = topic_articles[idx]
                        article.duplicate_sources.append({
                            "source": similar.source,
                            "url": str(similar.url),
                            "title": similar.title,
                        })

                        logger.debug(
                            "articles_clustered",
                            main_id=article.id,
                            similar_id=similar.id,
                            topic=topic,
                        )

                    total_clusters += 1

                clustered.append(article)
                used.add(i)

        logger.info(
            "article_clustering_complete",
            input_articles=len(articles),
            output_articles=len(clustered),
            clusters_formed=total_clusters,
        )

        return clustered

    def _extract_keywords(self, text: str) -> set:
        """Extract significant keywords from text.

        Args:
            text: Title or text to extract keywords from.

        Returns:
            Set of lowercase keywords.
        """
        if not text:
            return set()

        # German and English stopwords
        stopwords = {
            # German
            "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem",
            "im", "in", "auf", "von", "zu", "mit", "und", "oder", "aber", "ist", "sind",
            "wird", "werden", "wurde", "wurden", "hat", "haben", "für", "bei", "nach",
            # English
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "and", "or",
            "but", "is", "are", "was", "were", "has", "have", "had", "be", "been",
        }

        # Extract words (remove punctuation, convert to lowercase)
        import re
        words = re.findall(r'\b[a-zA-ZäöüÄÖÜß]+\b', text.lower())

        # Filter stopwords and short words
        keywords = {w for w in words if len(w) > 3 and w not in stopwords}

        return keywords

    def _is_similar(self, keywords1: set, keywords2: set, threshold: float = 0.3) -> bool:
        """Check if two keyword sets are similar enough to cluster.

        Args:
            keywords1: First set of keywords.
            keywords2: Second set of keywords.
            threshold: Minimum overlap ratio (default: 30%).

        Returns:
            True if articles should be clustered together.
        """
        if not keywords1 or not keywords2:
            return False

        # Calculate Jaccard similarity (intersection / union)
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        if not union:
            return False

        similarity = len(intersection) / len(union)

        # Also check for substantial keyword overlap (at least 2 common keywords)
        return similarity >= threshold and len(intersection) >= 2

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

    async def mark_articles_digested(
        self, articles: List[Article], digest_date: date, version: int
    ) -> None:
        """Mark articles as included in digest.

        This should be called AFTER the digest has been successfully saved
        to the database to ensure data consistency.

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
