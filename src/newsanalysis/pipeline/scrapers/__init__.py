"""Content scraping module for article extraction."""

from typing import Optional

from newsanalysis.core.enums import ExtractionMethod
from newsanalysis.pipeline.scrapers.base import BaseScraper
from newsanalysis.pipeline.scrapers.playwright_scraper import PlaywrightExtractor
from newsanalysis.pipeline.scrapers.trafilatura_scraper import TrafilaturaExtractor

__all__ = [
    "BaseScraper",
    "TrafilaturaExtractor",
    "PlaywrightExtractor",
    "create_scraper",
]


def create_scraper(
    method: ExtractionMethod = ExtractionMethod.TRAFILATURA,
    timeout: int = 30,
    user_agent: Optional[str] = None,
) -> BaseScraper:
    """
    Create a content scraper instance.

    Args:
        method: Extraction method to use
        timeout: Request timeout in seconds
        user_agent: Custom user agent string

    Returns:
        BaseScraper instance

    Raises:
        ValueError: If extraction method is not supported
    """
    if method == ExtractionMethod.TRAFILATURA:
        return TrafilaturaExtractor(timeout=timeout, user_agent=user_agent)
    elif method == ExtractionMethod.PLAYWRIGHT:
        return PlaywrightExtractor(timeout=timeout, user_agent=user_agent)
    else:
        raise ValueError(f"Unsupported extraction method: {method}")