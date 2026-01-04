"""Base content scraper for article extraction."""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from newsanalysis.core.article import ScrapedContent
from newsanalysis.core.enums import ExtractionMethod

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for content scrapers."""

    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the scraper.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    @abstractmethod
    async def extract(self, url: str) -> Optional[ScrapedContent]:
        """
        Extract content from a URL.

        Args:
            url: The URL to scrape

        Returns:
            ScrapedContent if successful, None if failed
        """
        pass

    @property
    @abstractmethod
    def extraction_method(self) -> ExtractionMethod:
        """Return the extraction method identifier."""
        pass

    def _calculate_quality_score(
        self,
        content: str,
        has_author: bool = False,
        has_date: bool = False,
    ) -> float:
        """
        Calculate content quality score (0.0-1.0).

        Quality factors:
        - Content length (0.4 weight)
        - Has author (0.3 weight)
        - Has date (0.3 weight)

        Args:
            content: Extracted content text
            has_author: Whether author was extracted
            has_date: Whether publish date was extracted

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0

        # Length score (0.0-0.4)
        # Optimal length: 1500-5000 chars
        # Below 500: poor quality
        # Above 10000: might be too much noise
        length = len(content)
        if length < 500:
            length_score = length / 500 * 0.4
        elif 1500 <= length <= 5000:
            length_score = 0.4
        elif 500 <= length < 1500:
            # Scale from 0.2 to 0.4
            length_score = 0.2 + ((length - 500) / 1000) * 0.2
        else:  # > 5000
            # Slowly decrease after 5000
            length_score = max(0.2, 0.4 - ((length - 5000) / 20000) * 0.2)

        score += length_score

        # Author score (0.0-0.3)
        if has_author:
            score += 0.3

        # Date score (0.0-0.3)
        if has_date:
            score += 0.3

        return min(1.0, score)
