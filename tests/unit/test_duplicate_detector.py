# tests/unit/test_duplicate_detector.py
"""Unit tests for semantic duplicate detector."""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, Mock

import pytest

from newsanalysis.core.article import Article
from newsanalysis.pipeline.dedup.duplicate_detector import (
    DuplicateCheckResponse,
    DuplicateDetector,
    DuplicateGroup,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock = Mock()
    mock.create_completion = AsyncMock()
    return mock


@pytest.fixture
def duplicate_detector(mock_llm_client):
    """DuplicateDetector instance with mock client."""
    return DuplicateDetector(
        llm_client=mock_llm_client,
        confidence_threshold=0.75,
        time_window_hours=48,
    )


@pytest.fixture
def sample_articles():
    """Sample articles for duplicate testing."""
    base_time = datetime.now(UTC)
    return [
        Article(
            id=1,
            url="https://reuters.com/tesla-earnings",
            normalized_url="https://reuters.com/tesla-earnings",
            url_hash="hash1" + "0" * 58,
            title="Tesla Q4 Earnings Beat Expectations",
            source="Reuters",
            published_at=base_time,
            collected_at=base_time,
            feed_priority=2,
            run_id="test_run",
        ),
        Article(
            id=2,
            url="https://bloomberg.com/tesla-q4-results",
            normalized_url="https://bloomberg.com/tesla-q4-results",
            url_hash="hash2" + "0" * 58,
            title="Tesla Reports Strong Fourth Quarter Results",
            source="Bloomberg",
            published_at=base_time + timedelta(hours=1),
            collected_at=base_time + timedelta(hours=1),
            feed_priority=2,
            run_id="test_run",
        ),
        Article(
            id=3,
            url="https://cnbc.com/elon-musk-tesla-earnings",
            normalized_url="https://cnbc.com/elon-musk-tesla-earnings",
            url_hash="hash3" + "0" * 58,
            title="Elon Musk's Tesla Exceeds Analyst Forecasts",
            source="CNBC",
            published_at=base_time + timedelta(hours=2),
            collected_at=base_time + timedelta(hours=2),
            feed_priority=3,
            run_id="test_run",
        ),
        Article(
            id=4,
            url="https://nzz.ch/swiss-bank-merger",
            normalized_url="https://nzz.ch/swiss-bank-merger",
            url_hash="hash4" + "0" * 58,
            title="Swiss Banks Announce Major Merger",
            source="NZZ",
            published_at=base_time + timedelta(hours=3),
            collected_at=base_time + timedelta(hours=3),
            feed_priority=1,
            run_id="test_run",
        ),
    ]


@pytest.mark.unit
class TestDuplicateCheckResponse:
    """Tests for DuplicateCheckResponse model."""

    def test_valid_response(self):
        """Should create valid duplicate check response."""
        response = DuplicateCheckResponse(
            is_duplicate=True,
            confidence=0.85,
            reason="Both articles report Tesla Q4 earnings",
        )
        assert response.is_duplicate is True
        assert response.confidence == 0.85

    def test_confidence_validation(self):
        """Should validate confidence range."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DuplicateCheckResponse(
                is_duplicate=True,
                confidence=1.5,  # Invalid
                reason="Test",
            )


@pytest.mark.unit
class TestDuplicateGroup:
    """Tests for DuplicateGroup model."""

    def test_group_creation(self):
        """Should create duplicate group."""
        group = DuplicateGroup(
            canonical_url_hash="hash1" + "0" * 58,
            duplicate_url_hashes=["hash2" + "0" * 58, "hash3" + "0" * 58],
            confidence=0.85,
        )
        assert group.canonical_url_hash == "hash1" + "0" * 58
        assert len(group.duplicate_url_hashes) == 2
        assert group.confidence == 0.85


@pytest.mark.unit
class TestDuplicateDetector:
    """Tests for DuplicateDetector class."""

    def test_initialization(self, mock_llm_client):
        """Should initialize with default prompts."""
        detector = DuplicateDetector(
            llm_client=mock_llm_client,
            confidence_threshold=0.75,
            time_window_hours=48,
        )
        assert detector.confidence_threshold == 0.75
        assert detector.time_window_hours == 48
        assert detector.system_prompt is not None
        assert detector.user_prompt_template is not None

    def test_group_by_time_window(self, duplicate_detector, sample_articles):
        """Should group articles within time window."""
        groups = duplicate_detector._group_by_time_window(sample_articles)

        # All 4 articles are within 48h of each other, so should be in one group
        assert len(groups) == 1
        assert len(groups[0]) == 4

    def test_group_by_time_window_splits_distant_articles(self, duplicate_detector):
        """Should split articles outside time window."""
        base_time = datetime.now(UTC)
        articles = [
            Article(
                id=1,
                url="https://example.com/1",
                normalized_url="https://example.com/1",
                url_hash="hash1" + "0" * 58,
                title="Article 1",
                source="Source",
                published_at=base_time,
                collected_at=base_time,
                feed_priority=1,
                run_id="test",
            ),
            Article(
                id=2,
                url="https://example.com/2",
                normalized_url="https://example.com/2",
                url_hash="hash2" + "0" * 58,
                title="Article 2",
                source="Source",
                published_at=base_time + timedelta(hours=72),  # 3 days later
                collected_at=base_time + timedelta(hours=72),
                feed_priority=1,
                run_id="test",
            ),
        ]

        groups = duplicate_detector._group_by_time_window(articles)

        # Articles are too far apart - each forms its own group (but single-article
        # groups are excluded, so we get empty list)
        assert len(groups) == 0

    @pytest.mark.asyncio
    async def test_detect_duplicates_empty_list(self, duplicate_detector):
        """Should handle empty article list."""
        groups, duplicates = await duplicate_detector.detect_duplicates([])
        assert groups == []
        assert duplicates == set()

    @pytest.mark.asyncio
    async def test_detect_duplicates_single_article(self, duplicate_detector, sample_articles):
        """Should handle single article."""
        groups, duplicates = await duplicate_detector.detect_duplicates([sample_articles[0]])
        assert groups == []
        assert duplicates == set()

    @pytest.mark.asyncio
    async def test_detect_duplicates_finds_duplicates(
        self, duplicate_detector, mock_llm_client, sample_articles
    ):
        """Should detect duplicate articles."""
        # Mock LLM responses - first 3 articles are duplicates (Tesla earnings)
        # Last article is different (Swiss bank)
        call_count = 0

        async def mock_completion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            messages = kwargs.get("messages", [])
            user_msg = messages[-1]["content"] if messages else ""

            # Tesla articles are duplicates of each other
            if "Tesla" in user_msg and "Swiss" not in user_msg:
                return {
                    "content": {
                        "is_duplicate": True,
                        "confidence": 0.90,
                        "reason": "Both cover Tesla Q4 earnings",
                    },
                    "usage": {"total_tokens": 100, "cost": 0.001},
                }
            else:
                return {
                    "content": {
                        "is_duplicate": False,
                        "confidence": 0.15,
                        "reason": "Different topics",
                    },
                    "usage": {"total_tokens": 100, "cost": 0.001},
                }

        mock_llm_client.create_completion = AsyncMock(side_effect=mock_completion)

        groups, duplicate_hashes = await duplicate_detector.detect_duplicates(sample_articles)

        # Should find at least one group (Tesla articles)
        assert len(groups) >= 1

        # The canonical article should be the one with highest priority (lowest number)
        # or earliest collected_at
        for group in groups:
            assert group.canonical_url_hash not in duplicate_hashes

    @pytest.mark.asyncio
    async def test_detect_duplicates_respects_confidence_threshold(
        self, duplicate_detector, mock_llm_client, sample_articles
    ):
        """Should only consider pairs above confidence threshold."""
        # Return low confidence for all comparisons
        mock_llm_client.create_completion = AsyncMock(
            return_value={
                "content": {
                    "is_duplicate": True,
                    "confidence": 0.50,  # Below 0.75 threshold
                    "reason": "Maybe similar",
                },
                "usage": {"total_tokens": 100, "cost": 0.001},
            }
        )

        groups, duplicate_hashes = await duplicate_detector.detect_duplicates(sample_articles)

        # Should find no duplicates due to low confidence
        assert len(groups) == 0
        assert len(duplicate_hashes) == 0

    @pytest.mark.asyncio
    async def test_detect_duplicates_handles_api_errors(
        self, duplicate_detector, mock_llm_client, sample_articles
    ):
        """Should handle API errors gracefully."""
        mock_llm_client.create_completion = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Should not raise, just return empty results
        groups, duplicate_hashes = await duplicate_detector.detect_duplicates(sample_articles)

        assert groups == []
        assert duplicate_hashes == set()

    def test_cluster_duplicates_empty(self, duplicate_detector):
        """Should handle empty duplicate pairs."""
        groups = duplicate_detector._cluster_duplicates([], [])
        assert groups == []

    def test_cluster_duplicates_single_pair(self, duplicate_detector, sample_articles):
        """Should cluster single pair correctly."""
        pairs = [(sample_articles[0], sample_articles[1], 0.85)]

        groups = duplicate_detector._cluster_duplicates(pairs, sample_articles[:2])

        assert len(groups) == 1
        assert len(groups[0].duplicate_url_hashes) == 1
        # Canonical should be the one with lower feed_priority (or earlier collected)
        # Both have priority 2, so it depends on collected_at

    def test_cluster_duplicates_transitive(self, duplicate_detector, sample_articles):
        """Should cluster transitively (A=B, B=C implies A=B=C)."""
        # A-B and B-C pairs
        pairs = [
            (sample_articles[0], sample_articles[1], 0.85),
            (sample_articles[1], sample_articles[2], 0.80),
        ]

        groups = duplicate_detector._cluster_duplicates(pairs, sample_articles[:3])

        # Should result in one group with all 3 articles
        assert len(groups) == 1
        assert len(groups[0].duplicate_url_hashes) == 2  # 2 duplicates + 1 canonical

    def test_canonical_selection_by_priority(self, duplicate_detector, sample_articles):
        """Should select canonical article by feed priority."""
        # Article 4 has priority 1 (government), others have 2 or 3
        pairs = [
            (sample_articles[0], sample_articles[3], 0.90),  # Reuters (2) vs NZZ (1)
        ]

        groups = duplicate_detector._cluster_duplicates(
            pairs, [sample_articles[0], sample_articles[3]]
        )

        assert len(groups) == 1
        # NZZ (priority 1) should be canonical
        assert groups[0].canonical_url_hash == sample_articles[3].url_hash
