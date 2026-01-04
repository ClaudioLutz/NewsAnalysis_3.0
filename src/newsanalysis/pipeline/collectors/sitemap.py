"""Sitemap XML collector."""

import re
from datetime import datetime
from typing import List
from xml.etree import ElementTree as ET

import httpx
from pydantic import HttpUrl

from newsanalysis.core.article import ArticleMetadata
from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors.base import BaseCollector
from newsanalysis.utils.date_utils import parse_date
from newsanalysis.utils.exceptions import CollectorError
from newsanalysis.utils.logging import get_logger
from newsanalysis.utils.text_utils import hash_url, normalize_url

logger = get_logger(__name__)


class SitemapCollector(BaseCollector):
    """Collector for XML sitemaps."""

    # XML namespaces used in sitemaps
    NAMESPACES = {
        "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
    }

    def __init__(self, feed_config: FeedConfig, timeout: int = 12):
        """Initialize sitemap collector.

        Args:
            feed_config: Feed configuration.
            timeout: HTTP request timeout in seconds.
        """
        super().__init__(feed_config)
        self.timeout = timeout

    async def collect(self) -> List[ArticleMetadata]:
        """Collect articles from XML sitemap.

        Returns:
            List of article metadata from sitemap.

        Raises:
            CollectorError: If sitemap fetch or parse fails.
        """
        logger.info(
            "collecting_sitemap",
            feed_name=self.feed_config.name,
            feed_url=str(self.feed_config.url),
        )

        try:
            # Fetch sitemap content
            sitemap_content = await self._fetch_sitemap()

            # Parse sitemap XML
            articles = self._parse_sitemap(sitemap_content)

            logger.info(
                "sitemap_collection_complete",
                feed_name=self.feed_config.name,
                articles_collected=len(articles),
            )

            return articles

        except Exception as e:
            logger.error(
                "sitemap_collection_failed",
                feed_name=self.feed_config.name,
                error=str(e),
            )
            raise CollectorError(f"Failed to collect from sitemap {self.feed_config.name}: {e}") from e

    async def _fetch_sitemap(self) -> str:
        """Fetch sitemap XML content via HTTP.

        Returns:
            Raw sitemap XML as string.

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

    def _parse_sitemap(self, xml_content: str) -> List[ArticleMetadata]:
        """Parse sitemap XML and extract article metadata.

        Args:
            xml_content: Raw XML content.

        Returns:
            List of article metadata.

        Raises:
            CollectorError: If XML parsing fails.
        """
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise CollectorError(f"Failed to parse sitemap XML: {e}") from e

        articles = []

        # Check if this is a sitemap index (contains other sitemaps)
        if root.tag.endswith("sitemapindex"):
            logger.warning(
                "sitemap_index_not_supported",
                feed_name=self.feed_config.name,
                message="Sitemap indexes not yet supported, use direct sitemap URLs",
            )
            return articles

        # Parse URL entries
        for url_elem in root.findall("sitemap:url", self.NAMESPACES):
            article = self._parse_url_entry(url_elem)
            if article:
                articles.append(article)

        return articles

    def _parse_url_entry(self, url_elem: ET.Element) -> ArticleMetadata | None:
        """Parse a single URL entry from sitemap.

        Args:
            url_elem: XML element for <url> entry.

        Returns:
            ArticleMetadata if valid, None otherwise.
        """
        try:
            # Extract location (URL)
            loc_elem = url_elem.find("sitemap:loc", self.NAMESPACES)
            if loc_elem is None or not loc_elem.text:
                return None

            url = loc_elem.text.strip()
            normalized = normalize_url(url)
            url_hash_value = hash_url(normalized)

            # Extract last modification date
            lastmod_elem = url_elem.find("sitemap:lastmod", self.NAMESPACES)
            published_at = None
            if lastmod_elem is not None and lastmod_elem.text:
                published_at = parse_date(lastmod_elem.text)

            # Check article age
            if not self._should_include_article(published_at):
                logger.debug(
                    "sitemap_article_too_old",
                    url=url,
                    published_at=published_at,
                )
                return None

            # Try to extract title from news:news extension
            title = self._extract_news_title(url_elem)
            if not title:
                # Fallback: extract title from URL path
                title = self._extract_title_from_url(url)

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

            return article

        except Exception as e:
            logger.warning(
                "sitemap_entry_parse_error",
                feed_name=self.feed_config.name,
                error=str(e),
            )
            return None

    def _extract_news_title(self, url_elem: ET.Element) -> str | None:
        """Extract title from Google News sitemap extension.

        Args:
            url_elem: URL element that may contain news:news child.

        Returns:
            Title if found, None otherwise.
        """
        news_elem = url_elem.find("news:news", self.NAMESPACES)
        if news_elem is not None:
            title_elem = news_elem.find("news:title", self.NAMESPACES)
            if title_elem is not None and title_elem.text:
                return title_elem.text.strip()
        return None

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a readable title from URL path.

        Args:
            url: Article URL.

        Returns:
            Extracted title.
        """
        # Extract path from URL
        path = url.split("//")[-1].split("/", 1)[-1] if "//" in url else url

        # Remove query parameters and anchors
        path = path.split("?")[0].split("#")[0]

        # Remove file extension
        path = re.sub(r"\.(html|htm|php|aspx)$", "", path)

        # Replace hyphens and underscores with spaces
        title = path.replace("-", " ").replace("_", " ")

        # Clean up multiple spaces
        title = " ".join(title.split())

        # Capitalize words
        title = title.title()

        return title if title else "Article from Sitemap"
