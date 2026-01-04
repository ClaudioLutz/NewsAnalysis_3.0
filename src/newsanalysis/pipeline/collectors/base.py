"""Base collector interface."""

from abc import ABC, abstractmethod
from typing import List

from newsanalysis.core.article import ArticleMetadata
from newsanalysis.core.config import FeedConfig


class BaseCollector(ABC):
    """Abstract base class for news collectors."""

    def __init__(self, feed_config: FeedConfig):
        """Initialize collector with feed configuration.

        Args:
            feed_config: Feed configuration with URL, type, priority, etc.
        """
        self.feed_config = feed_config

    @abstractmethod
    async def collect(self) -> List[ArticleMetadata]:
        """Collect articles from the news source.

        Returns:
            List of collected article metadata.

        Raises:
            CollectorError: If collection fails.
        """
        pass

    def _should_include_article(self, published_at) -> bool:
        """Check if article should be included based on age.

        Args:
            published_at: Article publication datetime.

        Returns:
            True if article is within max_age_hours, False otherwise.
        """
        from newsanalysis.utils.dates import is_within_hours

        if published_at is None:
            # Include articles without publication date
            return True

        return is_within_hours(published_at, self.feed_config.max_age_hours)
