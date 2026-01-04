"""Playwright-based content extractor for JavaScript-heavy sites."""

import logging
from datetime import datetime
from typing import Optional

import trafilatura
from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeout

from newsanalysis.core.article import ScrapedContent
from newsanalysis.core.enums import ExtractionMethod
from newsanalysis.pipeline.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class PlaywrightExtractor(BaseScraper):
    """Content extraction using Playwright for JavaScript rendering."""

    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        headless: bool = True,
        wait_for_network_idle: bool = True,
    ):
        """
        Initialize Playwright extractor.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
            headless: Run browser in headless mode
            wait_for_network_idle: Wait for network to be idle before extracting
        """
        super().__init__(timeout=timeout, user_agent=user_agent)
        self.headless = headless
        self.wait_for_network_idle = wait_for_network_idle
        self._browser: Optional[Browser] = None

    @property
    def extraction_method(self) -> ExtractionMethod:
        """Return the extraction method identifier."""
        return ExtractionMethod.PLAYWRIGHT

    async def extract(self, url: str) -> Optional[ScrapedContent]:
        """
        Extract content from a URL using Playwright.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedContent if successful, None if failed
        """
        try:
            logger.info("extracting_content_playwright", url=url)

            # Fetch rendered HTML
            html = await self._fetch_rendered_html(url)
            if not html:
                logger.warning("fetch_rendered_html_failed", url=url)
                return None

            # Use Trafilatura to extract text from rendered HTML
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                output_format="txt",
                url=url,
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

            # Calculate quality score (slightly lower than Trafilatura for same content)
            quality = self._calculate_quality_score(
                content=content,
                has_author=bool(author),
                has_date=has_date,
            )
            # Reduce quality by 5% since Playwright is a fallback
            quality = max(0.0, quality - 0.05)

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
            logger.error(
                f"Error extracting content from {url}: {e}",
                exc_info=True,
            )
            return None

    async def _fetch_rendered_html(self, url: str) -> Optional[str]:
        """
        Fetch and render HTML using Playwright.

        Args:
            url: The URL to fetch

        Returns:
            Rendered HTML string if successful, None if failed
        """
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=self.headless)

                try:
                    # Create context with custom user agent
                    context = await browser.new_context(
                        user_agent=self.user_agent,
                        viewport={"width": 1920, "height": 1080},
                    )

                    # Create page
                    page = await context.new_page()

                    # Set timeout
                    page.set_default_timeout(self.timeout * 1000)

                    # Navigate to URL
                    if self.wait_for_network_idle:
                        await page.goto(
                            url,
                            wait_until="networkidle",
                            timeout=self.timeout * 1000,
                        )
                    else:
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout * 1000,
                        )

                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(1000)

                    # Get rendered HTML
                    html = await page.content()

                    await context.close()
                    return html

                finally:
                    await browser.close()

        except PlaywrightTimeout:
            logger.warning("playwright_timeout", url=url)
            return None
        except Exception as e:
            logger.error("playwright_render_error", url=url, error=str(e))
            return None

    async def close(self):
        """Close browser if it's running."""
        if self._browser:
            await self._browser.close()
            self._browser = None
