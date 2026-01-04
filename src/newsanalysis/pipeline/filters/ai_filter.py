"""AI-powered article filter using OpenAI."""

import asyncio
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from newsanalysis.core.article import Article, ClassificationResult
from newsanalysis.core.config import Config
from newsanalysis.integrations.openai_client import OpenAIClient
from newsanalysis.services.cache_service import CacheService
from newsanalysis.services.config_loader import load_prompt_config
from newsanalysis.utils.exceptions import AIServiceError
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class ClassificationResponse(BaseModel):
    """Structured response from classification API."""

    match: bool = Field(..., description="Whether article is relevant")
    conf: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    topic: str = Field(..., description="Topic category")
    reason: str = Field(..., max_length=200, description="Brief explanation")


class AIFilter:
    """AI-powered article filter for relevance classification.

    Uses title + URL only (not full content) for 90% cost reduction.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        config: Config,
        cache_service: Optional[CacheService] = None,
    ):
        """Initialize AI filter.

        Args:
            openai_client: OpenAI client instance.
            config: Application configuration.
            cache_service: Optional cache service for caching classification results.
        """
        self.client = openai_client
        self.config = config
        self.cache_service = cache_service

        # Load classification prompts
        prompt_config = load_prompt_config("classification")
        self.system_prompt = prompt_config.system_prompt
        self.user_prompt_template = prompt_config.user_prompt_template

        logger.info(
            "ai_filter_initialized",
            model=config.model_mini,
            caching_enabled=cache_service is not None,
        )

    async def filter_articles(
        self,
        articles: List[Article],
        max_concurrent: int = 10,
    ) -> List[ClassificationResult]:
        """Filter articles using AI classification with concurrent processing.

        Args:
            articles: List of articles to classify.
            max_concurrent: Maximum number of concurrent API calls (default: 10)

        Returns:
            List of classification results.

        Raises:
            AIServiceError: If classification fails.
        """
        logger.info(
            "filtering_articles",
            count=len(articles),
            max_concurrent=max_concurrent,
        )

        # Check daily cost limit
        if not await self.client.check_daily_cost_limit(self.config.daily_cost_limit):
            raise AIServiceError("Daily cost limit exceeded")

        # Process in chunks to limit concurrency
        results = []
        for i in range(0, len(articles), max_concurrent):
            chunk = articles[i : i + max_concurrent]

            # Create tasks for this chunk
            tasks = [self._classify_article(article) for article in chunk]

            # Execute chunk concurrently
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.error(
                        "classification_failed",
                        title=chunk[j].title[:50],
                        error=str(result),
                    )
                    # Create a failed classification result
                    results.append(
                        ClassificationResult(
                            is_match=False,
                            confidence=0.0,
                            topic="error",
                            reason=f"Classification failed: {str(result)[:100]}",
                        )
                    )
                else:
                    results.append(result)
                    logger.debug(
                        "article_classified",
                        title=chunk[j].title[:50],
                        match=result.is_match,
                        confidence=result.confidence,
                    )

        # Calculate stats
        matched = sum(1 for r in results if r.is_match)
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0

        logger.info(
            "filtering_complete",
            total=len(results),
            matched=matched,
            rejected=len(results) - matched,
            avg_confidence=round(avg_confidence, 3),
        )

        return results

    async def _classify_article(self, article: Article) -> ClassificationResult:
        """Classify a single article.

        Args:
            article: Article to classify.

        Returns:
            Classification result.

        Raises:
            AIServiceError: If API call fails.
        """
        # Check cache first if available
        if self.cache_service:
            cached_result = self.cache_service.get_cached_classification(
                article.title, article.url
            )
            if cached_result:
                logger.debug(
                    "using_cached_classification",
                    title=article.title[:50],
                    match=cached_result.is_match,
                )
                return cached_result

        # Build user prompt with article metadata
        user_prompt = self.user_prompt_template.format(
            title=article.title,
            url=article.url,
            source=article.source,
        )

        # Create messages for OpenAI
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Call OpenAI API with structured output
        response = await self.client.create_completion(
            messages=messages,
            module="filter",
            request_type="classification",
            model=self.config.model_mini,  # Use mini model for classification
            response_format=ClassificationResponse,
            temperature=0.0,  # Deterministic
        )

        # Extract classification from structured response
        classification_data = response["content"]

        # Create ClassificationResult
        result = ClassificationResult(
            is_match=classification_data["match"],
            confidence=classification_data["conf"],
            topic=classification_data["topic"],
            reason=classification_data["reason"],
            filtered_at=datetime.now(),
        )

        # Apply confidence threshold
        if result.confidence < self.config.confidence_threshold:
            result.is_match = False
            logger.debug(
                "below_confidence_threshold",
                title=article.title[:50],
                confidence=result.confidence,
                threshold=self.config.confidence_threshold,
            )

        # Cache the result if cache service is available
        if self.cache_service:
            self.cache_service.cache_classification(article.title, article.url, result)

        return result

    async def filter_single_article(self, article: Article) -> ClassificationResult:
        """Filter a single article (convenience method).

        Args:
            article: Article to classify.

        Returns:
            Classification result.
        """
        results = await self.filter_articles([article])
        return results[0]
