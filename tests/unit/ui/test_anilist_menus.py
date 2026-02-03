"""Tests for AniList menu functions - particularly the search and watch flow.

Testing the flow: Search → Select → Watch (with and without AniList login)
"""

import argparse
from unittest.mock import Mock, patch
import pytest

from models.models import (
    AniListTitle,
    AniListAnime,
    AniListMediaListEntry,
    AniListViewerInfo,
    AniListAnimeStatistics,
    AniListStatistics,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_anilist_client():
    """Mock AniList client for all tests."""
    with patch("ui.anilist_menus.anilist_client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_anilist_anime_flow():
    """Mock the anilist_anime_flow function."""
    with patch("ui.anilist_menus.anilist_anime_flow") as mock_flow:
        yield mock_flow


@pytest.fixture
def mock_menu_navigate():
    """Mock menu_navigate function."""
    with patch("ui.anilist_menus.menu_navigate") as mock_menu:
        yield mock_menu


@pytest.fixture
def mock_loading():
    """Mock loading context manager."""
    with patch("ui.anilist_menus.loading") as mock_load:
        # loading() is used as a context manager, so we need to mock it properly
        mock_load.return_value.__enter__ = Mock(return_value=None)
        mock_load.return_value.__exit__ = Mock(return_value=None)
        yield mock_load


@pytest.fixture
def mock_anilist_main_menu():
    """Mock anilist_main_menu function."""
    with patch("ui.anilist_menus.anilist_main_menu") as mock_menu:
        yield mock_menu


@pytest.fixture
def mock_choose_status():
    """Mock _choose_status function."""
    with patch("ui.anilist_menus._choose_status") as mock_status:
        yield mock_status


@pytest.fixture
def mock_input():
    """Mock builtins.input function."""
    with patch("builtins.input") as mock_inp:
        yield mock_inp


@pytest.fixture
def sample_anime():
    """Create a sample AniList anime object."""
    return AniListAnime(
        id=123,
        title=AniListTitle(romaji="Dandadan", english="Dandadan", native="ダンダダン"),
        episodes=12,
        averageScore=87,
        seasonYear=2024,
        season="FALL",
    )


@pytest.fixture
def sample_media_list_entry():
    """Create a sample AniList media list entry with progress."""
    return AniListMediaListEntry(
        id=456,
        status="CURRENT",
        progress=5,
        score=8,
        media=AniListAnime(
            id=123,
            title=AniListTitle(romaji="Dandadan", english="Dandadan", native="ダンダダン"),
            episodes=12,
        ),
    )


@pytest.fixture
def sample_viewer_info():
    """Create a sample AniList viewer info."""
    return AniListViewerInfo(
        id=999,
        name="TestUser",
        statistics=AniListStatistics(
            anime=AniListAnimeStatistics(count=100, episodesWatched=2500, minutesWatched=150000)
        ),
    )


# ============================================================================
# UNIT TESTS: _start_watching_anime
# ============================================================================


class TestStartWatchingAnime:
    """Tests for _start_watching_anime function."""

    def test_calls_anilist_anime_flow_with_correct_parameters(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        sample_media_list_entry,
    ):
        """_start_watching_anime should call anilist_anime_flow with correct params."""
        # Setup
        from ui.anilist_menus import _start_watching_anime

        mock_anilist_client.get_media_list_entry.return_value = sample_media_list_entry

        # Execute
        _start_watching_anime("Dandadan", 123, "Dandadan Full Title")

        # Verify: anilist_anime_flow was called
        mock_anilist_anime_flow.assert_called_once()
        call_args = mock_anilist_anime_flow.call_args

        # Check positional arguments
        assert call_args[0][0] == "Dandadan"  # search_title
        assert call_args[0][1] == 123  # anime_id
        assert isinstance(call_args[0][2], argparse.Namespace)  # args
        assert call_args[0][2].debug is False  # debug flag

        # Check keyword arguments
        assert call_args[1]["anilist_progress"] == 5  # progress from entry
        assert call_args[1]["display_title"] == "Dandadan Full Title"

    def test_passes_zero_progress_when_no_entry(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
    ):
        """_start_watching_anime should pass 0 progress when no AniList entry."""
        from ui.anilist_menus import _start_watching_anime

        mock_anilist_client.get_media_list_entry.return_value = None

        _start_watching_anime("Dandadan", 123, "Dandadan Full Title")

        call_args = mock_anilist_anime_flow.call_args
        assert call_args[1]["anilist_progress"] == 0

    def test_passes_zero_progress_when_entry_has_none_progress(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
    ):
        """_start_watching_anime should pass 0 when entry.progress is None."""
        from ui.anilist_menus import _start_watching_anime

        entry = AniListMediaListEntry(
            id=456,
            status="CURRENT",
            progress=None,  # No progress set
        )
        mock_anilist_client.get_media_list_entry.return_value = entry

        _start_watching_anime("Dandadan", 123, "Dandadan Full Title")

        call_args = mock_anilist_anime_flow.call_args
        assert call_args[1]["anilist_progress"] == 0

    def test_creates_argparse_namespace_with_debug_false(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        sample_media_list_entry,
    ):
        """_start_watching_anime should create Namespace with debug=False."""
        from ui.anilist_menus import _start_watching_anime

        mock_anilist_client.get_media_list_entry.return_value = sample_media_list_entry

        _start_watching_anime("Dandadan", 123, "Dandadan Full Title")

        call_args = mock_anilist_anime_flow.call_args
        args = call_args[0][2]
        assert isinstance(args, argparse.Namespace)
        assert args.debug is False

    def test_fetches_progress_from_anilist_client(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
    ):
        """_start_watching_anime should call get_media_list_entry with anime_id."""
        from ui.anilist_menus import _start_watching_anime

        entry = AniListMediaListEntry(id=456, status="CURRENT", progress=3)
        mock_anilist_client.get_media_list_entry.return_value = entry

        _start_watching_anime("Dandadan", 123, "Display Title")

        # Verify the call
        mock_anilist_client.get_media_list_entry.assert_called_once_with(123)


# ============================================================================
# UNIT TESTS: _search_and_add_anime - Logged-in Users
# ============================================================================


class TestSearchAndAddAnimeLoggedIn:
    """Tests for _search_and_add_anime when user is logged in."""

    def test_watch_now_without_adding_to_list(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user clicks "▶️ Assistir agora" (first option), should watch immediately."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches, selects anime, then clicks watch
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Select anime from search results
            "▶️  Assistir agora",  # Action: watch now (first option)
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: anilist_anime_flow was called
        mock_anilist_anime_flow.assert_called_once()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()

    def test_add_then_watch_after_choosing_status(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user adds to list then chooses watch, should add then watch."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches, selects anime, clicks add, chooses status, clicks watch
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Select anime from search results
            "➕ Adicionar à lista",  # Action: add to list
            "📺 Watching (Assistindo)",  # Status: watching
            "▶️  Assistir agora",  # Watch now after adding
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: anime was added with CURRENT status
        mock_anilist_client.add_to_list.assert_called_once_with(123, "CURRENT")
        # Verify: playback started
        mock_anilist_anime_flow.assert_called_once()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()

    def test_add_then_go_back_without_watching(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user adds to list but chooses not to watch, should NOT start playback."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches, selects anime, clicks add, chooses status, clicks back
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Select anime from search results
            "➕ Adicionar à lista",  # Action: add to list
            "📋 Planning (Planejo assistir)",  # Status: planning
            "🔙 Voltar ao menu",  # Back to menu (don't watch)
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: anime was added with PLANNING status
        mock_anilist_client.add_to_list.assert_called_once_with(123, "PLANNING")
        # Verify: playback was NOT started
        mock_anilist_anime_flow.assert_not_called()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()

    def test_go_back_from_action_menu(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user clicks back from action menu, should return to main menu."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches, selects anime, then clicks back
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Select anime from search results
            "🔙 Voltar",  # Go back from action menu
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: nothing was added or started
        mock_anilist_client.add_to_list.assert_not_called()
        mock_anilist_anime_flow.assert_not_called()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()


# ============================================================================
# UNIT TESTS: _search_and_add_anime - Non-logged-in Users
# ============================================================================


class TestSearchAndAddAnimeNotLoggedIn:
    """Tests for _search_and_add_anime when user is NOT logged in."""

    def test_calls_start_watching_anime_directly(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """For non-logged-in users, should call _start_watching_anime directly."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches and selects anime
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Select anime from search results
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=False)

        # Verify: anilist_anime_flow was called (via _start_watching_anime)
        mock_anilist_anime_flow.assert_called_once()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()

    def test_no_add_to_list_option_for_non_logged_in(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """For non-logged-in users, no add to list menu should appear."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User searches and selects anime
        mock_menu_navigate.side_effect = [
            "Dandaban (2024, 12 eps) ⭐87%",  # Select from search results
        ]
        mock_input.return_value = "Dandaban"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandaban"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=False)

        # Verify: menu_navigate called only once (for search results)
        assert mock_menu_navigate.call_count == 1


# ============================================================================
# INTEGRATION TESTS: Complete Search to Playback Flow
# ============================================================================


class TestCompleteSearchToPlaybackFlow:
    """Integration tests for complete search → select → watch flow."""

    def test_end_to_end_search_and_watch_logged_in(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
        sample_media_list_entry,
    ):
        """End-to-end: Search → Select → Watch (logged in, with AniList progress)."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User has progress on this anime
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Search results
            "▶️  Assistir agora",  # Action: watch now
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = sample_media_list_entry
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify the complete flow
        mock_anilist_client.search_anime.assert_called_once_with("Dandadan")
        mock_anilist_anime_flow.assert_called_once()

        # Verify progress was passed
        call_args = mock_anilist_anime_flow.call_args
        assert call_args[1]["anilist_progress"] == 5

    def test_end_to_end_search_and_watch_no_progress(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """End-to-end: Search → Select → Watch (no prior progress)."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User hasn't started this anime
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Search results
            "▶️  Assistir agora",  # Action: watch now
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify the complete flow
        mock_anilist_anime_flow.assert_called_once()

        # Verify progress is 0
        call_args = mock_anilist_anime_flow.call_args
        assert call_args[1]["anilist_progress"] == 0

    def test_end_to_end_add_then_watch_flow(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """End-to-end: Search → Select → Add → Watch (complete flow)."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: Complete flow with add and watch
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Search results
            "➕ Adicionar à lista",  # Action: add to list
            "✅ Completed (Completo)",  # Status: completed
            "▶️  Assistir agora",  # Watch now
        ]
        mock_input.return_value = "Dandadan"
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify the complete flow
        mock_anilist_client.add_to_list.assert_called_once_with(123, "COMPLETED")
        mock_anilist_anime_flow.assert_called_once()


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Edge cases and error conditions."""

    def test_empty_search_query(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
    ):
        """Empty search query should return to main menu."""
        from ui.anilist_menus import _search_and_add_anime

        mock_input.return_value = ""
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify behavior
        mock_anilist_client.search_anime.assert_not_called()
        mock_anilist_main_menu.assert_called_once()

    def test_no_search_results(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
    ):
        """When no search results, should return to main menu."""
        from ui.anilist_menus import _search_and_add_anime

        mock_input.return_value = "NonExistentAnime"
        mock_anilist_client.search_anime.return_value = []
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify behavior
        mock_anilist_anime_flow.assert_not_called()
        mock_anilist_main_menu.assert_called_once()

    def test_user_cancels_search_results(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user cancels search results menu, should return to main menu."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User presses ESC on search results
        mock_input.return_value = "Dandadan"
        mock_menu_navigate.side_effect = [None]  # ESC on search results
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify behavior
        mock_anilist_anime_flow.assert_not_called()
        mock_anilist_main_menu.assert_called_once()

    def test_add_status_selection_cancelled(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When user cancels status selection, should show action menu again."""
        from ui.anilist_menus import _search_and_add_anime

        # Setup: User tries to add, cancels status, then clicks back
        mock_input.return_value = "Dandadan"
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",  # Search results
            "➕ Adicionar à lista",  # Action: add to list
            None,  # Cancelled status selection (ESC)
            "🔙 Voltar",  # Then go back
        ]
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = None
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: anime was NOT added (status selection was cancelled)
        mock_anilist_client.add_to_list.assert_not_called()
        # Verify: returned to main menu
        mock_anilist_main_menu.assert_called_once()

    def test_zero_progress_from_entry(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """When AniList entry has progress=0, should pass 0 not None."""
        from ui.anilist_menus import _search_and_add_anime

        entry = AniListMediaListEntry(
            id=456,
            status="CURRENT",
            progress=0,  # Zero progress (started but first ep not watched)
        )
        mock_input.return_value = "Dandadan"
        mock_menu_navigate.side_effect = [
            "Dandadan (2024, 12 eps) ⭐87%",
            "▶️  Assistir agora",
        ]
        mock_anilist_client.search_anime.return_value = [sample_anime]
        mock_anilist_client.format_title.return_value = "Dandadan"
        mock_anilist_client.get_media_list_entry.return_value = entry
        mock_anilist_main_menu.return_value = None

        # Execute
        _search_and_add_anime(is_logged_in=True)

        # Verify: progress=0 was passed
        call_args = mock_anilist_anime_flow.call_args
        assert call_args[1]["anilist_progress"] == 0


# ============================================================================
# STATUS MAPPING TESTS
# ============================================================================


class TestStatusMapping:
    """Tests for status selection and mapping."""

    def test_all_status_options_map_correctly(
        self,
        mock_anilist_client,
        mock_anilist_anime_flow,
        mock_menu_navigate,
        mock_loading,
        mock_anilist_main_menu,
        mock_input,
        sample_anime,
    ):
        """Test that all status options map to correct AniList status codes."""
        from ui.anilist_menus import _search_and_add_anime

        status_tests = [
            ("📺 Watching (Assistindo)", "CURRENT"),
            ("📋 Planning (Planejo assistir)", "PLANNING"),
            ("✅ Completed (Completo)", "COMPLETED"),
            ("⏸️  Paused (Pausado)", "PAUSED"),
            ("❌ Dropped (Dropado)", "DROPPED"),
            ("🔁 Rewatching (Reassistindo)", "REPEATING"),
        ]

        for display_text, expected_status in status_tests:
            # Reset mocks
            mock_anilist_client.reset_mock()
            mock_anilist_anime_flow.reset_mock()
            mock_menu_navigate.reset_mock()
            mock_anilist_main_menu.reset_mock()

            # Setup: Select anime, add, choose status, don't watch
            mock_menu_navigate.side_effect = [
                "Dandadan (2024, 12 eps) ⭐87%",
                "➕ Adicionar à lista",
                display_text,
                "🔙 Voltar ao menu",
            ]
            mock_input.return_value = "Dandadan"
            mock_anilist_client.search_anime.return_value = [sample_anime]
            mock_anilist_client.format_title.return_value = "Dandadan"
            mock_anilist_client.get_media_list_entry.return_value = None
            mock_anilist_main_menu.return_value = None

            # Execute
            _search_and_add_anime(is_logged_in=True)

            # Verify the correct status was used
            mock_anilist_client.add_to_list.assert_called_once_with(123, expected_status)


# ============================================================================
# UNIT TESTS: _get_episode_count
# ============================================================================


class TestGetEpisodeCount:
    """Tests for _get_episode_count function."""

    @pytest.fixture
    def mock_cache(self):
        """Mock cache system."""
        with patch("ui.anilist_menus.get_cache") as mock_cache_func:
            cache_mock = Mock()
            mock_cache_func.return_value = cache_mock
            yield cache_mock

    def test_returns_existing_episodes_when_not_null(
        self, mock_anilist_client, mock_cache
    ):
        """When media.episodes is not None, should return it directly."""
        from ui.anilist_menus import _get_episode_count

        # Execute
        result = _get_episode_count(123, 12)

        # Verify
        assert result == 12
        # Should not check cache or make API calls
        mock_cache.get.assert_not_called()
        mock_anilist_client.get_anime_by_id.assert_not_called()

    def test_returns_cached_episodes_when_media_episodes_is_null(
        self, mock_anilist_client, mock_cache
    ):
        """When media.episodes is None but cache has value, should return cached value."""
        from ui.anilist_menus import _get_episode_count

        # Setup: Cache has episode count
        mock_cache.get.return_value = 24

        # Execute
        result = _get_episode_count(123, None)

        # Verify
        assert result == 24
        mock_cache.get.assert_called_once_with("anilist_episodes:123")
        # Should not make API call
        mock_anilist_client.get_anime_by_id.assert_not_called()

    def test_fetches_from_api_when_cache_miss_and_media_episodes_is_null(
        self, mock_anilist_client, mock_cache, sample_anime
    ):
        """When media.episodes is None and cache miss, should fetch from API."""
        from ui.anilist_menus import _get_episode_count

        # Setup: Cache miss, API has episode count
        mock_cache.get.return_value = None
        mock_anilist_client.get_anime_by_id.return_value = sample_anime

        # Execute
        result = _get_episode_count(123, None)

        # Verify
        assert result == 12
        mock_cache.get.assert_called_once_with("anilist_episodes:123")
        mock_anilist_client.get_anime_by_id.assert_called_once_with(123)
        # Should cache the result
        mock_cache.set.assert_called_once_with("anilist_episodes:123", 12, ttl=604800)

    def test_returns_none_when_api_returns_none(
        self, mock_anilist_client, mock_cache
    ):
        """When API returns None, should return None and not cache."""
        from ui.anilist_menus import _get_episode_count

        # Setup: Cache miss, API returns None
        mock_cache.get.return_value = None
        mock_anilist_client.get_anime_by_id.return_value = None

        # Execute
        result = _get_episode_count(123, None)

        # Verify
        assert result is None
        mock_cache.get.assert_called_once_with("anilist_episodes:123")
        mock_anilist_client.get_anime_by_id.assert_called_once_with(123)
        # Should not cache None result
        mock_cache.set.assert_not_called()

    def test_returns_none_when_api_returns_anime_with_null_episodes(
        self, mock_anilist_client, mock_cache
    ):
        """When API returns anime with episodes=None, should return None and not cache."""
        from ui.anilist_menus import _get_episode_count

        # Setup: API returns anime with null episodes
        anime_with_null_episodes = AniListAnime(
            id=123,
            title=AniListTitle(romaji="Test Anime"),
            episodes=None,  # Null episodes
        )
        mock_cache.get.return_value = None
        mock_anilist_client.get_anime_by_id.return_value = anime_with_null_episodes

        # Execute
        result = _get_episode_count(123, None)

        # Verify
        assert result is None
        mock_cache.get.assert_called_once_with("anilist_episodes:123")
        mock_anilist_client.get_anime_by_id.assert_called_once_with(123)
        # Should not cache None result
        mock_cache.set.assert_not_called()

    def test_handles_api_exception_gracefully(
        self, mock_anilist_client, mock_cache
    ):
        """When API call fails with exception, should return None."""
        from ui.anilist_menus import _get_episode_count

        # Setup: Cache miss, API raises exception
        mock_cache.get.return_value = None
        mock_anilist_client.get_anime_by_id.side_effect = Exception("API Error")

        # Execute
        result = _get_episode_count(123, None)

        # Verify
        assert result is None
        mock_cache.get.assert_called_once_with("anilist_episodes:123")
        mock_anilist_client.get_anime_by_id.assert_called_once_with(123)
        # Should not cache on error
        mock_cache.set.assert_not_called()

    def test_cache_key_format_is_correct(self, mock_anilist_client, mock_cache):
        """Cache key should use format 'anilist_episodes:{anime_id}'."""
        from ui.anilist_menus import _get_episode_count

        # Execute with different anime IDs
        _get_episode_count(456, None)
        _get_episode_count(789, None)

        # Verify cache keys
        expected_calls = [
            ("anilist_episodes:456",),
            ("anilist_episodes:789",),
        ]
        actual_calls = [call[0] for call in mock_cache.get.call_args_list]
        assert actual_calls == expected_calls

    def test_cache_ttl_is_7_days(self, mock_anilist_client, mock_cache, sample_anime):
        """Cache TTL should be 7 days (604800 seconds)."""
        from ui.anilist_menus import _get_episode_count

        # Setup: Cache miss, API returns anime
        mock_cache.get.return_value = None
        mock_anilist_client.get_anime_by_id.return_value = sample_anime

        # Execute
        _get_episode_count(123, None)

        # Verify TTL
        mock_cache.set.assert_called_once_with("anilist_episodes:123", 12, ttl=604800)
