"""Semantic duplicate detector using multi-signal pre-filtering and LLM verification.

Pre-filter cascade (union — any signal triggers LLM comparison):
1. URL slug similarity (Jaccard on path tokens >= 0.5)
2. Embedding cosine similarity (multilingual, >= 0.65)
3. Entity overlap (existing: shared proper nouns/acronyms)
4. Title token Jaccard similarity (>= 0.3)
5. Content SimHash (hamming distance <= 10, if content available)

LLM comparison receives title + optional content snippet for better accuracy.
Cross-language dedup uses the same pipeline (multilingual embeddings handle DE/FR/IT).
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from newsanalysis.pipeline.dedup.embedding_service import EmbeddingService

import snowballstemmer
from pydantic import BaseModel, Field
from stop_words import get_stop_words

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
    duplicate_url_hashes: list[str] = Field(
        default_factory=list, description="URL hashes of duplicate articles"
    )
    confidence: float = Field(..., description="Average confidence across comparisons")
    detected_at: datetime = Field(default_factory=datetime.now)


class DuplicateDetector:
    """Detects semantically duplicate articles across different news sources.

    Uses a multi-signal pre-filter cascade followed by LLM verification:
    1. URL slug similarity — catches syndicated content with similar URLs
    2. Embedding cosine similarity — multilingual semantic matching (DE/FR/IT)
    3. Entity overlap — shared proper nouns, acronyms, numbers
    4. Title token Jaccard — token-level overlap for similar headlines
    5. Content SimHash — fuzzy content fingerprinting (if content available)

    Only candidate pairs passing at least one pre-filter go to LLM.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_config_path: str = "config/prompts/deduplication.yaml",
        confidence_threshold: float = 0.75,
        time_window_hours: int = 48,
        embedding_threshold: float = 0.65,
        jaccard_threshold: float = 0.30,
        url_slug_threshold: float = 0.50,
        simhash_max_distance: int = 15,
    ):
        """Initialize duplicate detector.

        Args:
            llm_client: LLM client instance (DeepSeek recommended for cost efficiency).
            prompt_config_path: Path to deduplication prompt config.
            confidence_threshold: Minimum confidence to consider articles as duplicates.
            time_window_hours: Maximum time difference between articles to compare.
            embedding_threshold: Minimum cosine similarity for embedding pre-filter.
            jaccard_threshold: Minimum Jaccard similarity for title token pre-filter.
            url_slug_threshold: Minimum Jaccard similarity for URL slug pre-filter.
            simhash_max_distance: Maximum hamming distance for SimHash content pre-filter.
        """
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.time_window_hours = time_window_hours
        self.embedding_threshold = embedding_threshold
        self.jaccard_threshold = jaccard_threshold
        self.url_slug_threshold = url_slug_threshold
        self.simhash_max_distance = simhash_max_distance

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

        # Lazy-init embedding service
        self._embedding_service: EmbeddingService | None = None

        logger.info(
            "duplicate_detector_initialized",
            confidence_threshold=confidence_threshold,
            time_window_hours=time_window_hours,
            embedding_threshold=embedding_threshold,
            jaccard_threshold=jaccard_threshold,
            url_slug_threshold=url_slug_threshold,
            simhash_max_distance=simhash_max_distance,
        )

    def _use_default_prompts(self) -> None:
        """Set default prompts if config file not found."""
        self.system_prompt = """You are a news article duplicate detector.
Your task is to determine if two articles refer to the SAME news story/event.

Consider articles as duplicates if they:
- Report on the same specific event, announcement, or development
- Cover the same company/person taking the same action
- Describe the same regulatory decision, court ruling, or business transaction

Consider articles as NOT duplicates if they:
- Cover different aspects of a broader topic
- Report on different events even if about the same company
- Are published weeks apart about ongoing developments

Be strict: only mark as duplicate if you are confident they cover the EXACT same story."""

        self.user_prompt_template = """Compare these two articles:

Article 1:
- Title: {title1}
- Source: {source1}
- Date: {date1}
{snippet1}

Article 2:
- Title: {title2}
- Source: {source2}
- Date: {date2}
{snippet2}

Are these articles covering the SAME specific news story or event?
Respond with JSON: {{"is_duplicate": bool, "confidence": float, "reason": "brief explanation"}}"""

    @property
    def embedding_service(self) -> EmbeddingService | None:
        """Lazy-load the embedding service."""
        if self._embedding_service is None:
            try:
                from newsanalysis.pipeline.dedup.embedding_service import EmbeddingService

                self._embedding_service = EmbeddingService(
                    similarity_threshold=self.embedding_threshold
                )
                if not self._embedding_service.available:
                    self._embedding_service = None
            except Exception as e:
                logger.warning("embedding_service_init_failed", error=str(e))
                self._embedding_service = None
        return self._embedding_service

    # ── Multilingual stop words ──────────────────────────────────────────

    _STOP_WORDS: set[str] = (
        set(get_stop_words("german"))
        | set(get_stop_words("french"))
        | set(get_stop_words("italian"))
        | set(get_stop_words("english"))
    )

    _STEMMERS = {
        "de": snowballstemmer.stemmer("german"),
        "fr": snowballstemmer.stemmer("french"),
        "it": snowballstemmer.stemmer("italian"),
    }

    _ENTITY_PATTERN = re.compile(r"[A-ZÄÖÜ][a-zäöüéèêàâîôûç]+|[A-ZÄÖÜ]{2,}|\d+[\.,]?\d*")

    # ── Pre-Filter 1: URL Slug Similarity ────────────────────────────────

    @staticmethod
    def _extract_slug_tokens(url: str) -> set[str]:
        """Extract meaningful tokens from the URL path.

        Splits the path on /, -, _ and filters out short/numeric-only tokens.
        E.g. "https://nzz.ch/wirtschaft/ubs-meldet-konkurs-2026" → {"wirtschaft", "ubs", "meldet", "konkurs"}
        """
        try:
            path = urlparse(str(url)).path
        except Exception:
            return set()
        tokens = re.split(r"[/\-_.]", path.lower())
        return {t for t in tokens if len(t) >= 3 and not t.isdigit()}

    @staticmethod
    def _url_slug_similarity(url1: str, url2: str) -> float:
        """Jaccard similarity between URL slug tokens."""
        tokens1 = DuplicateDetector._extract_slug_tokens(url1)
        tokens2 = DuplicateDetector._extract_slug_tokens(url2)
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union) if union else 0.0

    # ── Pre-Filter 2: Entity Overlap (existing) ─────────────────────────

    @staticmethod
    def _stem_word(word: str) -> str:
        """Stem a word using all stemmers, return the shortest result."""
        stems = [word]
        for stemmer in DuplicateDetector._STEMMERS.values():
            stems.append(stemmer.stemWord(word))
        return min(stems, key=len)

    @staticmethod
    def _extract_entities(title: str) -> set[str]:
        """Extract named entities and numbers from a title.

        Extracts capitalized words (proper nouns), acronyms, and numbers.
        Applies stemming to normalize inflected forms across languages.
        """
        tokens = DuplicateDetector._ENTITY_PATTERN.findall(title)
        entities = set()
        for token in tokens:
            lower = token.lower()
            if lower not in DuplicateDetector._STOP_WORDS and len(token) >= 2:
                if token.isupper() or token[0].isdigit():
                    entities.add(lower)
                else:
                    stemmed = DuplicateDetector._stem_word(lower)
                    if len(stemmed) >= 2:
                        entities.add(stemmed)
        return entities

    # ── Pre-Filter 3: Title Token Jaccard ────────────────────────────────

    @staticmethod
    def _title_token_jaccard(title1: str, title2: str) -> float:
        """Jaccard similarity on lowercased title tokens (excluding stop words).

        More permissive than entity overlap — catches common words that
        aren't proper nouns but still indicate the same story.
        """
        tokens1 = {
            t
            for t in re.findall(r"\w+", title1.lower())
            if len(t) >= 3 and t not in DuplicateDetector._STOP_WORDS
        }
        tokens2 = {
            t
            for t in re.findall(r"\w+", title2.lower())
            if len(t) >= 3 and t not in DuplicateDetector._STOP_WORDS
        }
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union) if union else 0.0

    # ── Pre-Filter 4: Content SimHash ────────────────────────────────────

    @staticmethod
    def _compute_simhash(text: str, hash_bits: int = 64) -> int:
        """Compute a SimHash fingerprint for text content.

        SimHash is a locality-sensitive hash: similar texts produce hashes
        with small hamming distance. Uses word-level shingles (3-grams).

        Args:
            text: Text content to hash.
            hash_bits: Number of bits in the hash (default 64).

        Returns:
            Integer SimHash value.
        """
        if not text:
            return 0

        # Normalize: lowercase, collapse whitespace
        text = re.sub(r"\s+", " ", text.lower().strip())
        words = text.split()

        if len(words) < 3:
            return 0

        # Generate 3-gram shingles
        vector = [0] * hash_bits
        for i in range(len(words) - 2):
            shingle = " ".join(words[i : i + 3])
            h = int(hashlib.md5(shingle.encode("utf-8")).hexdigest(), 16)
            for bit in range(hash_bits):
                if h & (1 << bit):
                    vector[bit] += 1
                else:
                    vector[bit] -= 1

        # Build fingerprint from sign of each dimension
        fingerprint = 0
        for bit in range(hash_bits):
            if vector[bit] > 0:
                fingerprint |= 1 << bit
        return fingerprint

    @staticmethod
    def _hamming_distance(hash1: int, hash2: int) -> int:
        """Count differing bits between two SimHash values."""
        return bin(hash1 ^ hash2).count("1")

    # ── Multi-Signal Pre-Filter ──────────────────────────────────────────

    def _multi_signal_pre_filter(
        self,
        pairs: list[tuple[Article, Article]],
        entity_cache: dict[str, set[str]] | None = None,
        simhash_cache: dict[str, int] | None = None,
        embedding_threshold_override: float | None = None,
    ) -> list[tuple[Article, Article]]:
        """Multi-signal pre-filter replacing the old entity-only pre-filter.

        A pair is a candidate if ANY of these signals fires:
        1. URL slug Jaccard >= url_slug_threshold
        2. Embedding cosine similarity >= embedding_threshold (or override)
        3. Shared entities (at least 1)
        4. Title token Jaccard >= jaccard_threshold
        5. Content SimHash hamming distance <= simhash_max_distance

        Args:
            pairs: All candidate pairs from time window grouping.
            entity_cache: Pre-computed entity cache (url_hash → entities).
            simhash_cache: Pre-computed SimHash cache (url_hash → simhash).
            embedding_threshold_override: Lower threshold for cross-language comparisons.

        Returns:
            Filtered pairs that pass at least one signal.
        """
        if entity_cache is None:
            entity_cache = {}
        if simhash_cache is None:
            simhash_cache = {}

        # Pre-compute entities and simhashes
        for a1, a2 in pairs:
            for a in (a1, a2):
                if a.url_hash not in entity_cache:
                    entity_cache[a.url_hash] = self._extract_entities(a.title)
                if a.url_hash not in simhash_cache and a.content:
                    simhash_cache[a.url_hash] = self._compute_simhash(a.content)

        # Batch-encode titles for embedding similarity
        all_hashes_in_pairs: set[str] = set()
        for a1, a2 in pairs:
            all_hashes_in_pairs.add(a1.url_hash)
            all_hashes_in_pairs.add(a2.url_hash)

        effective_emb_threshold = embedding_threshold_override or self.embedding_threshold

        if self.embedding_service:
            hash_list = list(all_hashes_in_pairs)
            title_map: dict[str, str] = {}
            for a1, a2 in pairs:
                title_map[a1.url_hash] = a1.title
                title_map[a2.url_hash] = a2.title
            self.embedding_service.encode_titles(
                [title_map[h] for h in hash_list], hash_list
            )
            # Get all similar pairs from embeddings (using effective threshold)
            old_threshold = self.embedding_service.similarity_threshold
            self.embedding_service.similarity_threshold = effective_emb_threshold
            embedding_pairs = self.embedding_service.get_similar_pairs(hash_list)
            self.embedding_service.similarity_threshold = old_threshold
            embedding_pair_set: set[frozenset[str]] = {
                frozenset((h1, h2)) for h1, h2, _ in embedding_pairs
            }
        else:
            embedding_pair_set = set()

        # Evaluate each pair against all signals
        filtered = []
        signal_stats = {
            "url_slug": 0,
            "embedding": 0,
            "entity": 0,
            "jaccard": 0,
            "simhash": 0,
        }

        for a1, a2 in pairs:
            matched = False

            # Signal 1: URL slug similarity
            url_sim = self._url_slug_similarity(str(a1.url), str(a2.url))
            if url_sim >= self.url_slug_threshold:
                signal_stats["url_slug"] += 1
                matched = True

            # Signal 2: Embedding cosine similarity
            if not matched and frozenset((a1.url_hash, a2.url_hash)) in embedding_pair_set:
                signal_stats["embedding"] += 1
                matched = True

            # Signal 3: Entity overlap
            if not matched:
                entities1 = entity_cache.get(a1.url_hash, set())
                entities2 = entity_cache.get(a2.url_hash, set())
                if entities1 & entities2:
                    signal_stats["entity"] += 1
                    matched = True

            # Signal 4: Title token Jaccard
            if not matched:
                jaccard = self._title_token_jaccard(a1.title, a2.title)
                if jaccard >= self.jaccard_threshold:
                    signal_stats["jaccard"] += 1
                    matched = True

            # Signal 5: Content SimHash
            if not matched:
                sh1 = simhash_cache.get(a1.url_hash)
                sh2 = simhash_cache.get(a2.url_hash)
                if sh1 and sh2:
                    dist = self._hamming_distance(sh1, sh2)
                    if dist <= self.simhash_max_distance:
                        signal_stats["simhash"] += 1
                        matched = True

            if matched:
                filtered.append((a1, a2))

        skipped = len(pairs) - len(filtered)
        logger.info(
            "multi_signal_pre_filter_complete",
            total_pairs=len(pairs),
            candidate_pairs=len(filtered),
            skipped_pairs=skipped,
            reduction_pct=round(skipped / len(pairs) * 100, 1) if pairs else 0,
            signal_hits=signal_stats,
        )

        return filtered

    # ── Main Duplicate Detection ─────────────────────────────────────────

    async def detect_duplicates(
        self,
        articles: list[Article],
        max_concurrent: int = 10,
    ) -> tuple[list[DuplicateGroup], set[str]]:
        """Detect duplicate articles in a batch.

        Uses multi-signal pre-filtering followed by LLM verification.

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

        # Find all candidate pairs within each time group
        all_pairs = []
        for group in time_groups:
            if len(group) > 1:
                for i, article1 in enumerate(group):
                    for article2 in group[i + 1 :]:
                        all_pairs.append((article1, article2))

        if not all_pairs:
            logger.info("no_candidate_pairs_found")
            return [], set()

        # Multi-signal pre-filter (replaces old entity-only pre-filter)
        candidate_pairs = self._multi_signal_pre_filter(all_pairs)

        if not candidate_pairs:
            logger.info("no_candidates_after_pre_filter")
            return [], set()

        logger.info("comparing_candidate_pairs", pair_count=len(candidate_pairs))

        # Compare pairs concurrently via LLM
        duplicate_pairs: list[tuple[Article, Article, float]] = []

        for i in range(0, len(candidate_pairs), max_concurrent):
            chunk = candidate_pairs[i : i + max_concurrent]
            tasks = [self._compare_articles(pair[0], pair[1]) for pair in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, BaseException):
                    logger.warning(
                        "duplicate_comparison_failed",
                        error=str(result),
                    )
                    continue

                is_dup, confidence = result
                if is_dup and confidence >= self.confidence_threshold:
                    duplicate_pairs.append((chunk[j][0], chunk[j][1], confidence))

        # Cluster duplicates using Union-Find
        duplicate_groups: list[DuplicateGroup] = self._cluster_duplicates(
            duplicate_pairs, articles
        )

        # Collect all duplicate url_hashes (excluding canonical)
        duplicate_hashes: set[str] = set()
        for dg in duplicate_groups:
            duplicate_hashes.update(dg.duplicate_url_hashes)

        logger.info(
            "duplicate_detection_complete",
            groups_found=len(duplicate_groups),
            duplicates_found=len(duplicate_hashes),
            articles_to_summarize=len(articles) - len(duplicate_hashes),
        )

        return duplicate_groups, duplicate_hashes

    async def detect_cross_language_duplicates(
        self,
        foreign_articles: list[Article],
        canonical_articles: list[Article],
        max_concurrent: int = 10,
    ) -> tuple[list[DuplicateGroup], set[str]]:
        """Detect FR/IT articles that duplicate DE canonical articles.

        Now uses multi-signal pre-filter with multilingual embeddings instead of
        brute-force all-pairs LLM comparison. This drastically reduces API costs
        while improving detection quality.

        Args:
            foreign_articles: FR/IT articles to check against DE canonicals.
            canonical_articles: DE articles that survived same-language dedup.
            max_concurrent: Maximum concurrent LLM calls.

        Returns:
            Tuple of (DuplicateGroup list, set of duplicate url_hashes).
        """
        if not foreign_articles or not canonical_articles:
            return [], set()

        logger.info(
            "cross_language_dedup_starting",
            foreign_count=len(foreign_articles),
            canonical_count=len(canonical_articles),
        )

        # Build all cross-language pairs
        all_pairs = [
            (foreign, canonical)
            for foreign in foreign_articles
            for canonical in canonical_articles
        ]

        logger.info("cross_language_pairs", pair_count=len(all_pairs))

        # Use multi-signal pre-filter with lower embedding threshold for cross-language
        # (translations create more distance in embedding space: SNB vs BNS, etc.)
        candidate_pairs = self._multi_signal_pre_filter(
            all_pairs, embedding_threshold_override=0.40
        )

        if not candidate_pairs:
            logger.info("no_cross_language_candidates_after_filter")
            return [], set()

        logger.info(
            "cross_language_candidates",
            candidate_count=len(candidate_pairs),
            reduction_pct=round(
                (1 - len(candidate_pairs) / len(all_pairs)) * 100, 1
            )
            if all_pairs
            else 0,
        )

        # Compare pairs concurrently via LLM
        duplicate_pairs: list[tuple[Article, Article, float]] = []

        for i in range(0, len(candidate_pairs), max_concurrent):
            chunk = candidate_pairs[i : i + max_concurrent]
            tasks = [self._compare_articles(pair[0], pair[1]) for pair in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, BaseException):
                    logger.warning(
                        "cross_language_comparison_failed",
                        error=str(result),
                    )
                    continue

                is_dup, confidence = result
                if is_dup and confidence >= self.confidence_threshold:
                    duplicate_pairs.append((chunk[j][0], chunk[j][1], confidence))

        # Cluster duplicates
        all_articles = foreign_articles + canonical_articles
        groups = self._cluster_duplicates(duplicate_pairs, all_articles)

        # Collect duplicate hashes (only foreign articles, never DE canonicals)
        canonical_hashes = {a.url_hash for a in canonical_articles}
        duplicate_hashes: set[str] = set()
        for group in groups:
            for dup_hash in group.duplicate_url_hashes:
                if dup_hash not in canonical_hashes:
                    duplicate_hashes.add(dup_hash)

        logger.info(
            "cross_language_dedup_complete",
            groups_found=len(groups),
            foreign_duplicates=len(duplicate_hashes),
        )

        return groups, duplicate_hashes

    # ── Time Window Grouping ─────────────────────────────────────────────

    def _group_by_time_window(self, articles: list[Article]) -> list[list[Article]]:
        """Group articles that fall within the time window of each other."""
        if not articles:
            return []

        def get_time(a: Article) -> datetime:
            return a.published_at or a.collected_at

        sorted_articles = sorted(articles, key=get_time)

        groups: list[list[Article]] = []
        current_group: list[Article] = [sorted_articles[0]]
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

        if len(current_group) > 1:
            groups.append(current_group)

        return groups

    # ── LLM Article Comparison ───────────────────────────────────────────

    async def _compare_articles(
        self, article1: Article, article2: Article
    ) -> tuple[bool, float]:
        """Compare two articles via LLM to determine if they're duplicates.

        Now includes optional content snippets for better accuracy.
        """
        date1 = (article1.published_at or article1.collected_at).strftime("%Y-%m-%d")
        date2 = (article2.published_at or article2.collected_at).strftime("%Y-%m-%d")

        # Build content snippets (first 300 chars of scraped content)
        snippet1 = ""
        if article1.content:
            preview = article1.content[:300].strip()
            snippet1 = f"- Content preview: {preview}"

        snippet2 = ""
        if article2.content:
            preview = article2.content[:300].strip()
            snippet2 = f"- Content preview: {preview}"

        user_prompt = self.user_prompt_template.format(
            title1=article1.title,
            source1=article1.source,
            date1=date1,
            snippet1=snippet1,
            title2=article2.title,
            source2=article2.source,
            date2=date2,
            snippet2=snippet2,
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

    # ── Clustering ───────────────────────────────────────────────────────

    def _cluster_duplicates(
        self,
        duplicate_pairs: list[tuple[Article, Article, float]],
        all_articles: list[Article],
    ) -> list[DuplicateGroup]:
        """Cluster duplicate pairs into groups using Union-Find."""
        if not duplicate_pairs:
            return []

        hash_to_article: dict[str, Article] = {a.url_hash: a for a in all_articles}

        # Union-Find
        parent: dict[str, str] = {}
        rank: dict[str, int] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
                rank[x] = 0
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1

        pair_confidence: dict[tuple[str, ...], float] = {}

        for article1, article2, confidence in duplicate_pairs:
            union(article1.url_hash, article2.url_hash)
            pair_key = tuple(sorted([article1.url_hash, article2.url_hash]))
            pair_confidence[pair_key] = confidence

        # Group by root
        clusters: dict[str, list[str]] = {}
        for url_hash in parent:
            root = find(url_hash)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(url_hash)

        # Convert to DuplicateGroup objects
        groups: list[DuplicateGroup] = []
        for members in clusters.values():
            if len(members) < 2:
                continue

            articles_in_group = [hash_to_article[h] for h in members if h in hash_to_article]
            if not articles_in_group:
                continue

            canonical = min(articles_in_group, key=lambda a: (a.feed_priority, a.collected_at))
            duplicates = [a.url_hash for a in articles_in_group if a.url_hash != canonical.url_hash]

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
