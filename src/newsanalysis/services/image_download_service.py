"""Async image download service with retry logic and error handling."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pybreaker import CircuitBreaker, CircuitBreakerError

# Use curl_cffi for TLS fingerprint impersonation (bypasses Akamai/Cloudflare)
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    curl_requests = None

from newsanalysis.core.article import Article, ArticleImage
from newsanalysis.services.image_cache import ImageCache
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)

# Thread pool for sync curl_cffi calls
_executor = ThreadPoolExecutor(max_workers=4)

# Global circuit breaker for image downloads
# Opens after 5 consecutive failures, stays open for 60 seconds
image_download_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="image_download_breaker"
)


class ImageDownloadService:
    """Service for downloading and caching article images with retry logic."""

    # Maximum file size for images (5MB)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024

    # Allowed image extensions
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    def __init__(
        self,
        image_cache: ImageCache,
        timeout: int = 30,
        max_concurrent: int = 10,
        max_retries: int = 3,
    ):
        """
        Initialize ImageDownloadService.

        Args:
            image_cache: ImageCache instance for filesystem operations
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent downloads
            max_retries: Maximum retry attempts per image
        """
        self.image_cache = image_cache
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def download_article_images(
        self, article: Article, images: List[ArticleImage]
    ) -> List[ArticleImage]:
        """
        Download all images for an article.

        Args:
            article: Article object with ID
            images: List of ArticleImage objects to download

        Returns:
            List of ArticleImage objects with updated local_path and metadata
        """
        if not article.id:
            logger.warning("article_missing_id", url=str(article.url))
            return images

        if not images:
            logger.debug("no_images_to_download", article_id=article.id)
            return []

        logger.info(
            "downloading_article_images",
            article_id=article.id,
            image_count=len(images),
        )

        # Create semaphore for concurrent download limiting
        semaphore = asyncio.Semaphore(self.max_concurrent)

        # Download all images concurrently
        tasks = [
            self._download_single_image(article.id, image, semaphore)
            for image in images
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        downloaded_images = []
        success_count = 0
        error_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "image_download_failed",
                    article_id=article.id,
                    image_url=images[i].image_url,
                    error=str(result),
                )
                error_count += 1
            elif result:
                downloaded_images.append(result)
                success_count += 1
            else:
                error_count += 1

        logger.info(
            "article_images_downloaded",
            article_id=article.id,
            success=success_count,
            errors=error_count,
            total=len(images),
        )

        return downloaded_images

    async def _download_single_image(
        self, article_id: int, image: ArticleImage, semaphore: asyncio.Semaphore
    ) -> Optional[ArticleImage]:
        """
        Download a single image with retry logic.

        Args:
            article_id: Article database ID
            image: ArticleImage object
            semaphore: Semaphore for concurrent download limiting

        Returns:
            Updated ArticleImage with local_path, or None if download failed
        """
        async with semaphore:
            try:
                # Validate URL
                if not self._validate_image_url(image.image_url):
                    logger.warning("invalid_image_url", url=image.image_url)
                    return None

                # Generate cache path
                cache_path = self.image_cache.generate_image_path(
                    article_id=article_id,
                    image_url=image.image_url,
                    is_featured=image.is_featured,
                )

                # Check if already cached
                if cache_path.exists():
                    logger.debug("image_already_cached", path=str(cache_path))
                    image.local_path = str(cache_path)
                    image.file_size = cache_path.stat().st_size
                    return image

                # Download with retry and circuit breaker
                content = None
                try:
                    content = await self._download_with_retry(image.image_url)
                except CircuitBreakerError:
                    logger.warning(
                        "circuit_breaker_open",
                        message="Image download circuit breaker is open, trying curl_cffi",
                        article_id=article_id,
                        url=image.image_url,
                    )
                except aiohttp.ClientResponseError as e:
                    # Try curl_cffi for 403/404 errors (bot protection)
                    if e.status in (403, 404) and CURL_CFFI_AVAILABLE:
                        logger.debug(
                            "aiohttp_blocked_trying_curl_cffi",
                            url=image.image_url,
                            status=e.status,
                        )
                    else:
                        raise

                # Fallback to curl_cffi if aiohttp failed or was blocked
                if content is None and CURL_CFFI_AVAILABLE:
                    content = await self._download_with_curl_cffi(image.image_url)

                if content:
                    # Save to cache
                    if self.image_cache.save_image(cache_path, content):
                        # Update image metadata
                        image.local_path = str(cache_path)
                        image.file_size = len(content)
                        image.format = self._get_image_format(cache_path)

                        logger.info(
                            "image_downloaded",
                            article_id=article_id,
                            url=image.image_url,
                            size=len(content),
                            path=str(cache_path),
                        )
                        return image
                    else:
                        logger.error("image_save_failed", url=image.image_url)
                        return None

            except Exception as e:
                logger.error(
                    "image_download_error",
                    article_id=article_id,
                    url=image.image_url,
                    error=str(e),
                    exc_info=True,
                )
                return None

        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError)
        ),
    )
    @image_download_breaker
    async def _download_with_retry(self, url: str) -> Optional[bytes]:
        """
        Download image with retry logic.

        Args:
            url: Image URL

        Returns:
            Image binary content or None

        Raises:
            aiohttp.ClientError: On HTTP errors
            asyncio.TimeoutError: On timeout
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            async with self.session.get(url) as response:
                # Check status
                response.raise_for_status()

                # Check Content-Length header
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > self.MAX_IMAGE_SIZE:
                    logger.warning(
                        "image_too_large",
                        url=url,
                        size=content_length,
                        max_size=self.MAX_IMAGE_SIZE,
                    )
                    return None

                # Check Content-Type
                content_type = response.headers.get("Content-Type", "").lower()
                if not any(t in content_type for t in ["image/", "application/octet-stream"]):
                    logger.warning("invalid_content_type", url=url, content_type=content_type)
                    return None

                # Download with size tracking
                content = b""
                async for chunk in response.content.iter_chunked(8192):
                    content += chunk
                    if len(content) > self.MAX_IMAGE_SIZE:
                        logger.warning("image_size_exceeded", url=url)
                        return None

                if len(content) == 0:
                    logger.warning("empty_image_content", url=url)
                    return None

                return content

        except aiohttp.ClientResponseError as e:
            logger.warning("http_error", url=url, status=e.status)
            raise
        except asyncio.TimeoutError:
            logger.warning("download_timeout", url=url)
            raise
        except Exception as e:
            logger.error("download_error", url=url, error=str(e))
            return None

    async def _download_with_curl_cffi(self, url: str) -> Optional[bytes]:
        """
        Download image using curl_cffi with Chrome TLS fingerprint impersonation.

        This bypasses bot protection (Akamai, Cloudflare) that blocks standard HTTP clients.

        Args:
            url: Image URL

        Returns:
            Image binary content or None
        """
        if not CURL_CFFI_AVAILABLE:
            return None

        def _sync_download():
            response = curl_requests.get(
                url,
                impersonate="chrome",
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()
            if not any(t in content_type for t in ["image/", "application/octet-stream"]):
                return None

            # Check size
            content = response.content
            if len(content) > self.MAX_IMAGE_SIZE:
                return None
            if len(content) == 0:
                return None

            return content

        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(_executor, _sync_download)

            if content:
                logger.debug("curl_cffi_image_download_success", url=url, size=len(content))
                return content
            return None

        except Exception as e:
            logger.warning("curl_cffi_image_download_failed", url=url, error=str(e))
            return None

    def _validate_image_url(self, url: str) -> bool:
        """
        Validate image URL.

        Args:
            url: Image URL

        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                return False

            # Check extension
            path_ext = Path(parsed.path).suffix.lower()
            if path_ext and path_ext not in self.ALLOWED_EXTENSIONS:
                return False

            return True

        except Exception:
            return False

    def _get_image_format(self, file_path: Path) -> str:
        """
        Get image format from file extension.

        Args:
            file_path: Path to image file

        Returns:
            Image format (JPEG, PNG, etc.)
        """
        ext_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".gif": "GIF",
            ".webp": "WebP",
        }
        return ext_map.get(file_path.suffix.lower(), "Unknown")

    async def download_batch(
        self, articles_with_images: List[tuple[Article, List[ArticleImage]]]
    ) -> Dict[int, List[ArticleImage]]:
        """
        Download images for multiple articles in batch.

        Args:
            articles_with_images: List of (Article, List[ArticleImage]) tuples

        Returns:
            Dictionary mapping article_id to list of downloaded ArticleImage objects
        """
        results: Dict[int, List[ArticleImage]] = {}

        for article, images in articles_with_images:
            if article.id:
                downloaded = await self.download_article_images(article, images)
                results[article.id] = downloaded

        return results
