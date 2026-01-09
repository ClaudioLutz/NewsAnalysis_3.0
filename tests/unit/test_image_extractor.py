"""Unit tests for image extraction."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from newsanalysis.pipeline.extractors.image_extractor import ImageExtractor
from newsanalysis.core.article import ArticleImage


@pytest.fixture
def image_extractor():
    """Create ImageExtractor instance."""
    return ImageExtractor(timeout=30, max_images=5)


@pytest.fixture
def sample_html():
    """Provide sample HTML for testing."""
    return """
    <html>
    <body>
        <article>
            <img src="https://example.com/featured.jpg" alt="Featured" width="800" height="600" />
            <img data-src="https://example.com/lazy.jpg" alt="Lazy" />
            <img src="relative/image.jpg" alt="Relative" />
            <img src="https://example.com/invalid.exe" alt="Invalid" />
        </article>
    </body>
    </html>
    """


@pytest.mark.unit
class TestImageExtractor:
    """Test ImageExtractor class."""

    def test_validate_image_url_valid(self, image_extractor):
        """Test URL validation with valid URLs."""
        assert image_extractor._validate_image_url("https://example.com/image.jpg") is True
        assert image_extractor._validate_image_url("http://example.com/image.png") is True
        assert image_extractor._validate_image_url("https://example.com/image.webp") is True

    def test_validate_image_url_invalid(self, image_extractor):
        """Test URL validation with invalid URLs."""
        assert image_extractor._validate_image_url("ftp://example.com/image.jpg") is False
        assert image_extractor._validate_image_url("https://example.com/script.exe") is False
        assert image_extractor._validate_image_url("file:///local/image.jpg") is False

    def test_parse_dimension_valid(self, image_extractor):
        """Test dimension parsing with valid inputs."""
        assert image_extractor._parse_dimension("800") == 800
        assert image_extractor._parse_dimension("600px") == 600
        assert image_extractor._parse_dimension("1920") == 1920

    def test_parse_dimension_invalid(self, image_extractor):
        """Test dimension parsing with invalid inputs."""
        assert image_extractor._parse_dimension(None) is None
        assert image_extractor._parse_dimension("invalid") is None
        assert image_extractor._parse_dimension("") is None

    def test_extract_with_beautifulsoup(self, image_extractor, sample_html):
        """Test BeautifulSoup extraction."""
        images = image_extractor._extract_with_beautifulsoup(
            "https://example.com/article", sample_html
        )

        # Should extract valid images (excluding invalid.exe)
        assert len(images) >= 2

        # Check first image
        assert images[0].image_url == "https://example.com/featured.jpg"
        assert images[0].extraction_method == "beautifulsoup"
        assert images[0].is_featured is False
        assert images[0].image_width == 800
        assert images[0].image_height == 600

        # Check second image (lazy-loaded)
        assert images[1].image_url == "https://example.com/lazy.jpg"

    def test_extract_with_beautifulsoup_excludes_featured(self, image_extractor, sample_html):
        """Test BeautifulSoup excludes featured image URL."""
        images = image_extractor._extract_with_beautifulsoup(
            "https://example.com/article",
            sample_html,
            featured_url="https://example.com/featured.jpg",
        )

        # Should not include the featured image
        image_urls = [img.image_url for img in images]
        assert "https://example.com/featured.jpg" not in image_urls

    @pytest.mark.asyncio
    async def test_extract_with_newspaper3k_success(self, image_extractor):
        """Test newspaper3k extraction with successful result."""
        with patch("newsanalysis.pipeline.extractors.image_extractor.NewspaperArticle") as MockArticle:
            # Mock newspaper article
            mock_article = Mock()
            mock_article.top_image = "https://example.com/top.jpg"
            MockArticle.return_value = mock_article

            result = await image_extractor._extract_with_newspaper3k("https://example.com/article")

            assert result is not None
            assert result.image_url == "https://example.com/top.jpg"
            assert result.is_featured is True
            assert result.extraction_method == "newspaper3k"
            assert result.extraction_quality == "high"

    @pytest.mark.asyncio
    async def test_extract_with_newspaper3k_failure(self, image_extractor):
        """Test newspaper3k extraction with failure."""
        with patch("newsanalysis.pipeline.extractors.image_extractor.NewspaperArticle") as MockArticle:
            # Mock newspaper article with exception
            MockArticle.return_value.download.side_effect = Exception("Download failed")

            result = await image_extractor._extract_with_newspaper3k("https://example.com/article")

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_html_success(self, image_extractor):
        """Test HTML fetching with successful response."""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.get.return_value = mock_response
            MockClient.return_value = mock_client

            html = await image_extractor._fetch_html("https://example.com/article")

            assert html == "<html><body>Test</body></html>"

    @pytest.mark.asyncio
    async def test_fetch_html_non_html_content(self, image_extractor):
        """Test HTML fetching with non-HTML content type."""
        mock_response = Mock()
        mock_response.headers = {"content-type": "application/json"}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.get.return_value = mock_response
            MockClient.return_value = mock_client

            html = await image_extractor._fetch_html("https://example.com/article")

            assert html is None

    @pytest.mark.asyncio
    async def test_fetch_html_timeout(self, image_extractor):
        """Test HTML fetching with timeout."""
        import httpx

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
            MockClient.return_value = mock_client

            html = await image_extractor._fetch_html("https://example.com/article")

            assert html is None

    @pytest.mark.asyncio
    async def test_extract_images_integration(self, image_extractor, sample_html):
        """Test full extraction workflow."""
        with patch.object(image_extractor, "_extract_with_newspaper3k") as mock_newspaper:
            with patch.object(image_extractor, "_fetch_html") as mock_fetch:
                # Mock newspaper3k returns featured image
                mock_newspaper.return_value = ArticleImage(
                    image_url="https://example.com/featured.jpg",
                    is_featured=True,
                    extraction_method="newspaper3k",
                    extraction_quality="high",
                )

                # Mock HTML fetch
                mock_fetch.return_value = sample_html

                # Extract images
                images = await image_extractor.extract_images("https://example.com/article")

                # Should have featured image plus additional images from BeautifulSoup
                assert len(images) > 0
                assert images[0].is_featured is True
                assert images[0].extraction_method == "newspaper3k"
