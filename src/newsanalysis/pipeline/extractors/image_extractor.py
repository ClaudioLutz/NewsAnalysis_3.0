"""Image extraction from web articles using newspaper3k and BeautifulSoup."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle

# Use curl_cffi for TLS fingerprint impersonation (bypasses Akamai/Cloudflare)
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None

from newsanalysis.core.article import ArticleImage
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# Thread pool for sync curl_cffi calls
_executor = ThreadPoolExecutor(max_workers=2)

# Minimum image dimensions to be considered a featured image
MIN_IMAGE_WIDTH = 300
MIN_IMAGE_HEIGHT = 200


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

        Priority order:
        1. OG:image meta tag (most reliable for news sites)
        2. newspaper3k featured image
        3. Large images from article content

        Args:
            url: The article URL
            html_content: Optional pre-fetched HTML content

        Returns:
            List of ArticleImage objects
        """
        images = []
        featured_url = None

        try:
            # Step 1: Fetch HTML (use curl_cffi to bypass bot protection)
            if not html_content:
                html_content = await self._fetch_html(url)

            if not html_content:
                logger.warning("no_html_for_image_extraction", url=url)
                return images

            # Step 2: Try OG:image first (most reliable for news sites)
            og_image = self._extract_og_image(url, html_content)
            if og_image:
                images.append(og_image)
                featured_url = og_image.image_url
                logger.info(
                    "extracted_og_image",
                    url=url,
                    image_url=og_image.image_url,
                )

            # Step 3: Try newspaper3k if no OG:image found
            if not images:
                featured_image = await self._extract_with_newspaper3k(url)
                if featured_image:
                    images.append(featured_image)
                    featured_url = featured_image.image_url
                    logger.info(
                        "extracted_featured_image",
                        url=url,
                        image_url=featured_image.image_url,
                    )

            # Step 4: Extract large content images as alternatives
            if len(images) < self.max_images:
                additional_images = self._extract_large_content_images(
                    url, html_content, exclude_url=featured_url
                )
                remaining_slots = self.max_images - len(images)
                images.extend(additional_images[:remaining_slots])

                if additional_images:
                    logger.info(
                        "extracted_content_images",
                        url=url,
                        count=len(additional_images),
                        total=len(images),
                    )

        except Exception as e:
            logger.error("image_extraction_error", url=url, error=str(e), exc_info=True)

        return images

    def _extract_og_image(self, url: str, html_content: str) -> Optional[ArticleImage]:
        """
        Extract Open Graph image from HTML meta tags.

        OG:image is the most reliable source for news article featured images.

        Args:
            url: Article URL
            html_content: HTML content

        Returns:
            ArticleImage if found, None otherwise
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Try og:image first (standard Open Graph)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                image_url = og_image["content"]
                # Convert relative URLs to absolute
                image_url = urljoin(url, image_url)

                if self._validate_image_url(image_url):
                    return ArticleImage(
                        image_url=image_url,
                        is_featured=True,
                        extraction_method="og_image",
                        extraction_quality="high",
                        created_at=datetime.now(),
                    )

            # Try twitter:image as fallback
            twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                image_url = twitter_image["content"]
                image_url = urljoin(url, image_url)

                if self._validate_image_url(image_url):
                    return ArticleImage(
                        image_url=image_url,
                        is_featured=True,
                        extraction_method="twitter_image",
                        extraction_quality="high",
                        created_at=datetime.now(),
                    )

        except Exception as e:
            logger.warning("og_image_extraction_failed", url=url, error=str(e))

        return None

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

    def _extract_large_content_images(
        self, url: str, html_content: str, exclude_url: Optional[str] = None
    ) -> List[ArticleImage]:
        """
        Extract large images from article content (likely to be article images, not icons).

        Args:
            url: Article URL (for converting relative URLs)
            html_content: HTML content
            exclude_url: URL to exclude (e.g., already extracted featured image)

        Returns:
            List of ArticleImage objects with large dimensions
        """
        images = []

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Find images in article content areas
            # Look in common article containers first
            article_containers = soup.find_all(
                ["article", "main", "div"],
                class_=lambda c: c and any(
                    x in str(c).lower() for x in ["article", "content", "story", "body"]
                ) if c else False
            )

            # If no specific container found, use whole document
            search_areas = article_containers if article_containers else [soup]

            for area in search_areas:
                for img in area.find_all("img"):
                    # Get image URL from various attributes
                    img_url = (
                        img.get("src")
                        or img.get("data-src")
                        or img.get("data-lazy")
                        or img.get("data-original")
                    )

                    if not img_url:
                        continue

                    # Convert relative to absolute
                    absolute_url = urljoin(url, img_url)

                    # Skip if already extracted or invalid
                    if exclude_url and absolute_url == exclude_url:
                        continue
                    if not self._validate_image_url(absolute_url):
                        continue

                    # Check dimensions if available
                    width = self._parse_dimension(img.get("width"))
                    height = self._parse_dimension(img.get("height"))

                    # Skip small images (likely icons/logos)
                    if width and width < MIN_IMAGE_WIDTH:
                        continue
                    if height and height < MIN_IMAGE_HEIGHT:
                        continue

                    # Skip images with suspicious patterns (avatars, icons, logos)
                    url_lower = absolute_url.lower()
                    if any(x in url_lower for x in ["avatar", "icon", "logo", "button", "pixel", "tracking", "1x1"]):
                        continue

                    images.append(
                        ArticleImage(
                            image_url=absolute_url,
                            is_featured=False,
                            extraction_method="content_image",
                            extraction_quality="medium",
                            image_width=width,
                            image_height=height,
                            created_at=datetime.now(),
                        )
                    )

        except Exception as e:
            logger.warning("content_image_extraction_failed", url=url, error=str(e))

        return images

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
            except Exception as e:
                logger.warning("curl_cffi_image_fetch_error", url=url, error=str(e))

        # Fall back to httpx
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

            if html and len(html) > 500:
                return html
            return None

        except Exception as e:
            logger.warning("curl_cffi_fetch_error", url=url, error=str(e))
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
