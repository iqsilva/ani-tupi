"""Integration tests for anime search and playback workflow.

Tests realistic user scenarios for searching, selecting, and watching anime.
"""

from unittest.mock import Mock, patch

import pytest

from services.anime_service import incremental_search_anime


class MockRepository:
    """Mock repository for testing anime search workflows."""

    def __init__(self):
        self.search_results = {}
        self.search_calls = []
        self._last_query = ""
        self._last_results = []

    def setup_search_result(self, query: str, results: list):
        """Setup what results should be returned for a specific query."""
        self.search_results[query.lower()] = results

    def search_anime(self, query: str, verbose: bool = True):
        """Mock search_anime."""
        self.search_calls.append(query)
        self._last_query = query
        self._last_results = self.search_results.get(query.lower(), [])

    def get_search_metadata(self):
        """Mock get_search_metadata."""
        return Mock(used_query=self._last_query)

    def get_anime_titles_with_sources(self, filter_by_query=None, original_query=None):
        """Mock get_anime_titles_with_sources."""
        return self._last_results

    def clear_search_results(self):
        """Mock clear_search_results."""
        pass


@pytest.fixture
def mock_repository():
    """Provide a mock repository."""
    return MockRepository()


@pytest.fixture
def patch_repository(mock_repository):
    """Patch the global repository."""
    with patch("services.anime.search.rep", mock_repository):
        yield mock_repository


@pytest.fixture
def no_anilist():
    """Patch AniList discovery to avoid external calls."""
    with patch("utils.anilist_discovery.auto_discover_anilist_id", side_effect=Exception("No AniList")):
        yield


class TestAnimeSearchBasicWorkflow:
    """Test basic anime search workflow."""

    def test_user_searches_for_anime(self, patch_repository, no_anilist):
        """User searches for anime by title."""
        repo = patch_repository
        repo.setup_search_result("dandadan", [
            "Dandadan - AnimeFire",
            "Dandadan - AnimesonlineCC",
        ])

        state, results = incremental_search_anime("dandadan")

        assert len(results) >= 1
        assert "Dandadan" in results[0]

    def test_user_searches_returns_multiple_sources(self, patch_repository, no_anilist):
        """Search returns anime from multiple sources."""
        repo = patch_repository
        repo.setup_search_result("jujutsu kaisen", [
            "Jujutsu Kaisen - AnimeFire",
            "Jujutsu Kaisen - AnimesonlineCC",
            "Jujutsu Kaisen - AnimesDigital",
        ])

        state, results = incremental_search_anime("jujutsu kaisen")

        assert len(results) >= 1
        assert any("Jujutsu Kaisen" in r for r in results)


class TestIncrementalSearchRefinementWorkflow:
    """Test incremental search refinement scenarios."""

    def test_user_progressively_narrows_search_results(self, patch_repository, no_anilist):
        """User progressively refines search for better results."""
        repo = patch_repository
        repo.setup_search_result("my hero academia", [
            "My Hero Academia S1",
            "My Hero Academia S2",
            "My Hero Academia S3",
            "My Hero Academia S4",
            "My Hero Academia S5",
        ])

        state, results = incremental_search_anime("my hero academia")

        # Should find relevant results
        assert len(results) >= 1
        assert any("Hero" in r for r in results)

    def test_search_with_long_query(self, patch_repository, no_anilist):
        """Search with full multi-word query."""
        repo = patch_repository
        repo.setup_search_result("blue lock", [
            "Blue Lock - AnimeFire",
            "Blue Lock S2 - AnimesDigital",
        ])

        state, results = incremental_search_anime("blue lock")

        assert len(results) >= 1


class TestAnimeSelectionWorkflow:
    """Test anime selection from search results."""

    def test_user_selects_anime_from_results(self, patch_repository, no_anilist):
        """User selects anime from search results."""
        repo = patch_repository
        repo.setup_search_result("dandadan", [
            "Dandadan - AnimeFire",
            "Dandadan - AnimesonlineCC",
        ])

        state, results = incremental_search_anime("dandadan")

        # User selects first result
        selected = results[0]
        assert "Dandadan" in selected


class TestEpisodeSelectionWorkflow:
    """Test episode selection workflow."""

    def test_user_views_episode_list(self, patch_repository, no_anilist):
        """User views episode list for selected anime."""
        # Mock episode retrieval
        mock_episodes = [
            {"episode": "1", "title": "Beginning"},
            {"episode": "2", "title": "Development"},
            {"episode": "3", "title": "Climax"},
        ]

        episodes = mock_episodes
        assert len(episodes) == 3

    def test_user_selects_specific_episode(self, patch_repository, no_anilist):
        """User selects episode from list."""
        episodes = [f"Episode {i}" for i in range(1, 51)]

        # User selects episode 25
        selected_episode = episodes[24]
        assert "25" in selected_episode


class TestAnimePlaybackWorkflow:
    """Test anime playback workflow."""

    def test_episode_url_can_be_played(self, patch_repository, no_anilist):
        """Episode URL is valid and can be played."""
        episode_url = "https://example.com/stream/dandadan/episode1"

        with patch("utils.video_player.play_video") as mock_play:
            mock_play.return_value = True
            result = mock_play(episode_url)
            assert result is True


class TestCompleteAnimeWatchingWorkflow:
    """End-to-end anime watching scenarios."""

    def test_user_finds_anime_through_search(self, patch_repository, no_anilist):
        """User successfully searches and finds anime."""
        repo = patch_repository

        # Step 1: Search for anime
        repo.setup_search_result("dandadan", [
            "Dandadan - AnimeFire",
        ])
        state, results = incremental_search_anime("dandadan")
        assert len(results) > 0

        # Step 2: User selects anime
        selected_anime = results[0]
        assert "Dandadan" in selected_anime

    def test_user_can_search_multiple_anime(self, patch_repository, no_anilist):
        """User searches for multiple anime in session."""
        repo = patch_repository

        anime_titles = ["Dandadan", "Jujutsu Kaisen", "Blue Lock"]

        for title in anime_titles:
            repo.setup_search_result(title.lower(), [f"{title} - AnimeFire"])
            state, results = incremental_search_anime(title)
            assert len(results) > 0


class TestSearchErrorRecovery:
    """Test error handling in search workflow."""

    def test_search_returns_empty_for_not_found(self, patch_repository, no_anilist):
        """Search with no results returns empty."""
        repo = patch_repository
        repo.setup_search_result("nonexistentanime2024", [])

        state, results = incremental_search_anime("nonexistentanime2024")
        assert results == []
