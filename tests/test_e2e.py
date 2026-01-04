# tests/test_e2e.py
"""End-to-end tests for the complete pipeline."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from newsanalysis.core.config import Config
from newsanalysis.database.connection import DatabaseConnection
from newsanalysis.pipeline.orchestrator import PipelineOrchestrator


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestEndToEnd:
    """End-to-end tests for complete workflows."""

    @patch("newsanalysis.pipeline.collectors.rss.feedparser")
    @patch("newsanalysis.integrations.openai_client.AsyncOpenAI")
    async def test_complete_pipeline_workflow(
        self,
        mock_openai_class,
        mock_feedparser,
        tmp_path: Path,
    ):
        """Test complete pipeline from collection to digest generation."""

        # Setup test environment
        db_path = tmp_path / "test.db"
        config = Config(
            db_path=str(db_path),
            output_dir=str(tmp_path / "out"),
            openai_api_key="test-key",
            confidence_threshold=0.70,
        )

        # Initialize database
        db = DatabaseConnection(str(db_path))
        schema_path = Path(__file__).parent.parent / "src" / "newsanalysis" / "database" / "schema.sql"
        with open(schema_path) as f:
            db.conn.executescript(f.read())
        db.conn.commit()

        # Mock RSS feed
        mock_feedparser.parse.return_value = {
            "entries": [
                {
                    "title": "Swiss Company Files for Bankruptcy",
                    "link": "https://example.com/article-1",
                    "published_parsed": None,
                    "summary": "A major Swiss company has filed for bankruptcy.",
                },
                {
                    "title": "Weather Update: Sunny Weekend Ahead",
                    "link": "https://example.com/article-2",
                    "published_parsed": None,
                    "summary": "The weather forecast shows sunny skies.",
                },
            ]
        }

        # Mock OpenAI responses
        mock_client = Mock()

        # Classification responses
        async def mock_classification(*args, **kwargs):
            title = kwargs.get("messages", [{}])[-1].get("content", "")
            if "Bankruptcy" in title:
                return Mock(
                    choices=[
                        Mock(
                            message=Mock(
                                content='{"match": true, "conf": 0.92, "topic": "creditreform_insights", "reason": "Bankruptcy article"}'
                            )
                        )
                    ],
                    usage=Mock(prompt_tokens=50, completion_tokens=30),
                )
            else:
                return Mock(
                    choices=[
                        Mock(
                            message=Mock(
                                content='{"match": false, "conf": 0.15, "topic": "weather", "reason": "Weather article"}'
                            )
                        )
                    ],
                    usage=Mock(prompt_tokens=50, completion_tokens=30),
                )

        mock_client.chat.completions.create = AsyncMock(side_effect=mock_classification)
        mock_openai_class.return_value = mock_client

        # Mock content scraping
        with patch("newsanalysis.pipeline.scrapers.trafilatura_scraper.extract") as mock_extract:
            mock_extract.return_value = "This is the full article content about bankruptcy proceedings. " * 20

            # Mock summary generation
            async def mock_summarization(*args, **kwargs):
                return Mock(
                    choices=[
                        Mock(
                            message=Mock(
                                content='{"title": "Swiss Company Bankruptcy", "summary": "A Swiss company filed for bankruptcy...", "key_points": ["Filed bankruptcy", "500 employees affected"], "entities": {"companies": ["Swiss Corp"], "people": [], "locations": ["Zurich"], "topics": ["bankruptcy"]}}'
                            )
                        )
                    ],
                    usage=Mock(prompt_tokens=200, completion_tokens=100),
                )

            mock_client.chat.completions.create = AsyncMock(side_effect=mock_summarization)

            # Create orchestrator
            orchestrator = PipelineOrchestrator(config=config, db=db)

            # Run complete pipeline
            await orchestrator.run(
                limit=10,
                skip_digest=True,  # Skip digest for faster test
            )

            # Verify results
            # 1. Articles were collected
            cursor = db.conn.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            assert total_articles > 0

            # 2. Classification occurred
            cursor = db.conn.execute("SELECT COUNT(*) FROM articles WHERE pipeline_stage = 'filtered'")
            filtered_count = cursor.fetchone()[0]
            assert filtered_count > 0

            # 3. Matched article was processed further
            cursor = db.conn.execute("SELECT COUNT(*) FROM articles WHERE is_match = TRUE")
            matched_count = cursor.fetchone()[0]
            assert matched_count > 0

        db.close()

    async def test_pipeline_with_limit(self, tmp_path: Path):
        """Test pipeline respects article limit."""
        db_path = tmp_path / "test.db"
        config = Config(
            db_path=str(db_path),
            output_dir=str(tmp_path / "out"),
            openai_api_key="test-key",
        )

        # Initialize database
        db = DatabaseConnection(str(db_path))
        schema_path = Path(__file__).parent.parent / "src" / "newsanalysis" / "database" / "schema.sql"
        with open(schema_path) as f:
            db.conn.executescript(f.read())
        db.conn.commit()

        with patch("newsanalysis.pipeline.orchestrator.create_collector") as mock_create:
            # Mock collector with many articles
            mock_collector = Mock()
            mock_collector.collect = AsyncMock(return_value=[
                Mock(
                    url=f"https://example.com/article-{i}",
                    url_hash=f"hash-{i}",
                    title=f"Article {i}",
                    source="Test",
                )
                for i in range(100)
            ])
            mock_create.return_value = mock_collector

            orchestrator = PipelineOrchestrator(config=config, db=db)

            # Run with limit
            await orchestrator.run(
                limit=5,
                skip_filtering=True,
                skip_scraping=True,
                skip_summarization=True,
                skip_digest=True,
            )

            # Should only process up to limit
            cursor = db.conn.execute("SELECT COUNT(*) FROM articles")
            count = cursor.fetchone()[0]
            assert count <= 5

        db.close()

    async def test_pipeline_handles_errors_gracefully(self, tmp_path: Path):
        """Test pipeline continues despite individual article errors."""
        db_path = tmp_path / "test.db"
        config = Config(
            db_path=str(db_path),
            output_dir=str(tmp_path / "out"),
            openai_api_key="test-key",
        )

        # Initialize database
        db = DatabaseConnection(str(db_path))
        schema_path = Path(__file__).parent.parent / "src" / "newsanalysis" / "database" / "schema.sql"
        with open(schema_path) as f:
            db.conn.executescript(f.read())
        db.conn.commit()

        with patch("newsanalysis.pipeline.orchestrator.create_collector") as mock_create:
            mock_collector = Mock()
            mock_collector.collect = AsyncMock(return_value=[
                Mock(
                    url="https://example.com/article-1",
                    url_hash="hash-1",
                    title="Good Article",
                    source="Test",
                ),
            ])
            mock_create.return_value = mock_collector

            orchestrator = PipelineOrchestrator(config=config, db=db)

            # Run pipeline (errors may occur, but should not crash)
            try:
                await orchestrator.run(
                    skip_filtering=True,
                    skip_scraping=True,
                    skip_summarization=True,
                    skip_digest=True,
                )
            except Exception:
                pytest.fail("Pipeline should handle errors gracefully")

        db.close()
