"""Unit tests for image cache."""

import pytest
from pathlib import Path
import tempfile
import shutil
import time

from newsanalysis.services.image_cache import ImageCache


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def image_cache(temp_cache_dir):
    """Create ImageCache instance."""
    return ImageCache(cache_root=temp_cache_dir, days_to_keep=30)


@pytest.mark.unit
class TestImageCache:
    """Test ImageCache class."""

    def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that initialization creates cache directory."""
        cache_root = temp_cache_dir / "new_cache"
        cache = ImageCache(cache_root=cache_root)

        assert cache_root.exists()
        assert cache_root.is_dir()

    def test_generate_image_path_structure(self, image_cache):
        """Test image path generation creates correct structure."""
        image_url = "https://example.com/image.jpg"
        path = image_cache.generate_image_path(
            article_id=123, image_url=image_url, is_featured=True
        )

        # Check path structure: cache/images/YYYY/MM/article_123_featured_{hash}.jpg
        assert "images" in path.parts
        assert path.name.startswith("article_123_featured_")
        assert path.suffix == ".jpg"

    def test_generate_image_path_non_featured(self, image_cache):
        """Test image path generation for non-featured images."""
        image_url = "https://example.com/image.png"
        path = image_cache.generate_image_path(
            article_id=456, image_url=image_url, is_featured=False
        )

        assert "article_456_" in path.name
        assert "_featured_" not in path.name
        assert path.suffix == ".png"

    def test_generate_image_path_no_extension(self, image_cache):
        """Test image path generation for URLs without extension."""
        image_url = "https://example.com/image"
        path = image_cache.generate_image_path(
            article_id=789, image_url=image_url, is_featured=False
        )

        # Should default to .jpg
        assert path.suffix == ".jpg"

    def test_generate_image_path_consistency(self, image_cache):
        """Test that same URL generates same hash."""
        image_url = "https://example.com/same-image.jpg"

        path1 = image_cache.generate_image_path(
            article_id=100, image_url=image_url, is_featured=False
        )
        path2 = image_cache.generate_image_path(
            article_id=100, image_url=image_url, is_featured=False
        )

        # Paths should be identical (same hash)
        assert path1.name == path2.name

    def test_save_and_get_image(self, image_cache):
        """Test saving and retrieving image."""
        test_content = b"fake image content"
        image_path = image_cache.cache_root / "test_image.jpg"

        # Save image
        success = image_cache.save_image(image_path, test_content)
        assert success is True
        assert image_path.exists()

        # Retrieve image
        retrieved_content = image_cache.get_image(image_path)
        assert retrieved_content == test_content

    def test_get_image_nonexistent(self, image_cache):
        """Test retrieving non-existent image."""
        nonexistent_path = image_cache.cache_root / "nonexistent.jpg"
        content = image_cache.get_image(nonexistent_path)

        assert content is None

    def test_delete_image(self, image_cache):
        """Test deleting image."""
        test_content = b"fake image content"
        image_path = image_cache.cache_root / "delete_test.jpg"

        # Save image first
        image_cache.save_image(image_path, test_content)
        assert image_path.exists()

        # Delete image
        success = image_cache.delete_image(image_path)
        assert success is True
        assert not image_path.exists()

    def test_delete_nonexistent_image(self, image_cache):
        """Test deleting non-existent image."""
        nonexistent_path = image_cache.cache_root / "nonexistent.jpg"
        success = image_cache.delete_image(nonexistent_path)

        # Should return False for non-existent file
        assert success is False

    def test_cleanup_old_images(self, image_cache):
        """Test cleanup of old images."""
        # Create test images
        images_dir = image_cache.cache_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create an old image (modified 40 days ago)
        old_image = images_dir / "old_image.jpg"
        old_image.write_bytes(b"old content")
        old_time = time.time() - (40 * 86400)  # 40 days ago
        import os
        os.utime(old_image, (old_time, old_time))

        # Create a recent image
        new_image = images_dir / "new_image.jpg"
        new_image.write_bytes(b"new content")

        # Run cleanup (should remove files older than 30 days)
        cleanup_stats = image_cache.cleanup_old_images()

        # Old image should be deleted, new image should remain
        assert cleanup_stats["deleted_count"] == 1
        assert cleanup_stats["freed_mb"] >= 0.0
        assert cleanup_stats["errors"] == 0
        assert not old_image.exists()
        assert new_image.exists()

    def test_get_cache_size(self, image_cache):
        """Test cache size calculation."""
        images_dir = image_cache.cache_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create test images with known sizes
        image1 = images_dir / "image1.jpg"
        image1.write_bytes(b"x" * 1024)  # 1KB

        image2 = images_dir / "image2.jpg"
        image2.write_bytes(b"x" * 2048)  # 2KB

        # Calculate size
        total_size = image_cache.get_cache_size()

        assert total_size == 3072  # 3KB

    def test_get_cache_stats(self, image_cache):
        """Test cache statistics."""
        images_dir = image_cache.cache_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create test images
        for i in range(3):
            image = images_dir / f"image{i}.jpg"
            image.write_bytes(b"x" * 1024)  # 1KB each

        stats = image_cache.get_cache_stats()

        assert stats["total_images"] == 3
        # 3KB total = 0.00 MB when rounded, so check >= 0
        assert stats["total_size_mb"] >= 0
        assert stats["cache_path"] == str(image_cache.cache_root)
        assert stats["days_to_keep"] == 30

    def test_get_cache_stats_empty_cache(self, image_cache):
        """Test cache statistics with empty cache."""
        stats = image_cache.get_cache_stats()

        assert stats["total_images"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["cache_path"] == str(image_cache.cache_root)

    def test_cleanup_empty_dirs(self, image_cache):
        """Test cleanup of empty directories."""
        # Create nested empty directories
        empty_dir = image_cache.cache_root / "images" / "2024" / "01" / "empty"
        empty_dir.mkdir(parents=True, exist_ok=True)

        # Create a file in a different directory
        file_dir = image_cache.cache_root / "images" / "2024" / "02"
        file_dir.mkdir(parents=True, exist_ok=True)
        test_file = file_dir / "test.jpg"
        test_file.write_bytes(b"content")

        # Run cleanup
        image_cache._cleanup_empty_dirs(image_cache.cache_root / "images")

        # Empty directory should be removed
        assert not empty_dir.exists()

        # Directory with file should remain
        assert file_dir.exists()
        assert test_file.exists()
