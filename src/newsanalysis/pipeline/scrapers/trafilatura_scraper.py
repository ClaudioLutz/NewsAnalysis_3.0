"""Trafilatura-based content extractor for fast web scraping."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import trafilatura
from trafilatura.settings import use_config

# Use curl_cffi for TLS fingerprint impersonation (bypasses Akamai/Cloudflare)
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None

# Fallback to httpx if curl_cffi not available
import httpx

from newsanalysis.core.article import ScrapedContent
from newsanalysis.core.enums import ExtractionMethod
from newsanalysis.pipeline.scrapers.base import BaseScraper
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# Thread pool for sync curl_cffi calls
_executor = ThreadPoolExecutor(max_workers=4)


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
            logger.info("extracting_content_trafilatura", url=url)

            # Fetch HTML
            html = await self._fetch_html(url)
            if not html:
                logger.warning("fetch_html_failed", url=url)
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
                logger.warning("no_content_extracted", url=url)
                return None

            # Validate minimum content length
            if len(content) < 100:
                logger.warning("content_too_short", url=url, length=len(content))
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
            logger.error("extraction_error", url=url, error=str(e), exc_info=True)
            return None

    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL.

        Uses curl_cffi with Chrome TLS fingerprint impersonation to bypass
        bot protection (Akamai, Cloudflare). Falls back to httpx if unavailable.

        Args:
            url: The URL to fetch

        Returns:
            HTML string if successful, None if failed
        """
        # Try curl_cffi first (bypasses TLS fingerprinting)
        if CURL_CFFI_AVAILABLE:
            try:
                html = await self._fetch_with_curl_cffi(url)
                if html:
                    return html
                logger.warning("curl_cffi_failed_trying_httpx", url=url)
            except Exception as e:
                logger.warning("curl_cffi_error", url=url, error=str(e))

        # Fall back to httpx
        return await self._fetch_with_httpx(url)

    async def _fetch_with_curl_cffi(self, url: str) -> Optional[str]:
        """Fetch HTML using curl_cffi with Chrome impersonation."""
        def _sync_fetch():
            response = curl_requests.get(
                url,
                impersonate="chrome",
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response.text

        try:
            loop = asyncio.get_event_loop()
            html = await loop.run_in_executor(_executor, _sync_fetch)

            # Basic validation
            if html and len(html) > 500:
                return html
            return None

        except Exception as e:
            logger.warning("curl_cffi_fetch_error", url=url, error=str(e))
            return None

    async def _fetch_with_httpx(self, url: str) -> Optional[str]:
        """Fetch HTML using httpx (fallback method)."""
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
                    logger.warning("non_html_content", url=url, content_type=content_type)
                    return None

                return response.text

        except httpx.TimeoutException:
            logger.warning("fetch_timeout", url=url)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("http_error", url=url, status_code=e.response.status_code)
            return None
        except Exception as e:
            logger.error("fetch_error", url=url, error=str(e))
            return None
