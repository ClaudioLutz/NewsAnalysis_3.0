"""HTML page collector using Beautiful Soup."""

import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from newsanalysis.core.article import ArticleMetadata
from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors.base import BaseCollector
from newsanalysis.utils.exceptions import CollectorError
from newsanalysis.utils.logging import get_logger
from newsanalysis.utils.text_utils import hash_url, normalize_url

logger = get_logger(__name__)


class HTMLCollector(BaseCollector):
    """Collector for HTML pages with article links.

    Extracts article links from a listing page (e.g., news archive, category page).
    """

    def __init__(
        self,
        feed_config: FeedConfig,
        timeout: int = 12,
        link_selector: str = "a[href]",
        title_attribute: str = "text",
    ):
        """Initialize HTML collector.

        Args:
            feed_config: Feed configuration.
            timeout: HTTP request timeout in seconds.
            link_selector: CSS selector for article links.
            title_attribute: Attribute to use for title ('text', 'title', or custom attribute name).
        """
        super().__init__(feed_config)
        self.timeout = timeout
        self.link_selector = link_selector
        self.title_attribute = title_attribute

    async def collect(self) -> List[ArticleMetadata]:
        """Collect articles from HTML page.

        Returns:
            List of article metadata extracted from HTML.

        Raises:
            CollectorError: If HTML fetch or parse fails.
        """
        logger.info(
            "collecting_html",
            feed_name=self.feed_config.name,
            feed_url=str(self.feed_config.url),
        )

        try:
            # Fetch HTML page
            html_content = await self._fetch_page()

            # Parse HTML and extract articles
            articles = self._extract_articles_from_html(html_content)

            logger.info(
                "html_collection_complete",
                feed_name=self.feed_config.name,
                articles_collected=len(articles),
            )

            return articles

        except Exception as e:
            logger.error(
                "html_collection_failed",
                feed_name=self.feed_config.name,
                error=str(e),
            )
            raise CollectorError(f"Failed to collect from HTML page {self.feed_config.name}: {e}") from e

    async def _fetch_page(self) -> str:
        """Fetch HTML page content via HTTP.

        Returns:
            Raw HTML content as string.

        Raises:
            CollectorError: If HTTP request fails.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = await client.get(str(self.feed_config.url))
                response.raise_for_status()
                return response.text

        except httpx.HTTPError as e:
            raise CollectorError(f"HTTP request failed for {self.feed_config.url}: {e}") from e

    def _extract_articles_from_html(self, html_content: str) -> List[ArticleMetadata]:
        """Parse HTML and extract article links.

        Args:
            html_content: Raw HTML content.

        Returns:
            List of article metadata.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        articles = []
        seen_urls = set()

        # Find all links matching the selector
        links = soup.select(self.link_selector)

        for link in links:
            try:
                # Extract URL
                href = link.get("href")
                if not href:
                    continue

                # Convert relative URLs to absolute
                url = urljoin(str(self.feed_config.url), href)

                # Filter out non-article links
                if not self._is_article_link(url):
                    continue

                # Normalize URL
                normalized = normalize_url(url)

                # Skip duplicates
                if normalized in seen_urls:
                    continue
                seen_urls.add(normalized)

                url_hash_value = hash_url(normalized)

                # Extract title
                title = self._extract_title(link)
                if not title or len(title) < 5:
                    logger.debug("html_link_no_title", url=url)
                    continue

                # Create article metadata
                article = ArticleMetadata(
                    url=HttpUrl(url),
                    normalized_url=normalized,
                    url_hash=url_hash_value,
                    title=title,
                    source=self.feed_config.name,
                    published_at=None,  # HTML collector doesn't extract dates
                    collected_at=datetime.now(),
                    feed_priority=self.feed_config.priority,
                )

                articles.append(article)

            except Exception as e:
                logger.warning(
                    "html_link_parse_error",
                    feed_name=self.feed_config.name,
                    error=str(e),
                )
                continue

        return articles

    def _extract_title(self, link_elem) -> str:
        """Extract title from link element.

        Args:
            link_elem: BeautifulSoup link element.

        Returns:
            Extracted title.
        """
        if self.title_attribute == "text":
            # Use link text
            title = link_elem.get_text(strip=True)
        elif self.title_attribute == "title":
            # Use title attribute
            title = link_elem.get("title", "").strip()
        else:
            # Use custom attribute
            title = link_elem.get(self.title_attribute, "").strip()

        # Fallback: use link text if custom attribute is empty
        if not title:
            title = link_elem.get_text(strip=True)

        return title

    def _is_article_link(self, url: str) -> bool:
        """Check if URL is likely an article link.

        Filters out navigation, static pages, external links, etc.

        Args:
            url: URL to check.

        Returns:
            True if URL looks like an article, False otherwise.
        """
        parsed = urlparse(url)

        # Must be same domain as feed URL
        feed_domain = urlparse(str(self.feed_config.url)).netloc
        if parsed.netloc and parsed.netloc != feed_domain:
            return False

        # Exclude common non-article paths
        exclude_patterns = [
            r"/tag/",
            r"/category/",
            r"/author/",
            r"/page/\d+",
            r"/search",
            r"/login",
            r"/register",
            r"/contact",
            r"/about",
            r"/impressum",
            r"/datenschutz",
            r"/privacy",
            r"/terms",
            r"#",
            r"javascript:",
            r"mailto:",
            r"\.(pdf|jpg|jpeg|png|gif|zip|exe|dmg)$",
        ]

        path = parsed.path.lower()
        for pattern in exclude_patterns:
            if re.search(pattern, path):
                return False

        return True
