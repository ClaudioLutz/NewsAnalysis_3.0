"""Semantic duplicate detector using LLM for cross-source article deduplication."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from newsanalysis.core.article import Article
from newsanalysis.integrations.provider_factory import LLMClient
from newsanalysis.services.config_loader import load_yaml
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class DuplicateCheckResponse(BaseModel):
    """Structured response from duplicate detection API."""

    is_duplicate: bool = Field(
        ..., description="Whether articles cover the same news story"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for duplicate detection"
    )
    reason: str = Field(
        ..., max_length=200, description="Brief explanation of the decision"
    )


class DuplicateGroup(BaseModel):
    """A group of duplicate articles covering the same story."""

    canonical_url_hash: str = Field(..., description="URL hash of the canonical article")
    duplicate_url_hashes: List[str] = Field(
        default_factory=list, description="URL hashes of duplicate articles"
    )
    confidence: float = Field(..., description="Average confidence across comparisons")
    detected_at: datetime = Field(default_factory=datetime.now)


class DuplicateDetector:
    """Detects semantically duplicate articles across different news sources.

    Uses LLM to compare article titles and determine if they cover the same story,
    even when published by different sources with different wording.

    Strategy:
    1. Group articles by publication date (same-day window)
    2. Within each group, compare titles pairwise using LLM
    3. Cluster duplicates and select canonical article (highest priority source)
    4. Mark duplicates to skip summarization
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_config_path: str = "config/prompts/deduplication.yaml",
        confidence_threshold: float = 0.75,
        time_window_hours: int = 48,
    ):
        """Initialize duplicate detector.

        Args:
            llm_client: LLM client instance (DeepSeek recommended for cost efficiency).
            prompt_config_path: Path to deduplication prompt config.
            confidence_threshold: Minimum confidence to consider articles as duplicates.
            time_window_hours: Maximum time difference between articles to compare.
        """
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.time_window_hours = time_window_hours

        # Load prompt configuration
        try:
            config = load_yaml(Path(prompt_config_path))
            self.system_prompt = config["system_prompt"]
            self.user_prompt_template = config["user_prompt_template"]
        except Exception as e:
            logger.warning(
                "dedup_prompt_config_not_found_using_defaults",
                path=prompt_config_path,
                error=str(e),
            )
            self._use_default_prompts()

        logger.info(
            "duplicate_detector_initialized",
            confidence_threshold=confidence_threshold,
            time_window_hours=time_window_hours,
        )

    def _use_default_prompts(self) -> None:
        """Set default prompts if config file not found."""
        self.system_prompt = """You are a news article duplicate detector.
Your task is to determine if two article titles refer to the SAME news story/event.

Consider articles as duplicates if they:
- Report on the same specific event, announcement, or development
- Cover the same company/person taking the same action
- Describe the same regulatory decision, court ruling, or business transaction

Consider articles as NOT duplicates if they:
- Cover different aspects of a broader topic
- Report on different events even if about the same company
- Are published weeks apart about ongoing developments

Be strict: only mark as duplicate if you are confident they cover the EXACT same story."""

        self.user_prompt_template = """Compare these two article titles:

Article 1:
- Title: {title1}
- Source: {source1}
- Published: {date1}

Article 2:
- Title: {title2}
- Source: {source2}
- Published: {date2}

Are these articles covering the SAME specific news story or event?
Respond with JSON: {{"is_duplicate": bool, "confidence": float, "reason": "brief explanation"}}"""

    async def detect_duplicates(
        self,
        articles: List[Article],
        max_concurrent: int = 10,
    ) -> Tuple[List[DuplicateGroup], Set[str]]:
        """Detect duplicate articles in a batch.

        Args:
            articles: List of articles to check for duplicates.
            max_concurrent: Maximum concurrent LLM calls.

        Returns:
            Tuple of:
            - List of DuplicateGroup objects
            - Set of url_hashes that are duplicates (should skip summarization)
        """
        if len(articles) < 2:
            return [], set()

        logger.info("detecting_duplicates", article_count=len(articles))

        # Group articles by time window for comparison
        time_groups = self._group_by_time_window(articles)

        # Find candidate pairs within each time group
        candidate_pairs = []
        for group in time_groups:
            if len(group) > 1:
                # Generate all pairs within the group
                for i, article1 in enumerate(group):
                    for article2 in group[i + 1 :]:
                        candidate_pairs.append((article1, article2))

        if not candidate_pairs:
            logger.info("no_candidate_pairs_found")
            return [], set()

        logger.info("comparing_candidate_pairs", pair_count=len(candidate_pairs))

        # Compare pairs concurrently
        duplicate_pairs: List[Tuple[Article, Article, float]] = []

        for i in range(0, len(candidate_pairs), max_concurrent):
            chunk = candidate_pairs[i : i + max_concurrent]
            tasks = [
                self._compare_articles(pair[0], pair[1]) for pair in chunk
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        "duplicate_comparison_failed",
                        error=str(result),
                    )
                    continue

                is_dup, confidence = result
                if is_dup and confidence >= self.confidence_threshold:
                    duplicate_pairs.append((chunk[j][0], chunk[j][1], confidence))

        # Cluster duplicates using Union-Find
        duplicate_groups = self._cluster_duplicates(duplicate_pairs, articles)

        # Collect all duplicate url_hashes (excluding canonical)
        duplicate_hashes: Set[str] = set()
        for group in duplicate_groups:
            duplicate_hashes.update(group.duplicate_url_hashes)

        logger.info(
            "duplicate_detection_complete",
            groups_found=len(duplicate_groups),
            duplicates_found=len(duplicate_hashes),
            articles_to_summarize=len(articles) - len(duplicate_hashes),
        )

        return duplicate_groups, duplicate_hashes

    def _group_by_time_window(self, articles: List[Article]) -> List[List[Article]]:
        """Group articles that fall within the time window of each other.

        Args:
            articles: List of articles to group.

        Returns:
            List of article groups (articles within time window).
        """
        if not articles:
            return []

        # Sort by published_at (use collected_at as fallback)
        def get_time(a: Article) -> datetime:
            return a.published_at or a.collected_at

        sorted_articles = sorted(articles, key=get_time)

        groups: List[List[Article]] = []
        current_group: List[Article] = [sorted_articles[0]]
        group_start_time = get_time(sorted_articles[0])

        for article in sorted_articles[1:]:
            article_time = get_time(article)
            time_diff = article_time - group_start_time

            if time_diff <= timedelta(hours=self.time_window_hours):
                current_group.append(article)
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [article]
                group_start_time = article_time

        # Don't forget the last group
        if len(current_group) > 1:
            groups.append(current_group)

        return groups

    async def _compare_articles(
        self, article1: Article, article2: Article
    ) -> Tuple[bool, float]:
        """Compare two articles to determine if they're duplicates.

        Args:
            article1: First article.
            article2: Second article.

        Returns:
            Tuple of (is_duplicate, confidence).
        """
        # Format dates for prompt
        date1 = (article1.published_at or article1.collected_at).strftime("%Y-%m-%d")
        date2 = (article2.published_at or article2.collected_at).strftime("%Y-%m-%d")

        user_prompt = self.user_prompt_template.format(
            title1=article1.title,
            source1=article1.source,
            date1=date1,
            title2=article2.title,
            source2=article2.source,
            date2=date2,
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await self.llm_client.create_completion(
                messages=messages,
                module="dedup",
                request_type="duplicate_detection",
                response_format=DuplicateCheckResponse,
                temperature=0.0,
            )

            result = response["content"]
            is_duplicate = result["is_duplicate"]
            confidence = result["confidence"]

            logger.debug(
                "articles_compared",
                title1=article1.title[:40],
                title2=article2.title[:40],
                is_duplicate=is_duplicate,
                confidence=confidence,
            )

            return is_duplicate, confidence

        except Exception as e:
            logger.error(
                "article_comparison_failed",
                title1=article1.title[:40],
                title2=article2.title[:40],
                error=str(e),
            )
            raise

    def _cluster_duplicates(
        self,
        duplicate_pairs: List[Tuple[Article, Article, float]],
        all_articles: List[Article],
    ) -> List[DuplicateGroup]:
        """Cluster duplicate pairs into groups using Union-Find.

        Args:
            duplicate_pairs: List of (article1, article2, confidence) tuples.
            all_articles: All articles for reference.

        Returns:
            List of DuplicateGroup objects.
        """
        if not duplicate_pairs:
            return []

        # Build URL hash to article mapping
        hash_to_article: Dict[str, Article] = {a.url_hash: a for a in all_articles}

        # Union-Find data structure
        parent: Dict[str, str] = {}
        rank: Dict[str, int] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
                rank[x] = 0
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px == py:
                return
            # Union by rank
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1

        # Track confidence for each pair
        pair_confidence: Dict[Tuple[str, str], float] = {}

        # Process pairs
        for article1, article2, confidence in duplicate_pairs:
            union(article1.url_hash, article2.url_hash)
            pair_key = tuple(sorted([article1.url_hash, article2.url_hash]))
            pair_confidence[pair_key] = confidence

        # Group by root
        clusters: Dict[str, List[str]] = {}
        for url_hash in parent:
            root = find(url_hash)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(url_hash)

        # Convert to DuplicateGroup objects
        groups: List[DuplicateGroup] = []
        for members in clusters.values():
            if len(members) < 2:
                continue

            # Select canonical article (lowest feed_priority = highest importance)
            articles_in_group = [hash_to_article[h] for h in members if h in hash_to_article]
            if not articles_in_group:
                continue

            canonical = min(articles_in_group, key=lambda a: (a.feed_priority, a.collected_at))
            duplicates = [a.url_hash for a in articles_in_group if a.url_hash != canonical.url_hash]

            # Calculate average confidence for the group
            group_confidences = []
            for h in members:
                for other_h in members:
                    if h != other_h:
                        pair_key = tuple(sorted([h, other_h]))
                        if pair_key in pair_confidence:
                            group_confidences.append(pair_confidence[pair_key])

            avg_confidence = (
                sum(group_confidences) / len(group_confidences)
                if group_confidences
                else self.confidence_threshold
            )

            groups.append(
                DuplicateGroup(
                    canonical_url_hash=canonical.url_hash,
                    duplicate_url_hashes=duplicates,
                    confidence=avg_confidence,
                )
            )

            logger.info(
                "duplicate_group_found",
                canonical_title=canonical.title[:50],
                canonical_source=canonical.source,
                duplicate_count=len(duplicates),
                avg_confidence=round(avg_confidence, 3),
            )

        return groups
