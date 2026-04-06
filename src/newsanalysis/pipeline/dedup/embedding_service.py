"""Multilingual sentence embedding service for semantic similarity pre-filtering.

Uses a multilingual model that maps DE/FR/IT/EN into a shared vector space,
enabling both same-language and cross-language duplicate detection without LLM calls.
"""

from typing import TYPE_CHECKING

from newsanalysis.utils.logging import get_logger

if TYPE_CHECKING:
    import numpy as np

logger = get_logger(__name__)

# Lazy-loaded singleton to avoid import-time torch overhead
_model_instance = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_model():  # type: ignore[no-untyped-def]
    """Lazy-load the sentence-transformers model (singleton)."""
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("loading_embedding_model", model=_MODEL_NAME)
            _model_instance = SentenceTransformer(_MODEL_NAME)
            logger.info("embedding_model_loaded", model=_MODEL_NAME)
        except ImportError:
            logger.warning(
                "sentence_transformers_not_installed",
                hint="pip install sentence-transformers",
            )
            raise
    return _model_instance


class EmbeddingService:
    """Computes and caches sentence embeddings for duplicate detection.

    Encodes article titles into dense vectors and computes cosine similarity
    for fast pre-filtering before expensive LLM comparison.
    """

    def __init__(self, similarity_threshold: float = 0.65) -> None:
        self.similarity_threshold = similarity_threshold
        self._embedding_cache: dict[str, np.ndarray] = {}
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        """Check if sentence-transformers is installed."""
        if self._available is None:
            try:
                _get_model()
                self._available = True
            except (ImportError, Exception) as e:
                logger.warning("embedding_service_unavailable", error=str(e))
                self._available = False
        return self._available

    def encode_titles(self, titles: list[str], url_hashes: list[str]) -> None:
        """Batch-encode titles and cache by url_hash.

        Args:
            titles: List of article titles.
            url_hashes: Corresponding url_hash identifiers.
        """
        import numpy as np

        if not self.available or not titles:
            return

        # Only encode titles not yet cached
        new_indices = [i for i, h in enumerate(url_hashes) if h not in self._embedding_cache]
        if not new_indices:
            return

        new_titles = [titles[i] for i in new_indices]
        new_hashes = [url_hashes[i] for i in new_indices]

        model = _get_model()
        embeddings = model.encode(new_titles, batch_size=64, show_progress_bar=False)

        for h, emb in zip(new_hashes, embeddings, strict=True):
            self._embedding_cache[h] = emb / np.linalg.norm(emb)  # L2 normalize

        logger.debug(
            "titles_encoded",
            new_count=len(new_indices),
            cache_size=len(self._embedding_cache),
        )

    def get_similar_pairs(
        self, url_hashes: list[str]
    ) -> list[tuple[str, str, float]]:
        """Find all pairs above the similarity threshold using cosine similarity.

        Args:
            url_hashes: List of url_hashes to compare pairwise.

        Returns:
            List of (hash1, hash2, cosine_similarity) tuples.
        """
        import numpy as np

        if not self.available:
            return []

        # Build embedding matrix for requested hashes
        valid_hashes = [h for h in url_hashes if h in self._embedding_cache]
        if len(valid_hashes) < 2:
            return []

        embeddings = np.stack([self._embedding_cache[h] for h in valid_hashes])

        # Cosine similarity matrix (embeddings are already L2-normalized)
        sim_matrix = embeddings @ embeddings.T

        # Extract pairs above threshold (upper triangle only)
        similar_pairs: list[tuple[str, str, float]] = []
        n = len(valid_hashes)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(sim_matrix[i, j])
                if sim >= self.similarity_threshold:
                    similar_pairs.append((valid_hashes[i], valid_hashes[j], sim))

        logger.info(
            "embedding_similar_pairs",
            total_compared=n * (n - 1) // 2,
            similar_count=len(similar_pairs),
            threshold=self.similarity_threshold,
        )

        return similar_pairs

    def get_similarity(self, hash1: str, hash2: str) -> float | None:
        """Get cosine similarity between two cached embeddings.

        Returns:
            Cosine similarity (0-1) or None if either embedding is missing.
        """
        if hash1 not in self._embedding_cache or hash2 not in self._embedding_cache:
            return None
        emb1 = self._embedding_cache[hash1]
        emb2 = self._embedding_cache[hash2]
        return float(emb1 @ emb2)

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
