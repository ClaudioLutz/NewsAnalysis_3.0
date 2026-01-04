"""Article summarizer with OpenAI integration and entity extraction."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from newsanalysis.core.article import ArticleSummary, EntityData
from newsanalysis.integrations.openai_client import OpenAIClient
from newsanalysis.services.cache_service import CacheService
from newsanalysis.services.config_loader import load_yaml_config

logger = logging.getLogger(__name__)


class SummaryResponse(BaseModel):
    """Structured response from OpenAI for summarization."""

    title: str = Field(..., max_length=150, description="Normalized article title")
    summary: str = Field(
        ...,
        min_length=100,
        max_length=1000,
        description="Article summary (150-200 words)",
    )
    key_points: List[str] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="Key bullet points",
    )
    entities: Dict[str, List[str]] = Field(
        ...,
        description="Extracted entities (companies, people, locations, topics)",
    )


class ArticleSummarizer:
    """Summarize articles using OpenAI with entity extraction."""

    def __init__(
        self,
        openai_client: OpenAIClient,
        prompt_config_path: str = "config/prompts/summarization.yaml",
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize article summarizer.

        Args:
            openai_client: OpenAI client instance
            prompt_config_path: Path to summarization prompt config
            model: OpenAI model to use
            temperature: Sampling temperature
            cache_service: Optional cache service for caching summaries
        """
        self.openai_client = openai_client
        self.model = model
        self.temperature = temperature
        self.cache_service = cache_service

        # Load prompt configuration
        config = load_yaml_config(prompt_config_path)
        self.system_prompt = config["system_prompt"]
        self.user_prompt_template = config["user_prompt_template"]

        logger.info(
            "article_summarizer_initialized",
            model=model,
            temperature=temperature,
            caching_enabled=cache_service is not None,
        )

    async def summarize(
        self,
        title: str,
        source: str,
        content: str,
        url: Optional[str] = None,
    ) -> Optional[ArticleSummary]:
        """
        Summarize an article and extract entities.

        Args:
            title: Article title
            source: Article source
            content: Article content
            url: Article URL (for logging)

        Returns:
            ArticleSummary if successful, None if failed
        """
        try:
            logger.info(f"Summarizing article: {title[:50]}...")

            # Check cache first if available
            if self.cache_service:
                cached_summary = self.cache_service.get_cached_summary(content)
                if cached_summary:
                    logger.debug(
                        "using_cached_summary",
                        title=title[:50],
                    )
                    # Parse cached JSON data
                    entities_dict = json.loads(cached_summary["entities"])
                    entities = EntityData(
                        companies=entities_dict.get("companies", []),
                        people=entities_dict.get("people", []),
                        locations=entities_dict.get("locations", []),
                        topics=entities_dict.get("topics", []),
                    )
                    return ArticleSummary(
                        summary_title=cached_summary["summary_title"],
                        summary=cached_summary["summary"],
                        key_points=json.loads(cached_summary["key_points"]),
                        entities=entities,
                        summarized_at=datetime.now(),
                    )

            # Build messages
            user_prompt = self.user_prompt_template.format(
                title=title,
                source=source,
                content=content,
            )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Call OpenAI API with structured output
            response = await self.openai_client.create_completion(
                messages=messages,
                module="summarizer",
                request_type="summarization",
                model=self.model,
                response_format=SummaryResponse,
                temperature=self.temperature,
            )

            # Extract content
            content_dict = response["content"]
            usage = response["usage"]

            # Parse entities
            entities_dict = content_dict["entities"]
            entities = EntityData(
                companies=entities_dict.get("companies", []),
                people=entities_dict.get("people", []),
                locations=entities_dict.get("locations", []),
                topics=entities_dict.get("topics", []),
            )

            # Create ArticleSummary
            summary = ArticleSummary(
                summary_title=content_dict["title"],
                summary=content_dict["summary"],
                key_points=content_dict["key_points"],
                entities=entities,
                summarized_at=datetime.now(),
            )

            # Cache the result if cache service is available
            if self.cache_service:
                self.cache_service.cache_summary(
                    content=content,
                    summary_title=summary.summary_title,
                    summary=summary.summary,
                    key_points=json.dumps(summary.key_points),
                    entities=json.dumps({
                        "companies": entities.companies,
                        "people": entities.people,
                        "locations": entities.locations,
                        "topics": entities.topics,
                    }),
                )

            logger.info(
                "summarization_success",
                title=title[:50],
                tokens=usage["total_tokens"],
                cost=usage["cost"],
                num_key_points=len(summary.key_points),
                num_companies=len(entities.companies),
            )

            return summary

        except Exception as e:
            logger.error(
                f"Error summarizing article '{title[:50]}...': {e}",
                exc_info=True,
            )
            return None

    async def summarize_batch(
        self,
        articles: List[Dict[str, str]],
        max_concurrent: int = 5,
    ) -> List[Optional[ArticleSummary]]:
        """
        Summarize multiple articles in batch with concurrent processing.

        Uses asyncio.gather() for parallel API calls with configurable concurrency limit.
        For even more cost savings (50%), use OpenAI Batch API (24h latency).

        Args:
            articles: List of article dicts with 'title', 'source', 'content', 'url'
            max_concurrent: Maximum number of concurrent API calls (default: 5)

        Returns:
            List of ArticleSummary objects (None for failed articles)
        """
        logger.info(
            f"Summarizing batch of {len(articles)} articles "
            f"(max_concurrent={max_concurrent})"
        )

        # Process in chunks to limit concurrency
        summaries = []
        for i in range(0, len(articles), max_concurrent):
            chunk = articles[i : i + max_concurrent]

            # Create tasks for this chunk
            tasks = [
                self.summarize(
                    title=article["title"],
                    source=article["source"],
                    content=article["content"],
                    url=article.get("url"),
                )
                for article in chunk
            ]

            # Execute chunk concurrently
            chunk_summaries = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            for summary in chunk_summaries:
                if isinstance(summary, Exception):
                    logger.error(f"Error in batch summarization: {summary}")
                    summaries.append(None)
                else:
                    summaries.append(summary)

        successful = sum(1 for s in summaries if s is not None)
        logger.info(
            f"Batch summarization complete: {successful}/{len(articles)} successful"
        )

        return summaries

    def get_stats(self, summaries: List[Optional[ArticleSummary]]) -> Dict[str, any]:
        """
        Calculate summarization statistics.

        Args:
            summaries: List of summaries (including None for failures)

        Returns:
            Statistics dictionary
        """
        successful = [s for s in summaries if s is not None]
        total = len(summaries)
        success_count = len(successful)

        if not successful:
            return {
                "total": total,
                "successful": 0,
                "failed": total,
                "success_rate": 0.0,
                "avg_key_points": 0.0,
                "avg_companies": 0.0,
                "avg_people": 0.0,
            }

        avg_key_points = sum(len(s.key_points) for s in successful) / success_count
        avg_companies = (
            sum(len(s.entities.companies) for s in successful) / success_count
        )
        avg_people = sum(len(s.entities.people) for s in successful) / success_count

        return {
            "total": total,
            "successful": success_count,
            "failed": total - success_count,
            "success_rate": success_count / total,
            "avg_key_points": round(avg_key_points, 1),
            "avg_companies": round(avg_companies, 1),
            "avg_people": round(avg_people, 1),
        }
