# tests/integration/test_pipeline.py
"""Integration tests for pipeline orchestrator."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from newsanalysis.pipeline.orchestrator import PipelineOrchestrator


@pytest.mark.integration
@pytest.mark.asyncio
class TestPipelineOrchestrator:
    """Integration tests for PipelineOrchestrator."""

    @patch("newsanalysis.pipeline.orchestrator.create_collector")
    @patch("newsanalysis.pipeline.orchestrator.OpenAIClient")
    async def test_pipeline_collection_stage(
        self,
        mock_openai_class,
        mock_create_collector,
        test_config,
        test_db,
        sample_articles,
    ):
        """Should successfully run collection stage."""
        # Mock collector
        mock_collector = Mock()
        mock_collector.collect = AsyncMock(return_value=sample_articles)
        mock_create_collector.return_value = mock_collector

        # Mock OpenAI client
        mock_openai = Mock()
        mock_openai_class.return_value = mock_openai

        # Create orchestrator
        orchestrator = PipelineOrchestrator(config=test_config, db=test_db)

        # Run collection only
        await orchestrator.run(
            skip_filtering=True,
            skip_scraping=True,
            skip_summarization=True,
            skip_digest=True,
        )

        # Verify articles collected
        assert mock_collector.collect.called

    @patch("newsanalysis.pipeline.orchestrator.create_collector")
    @patch("newsanalysis.pipeline.orchestrator.AIFilter")
    @patch("newsanalysis.pipeline.orchestrator.OpenAIClient")
    async def test_pipeline_filtering_stage(
        self,
        mock_openai_class,
        mock_filter_class,
        mock_create_collector,
        test_config,
        test_db,
        sample_articles,
    ):
        """Should successfully run collection and filtering stages."""
        # Mock collector
        mock_collector = Mock()
        mock_collector.collect = AsyncMock(return_value=sample_articles)
        mock_create_collector.return_value = mock_collector

        # Mock OpenAI client
        mock_openai = Mock()
        mock_openai_class.return_value = mock_openai

        # Mock AI filter
        mock_filter = Mock()
        mock_filter.classify_batch = AsyncMock(return_value=[
            {"is_match": True, "confidence": 0.85, "topic": "test", "reason": "test"}
            for _ in sample_articles
        ])
        mock_filter_class.return_value = mock_filter

        # Create orchestrator
        orchestrator = PipelineOrchestrator(config=test_config, db=test_db)

        # Run collection and filtering
        await orchestrator.run(
            skip_scraping=True,
            skip_summarization=True,
            skip_digest=True,
        )

        # Verify filtering ran
        assert mock_filter.classify_batch.called

    async def test_pipeline_handles_empty_collection(self, test_config, test_db):
        """Should handle empty collection gracefully."""
        # Create orchestrator
        orchestrator = PipelineOrchestrator(config=test_config, db=test_db)

        with patch("newsanalysis.pipeline.orchestrator.create_collector") as mock_create:
            mock_collector = Mock()
            mock_collector.collect = AsyncMock(return_value=[])
            mock_create.return_value = mock_collector

            # Run pipeline
            await orchestrator.run()

            # Should complete without errors
            assert True

    async def test_pipeline_tracks_run_id(self, test_config, test_db):
        """Should track pipeline run with unique run ID."""
        orchestrator = PipelineOrchestrator(config=test_config, db=test_db)

        # Get run ID
        run_id = orchestrator.run_id

        assert run_id is not None
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    async def test_pipeline_statistics(self, test_config, test_db, sample_articles):
        """Should track pipeline statistics."""
        orchestrator = PipelineOrchestrator(config=test_config, db=test_db)

        with patch("newsanalysis.pipeline.orchestrator.create_collector") as mock_create:
            mock_collector = Mock()
            mock_collector.collect = AsyncMock(return_value=sample_articles)
            mock_create.return_value = mock_collector

            # Run collection only
            await orchestrator.run(
                skip_filtering=True,
                skip_scraping=True,
                skip_summarization=True,
                skip_digest=True,
            )

            # Check statistics
            cursor = test_db.conn.execute(
                "SELECT collected_count FROM pipeline_runs WHERE run_id = ?",
                (orchestrator.run_id,)
            )
            row = cursor.fetchone()

            assert row is not None
            assert row[0] > 0  # collected_count
