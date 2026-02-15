"""Tests for PlaybackService - TDD approach.

Tests are written BEFORE implementation following the TDD cycle:
1. RED - Write failing tests
2. GREEN - Implement minimal code to pass
3. REFACTOR - Improve code quality

This service orchestrates the full playback flow including:
- Preparing playback context from search or history
- Getting episode URLs
- Syncing progress to AniList
- Episode navigation
"""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch
import pytest

from services.anime.anilist_discovery_service import AniListDiscoveryResult


# =============================================================================
# Step 1: Test Immutable Data Types
# =============================================================================


class TestPlaybackContextDataclass:
    """Tests for the immutable PlaybackContext dataclass."""

    def test_dataclass_is_frozen(self):
        """PlaybackContext should be immutable (frozen)."""
        from services.anime.playback_service import PlaybackContext

        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=0,
            source=None,
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=("Episodio 1", "Episodio 2"),
        )

        # Should raise error when trying to modify
        with pytest.raises(FrozenInstanceError):
            ctx.episode_idx = 1

    def test_dataclass_with_all_fields_populated(self):
        """Should create context with all fields populated."""
        from services.anime.playback_service import PlaybackContext

        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=5,
            source="animefire",
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes_anilist=24,
            num_episodes=24,
            episode_list=tuple(f"Episodio {i}" for i in range(1, 25)),
        )

        assert ctx.anime_title == "Dandadan"
        assert ctx.episode_idx == 5
        assert ctx.source == "animefire"
        assert ctx.anilist_id == 12345
        assert ctx.anilist_title == "Dandadan"
        assert ctx.total_episodes_anilist == 24
        assert ctx.num_episodes == 24
        assert len(ctx.episode_list) == 24

    def test_dataclass_with_optional_fields_none(self):
        """Should create context with optional fields as None."""
        from services.anime.playback_service import PlaybackContext

        ctx = PlaybackContext(
            anime_title="Test Anime",
            episode_idx=0,
            source=None,
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=(),
        )

        assert ctx.source is None
        assert ctx.anilist_id is None
        assert ctx.anilist_title is None
        assert ctx.total_episodes_anilist is None


class TestEpisodePlaybackResultDataclass:
    """Tests for the immutable EpisodePlaybackResult dataclass."""

    def test_dataclass_is_frozen(self):
        """EpisodePlaybackResult should be immutable (frozen)."""
        from services.anime.playback_service import EpisodePlaybackResult

        result = EpisodePlaybackResult(
            player_url="https://example.com/video.mp4",
            source="animefire",
            success=True,
            error_message=None,
        )

        # Should raise error when trying to modify
        with pytest.raises(FrozenInstanceError):
            result.success = False

    def test_successful_result(self):
        """Should create a successful result with URL and source."""
        from services.anime.playback_service import EpisodePlaybackResult

        result = EpisodePlaybackResult(
            player_url="https://example.com/video.mp4",
            source="animefire",
            success=True,
            error_message=None,
        )

        assert result.player_url == "https://example.com/video.mp4"
        assert result.source == "animefire"
        assert result.success is True
        assert result.error_message is None

    def test_failed_result(self):
        """Should create a failed result with error message."""
        from services.anime.playback_service import EpisodePlaybackResult

        result = EpisodePlaybackResult(
            player_url=None,
            source=None,
            success=False,
            error_message="No video source found",
        )

        assert result.player_url is None
        assert result.source is None
        assert result.success is False
        assert result.error_message == "No video source found"


# =============================================================================
# Step 2: Tests for prepare_playback_from_search()
# =============================================================================


class TestPreparePlaybackFromSearch:
    """Tests for prepare_playback_from_search function."""

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_basic_search_result(self, mock_discover, mock_rep):
        """Test 1: Basic Search Result.

        Input: args, selected_anime="Dandadan", episode_idx=0, source="animefire"
        Expected: Returns PlaybackContext with all fields populated
        Verify: discover_anilist_info() is called to populate anilist_id, anilist_title
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup mocks
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=12,
            mal_id=57334,
            found=True,
            authenticated=True,
        )
        mock_rep.get_episode_list.return_value = [
            "Episodio 1",
            "Episodio 2",
            "Episodio 3",
        ]

        # Execute
        result = prepare_playback_from_search(
            selected_anime="Dandadan",
            episode_idx=0,
            source="animefire",
        )

        # Verify
        assert result is not None
        assert result.anime_title == "Dandadan"
        assert result.episode_idx == 0
        assert result.source == "animefire"
        assert result.anilist_id == 12345
        assert result.anilist_title == "Dandadan"
        assert result.total_episodes_anilist == 12
        assert result.num_episodes == 3
        assert result.episode_list == ("Episodio 1", "Episodio 2", "Episodio 3")

        # Verify discover was called
        mock_discover.assert_called_once_with("Dandadan")

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_search_without_anilist_authentication(self, mock_discover, mock_rep):
        """Test 2: Search Without AniList Authentication.

        Input: AniList not authenticated
        Expected: PlaybackContext with anilist_id=None, anilist_title=None
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup: AniList not authenticated
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=False,
        )
        mock_rep.get_episode_list.return_value = ["Ep 1", "Ep 2"]

        # Execute
        result = prepare_playback_from_search(
            selected_anime="Dandadan",
            episode_idx=0,
            source="animefire",
        )

        # Verify
        assert result is not None
        assert result.anilist_id is None
        assert result.anilist_title is None
        assert result.total_episodes_anilist is None

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_search_with_episode_list(self, mock_discover, mock_rep):
        """Test 3: Search With Episode List.

        Input: Valid anime and source
        Expected: episode_list populated from repository
        Verify: Uses rep.get_episode_list() to get episodes
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup
        episode_titles = [f"Episodio {i}" for i in range(1, 25)]
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=True,
        )
        mock_rep.get_episode_list.return_value = episode_titles

        # Execute
        result = prepare_playback_from_search(
            selected_anime="Test Anime",
            episode_idx=5,
            source="animesdigital",
        )

        # Verify
        assert result is not None
        assert result.num_episodes == 24
        assert len(result.episode_list) == 24
        assert result.episode_list[0] == "Episodio 1"
        assert result.episode_list[23] == "Episodio 24"

        # Verify repository was called
        mock_rep.get_episode_list.assert_called_once_with("Test Anime")

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_search_with_mixed_episode_counts(self, mock_discover, mock_rep):
        """Test 4: Search With Mixed Episode Counts.

        Input: scraper has 24 episodes, AniList says 25
        Expected: num_episodes=24, total_episodes_anilist=25
        Verify: Both sources are captured
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup: Scraper has 24, AniList has 25
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Some Anime",
            total_episodes=25,  # AniList says 25
            mal_id=40748,
            found=True,
            authenticated=True,
        )
        mock_rep.get_episode_list.return_value = [f"Ep {i}" for i in range(1, 25)]  # 24 episodes

        # Execute
        result = prepare_playback_from_search(
            selected_anime="Some Anime",
            episode_idx=0,
            source="animefire",
        )

        # Verify both counts are captured
        assert result is not None
        assert result.num_episodes == 24  # From scraper
        assert result.total_episodes_anilist == 25  # From AniList


# =============================================================================
# Step 3: Tests for prepare_playback_from_history()
# =============================================================================


class TestPreparePlaybackFromHistory:
    """Tests for prepare_playback_from_history function."""

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    @patch("services.anime.playback_service.load_history")
    def test_load_from_history(self, mock_load_history, mock_discover, mock_rep):
        """Test 5: Load From History.

        Input: History file has saved anime state
        Expected: Returns PlaybackContext with episode_idx from history
        Verify: Uses load_history() from history_service
        """
        from services.anime.playback_service import prepare_playback_from_history

        # Setup: History returns saved state
        mock_load_history.return_value = ("Dandadan", 5, 12345, "Dandadan")
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=12,
            mal_id=57334,
            found=True,
            authenticated=True,
        )
        mock_rep.get_episode_list.return_value = [f"Ep {i}" for i in range(1, 13)]

        # Execute
        result = prepare_playback_from_history()

        # Verify
        assert result is not None
        assert result.anime_title == "Dandadan"
        assert result.episode_idx == 5
        assert result.anilist_id == 12345
        assert result.num_episodes == 12

        # Verify load_history was called
        mock_load_history.assert_called_once()

    @patch("services.anime.playback_service.load_history")
    def test_history_load_failure(self, mock_load_history):
        """Test 6: History Load Failure.

        Input: History file missing or corrupted
        Expected: Returns None (graceful degradation)
        """
        from services.anime.playback_service import prepare_playback_from_history

        # Setup: History returns None
        mock_load_history.return_value = None

        # Execute
        result = prepare_playback_from_history()

        # Verify graceful degradation
        assert result is None

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    @patch("services.anime.playback_service.load_history")
    def test_history_with_anilist_id(self, mock_load_history, mock_discover, mock_rep):
        """Test 7: History With AniList ID.

        Input: History entry has anilist_id saved
        Expected: PlaybackContext includes anilist_id and discovers full info
        Verify: Uses discover_anilist_info() to enrich saved ID
        """
        from services.anime.playback_service import prepare_playback_from_history

        # Setup: History has AniList ID
        mock_load_history.return_value = ("Test Anime", 3, 99999, "Test Anime (Romaji)")
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=99999,
            anilist_title="Test Anime (Romaji)",
            total_episodes=24,
            mal_id=12345,
            found=True,
            authenticated=True,
        )
        mock_rep.get_episode_list.return_value = [f"Ep {i}" for i in range(1, 25)]

        # Execute
        result = prepare_playback_from_history()

        # Verify AniList info is enriched
        assert result is not None
        assert result.anilist_id == 99999
        assert result.anilist_title == "Test Anime (Romaji)"
        assert result.total_episodes_anilist == 24

        # Verify discover was called with the title
        mock_discover.assert_called_once_with("Test Anime")


# =============================================================================
# Step 4: Tests for get_episode_url_and_source()
# =============================================================================


class TestGetEpisodeUrlAndSource:
    """Tests for get_episode_url_and_source function."""

    @patch("services.anime.playback_service.rep")
    def test_successful_video_url_extraction(self, mock_rep):
        """Test 8: Successful Video URL Extraction.

        Input: anime_title="Dandadan", episode=5
        Expected: Returns EpisodePlaybackResult with player_url and source
        Verify: Uses rep.search_player() to get URL
        """
        from services.anime.playback_service import get_episode_url_and_source

        # Setup
        mock_rep.search_player.return_value = "https://video.example.com/ep5.mp4"
        mock_rep.get_episode_url_and_source.return_value = (
            "https://page.example.com/ep5",
            "animefire",
        )

        # Execute
        result = get_episode_url_and_source("Dandadan", 5)

        # Verify
        assert result.success is True
        assert result.player_url == "https://video.example.com/ep5.mp4"
        assert result.source == "animefire"
        assert result.error_message is None

        # Verify search_player was called
        mock_rep.search_player.assert_called_once_with("Dandadan", 5)

    @patch("services.anime.playback_service.rep")
    def test_no_video_found(self, mock_rep):
        """Test 9: No Video Found.

        Input: Valid anime/episode but no scraper could extract video
        Expected: Returns EpisodePlaybackResult with success=False, error_message set
        """
        from services.anime.playback_service import get_episode_url_and_source

        # Setup: No video found
        mock_rep.search_player.return_value = None
        mock_rep.get_episode_url_and_source.return_value = None

        # Execute
        result = get_episode_url_and_source("Dandadan", 5)

        # Verify
        assert result.success is False
        assert result.player_url is None
        assert result.error_message is not None
        assert (
            "video" in result.error_message.lower() or "encontrado" in result.error_message.lower()
        )

    @patch("services.anime.playback_service.rep")
    def test_api_error_during_lookup(self, mock_rep):
        """Test 10: API Error During Lookup.

        Input: rep.search_player() raises exception
        Expected: Returns EpisodePlaybackResult with success=False, error message
        """
        from services.anime.playback_service import get_episode_url_and_source

        # Setup: Exception thrown
        mock_rep.search_player.side_effect = Exception("Network error")

        # Execute - should NOT raise exception
        result = get_episode_url_and_source("Dandadan", 5)

        # Verify graceful error handling
        assert result.success is False
        assert result.player_url is None
        assert result.error_message is not None


# =============================================================================
# Step 5: Tests for sync_progress_to_anilist()
# =============================================================================


class TestSyncProgressToAnilist:
    """Tests for sync_progress_to_anilist function."""

    def test_not_authenticated(self):
        """Test 11: Not Authenticated.

        Input: anilist_id=None, episode=5, watched=True
        Expected: Returns False (no sync attempted)
        """
        from services.anime.playback_service import sync_progress_to_anilist

        # Execute with no anilist_id
        result = sync_progress_to_anilist(
            anilist_id=None,
            episode=5,
            num_episodes=24,
        )

        # Verify no sync attempted
        assert result is False

    @patch("services.anime.playback_service.anilist_client")
    def test_sync_episode_progress(self, mock_anilist):
        """Test 12: Sync Episode Progress.

        Input: Valid anilist_id, episode=5, watched=True
        Expected: Returns True, calls anilist_client.update_progress()
        Verify: Calls are made in correct order
        """
        from services.anime.playback_service import sync_progress_to_anilist

        # Setup
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.is_in_any_list.return_value = True
        mock_anilist.get_media_list_entry.return_value = MagicMock(status="CURRENT")
        mock_anilist.update_progress.return_value = True
        # Mock get_anime_by_id for validation
        mock_anime = MagicMock()
        mock_anime.episodes = 24
        mock_anilist.get_anime_by_id.return_value = mock_anime

        # Execute
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=5,
            num_episodes=24,
        )

        # Verify
        assert result is True
        mock_anilist.update_progress.assert_called_once_with(12345, 5)

    @patch("services.anime.playback_service.anilist_client")
    def test_add_anime_to_list(self, mock_anilist):
        """Test 13: Add Anime To List.

        Input: Valid anime but not in any AniList list
        Expected: Calls anilist_client.add_to_list() first, then update_progress()
        """
        from services.anime.playback_service import sync_progress_to_anilist

        # Setup: Anime not in any list
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.is_in_any_list.return_value = False
        mock_anilist.add_to_list.return_value = True
        mock_anilist.update_progress.return_value = True
        # Mock get_anime_by_id for validation
        mock_anime = MagicMock()
        mock_anime.episodes = 24
        mock_anilist.get_anime_by_id.return_value = mock_anime

        # Execute
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=5,
            num_episodes=24,
        )

        # Verify add_to_list was called before update_progress
        assert result is True
        mock_anilist.add_to_list.assert_called_once()
        mock_anilist.update_progress.assert_called_once_with(12345, 5)

    @patch("services.anime.playback_service.anilist_client")
    def test_promote_status_planning_to_current(self, mock_anilist):
        """Test 14: Promote Status (PLANNING -> CURRENT).

        Input: Anime in PLANNING status
        Expected: Calls add_to_list with Status.CURRENT before updating progress
        """
        from services.anime.playback_service import sync_progress_to_anilist
        from models.models import Status

        # Setup: Anime in PLANNING
        mock_entry = MagicMock()
        mock_entry.status = "PLANNING"
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.is_in_any_list.return_value = True
        mock_anilist.get_media_list_entry.return_value = mock_entry
        mock_anilist.add_to_list.return_value = True
        mock_anilist.update_progress.return_value = True
        # Mock get_anime_by_id for validation
        mock_anime = MagicMock()
        mock_anime.episodes = 24
        mock_anilist.get_anime_by_id.return_value = mock_anime

        # Execute
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=1,
            num_episodes=24,
        )

        # Verify status promotion
        assert result is True
        mock_anilist.add_to_list.assert_called_once_with(12345, Status.CURRENT)

    @patch("services.anime.playback_service.anilist_client")
    def test_complete_anime_last_episode(self, mock_anilist):
        """Test 15: Complete Anime (Last Episode).

        Input: Watching last episode (episode=24, num_episodes=24)
        Expected: Calls change_status with Status.COMPLETED after progress update
        """
        from services.anime.playback_service import sync_progress_to_anilist
        from models.models import Status

        # Setup: Last episode
        mock_entry = MagicMock()
        mock_entry.status = "CURRENT"
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.is_in_any_list.return_value = True
        mock_anilist.get_media_list_entry.return_value = mock_entry
        mock_anilist.update_progress.return_value = True
        mock_anilist.change_status.return_value = True
        # Mock get_anime_by_id for validation
        mock_anime = MagicMock()
        mock_anime.episodes = 24
        mock_anilist.get_anime_by_id.return_value = mock_anime

        # Execute: Last episode
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=24,
            num_episodes=24,
        )

        # Verify completion
        assert result is True
        mock_anilist.change_status.assert_called_once_with(12345, Status.COMPLETED)

    @patch("services.anime.playback_service.anilist_client")
    def test_anilist_api_fails(self, mock_anilist):
        """Test 16: AniList API Fails.

        Input: anilist_client.update_progress() raises exception
        Expected: Returns False, error is logged but not raised
        """
        from services.anime.playback_service import sync_progress_to_anilist

        # Setup: API fails
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.is_in_any_list.return_value = True
        mock_anilist.get_media_list_entry.return_value = MagicMock(status="CURRENT")
        mock_anilist.update_progress.side_effect = Exception("API error")

        # Execute - should NOT raise exception
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=5,
            num_episodes=24,
        )

        # Verify graceful failure
        assert result is False


# =============================================================================
# Step 6: Tests for navigate_episodes()
# =============================================================================


class TestNavigateEpisodes:
    """Tests for navigate_episodes function."""

    def test_navigate_to_next_episode(self):
        """Test 17: Navigate to Next Episode.

        Input: episode_idx=0, num_episodes=12, action="next"
        Expected: Returns new PlaybackContext with episode_idx=1
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup: Current context
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=0,
            source="animefire",
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes_anilist=12,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="next")

        # Verify
        assert new_ctx.episode_idx == 1
        # Verify immutability - original unchanged
        assert ctx.episode_idx == 0
        # Verify other fields preserved
        assert new_ctx.anime_title == "Dandadan"
        assert new_ctx.source == "animefire"

    def test_cannot_go_past_last_episode(self):
        """Test 18: Cannot Go Past Last Episode.

        Input: episode_idx=11, num_episodes=12, action="next"
        Expected: Returns same PlaybackContext (no change)
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup: At last episode
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=11,  # Last episode (0-indexed)
            source="animefire",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="next")

        # Verify no change
        assert new_ctx.episode_idx == 11

    def test_navigate_to_previous_episode(self):
        """Test 19: Navigate to Previous Episode.

        Input: episode_idx=5, action="previous"
        Expected: Returns new PlaybackContext with episode_idx=4
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=5,
            source="animefire",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="previous")

        # Verify
        assert new_ctx.episode_idx == 4

    def test_cannot_go_before_first_episode(self):
        """Test: Cannot Go Before First Episode.

        Input: episode_idx=0, action="previous"
        Expected: Returns same PlaybackContext (no change)
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup: At first episode
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=0,
            source="animefire",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="previous")

        # Verify no change
        assert new_ctx.episode_idx == 0

    def test_choose_specific_episode(self):
        """Test 20: Choose Specific Episode.

        Input: episode_idx selected from menu
        Expected: Returns new PlaybackContext with selected episode_idx
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=0,
            source="animefire",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=24,
            episode_list=tuple(f"Ep {i}" for i in range(1, 25)),
        )

        # Execute: Jump to episode 15 (index 14)
        new_ctx = navigate_episodes(ctx, action="choose", target_idx=14)

        # Verify
        assert new_ctx.episode_idx == 14

    def test_replay_current_episode(self):
        """Test: Replay Current Episode.

        Input: action="replay"
        Expected: Returns same episode_idx (replay)
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=5,
            source="animefire",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="replay")

        # Verify same episode
        assert new_ctx.episode_idx == 5

    def test_navigate_preserves_all_context_fields(self):
        """Test: Navigation preserves all other context fields.

        Input: Navigate to next episode
        Expected: All fields except episode_idx are preserved
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        # Setup: Full context
        ctx = PlaybackContext(
            anime_title="Dandadan",
            episode_idx=5,
            source="animefire",
            anilist_id=12345,
            anilist_title="Dandadan (Romaji)",
            total_episodes_anilist=24,
            num_episodes=24,
            episode_list=tuple(f"Ep {i}" for i in range(1, 25)),
        )

        # Execute
        new_ctx = navigate_episodes(ctx, action="next")

        # Verify all other fields preserved
        assert new_ctx.anime_title == ctx.anime_title
        assert new_ctx.source == ctx.source
        assert new_ctx.anilist_id == ctx.anilist_id
        assert new_ctx.anilist_title == ctx.anilist_title
        assert new_ctx.total_episodes_anilist == ctx.total_episodes_anilist
        assert new_ctx.num_episodes == ctx.num_episodes
        assert new_ctx.episode_list == ctx.episode_list
        # Only episode_idx changed
        assert new_ctx.episode_idx == 6


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_empty_episode_list(self, mock_discover, mock_rep):
        """Test: Empty episode list from repository.

        Input: Repository returns empty list
        Expected: PlaybackContext with num_episodes=0, empty episode_list
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup: Empty episode list
        mock_discover.return_value = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=False,
        )
        mock_rep.get_episode_list.return_value = []

        # Execute
        result = prepare_playback_from_search(
            selected_anime="New Anime",
            episode_idx=0,
            source=None,
        )

        # Verify
        assert result is not None
        assert result.num_episodes == 0
        assert result.episode_list == ()

    @patch("services.anime.playback_service.rep")
    @patch("services.anime.playback_service.discover_anilist_info")
    def test_discover_anilist_info_exception(self, mock_discover, mock_rep):
        """Test: discover_anilist_info raises exception.

        Input: discover_anilist_info throws error
        Expected: Graceful handling, returns PlaybackContext without AniList info
        """
        from services.anime.playback_service import prepare_playback_from_search

        # Setup: Exception in discovery
        mock_discover.side_effect = Exception("AniList API down")
        mock_rep.get_episode_list.return_value = ["Ep 1", "Ep 2"]

        # Execute - should NOT raise
        result = prepare_playback_from_search(
            selected_anime="Test Anime",
            episode_idx=0,
            source="animefire",
        )

        # Verify graceful handling
        assert result is not None
        assert result.anilist_id is None
        assert result.anilist_title is None

    @patch("services.anime.playback_service.anilist_client")
    def test_sync_with_unauthenticated_client(self, mock_anilist):
        """Test: Sync when anilist_client is not authenticated.

        Input: anilist_id provided but client not authenticated
        Expected: Returns False, no API calls made
        """
        from services.anime.playback_service import sync_progress_to_anilist

        # Setup: Not authenticated
        mock_anilist.is_authenticated.return_value = False

        # Execute
        result = sync_progress_to_anilist(
            anilist_id=12345,
            episode=5,
            num_episodes=24,
        )

        # Verify no sync
        assert result is False
        mock_anilist.update_progress.assert_not_called()

    def test_navigate_with_invalid_action(self):
        """Test: Navigate with unknown action.

        Input: action="invalid"
        Expected: Returns same context unchanged
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        ctx = PlaybackContext(
            anime_title="Test",
            episode_idx=5,
            source=None,
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=(),
        )

        # Execute with invalid action
        new_ctx = navigate_episodes(ctx, action="invalid")

        # Verify no change
        assert new_ctx.episode_idx == 5

    def test_navigate_choose_out_of_bounds(self):
        """Test: Navigate choose with out-of-bounds target.

        Input: target_idx=100 but only 12 episodes
        Expected: Clamps to last valid episode
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        ctx = PlaybackContext(
            anime_title="Test",
            episode_idx=0,
            source=None,
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute with out-of-bounds target
        new_ctx = navigate_episodes(ctx, action="choose", target_idx=100)

        # Verify clamped to last episode
        assert new_ctx.episode_idx == 11  # Last valid index

    def test_navigate_choose_negative_target(self):
        """Test: Navigate choose with negative target.

        Input: target_idx=-5
        Expected: Clamps to first episode (0)
        """
        from services.anime.playback_service import PlaybackContext, navigate_episodes

        ctx = PlaybackContext(
            anime_title="Test",
            episode_idx=5,
            source=None,
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=12,
            episode_list=tuple(f"Ep {i}" for i in range(1, 13)),
        )

        # Execute with negative target
        new_ctx = navigate_episodes(ctx, action="choose", target_idx=-5)

        # Verify clamped to first episode
        assert new_ctx.episode_idx == 0
