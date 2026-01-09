#!/usr/bin/env python3
"""Script to retroactively extract images for articles that don't have them yet."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.database.repository import ArticleRepository
from newsanalysis.pipeline.extractors.image_extractor import ImageExtractor
from newsanalysis.services.image_cache import ImageCache
from newsanalysis.services.image_download_service import ImageDownloadService
from newsanalysis.utils.logging import get_logger

logger = get_logger(__name__)


async def extract_missing_images():
    """Extract images for articles that don't have them yet."""

    # Initialize services
    config = Config()
    db = DatabaseConnection(Path("news.db"))
    db.connect()

    repository = ArticleRepository(db)
    image_extractor = ImageExtractor(timeout=config.request_timeout_sec, max_images=5)
    image_cache = ImageCache(cache_root=Path("cache"), days_to_keep=30)

    # Get all scraped articles directly from database
    cursor = db.conn.execute("""
        SELECT id, url, title, scraped_at
        FROM articles
        WHERE scraped_at IS NOT NULL
        ORDER BY scraped_at DESC
    """)

    from newsanalysis.core.article import Article
    from datetime import datetime

    all_articles = []
    for row in cursor.fetchall():
        url_str = row[1]
        article = Article(
            id=row[0],
            url=url_str,
            title=row[2],
            source="",
            published_at=datetime.now(),
            collected_at=datetime.now(),
            normalized_url=url_str.lower().strip(),
            url_hash=str(hash(url_str)),
            feed_priority=1,
            run_id="manual_image_extraction"
        )
        all_articles.append(article)

    if not all_articles:
        print("No articles found")
        return

    # Get articles that already have images
    articles_with_images = set()
    cursor = db.conn.execute("SELECT DISTINCT article_id FROM article_images")
    for row in cursor.fetchall():
        articles_with_images.add(row[0])

    # Filter to articles without images
    articles_without_images = [a for a in all_articles if a.id not in articles_with_images]

    print(f"Found {len(all_articles)} scraped articles")
    print(f"Already have images: {len(articles_with_images)} articles")
    print(f"Need image extraction: {len(articles_without_images)} articles")
    print()

    if not articles_without_images:
        print("All articles already have images extracted!")
        return

    # Extract images for articles without them
    total_extracted = 0
    total_downloaded = 0
    total_failed = 0

    async with ImageDownloadService(
        image_cache=image_cache,
        timeout=config.request_timeout_sec,
        max_concurrent=10,
        max_retries=3,
    ) as download_service:
        for i, article in enumerate(articles_without_images, 1):
            try:
                print(f"[{i}/{len(articles_without_images)}] Processing: {article.title[:60]}...")

                # Extract image URLs
                images = await image_extractor.extract_images(
                    url=str(article.url),
                    html_content=None,
                )

                if images:
                    total_extracted += len(images)
                    print(f"  -> Extracted {len(images)} images")

                    # Set article_id on images
                    for img in images:
                        img.article_id = article.id

                    # Download images
                    downloaded_images = await download_service.download_article_images(
                        article=article,
                        images=images,
                    )

                    if downloaded_images:
                        total_downloaded += len(downloaded_images)
                        print(f"  -> Downloaded {len(downloaded_images)} images")

                        # Save to database
                        repository.save_article_images(downloaded_images)
                    else:
                        print(f"  -> No images downloaded")
                else:
                    print(f"  -> No images found")

            except Exception as e:
                total_failed += 1
                print(f"  -> ERROR: {e}")
                logger.error(
                    "image_extraction_failed",
                    article_id=article.id,
                    url=str(article.url),
                    error=str(e),
                )

    print()
    print("=" * 60)
    print("Image Extraction Complete!")
    print("=" * 60)
    print(f"Articles processed: {len(articles_without_images)}")
    print(f"Images extracted: {total_extracted}")
    print(f"Images downloaded: {total_downloaded}")
    print(f"Failed: {total_failed}")
    print()

    # Show updated statistics
    cursor = db.conn.execute("SELECT COUNT(DISTINCT article_id) FROM article_images")
    total_with_images = cursor.fetchone()[0]
    cursor = db.conn.execute("SELECT COUNT(*) FROM article_images WHERE local_path IS NOT NULL")
    total_cached = cursor.fetchone()[0]

    print("Updated Database Statistics:")
    print(f"Articles with images: {total_with_images}/{len(all_articles)} ({100*total_with_images/len(all_articles):.1f}%)")
    print(f"Total images cached: {total_cached}")

    db.close()


if __name__ == "__main__":
    asyncio.run(extract_missing_images())
