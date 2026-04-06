"""Semantic deduplication module for detecting duplicate news stories."""

from newsanalysis.pipeline.dedup.duplicate_detector import DuplicateDetector
from newsanalysis.pipeline.dedup.embedding_service import EmbeddingService

__all__ = ["DuplicateDetector", "EmbeddingService"]
