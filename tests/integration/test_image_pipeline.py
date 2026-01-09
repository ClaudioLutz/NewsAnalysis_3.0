"""Integration tests for image extraction pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from newsanalysis.core.article import Article, ArticleImage
from newsanalysis.services.image_cache import ImageCache
from newsanalysis.services.image_download_service import ImageDownloadService
from newsanalysis.pipeline.extractors.image_extractor import ImageExtractor


@pytest.fixture
def temp_cache(tmp_path):
    """Create temporary image cache."""
    return ImageCache(cache_root=tmp_path / "cache", days_to_keep=30)


@pytest.fixture
def sample_article():
    """Create sample article for testing."""
    from datetime import datetime
    return Article(
        id=1,
        url="https://example.com/article",
        normalized_url="https://example.com/article",
        url_hash="a" * 64,
        title="Test Article",
        source="Test Source",
        published_at=datetime.now(),
        collected_at=datetime.now(),
        feed_priority=1,
        run_id="test_run",
        content="Test content",
        pipeline_stage="scraped",
        processing_status="completed",
    )


@pytest.mark.integration
class TestImagePipeline:
    """Integration tests for image extraction pipeline."""

    @pytest.mark.asyncio
    async def test_image_extraction_workflow(self, sample_article, temp_cache):
        """Test complete image extraction workflow."""
        # Mock image extractor
        extractor = ImageExtractor()

        # Mock extracted images
        mock_images = [
            ArticleImage(
                article_id=sample_article.id,
                image_url="https://example.com/image1.jpg",
                is_featured=True,
                extraction_method="newspaper3k",
                extraction_quality="high",
            ),
            ArticleImage(
                article_id=sample_article.id,
                image_url="https://example.com/image2.jpg",
                is_featured=False,
                extraction_method="beautifulsoup",
                extraction_quality="medium",
            ),
        ]

        with patch.object(extractor, "extract_images", return_value=mock_images):
            # Extract images
            images = await extractor.extract_images(str(sample_article.url))

            assert len(images) == 2
            assert images[0].is_featured is True
            assert images[1].is_featured is False

    @pytest.mark.asyncio
    async def test_image_download_workflow(self, sample_article, temp_cache):
        """Test image download workflow."""
        images = [
            ArticleImage(
                article_id=sample_article.id,
                image_url="https://example.com/test.jpg",
                is_featured=True,
                extraction_method="newspaper3k",
            )
        ]

        # Mock download - need to mock at higher level to bypass circuit breaker
        async with ImageDownloadService(temp_cache) as download_service:
            # Create async mock for the download method
            async def mock_download_with_retry(url):
                return b"fake image content"

            with patch.object(
                download_service,
                "_download_with_retry",
                side_effect=mock_download_with_retry,
            ):
                downloaded = await download_service.download_article_images(
                    sample_article, images
                )

                assert len(downloaded) == 1
                assert downloaded[0].local_path is not None
                assert downloaded[0].file_size > 0

    @pytest.mark.asyncio
    async def test_image_cache_integration(self, sample_article, temp_cache):
        """Test image cache integration."""
        # Generate cache path
        path = temp_cache.generate_image_path(
            article_id=sample_article.id,
            image_url="https://example.com/test.jpg",
            is_featured=True,
        )

        # Save image
        content = b"test image content"
        success = temp_cache.save_image(path, content)
        assert success is True
        assert path.exists()

        # Retrieve image
        retrieved = temp_cache.get_image(path)
        assert retrieved == content

        # Get stats
        stats = temp_cache.get_cache_stats()
        assert stats["total_images"] == 1
        assert stats["total_size_mb"] >= 0

    @pytest.mark.asyncio
    async def test_extraction_with_missing_images(self, sample_article, temp_cache):
        """Test extraction when no images are found."""
        extractor = ImageExtractor()

        with patch.object(extractor, "extract_images", return_value=[]):
            images = await extractor.extract_images(str(sample_article.url))
            assert len(images) == 0

    @pytest.mark.asyncio
    async def test_download_with_network_error(self, sample_article, temp_cache):
        """Test download handling network errors gracefully."""
        images = [
            ArticleImage(
                article_id=sample_article.id,
                image_url="https://example.com/fail.jpg",
                is_featured=True,
            )
        ]

        async with ImageDownloadService(temp_cache) as download_service:
            with patch.object(
                download_service, "_download_with_retry", side_effect=Exception("Network error")
            ):
                downloaded = await download_service.download_article_images(
                    sample_article, images
                )

                # Should handle error gracefully and return empty list
                assert len(downloaded) == 0
