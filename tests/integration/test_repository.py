# tests/integration/test_repository.py
"""Integration tests for ArticleRepository."""

from datetime import datetime, UTC

import pytest

from newsanalysis.core.article import Article
from newsanalysis.database.repository import ArticleRepository


@pytest.mark.integration
class TestArticleRepository:
    """Integration tests for ArticleRepository."""

    def test_save_collected_articles(self, test_db, sample_articles):
        """Should save collected articles to database."""
        repo = ArticleRepository(test_db)

        # Save articles
        saved_count = repo.save_collected_articles(sample_articles, run_id="test-run-1")

        assert saved_count == len(sample_articles)

        # Verify in database
        cursor = test_db.conn.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        assert count == len(sample_articles)

    def test_save_collected_articles_prevents_duplicates(self, test_db, sample_article):
        """Should prevent duplicate articles with same URL hash."""
        repo = ArticleRepository(test_db)

        # Save article twice
        repo.save_collected_articles([sample_article], run_id="test-run-1")
        repo.save_collected_articles([sample_article], run_id="test-run-2")

        # Should only have one article
        cursor = test_db.conn.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        assert count == 1

    def test_update_classification(self, test_db, sample_article):
        """Should update article with classification results."""
        repo = ArticleRepository(test_db)

        # Save article
        repo.save_collected_articles([sample_article], run_id="test-run-1")

        # Update classification
        repo.update_classification(
            url_hash=sample_article.url_hash,
            is_match=True,
            confidence=0.85,
            topic="creditreform_insights",
            reason="Test reason",
        )

        # Verify update
        article = repo.find_by_url_hash(sample_article.url_hash)
        assert article is not None
        assert article.is_match is True
        assert article.confidence == 0.85
        assert article.pipeline_stage == "filtered"

    def test_update_scraped_content(self, test_db, sample_article):
        """Should update article with scraped content."""
        repo = ArticleRepository(test_db)

        # Save and classify article
        repo.save_collected_articles([sample_article], run_id="test-run-1")
        repo.update_classification(
            url_hash=sample_article.url_hash,
            is_match=True,
            confidence=0.85,
            topic="test",
            reason="test",
        )

        # Update with scraped content
        repo.update_scraped_content(
            url_hash=sample_article.url_hash,
            content="Test article content with plenty of text.",
            author="Test Author",
            extraction_method="trafilatura",
            extraction_quality=0.9,
        )

        # Verify update
        article = repo.find_by_url_hash(sample_article.url_hash)
        assert article is not None
        assert article.content == "Test article content with plenty of text."
        assert article.author == "Test Author"
        assert article.extraction_method == "trafilatura"
        assert article.extraction_quality == 0.9
        assert article.pipeline_stage == "scraped"

    def test_update_summary(self, test_db, sample_article):
        """Should update article with summary."""
        repo = ArticleRepository(test_db)

        # Save, classify, and scrape article
        repo.save_collected_articles([sample_article], run_id="test-run-1")
        repo.update_classification(
            url_hash=sample_article.url_hash,
            is_match=True,
            confidence=0.85,
            topic="test",
            reason="test",
        )
        repo.update_scraped_content(
            url_hash=sample_article.url_hash,
            content="Test content",
            author="Test Author",
            extraction_method="trafilatura",
            extraction_quality=0.9,
        )

        # Update with summary
        repo.update_summary(
            url_hash=sample_article.url_hash,
            summary_title="Test Summary Title",
            summary="This is the summary.",
            key_points=["Point 1", "Point 2"],
            entities={
                "companies": ["Company A"],
                "people": ["Person X"],
                "locations": ["Zurich"],
                "topics": ["finance"],
            },
        )

        # Verify update
        article = repo.find_by_url_hash(sample_article.url_hash)
        assert article is not None
        assert article.summary_title == "Test Summary Title"
        assert article.summary == "This is the summary."
        assert len(article.key_points) == 2
        assert "Company A" in article.entities["companies"]
        assert article.pipeline_stage == "summarized"

    def test_get_articles_for_scraping(self, test_db, sample_articles):
        """Should retrieve matched articles for scraping."""
        repo = ArticleRepository(test_db)

        # Save articles
        repo.save_collected_articles(sample_articles, run_id="test-run-1")

        # Classify some as matched
        repo.update_classification(
            url_hash=sample_articles[0].url_hash,
            is_match=True,
            confidence=0.85,
            topic="test",
            reason="test",
        )
        repo.update_classification(
            url_hash=sample_articles[1].url_hash,
            is_match=False,
            confidence=0.2,
            topic="test",
            reason="test",
        )

        # Get articles for scraping
        articles = repo.get_articles_for_scraping()

        assert len(articles) == 1
        assert articles[0].url_hash == sample_articles[0].url_hash
        assert articles[0].is_match is True

    def test_mark_article_failed(self, test_db, sample_article):
        """Should mark article as failed with error."""
        repo = ArticleRepository(test_db)

        # Save article
        repo.save_collected_articles([sample_article], run_id="test-run-1")

        # Mark as failed
        repo.mark_article_failed(
            url_hash=sample_article.url_hash,
            error_message="Test error message",
        )

        # Verify update
        article = repo.find_by_url_hash(sample_article.url_hash)
        assert article is not None
        assert article.processing_status == "failed"
        assert article.error_count == 1
        assert "Test error message" in article.error_message

    def test_find_by_url_hash(self, test_db, sample_article):
        """Should find article by URL hash."""
        repo = ArticleRepository(test_db)

        # Save article
        repo.save_collected_articles([sample_article], run_id="test-run-1")

        # Find by hash
        found = repo.find_by_url_hash(sample_article.url_hash)

        assert found is not None
        assert found.url == sample_article.url
        assert found.title == sample_article.title

    def test_find_by_url_hash_not_found(self, test_db):
        """Should return None when article not found."""
        repo = ArticleRepository(test_db)

        found = repo.find_by_url_hash("non-existent-hash")

        assert found is None
