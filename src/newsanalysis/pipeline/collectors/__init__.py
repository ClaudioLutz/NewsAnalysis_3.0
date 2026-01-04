"""News collectors for different feed types."""

from newsanalysis.core.config import FeedConfig
from newsanalysis.pipeline.collectors.base import BaseCollector
from newsanalysis.pipeline.collectors.html import HTMLCollector
from newsanalysis.pipeline.collectors.rss import RSSCollector
from newsanalysis.pipeline.collectors.sitemap import SitemapCollector
from newsanalysis.utils.exceptions import CollectorError

__all__ = [
    "BaseCollector",
    "RSSCollector",
    "SitemapCollector",
    "HTMLCollector",
    "create_collector",
]


def create_collector(feed_config: FeedConfig, timeout: int = 12) -> BaseCollector:
    """Factory function to create appropriate collector for feed type.

    Args:
        feed_config: Feed configuration.
        timeout: HTTP request timeout in seconds.

    Returns:
        Collector instance for the feed type.

    Raises:
        CollectorError: If feed type is not supported.
    """
    collectors = {
        "rss": RSSCollector,
        "sitemap": SitemapCollector,
        "html": HTMLCollector,
    }

    collector_class = collectors.get(feed_config.type)
    if collector_class is None:
        raise CollectorError(f"Unsupported feed type: {feed_config.type}")

    return collector_class(feed_config, timeout)
