"""JSON output formatter."""

import json
from typing import Any, Dict

from newsanalysis.core.digest import DailyDigest
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class JSONFormatter:
    """Format digest as JSON output."""

    def format(self, digest: DailyDigest) -> str:
        """Format digest as JSON.

        Args:
            digest: Daily digest to format.

        Returns:
            JSON string.
        """
        logger.info("formatting_json_digest", date=str(digest.date))

        try:
            # Convert digest to dictionary
            digest_dict = self._build_digest_dict(digest)

            # Format as pretty JSON
            json_output = json.dumps(digest_dict, indent=2, ensure_ascii=False)

            logger.info("json_formatted", size=len(json_output))

            return json_output

        except Exception as e:
            logger.error("json_formatting_failed", error=str(e))
            raise

    def _build_digest_dict(self, digest: DailyDigest) -> Dict[str, Any]:
        """Build digest dictionary for JSON serialization.

        Args:
            digest: Daily digest.

        Returns:
            Dictionary representation.
        """
        return {
            "digest_metadata": {
                "date": digest.date.isoformat(),
                "version": digest.version,
                "generated_at": digest.generated_at.isoformat(),
                "article_count": digest.article_count,
                "cluster_count": digest.cluster_count,
                "run_id": digest.run_id,
            },
            "meta_analysis": {
                "key_themes": digest.meta_analysis.key_themes,
                "credit_risk_signals": digest.meta_analysis.credit_risk_signals,
                "regulatory_updates": digest.meta_analysis.regulatory_updates,
                "market_insights": digest.meta_analysis.market_insights,
            },
            "articles": [self._format_article(article) for article in digest.articles],
        }

    def _format_article(self, article) -> Dict[str, Any]:
        """Format article for JSON output.

        Args:
            article: Article object.

        Returns:
            Article dictionary.
        """
        return {
            "id": article.id,
            "url": str(article.url),
            "title": article.summary_title or article.title,
            "source": article.source,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "topic": article.topic,
            "confidence": article.confidence,
            "summary": article.summary,
            "key_points": article.key_points or [],
            "entities": {
                "companies": article.entities.get("companies", []) if article.entities else [],
                "people": article.entities.get("people", []) if article.entities else [],
                "locations": article.entities.get("locations", []) if article.entities else [],
                "topics": article.entities.get("topics", []) if article.entities else [],
            }
            if article.entities
            else {"companies": [], "people": [], "locations": [], "topics": []},
            "metadata": {
                "feed_priority": article.feed_priority,
                "extraction_method": article.extraction_method.value if article.extraction_method else None,
                "extraction_quality": article.extraction_quality,
                "content_length": article.content_length,
                "author": article.author,
            },
        }
