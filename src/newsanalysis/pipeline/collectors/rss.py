"""RSS feed collector."""

import asyncio
from datetime import datetime
from typing import List

import feedparser
import httpx
from pydantic import HttpUrl

from newsanalysis.core.article import ArticleMetadata
from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors.base import BaseCollector
from newsanalysis.utils.dates import parse_date
from newsanalysis.utils.exceptions import CollectorError
from newsanalysis.utils.logging import get_logger
from newsanalysis.utils.text import hash_url, normalize_url

logger = get_logger(__name__)


class RSSCollector(BaseCollector):
    """Collector for RSS feeds."""

    def __init__(self, feed_config: FeedConfig, timeout: int = 12):
        """Initialize RSS collector.

        Args:
            feed_config: Feed configuration.
            timeout: HTTP request timeout in seconds.
        """
        super().__init__(feed_config)
        self.timeout = timeout

    async def collect(self) -> List[ArticleMetadata]:
        """Collect articles from RSS feed.

        Returns:
            List of article metadata from RSS feed.

        Raises:
            CollectorError: If RSS feed fetch or parse fails.
        """
        logger.info(
            "collecting_rss",
            feed_name=self.feed_config.name,
            feed_url=str(self.feed_config.url),
        )

        try:
            # Fetch RSS feed content
            feed_content = await self._fetch_feed()

            # Parse RSS feed
            feed = feedparser.parse(feed_content)

            if feed.bozo:
                logger.warning(
                    "rss_parse_warning",
                    feed_name=self.feed_config.name,
                    exception=str(feed.bozo_exception) if hasattr(feed, "bozo_exception") else None,
                )

            # Extract articles
            articles = self._extract_articles(feed)

            logger.info(
                "rss_collection_complete",
                feed_name=self.feed_config.name,
                articles_collected=len(articles),
            )

            return articles

        except Exception as e:
            logger.error(
                "rss_collection_failed",
                feed_name=self.feed_config.name,
                error=str(e),
            )
            raise CollectorError(f"Failed to collect from RSS feed {self.feed_config.name}: {e}") from e

    async def _fetch_feed(self) -> str:
        """Fetch RSS feed content via HTTP.

        Returns:
            Raw RSS feed content as string.

        Raises:
            CollectorError: If HTTP request fails.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(str(self.feed_config.url))
                response.raise_for_status()
                return response.text

        except httpx.HTTPError as e:
            raise CollectorError(f"HTTP request failed for {self.feed_config.url}: {e}") from e

    def _extract_articles(self, feed) -> List[ArticleMetadata]:
        """Extract article metadata from parsed RSS feed.

        Args:
            feed: Parsed feedparser feed object.

        Returns:
            List of article metadata.
        """
        articles = []

        for entry in feed.entries:
            try:
                # Extract URL
                url = entry.get("link")
                if not url:
                    logger.debug("rss_entry_no_link", entry_title=entry.get("title", "Unknown"))
                    continue

                # Normalize URL
                normalized = normalize_url(url)
                url_hash_value = hash_url(normalized)

                # Extract title
                title = entry.get("title", "").strip()
                if not title:
                    logger.debug("rss_entry_no_title", url=url)
                    continue

                # Parse publication date
                published_at = None
                if "published" in entry:
                    published_at = parse_date(entry.published)
                elif "updated" in entry:
                    published_at = parse_date(entry.updated)

                # Check article age
                if not self._should_include_article(published_at):
                    logger.debug(
                        "rss_article_too_old",
                        title=title,
                        published_at=published_at,
                    )
                    continue

                # Create article metadata
                article = ArticleMetadata(
                    url=HttpUrl(url),
                    normalized_url=normalized,
                    url_hash=url_hash_value,
                    title=title,
                    source=self.feed_config.name,
                    published_at=published_at,
                    collected_at=datetime.now(),
                    feed_priority=self.feed_config.priority,
                )

                articles.append(article)

            except Exception as e:
                logger.warning(
                    "rss_entry_parse_error",
                    feed_name=self.feed_config.name,
                    error=str(e),
                )
                continue

        return articles
