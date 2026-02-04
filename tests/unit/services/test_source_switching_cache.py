"""Unit tests for source switching with cache.

Tests that source switching respects the cache-first approach and doesn't
unnecessarily re-search scrapers when results are available in cache.
"""

import pytest
from unittest.mock import Mock, patch
from services.anime.source_management import switch_anime_source


@pytest.fixture
def setup_mocks():
    """Setup all necessary mocks for source switching tests."""
    patches = []

    # Patch repository
    mock_rep_patch = patch("services.anime.source_management.rep")
    mock_rep = mock_rep_patch.start()
    patches.append(mock_rep_patch)

    # Setup repository mock
    mock_rep.anime_episodes_urls = {}
    mock_rep.save_episode_state.return_value = {"urls": [], "titles": []}
    mock_rep.load_from_cache = Mock()
    mock_rep.search_anime = Mock()
    mock_rep.get_search_metadata.return_value = Mock(used_query="test query")
    mock_rep.get_anime_titles_with_sources.return_value = ["Test Anime [animefire]"]
    mock_rep.get_episode_list.return_value = ["Episódio 1"]

    # Patch cache
    mock_cache_patch = patch("services.anime.source_management.get_cache")
    mock_get_cache = mock_cache_patch.start()
    patches.append(mock_cache_patch)

    # Patch title normalization
    mock_norm_patch = patch("services.anime.source_management.normalize_anime_title")
    mock_normalize = mock_norm_patch.start()
    mock_normalize.return_value = ["test"]  # Single variant for simplicity
    patches.append(mock_norm_patch)

    # Patch AniList search title loader
    mock_anilist_patch = patch("services.anime.source_management.load_anilist_search_title")
    mock_load_anilist = mock_anilist_patch.start()
    mock_load_anilist.return_value = None  # Use current_anime instead
    patches.append(mock_anilist_patch)

    # Patch loading context manager
    mock_loading_patch = patch("services.anime.source_management.loading")
    mock_loading = mock_loading_patch.start()
    mock_loading.return_value.__enter__ = Mock()
    mock_loading.return_value.__exit__ = Mock(return_value=None)
    patches.append(mock_loading_patch)

    # Patch menu_navigate
    mock_menu_patch = patch("services.anime.source_management.menu_navigate")
    mock_menu = mock_menu_patch.start()
    # First call: anime selection, Second call: episode selection
    mock_menu.side_effect = ["Test Anime [animefire]", "Episódio 1"]
    patches.append(mock_menu_patch)

    # Patch history file access to avoid progress detection
    mock_open_patch = patch("builtins.open", side_effect=FileNotFoundError)
    mock_open_patch.start()
    patches.append(mock_open_patch)

    # Patch anilist client (it's imported inside the function)
    mock_anilist_client_patch = patch("services.anilist_service.anilist_client")
    mock_anilist_client = mock_anilist_client_patch.start()
    mock_anilist_client.is_authenticated.return_value = False
    patches.append(mock_anilist_client_patch)

    yield {
        "rep": mock_rep,
        "get_cache": mock_get_cache,
        "normalize": mock_normalize,
        "load_anilist": mock_load_anilist,
        "loading": mock_loading,
        "menu": mock_menu,
    }

    # Cleanup
    for p in patches:
        p.stop()


class TestSourceSwitchingCache:
    """Test source switching cache behavior."""

    def test_uses_cache_when_available(self, setup_mocks):
        """When switching source, should use cache if results are cached."""
        mocks = setup_mocks
        # Setup: Cache returns data
        cache_data = Mock(episode_count=12, episode_urls=["url1", "url2"])
        mocks["get_cache"].return_value = cache_data

        # Call switch_anime_source
        switch_anime_source("Current Anime", Mock())

        # Verify cache was checked
        mocks["get_cache"].assert_called()

        # Verify load_from_cache was called when cache was available
        mocks["rep"].load_from_cache.assert_called()

        # Verify search_anime was called with verbose=False (background search for sources)
        # This indicates cache was found and we're just discovering sources
        search_anime_calls = mocks["rep"].search_anime.call_args_list
        assert len(search_anime_calls) > 0
        # Check that at least one call has verbose=False
        verbose_false_called = any(
            call_obj[1].get("verbose") is False for call_obj in search_anime_calls
        )
        assert verbose_false_called, (
            "search_anime should be called with verbose=False after cache load"
        )

    def test_searches_scrapers_when_cache_miss(self, setup_mocks):
        """When cache miss, should use incremental search (3 words + filter)."""
        mocks = setup_mocks
        # Setup: No cache
        mocks["get_cache"].return_value = None

        # Mock incremental_search_anime (imported inside the function)
        with patch("services.anime.search.incremental_search_anime") as mock_incremental:
            mock_incremental.return_value = (Mock(), [])  # Returns (state, results)

            # Call switch_anime_source
            switch_anime_source("Current Anime", Mock())

            # Verify cache was checked
            mocks["get_cache"].assert_called()

            # Verify load_from_cache was NOT called
            mocks["rep"].load_from_cache.assert_not_called()

            # Verify incremental_search_anime was called (not simple search)
            mock_incremental.assert_called()

    def test_returns_selected_anime_and_episode_idx(self, setup_mocks):
        """Should return the selected anime title and episode index."""
        mocks = setup_mocks
        # Setup: Anime found with episode selected
        mocks["get_cache"].return_value = None

        # Call switch_anime_source
        result = switch_anime_source("Current Anime", Mock())

        # Verify result is a tuple of (anime_title, episode_idx)
        assert result is not None
        assert len(result) == 2
        assert result[0] is not None  # Anime title
        assert isinstance(result[1], int)  # Episode index
        assert result[1] >= 0
