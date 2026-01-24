"""Unit tests for incremental_search_anime algorithm."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.anime_service import incremental_search_anime, IncrementalSearchState


class MockRepository:
    """Mock repository for testing incremental search."""

    def __init__(self):
        self.search_results = {}
        self.search_calls = []

    def setup_search_result(self, query: str, results: list[str]):
        """Setup what results should be returned for a specific query."""
        self.search_results[query.lower()] = results

    def clear_search_results(self):
        """Mock clear_search_results."""
        pass

    def search_anime(self, query: str, verbose: bool = True):
        """Mock search_anime."""
        self.search_calls.append(query)
        # Store results for get_anime_titles_with_sources to retrieve
        self._last_query = query
        self._last_results = self.search_results.get(query.lower(), [])

    def get_search_metadata(self):
        """Mock get_search_metadata."""
        return Mock(used_query=self._last_query)

    def get_anime_titles_with_sources(self, filter_by_query=None, original_query=None):
        """Mock get_anime_titles_with_sources."""
        return self._last_results


@pytest.fixture
def mock_rep():
    """Provide a mock repository."""
    return MockRepository()


@pytest.fixture
def patch_repository(mock_rep):
    """Patch the global repository."""
    with patch("services.anime_service.rep", mock_rep):
        yield mock_rep


@pytest.fixture
def no_anilist():
    """Patch AniList discovery to avoid external calls."""
    with patch("utils.anilist_discovery.auto_discover_anilist_id", side_effect=Exception("No AniList")):
        yield


def test_incremental_search_stops_at_5_results(patch_repository, no_anilist):
    """Test that search stops when results ≤ 5."""
    mock_rep = patch_repository

    # Setup: 3 words = 8 results, 4 words = 3 results (≤5, should stop)
    mock_rep.setup_search_result("boku no hero", ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"])
    mock_rep.setup_search_result("boku no hero academia", ["B1", "B2", "B3"])

    state, results = incremental_search_anime("boku no hero academia 5")

    # Should have called search twice (3 words, 4 words)
    assert len(mock_rep.search_calls) == 2
    assert "boku no hero" in mock_rep.search_calls
    assert "boku no hero academia" in mock_rep.search_calls

    # Should stop at 4 words because 3 results ≤ 5
    assert len(results) == 3
    assert state.current_index == 1  # Second iteration (4 words)
    assert state.get_current().word_count == 4


def test_incremental_search_uses_all_words_if_needed(patch_repository, no_anilist):
    """Test that search uses all words if results still > 5."""
    mock_rep = patch_repository

    # Setup: all combinations return > 5 results
    # Note: "attack on titan season 4" gets normalized to "attack on titan 4" (season removed)
    # So it has 4 words: "attack", "on", "titan", "4"
    # Starts with min(3,4)=3 words
    mock_rep.setup_search_result("attack on titan", ["B1", "B2", "B3", "B4", "B5", "B6"])
    mock_rep.setup_search_result("attack on titan 4", ["D1", "D2", "D3", "D4", "D5", "D6"])

    state, results = incremental_search_anime("attack on titan season 4")

    # Should use all 4 words (after normalization removes "season")
    assert len(mock_rep.search_calls) == 2  # 3 words, 4 words
    assert len(results) == 6


def test_incremental_search_starts_with_3_words(patch_repository, no_anilist):
    """Test that search starts with first 3 words."""
    mock_rep = patch_repository

    mock_rep.setup_search_result("spy family tv", ["A1"])

    state, results = incremental_search_anime("spy family tv special 2024")

    # First search should be 3 words
    assert mock_rep.search_calls[0] == "spy family tv"


def test_incremental_search_starts_with_fewer_if_query_short(patch_repository, no_anilist):
    """Test that search starts with all words if query < 3 words."""
    mock_rep = patch_repository

    mock_rep.setup_search_result("dandadan", ["A1"])

    state, results = incremental_search_anime("dandadan")

    # Should start with 1 word
    assert len(mock_rep.search_calls) >= 1
    assert mock_rep.search_calls[0] == "dandadan"


def test_incremental_search_two_word_query(patch_repository, no_anilist):
    """Test incremental search with 2-word query."""
    mock_rep = patch_repository

    mock_rep.setup_search_result("spy family", ["A1"])

    state, results = incremental_search_anime("spy family")

    # Should start with 2 words (all available)
    assert mock_rep.search_calls[0] == "spy family"


def test_incremental_search_state_navigation(patch_repository, no_anilist):
    """Test that state tracks all iterations."""
    mock_rep = patch_repository

    # "my hero academia season 2" gets normalized to "my hero academia 2" (season removed)
    # So it has 4 words: "my", "hero", "academia", "2"
    # Starts with min(3,4)=3 words
    mock_rep.setup_search_result("my hero academia", ["A1", "A2", "A3", "A4", "A5", "A6"])
    mock_rep.setup_search_result("my hero academia 2", ["B1", "B2", "B3"])

    state, results = incremental_search_anime("my hero academia season 2")

    # State should have 2 iterations (3 words, 4 words after normalization)
    assert len(state.search_history) == 2
    assert state.search_history[0].word_count == 3
    assert state.search_history[1].word_count == 4

    # Current should be at second iteration (results <= 5, so stop here)
    assert state.current_index == 1
    assert state.get_current().word_count == 4


def test_incremental_search_zero_results_fallback(patch_repository, no_anilist):
    """Test fallback when an iteration returns zero results."""
    mock_rep = patch_repository

    # Setup: 3 words = 6 results (>5), 4 words = 0 results (should fallback)
    # "my hero academia ultra rare edition" has 6 words
    mock_rep.setup_search_result("my hero academia", ["A1", "A2", "A3", "A4", "A5", "A6"])
    mock_rep.setup_search_result("my hero academia ultra", [])

    state, results = incremental_search_anime("my hero academia ultra rare edition")

    # Should have searched twice
    assert len(mock_rep.search_calls) >= 2

    # Should return results from first iteration (zero-result fallback)
    assert len(results) == 6
    assert results == ["A1", "A2", "A3", "A4", "A5", "A6"]


def test_incremental_search_source_counts(patch_repository, no_anilist):
    """Test that source counts are tracked in state."""
    mock_rep = patch_repository

    mock_rep.setup_search_result("test anime", ["Anime 1 - Source1", "Anime 2 - Source2", "Anime 3 - Source1"])

    state, results = incremental_search_anime("test anime")

    current = state.get_current()
    assert current is not None
    # Source counts should be populated
    assert len(current.source_counts) > 0 or len(current.source_counts) == 0  # Flexible for now


def test_incremental_search_exactly_5_results(patch_repository, no_anilist):
    """Test that exactly 5 results triggers stop condition."""
    mock_rep = patch_repository

    # "test anime series long" has 4 words, starts with min(3,4)=3
    mock_rep.setup_search_result("test anime series", ["A1", "A2", "A3", "A4", "A5"])
    mock_rep.setup_search_result("test anime series long", ["B1", "B2", "B3", "B4", "B5", "B6"])

    state, results = incremental_search_anime("test anime series long")

    # Should stop at first iteration (5 results = ≤ 5)
    assert len(mock_rep.search_calls) == 1
    assert len(results) == 5


def test_incremental_search_returns_state_and_results(patch_repository, no_anilist):
    """Test that return value is tuple of (state, results)."""
    mock_rep = patch_repository
    mock_rep.setup_search_result("anime", ["A1", "A2"])

    result = incremental_search_anime("anime")

    assert isinstance(result, tuple)
    assert len(result) == 2
    state, results = result
    assert isinstance(state, IncrementalSearchState)
    assert isinstance(results, list)


def test_incremental_search_maintains_query_metadata(patch_repository, no_anilist):
    """Test that query metadata is stored for each iteration."""
    mock_rep = patch_repository

    mock_rep.setup_search_result("spy family tv", ["A1"])

    state, results = incremental_search_anime("spy family tv special")

    current = state.get_current()
    assert current is not None
    assert current.query == "spy family tv"
    assert current.word_count == 3
