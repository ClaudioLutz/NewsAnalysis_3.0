"""Image extraction from web articles using newspaper3k and BeautifulSoup."""

from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle

from newsanalysis.core.article import ArticleImage
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class ImageExtractor:
    """Extract images from web articles using newspaper3k and BeautifulSoup."""

    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        max_images: int = 5,
    ):
        """
        Initialize ImageExtractor.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
            max_images: Maximum number of images to extract per article
        """
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.max_images = max_images

    async def extract_images(
        self, url: str, html_content: Optional[str] = None
    ) -> List[ArticleImage]:
        """
        Extract images from an article URL.

        Uses newspaper3k for featured image and BeautifulSoup for additional images.

        Args:
            url: The article URL
            html_content: Optional pre-fetched HTML content

        Returns:
            List of ArticleImage objects
        """
        images = []

        try:
            # Step 1: Try newspaper3k for featured image
            featured_image = await self._extract_with_newspaper3k(url)
            if featured_image:
                images.append(featured_image)
                logger.info(
                    "extracted_featured_image",
                    url=url,
                    image_url=featured_image.image_url,
                )

            # Step 2: Use BeautifulSoup for additional images
            if html_content or len(images) < self.max_images:
                # Fetch HTML if not provided
                if not html_content:
                    html_content = await self._fetch_html(url)

                if html_content:
                    additional_images = self._extract_with_beautifulsoup(
                        url, html_content, featured_url=images[0].image_url if images else None
                    )
                    # Limit to max_images total
                    remaining_slots = self.max_images - len(images)
                    images.extend(additional_images[:remaining_slots])

                    logger.info(
                        "extracted_additional_images",
                        url=url,
                        count=len(additional_images),
                        total=len(images),
                    )

        except Exception as e:
            logger.error("image_extraction_error", url=url, error=str(e), exc_info=True)

        return images

    async def _extract_with_newspaper3k(self, url: str) -> Optional[ArticleImage]:
        """
        Extract featured image using newspaper3k.

        Args:
            url: Article URL

        Returns:
            ArticleImage if successful, None otherwise
        """
        try:
            article = NewspaperArticle(url)
            article.download()
            article.parse()

            if article.top_image:
                return ArticleImage(
                    image_url=article.top_image,
                    is_featured=True,
                    extraction_method="newspaper3k",
                    extraction_quality="high",
                    created_at=datetime.now(),
                )

        except Exception as e:
            logger.warning("newspaper3k_failed", url=url, error=str(e))

        return None

    def _extract_with_beautifulsoup(
        self, url: str, html_content: str, featured_url: Optional[str] = None
    ) -> List[ArticleImage]:
        """
        Extract images using BeautifulSoup.

        Args:
            url: Article URL (for converting relative URLs)
            html_content: HTML content
            featured_url: URL of featured image to exclude

        Returns:
            List of ArticleImage objects
        """
        images = []

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find all img tags
            for img in soup.find_all("img"):
                # Check multiple attributes for lazy-loaded images
                img_url = (
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-lazy")
                    or img.get("data-original")
                    or img.get("data-url")
                )

                if img_url:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(url, img_url)

                    # Skip if this is the featured image
                    if featured_url and absolute_url == featured_url:
                        continue

                    # Validate URL
                    if self._validate_image_url(absolute_url):
                        images.append(
                            ArticleImage(
                                image_url=absolute_url,
                                is_featured=False,
                                extraction_method="beautifulsoup",
                                extraction_quality="medium",
                                image_width=self._parse_dimension(img.get("width")),
                                image_height=self._parse_dimension(img.get("height")),
                                created_at=datetime.now(),
                            )
                        )

        except Exception as e:
            logger.warning("beautifulsoup_failed", url=url, error=str(e))

        return images

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

    def _validate_image_url(self, url: str) -> bool:
        """
        Validate image URL.

        Args:
            url: Image URL to validate

        Returns:
            True if valid, False otherwise
        """
        from urllib.parse import urlparse
        from pathlib import Path

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                return False

            # Check extension
            path_ext = Path(parsed.path).suffix.lower()
            allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
            if path_ext and path_ext not in allowed_extensions:
                return False

            return True

        except Exception:
            return False

    def _parse_dimension(self, value: Optional[str]) -> Optional[int]:
        """
        Parse dimension string to integer.

        Args:
            value: Dimension string (e.g., "600" or "600px")

        Returns:
            Integer dimension or None
        """
        if not value:
            return None

        try:
            # Remove 'px' suffix if present
            value_str = str(value).replace("px", "").strip()
            return int(value_str)
        except (ValueError, AttributeError):
            return None
