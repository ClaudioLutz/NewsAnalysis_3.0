"""Trafilatura-based content extractor for fast web scraping."""

import logging
from datetime import datetime
from typing import Optional

import httpx
import trafilatura
from trafilatura.settings import use_config

from newsanalysis.core.article import ScrapedContent
from newsanalysis.core.enums import ExtractionMethod
from newsanalysis.pipeline.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class TrafilaturaExtractor(BaseScraper):
    """Fast content extraction using Trafilatura library."""

    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        include_comments: bool = False,
        include_tables: bool = True,
    ):
        """
        Initialize Trafilatura extractor.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
            include_comments: Whether to include comments
            include_tables: Whether to include tables
        """
        super().__init__(timeout=timeout, user_agent=user_agent)
        self.include_comments = include_comments
        self.include_tables = include_tables

        # Configure Trafilatura
        self.config = use_config()
        self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", str(timeout))

    @property
    def extraction_method(self) -> ExtractionMethod:
        """Return the extraction method identifier."""
        return ExtractionMethod.TRAFILATURA

    async def extract(self, url: str) -> Optional[ScrapedContent]:
        """
        Extract content from a URL using Trafilatura.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedContent if successful, None if failed
        """
        try:
            logger.info(f"Extracting content from {url} using Trafilatura")

            # Fetch HTML
            html = await self._fetch_html(url)
            if not html:
                logger.warning(f"Failed to fetch HTML from {url}")
                return None

            # Extract content using Trafilatura
            content = trafilatura.extract(
                html,
                include_comments=self.include_comments,
                include_tables=self.include_tables,
                include_formatting=False,
                output_format="txt",
                url=url,
                config=self.config,
            )

            if not content:
                logger.warning(f"No content extracted from {url}")
                return None

            # Validate minimum content length
            if len(content) < 100:
                logger.warning(
                    f"Content too short ({len(content)} chars) from {url}"
                )
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(html, default_url=url)

            # Get author if available
            author = None
            if metadata and metadata.author:
                author = metadata.author

            # Check if we have publish date
            has_date = bool(metadata and metadata.date)

            # Calculate quality score
            quality = self._calculate_quality_score(
                content=content,
                has_author=bool(author),
                has_date=has_date,
            )

            logger.info(
                f"Extracted {len(content)} chars from {url} "
                f"(quality: {quality:.2f})"
            )

            return ScrapedContent(
                content=content,
                author=author,
                content_length=len(content),
                extraction_method=self.extraction_method,
                extraction_quality=quality,
                scraped_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}", exc_info=True)
            return None

    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL.

        Args:
            url: The URL to fetch

        Returns:
            HTML string if successful, None if failed
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    logger.warning(
                        f"Non-HTML content type: {content_type} for {url}"
                    )
                    return None

                return response.text

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
