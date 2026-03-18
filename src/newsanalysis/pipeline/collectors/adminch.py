"""Collector for news.admin.ch (Swiss Federal Administration).

The federal government replaced their RSS feed with a Nuxt.js SPA in April 2025.
This collector scrapes the server-side-rendered news listing page, which contains
article cards with date, title, description, and link — but no images.
Only articles published today are collected.
"""

import re
from datetime import UTC, datetime

import httpx
from pydantic import HttpUrl

from newsanalysis.core.article import ArticleMetadata
from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors.base import BaseCollector
from newsanalysis.utils.exceptions import CollectorError
from newsanalysis.utils.logging import get_logger
from newsanalysis.utils.text_utils import hash_url, normalize_url

logger = get_logger(__name__)

# German month names for parsing dates like "17. März 2026"
GERMAN_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}


def _parse_german_date(date_str: str) -> datetime | None:
    """Parse a German date string like '17. März 2026'.

    Args:
        date_str: German date string.

    Returns:
        Parsed datetime or None if parsing fails.
    """
    match = re.match(r"(\d{1,2})\.\s+(\w+)\s+(\d{4})", date_str.strip())
    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2).lower()
    year = int(match.group(3))

    month = GERMAN_MONTHS.get(month_name)
    if month is None:
        return None

    try:
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


class AdminChCollector(BaseCollector):
    """Collector for the Swiss Federal Administration news portal.

    Scrapes the SSR news listing at news.admin.ch/de/newnsb and extracts
    only today's articles. The page renders ~12 article cards with date,
    title, description, and link (no images).
    """

    LISTING_URL = (
        "https://www.news.admin.ch/de/newnsb"
        "?newsCategoryIDs=medienmitteilung&sort=dateDecreasing&display=list"
    )

    def __init__(self, feed_config: FeedConfig, timeout: int = 15):
        """Initialize admin.ch collector.

        Args:
            feed_config: Feed configuration.
            timeout: HTTP request timeout in seconds.
        """
        super().__init__(feed_config)
        self.timeout = timeout

    async def collect(self) -> list[ArticleMetadata]:
        """Collect today's articles from news.admin.ch.

        Returns:
            List of article metadata for today only.

        Raises:
            CollectorError: If fetch or parse fails.
        """
        logger.info(
            "collecting_adminch",
            feed_name=self.feed_config.name,
            feed_url=self.LISTING_URL,
        )

        try:
            html = await self._fetch_page()
            articles = self._extract_articles(html)

            logger.info(
                "adminch_collection_complete",
                feed_name=self.feed_config.name,
                articles_collected=len(articles),
            )

            return articles

        except Exception as e:
            logger.error(
                "adminch_collection_failed",
                feed_name=self.feed_config.name,
                error=str(e),
            )
            raise CollectorError(f"Failed to collect from {self.feed_config.name}: {e}") from e

    async def _fetch_page(self) -> str:
        """Fetch the news listing page.

        Returns:
            Raw HTML content.

        Raises:
            CollectorError: If HTTP request fails.
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, follow_redirects=True, headers=headers
            ) as client:
                response = await client.get(self.LISTING_URL)
                response.raise_for_status()
                return response.text

        except httpx.HTTPError as e:
            raise CollectorError(f"HTTP request failed for {self.LISTING_URL}: {e}") from e

    def _extract_articles(self, html: str) -> list[ArticleMetadata]:
        """Extract today's articles from the SSR HTML.

        The page contains card elements with structure:
          <div class="card card--list-without-image card--clickable" ...>
            <span class="meta-info__item">17. März 2026</span>
            <h2>Title</h2>
            <a href="/de/newnsb/{id}">

        Args:
            html: Raw HTML content.

        Returns:
            List of today's articles.
        """
        today = datetime.now(UTC).date()
        articles: list[ArticleMetadata] = []
        seen_urls: set[str] = set()

        # Find all card blocks
        card_pattern = re.compile(
            r'<div[^>]*class="card card--list-without-image[^"]*"[^>]*>',
        )
        card_starts = [m.start() for m in card_pattern.finditer(html)]

        for i, start in enumerate(card_starts):
            end = card_starts[i + 1] if i + 1 < len(card_starts) else start + 5000
            card_html = html[start:end]

            try:
                # Extract date
                date_match = re.search(r'<span class="meta-info__item">([^<]+)</span>', card_html)
                if not date_match:
                    continue

                published_at = _parse_german_date(date_match.group(1))
                if published_at is None:
                    continue

                # Only today's articles
                if published_at.date() != today:
                    logger.debug(
                        "adminch_article_not_today",
                        date=date_match.group(1),
                    )
                    continue

                # Check max_age_hours filter from base class
                if not self._should_include_article(published_at):
                    continue

                # Extract title from <h2>
                title_match = re.search(r"<h2[^>]*>([^<]+)</h2>", card_html)
                if not title_match:
                    continue
                title = title_match.group(1).strip()
                if not title:
                    continue

                # Extract link
                link_match = re.search(r'href="(/de/newnsb/[A-Za-z0-9_-]+)"', card_html)
                if not link_match:
                    continue

                url = f"https://www.news.admin.ch{link_match.group(1)}"
                normalized = normalize_url(url)

                if normalized in seen_urls:
                    continue
                seen_urls.add(normalized)

                url_hash_value = hash_url(normalized)

                article = ArticleMetadata(
                    url=HttpUrl(url),
                    normalized_url=normalized,
                    url_hash=url_hash_value,
                    title=title,
                    source=self.feed_config.name,
                    published_at=published_at,
                    collected_at=datetime.now(UTC),
                    feed_priority=self.feed_config.priority,
                )
                articles.append(article)

            except Exception as e:
                logger.warning(
                    "adminch_card_parse_error",
                    error=str(e),
                )
                continue

        return articles
