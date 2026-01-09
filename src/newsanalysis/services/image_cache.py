"""Filesystem cache manager for article images."""

import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


class ImageCache:
    """Manage filesystem cache for article images."""

    def __init__(self, cache_root: Path, days_to_keep: int = 30):
        """
        Initialize ImageCache.

        Args:
            cache_root: Root directory for image cache
            days_to_keep: Number of days to keep cached images
        """
        self.cache_root = Path(cache_root)
        self.days_to_keep = days_to_keep

        # Ensure cache directory exists
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def generate_image_path(
        self, article_id: int, image_url: str, is_featured: bool = False
    ) -> Path:
        """
        Generate organized file path for cached image.

        Creates structure: cache/images/YYYY/MM/article_{id}_{featured}_{hash}.ext

        Args:
            article_id: Article database ID
            image_url: Image URL
            is_featured: Whether this is the featured image

        Returns:
            Path object for the image file
        """
        # Create date-based directory structure
        now = datetime.now()
        year_month_dir = self.cache_root / "images" / now.strftime("%Y") / now.strftime("%m")
        year_month_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename from URL hash
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]

        # Determine file extension from URL
        ext = Path(image_url).suffix or ".jpg"

        # Build filename
        featured_tag = "_featured" if is_featured else ""
        filename = f"article_{article_id}{featured_tag}_{url_hash}{ext}"

        return year_month_dir / filename

    def save_image(self, image_path: Path, content: bytes) -> bool:
        """
        Save image content to filesystem.

        Args:
            image_path: Path where image should be saved
            content: Image binary content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            image_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(image_path, "wb") as f:
                f.write(content)

            logger.info("image_saved", path=str(image_path), size=len(content))
            return True

        except Exception as e:
            logger.error("image_save_failed", path=str(image_path), error=str(e))
            return False

    def get_image(self, image_path: Path) -> Optional[bytes]:
        """
        Retrieve image content from filesystem.

        Args:
            image_path: Path to image file

        Returns:
            Image binary content if exists, None otherwise
        """
        try:
            if image_path.exists():
                with open(image_path, "rb") as f:
                    return f.read()
        except Exception as e:
            logger.error("image_read_failed", path=str(image_path), error=str(e))

        return None

    def delete_image(self, image_path: Path) -> bool:
        """
        Delete image from filesystem.

        Args:
            image_path: Path to image file

        Returns:
            True if successful, False otherwise
        """
        try:
            if image_path.exists():
                image_path.unlink()
                logger.info("image_deleted", path=str(image_path))
                return True
        except Exception as e:
            logger.error("image_delete_failed", path=str(image_path), error=str(e))

        return False

    def cleanup_old_images(self) -> Dict[str, Any]:
        """
        Remove images older than days_to_keep.

        Returns:
            Dictionary with cleanup statistics including:
            - deleted_count: Number of images deleted
            - freed_mb: Megabytes of disk space freed
            - empty_dirs_removed: Number of empty directories removed
            - errors: Number of errors encountered
        """
        cutoff_time = time.time() - (self.days_to_keep * 86400)
        deleted_count = 0
        freed_bytes = 0
        errors = 0

        try:
            images_dir = self.cache_root / "images"
            if not images_dir.exists():
                logger.debug("cleanup_skipped", reason="images directory does not exist")
                return {
                    "deleted_count": 0,
                    "freed_mb": 0.0,
                    "empty_dirs_removed": 0,
                    "errors": 0,
                }

            # Find all image files
            for img_file in images_dir.rglob("*"):
                if img_file.is_file():
                    # Check modification time
                    try:
                        file_stat = img_file.stat()
                        if file_stat.st_mtime < cutoff_time:
                            file_size = file_stat.st_size
                            img_file.unlink()
                            deleted_count += 1
                            freed_bytes += file_size

                            age_days = (time.time() - file_stat.st_mtime) / 86400
                            logger.debug(
                                "image_cleaned",
                                path=str(img_file),
                                size_bytes=file_size,
                                age_days=round(age_days, 1),
                            )
                    except Exception as e:
                        errors += 1
                        logger.warning(
                            "cleanup_failed", path=str(img_file), error=str(e)
                        )

            # Clean up empty directories
            empty_dirs_removed = self._cleanup_empty_dirs_with_count(images_dir)

            freed_mb = freed_bytes / (1024 * 1024)

            logger.info(
                "cleanup_complete",
                deleted_count=deleted_count,
                freed_mb=round(freed_mb, 2),
                empty_dirs_removed=empty_dirs_removed,
                errors=errors,
                days_to_keep=self.days_to_keep,
            )

            return {
                "deleted_count": deleted_count,
                "freed_mb": round(freed_mb, 2),
                "empty_dirs_removed": empty_dirs_removed,
                "errors": errors,
            }

        except Exception as e:
            logger.error("cleanup_error", error=str(e))
            return {
                "deleted_count": 0,
                "freed_mb": 0.0,
                "empty_dirs_removed": 0,
                "errors": 1,
            }

    def _cleanup_empty_dirs(self, root_dir: Path) -> None:
        """
        Remove empty directories recursively.

        Args:
            root_dir: Root directory to clean
        """
        try:
            for dirpath in sorted(root_dir.rglob("*"), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    logger.debug("empty_dir_removed", path=str(dirpath))
        except Exception as e:
            logger.warning("empty_dir_cleanup_failed", error=str(e))

    def _cleanup_empty_dirs_with_count(self, root_dir: Path) -> int:
        """
        Remove empty directories recursively and return count.

        Args:
            root_dir: Root directory to clean

        Returns:
            Number of directories removed
        """
        removed_count = 0
        try:
            for dirpath in sorted(root_dir.rglob("*"), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    removed_count += 1
                    logger.debug("empty_dir_removed", path=str(dirpath))
        except Exception as e:
            logger.warning("empty_dir_cleanup_failed", error=str(e))

        return removed_count

    def get_cache_size(self) -> int:
        """
        Calculate total cache size in bytes.

        Returns:
            Total size of cached images in bytes
        """
        total_size = 0

        try:
            images_dir = self.cache_root / "images"
            if images_dir.exists():
                for img_file in images_dir.rglob("*"):
                    if img_file.is_file():
                        total_size += img_file.stat().st_size

        except Exception as e:
            logger.error("cache_size_calculation_failed", error=str(e))

        return total_size

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            images_dir = self.cache_root / "images"
            if not images_dir.exists():
                return {
                    "total_images": 0,
                    "total_size_mb": 0.0,
                    "cache_path": str(self.cache_root),
                }

            # Count files and total size
            file_count = 0
            total_size = 0

            for img_file in images_dir.rglob("*"):
                if img_file.is_file():
                    file_count += 1
                    total_size += img_file.stat().st_size

            return {
                "total_images": file_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_path": str(self.cache_root),
                "days_to_keep": self.days_to_keep,
            }

        except Exception as e:
            logger.error("cache_stats_failed", error=str(e))
            return {
                "total_images": 0,
                "total_size_mb": 0.0,
                "cache_path": str(self.cache_root),
                "error": str(e),
            }

    def check_disk_space_warnings(self, warning_threshold_mb: float = 1000.0) -> Dict[str, Any]:
        """
        Check if cache size exceeds warning thresholds.

        Args:
            warning_threshold_mb: Warning threshold in megabytes (default: 1GB)

        Returns:
            Dictionary with disk space warning information
        """
        stats = self.get_cache_stats()
        total_mb = stats.get("total_size_mb", 0.0)

        warning_triggered = total_mb > warning_threshold_mb

        if warning_triggered:
            logger.warning(
                "cache_size_warning",
                current_size_mb=total_mb,
                threshold_mb=warning_threshold_mb,
                message=f"Cache size ({total_mb:.2f}MB) exceeds threshold ({warning_threshold_mb}MB)",
            )

        return {
            "warning_triggered": warning_triggered,
            "current_size_mb": total_mb,
            "threshold_mb": warning_threshold_mb,
            "total_images": stats.get("total_images", 0),
        }
