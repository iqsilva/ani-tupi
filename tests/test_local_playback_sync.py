"""Tests for local anime library playback, history tracking, and AniList sync.

Tests the complete flow of local episode playback including:
- Phase 1: Local history tracking (regardless of AniList sync)
- Phase 2: Interactive discovery for local titles
- Phase 3: Independent file deletion config
- Phase 4: File deletion logic independent from sync success
"""

from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.anilist_discovery import get_anilist_id_with_interactive_fallback
from models.config import settings


class TestPhase1LocalHistoryTracking:
    """Phase 1: Always save local history (including local episodes)."""

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.save_history")
    def test_save_history_for_local_episodes(self, mock_save, mock_menu):
        """Local episodes should be saved to history."""
        from commands.anime import handle_post_playback_confirmation

        # User confirms watching until end
        mock_menu.return_value = "✅ Sim, assisti até o final"

        result = handle_post_playback_confirmation(
            anime_title="Chainsaw Man Dublado",
            episode_number=5,
            num_episodes=12,
            anilist_id=None,  # No AniList match
            source=None,
            is_local=True,
            file_path=Path("/home/user/.local/share/ani-tupi/anime/Chainsaw Man Dublado/5.mkv"),
        )

        # Confirm user watched until end
        assert result is True

        # Verify history was saved for local episode
        mock_save.assert_called_once()
        # Check positional args: save_history(anime, episode, anilist_id, source, total_episodes)
        call_args = mock_save.call_args[0]
        assert call_args[0] == "Chainsaw Man Dublado"  # anime
        assert call_args[1] == 4  # episode (0-indexed)
        assert call_args[2] is None  # anilist_id
        assert call_args[3] == "local"  # source

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.sync_progress_to_anilist")
    @patch("commands.anime.save_history")
    def test_save_history_with_anilist_id_local(self, mock_save, mock_sync, mock_menu):
        """Local episodes with anilist_id should save history with that ID."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"
        mock_sync.return_value = True

        result = handle_post_playback_confirmation(
            anime_title="Dandadan",
            episode_number=10,
            num_episodes=25,
            anilist_id=123456,  # Found via discovery
            source="local",
            is_local=True,
            file_path=Path("/home/user/.local/share/ani-tupi/anime/Dandadan/10.mkv"),
        )

        assert result is True

        # Verify history was saved with anilist_id
        mock_save.assert_called_once()
        call_args = mock_save.call_args[0]
        assert call_args[2] == 123456  # anilist_id
        assert call_args[3] == "local"  # source

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.save_history")
    def test_history_marked_as_local_source(self, mock_save, mock_menu):
        """History for local episodes should be marked with source='local'."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"

        handle_post_playback_confirmation(
            anime_title="Jujutsu Kaisen",
            episode_number=1,
            num_episodes=24,
            anilist_id=None,
            source=None,  # No source provided
            is_local=True,
            file_path=Path("/some/path/1.mkv"),
        )

        # Verify source is marked as "local"
        mock_save.assert_called_once()
        call_args = mock_save.call_args[0]
        assert call_args[3] == "local"  # source arg at index 3


class TestPhase2InteractiveDiscovery:
    """Phase 2: Interactive discovery for local titles (below 95% threshold)."""

    @patch("utils.anilist_discovery.auto_discover_anilist_id")
    def test_automatic_match_above_threshold(self, mock_discover):
        """Matches >= 95% should be used automatically."""
        from models.models import AniListSearchResult

        mock_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=98, title="Dandadan"),
        ]

        result = get_anilist_id_with_interactive_fallback(
            "Dandadan",
            strict_threshold=95,
        )

        assert result == 12345

    @patch("ui.components.menu_navigate")
    @patch("utils.anilist_discovery.auto_discover_anilist_id")
    def test_interactive_list_below_threshold(self, mock_discover, mock_menu):
        """Matches < 95% should show interactive list."""
        from models.models import AniListSearchResult

        mock_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=85, title="Chainsaw Man"),
            AniListSearchResult(anilist_id=54321, score=80, title="Chainsaw Man Dublado"),
            AniListSearchResult(anilist_id=99999, score=75, title="Chainsaws"),
        ]
        # User selects second option
        mock_menu.return_value = "Chainsaw Man Dublado (80%)"

        result = get_anilist_id_with_interactive_fallback(
            "Chainsaw Man Dublado",
            strict_threshold=95,
        )

        assert result == 54321
        mock_menu.assert_called_once()

    @patch("services.anilist_service.anilist_client")
    @patch("utils.anilist_discovery.get_cache")
    @patch("ui.components.menu_navigate")
    @patch("utils.anilist_discovery.auto_discover_anilist_id")
    def test_cache_user_selection(self, mock_discover, mock_menu, mock_cache_fn, mock_anilist):
        """User's selection should be cached for future episodes."""
        from models.models import AniListSearchResult

        mock_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=85, title="Jujutsu Kaisen"),
        ]
        mock_menu.return_value = "Jujutsu Kaisen (85%)"

        mock_cache = MagicMock()
        mock_cache_fn.return_value = mock_cache

        # Mock anime existence check
        mock_anime = MagicMock()
        mock_anime.title.romaji = "Jujutsu Kaisen"
        mock_anime.episodes = 24
        mock_anilist.get_anime_by_id.return_value = mock_anime

        get_anilist_id_with_interactive_fallback(
            "Jujutsu Kaisen",
            strict_threshold=95,
        )

        # Verify cache was updated with 30-day TTL
        mock_cache.set.assert_called_once()
        # cache.set() is called, check the arguments
        called_args = mock_cache.set.call_args
        cache_key = called_args[0][0]
        cached_value = called_args[0][1]
        # TTL could be in args[2] or in kwargs['ttl']
        ttl = called_args[0][2] if len(called_args[0]) > 2 else called_args[1].get("ttl")

        assert cache_key == "anilist_id:jujutsu kaisen"
        assert len(cached_value) > 0
        assert ttl == 2592000  # 30 days

    @patch("utils.anilist_discovery.auto_discover_anilist_id")
    def test_no_matches_returns_none(self, mock_discover):
        """No matches should return None."""
        mock_discover.return_value = []

        result = get_anilist_id_with_interactive_fallback(
            "Nonexistent Anime ZZZZ",
            strict_threshold=95,
        )

        assert result is None

    @patch("ui.components.menu_navigate")
    @patch("utils.anilist_discovery.auto_discover_anilist_id")
    def test_user_skips_selection(self, mock_discover, mock_menu):
        """User selecting 'Nenhuma das opções' should return None."""
        from models.models import AniListSearchResult

        mock_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=75, title="Random Anime"),
        ]
        mock_menu.return_value = "⏭️  Nenhuma das opções (pular sync)"

        result = get_anilist_id_with_interactive_fallback(
            "Unknown Title",
            strict_threshold=95,
        )

        assert result is None


class TestPhase3DeleteAfterWatchConfig:
    """Phase 3: New config option for independent file deletion."""

    def test_delete_after_watch_config_exists(self):
        """delete_after_watch config option should exist in OfflineSyncConfig."""
        assert hasattr(settings.offline_sync, "delete_after_watch")
        assert isinstance(settings.offline_sync.delete_after_watch, bool)

    def test_delete_after_watch_default_true(self):
        """delete_after_watch should default to True (automatic cleanup)."""
        assert settings.offline_sync.delete_after_watch is True

    def test_enable_file_cleanup_still_exists(self):
        """Existing enable_file_cleanup config should still exist (sync-based deletion)."""
        assert hasattr(settings.offline_sync, "enable_file_cleanup")
        assert isinstance(settings.offline_sync.enable_file_cleanup, bool)


class TestPhase4IndependentDeletion:
    """Phase 4: File deletion independent from AniList sync success."""

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.sync_progress_to_anilist")
    @patch("commands.anime.save_history")
    def test_delete_after_successful_sync_if_configured(self, mock_save, mock_sync, mock_menu):
        """Files should delete after successful sync if enable_file_cleanup=True."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"
        mock_sync.return_value = True

        mock_service = MagicMock()
        mock_service.delete_episode.return_value = True

        with patch("models.config.settings") as mock_settings:
            mock_settings.offline_sync.enable_file_cleanup = True
            mock_settings.offline_sync.delete_after_watch = False

            with patch(
                "services.local_anime_service.LocalAnimeService",
                return_value=mock_service,
            ):
                handle_post_playback_confirmation(
                    anime_title="Dandadan",
                    episode_number=5,
                    num_episodes=12,
                    anilist_id=123456,
                    source="animefire",
                    is_local=True,
                    file_path=Path("/home/user/.local/share/ani-tupi/anime/Dandadan/5.mkv"),
                )

                # Verify delete was called
                mock_service.delete_episode.assert_called_once_with("Dandadan", 5)

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.sync_progress_to_anilist")
    @patch("commands.anime.save_history")
    def test_delete_after_watch_even_if_no_anilist_id(self, mock_save, mock_sync, mock_menu):
        """Files should delete based on delete_after_watch even without anilist_id."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"

        mock_service = MagicMock()
        mock_service.delete_episode.return_value = True

        with patch("models.config.settings") as mock_settings:
            mock_settings.offline_sync.delete_after_watch = True
            mock_settings.offline_sync.enable_file_cleanup = False

            with patch(
                "services.local_anime_service.LocalAnimeService",
                return_value=mock_service,
            ):
                # No anilist_id - discovery failed
                handle_post_playback_confirmation(
                    anime_title="Chainsaw Man Dublado",
                    episode_number=5,
                    num_episodes=12,
                    anilist_id=None,  # No AniList match
                    source=None,
                    is_local=True,
                    file_path=Path(
                        "/home/user/.local/share/ani-tupi/anime/Chainsaw Man Dublado/5.mkv"
                    ),
                )

                # Verify delete was called (via new delete_after_watch logic)
                mock_service.delete_episode.assert_called_once_with("Chainsaw Man Dublado", 5)


class TestCompleteLocalPlaybackFlow:
    """Integration tests for complete local playback flow."""

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.sync_progress_to_anilist")
    @patch("commands.anime.save_history")
    def test_local_episode_saved_to_history_only(self, mock_save, mock_sync, mock_menu):
        """Local episode with no AniList match should be saved to history only."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"

        mock_service = MagicMock()
        mock_service.delete_episode.return_value = False  # No deletion

        with patch("models.config.settings") as mock_settings:
            mock_settings.offline_sync.delete_after_watch = False
            mock_settings.offline_sync.enable_file_cleanup = False

            with patch(
                "services.local_anime_service.LocalAnimeService",
                return_value=mock_service,
            ):
                result = handle_post_playback_confirmation(
                    anime_title="Unknown Title",
                    episode_number=1,
                    num_episodes=12,
                    anilist_id=None,
                    source=None,
                    is_local=True,
                    file_path=Path("/home/user/.local/share/ani-tupi/anime/Unknown Title/1.mkv"),
                )

                assert result is True

                # Verify history was saved
                mock_save.assert_called_once()

                # Verify sync was NOT attempted
                mock_sync.assert_not_called()

                # Verify delete was NOT called
                mock_service.delete_episode.assert_not_called()

    @patch("commands.anime.menu_navigate")
    @patch("commands.anime.sync_progress_to_anilist")
    @patch("commands.anime.save_history")
    def test_local_episode_full_flow_with_sync_and_delete(self, mock_save, mock_sync, mock_menu):
        """Complete flow: save history, sync AniList, delete file."""
        from commands.anime import handle_post_playback_confirmation

        mock_menu.return_value = "✅ Sim, assisti até o final"
        mock_sync.return_value = True

        mock_service = MagicMock()
        mock_service.delete_episode.return_value = True

        with patch("models.config.settings") as mock_settings:
            mock_settings.offline_sync.delete_after_watch = True
            mock_settings.offline_sync.enable_file_cleanup = True

            with patch(
                "services.local_anime_service.LocalAnimeService",
                return_value=mock_service,
            ):
                result = handle_post_playback_confirmation(
                    anime_title="Dandadan",
                    episode_number=5,
                    num_episodes=12,
                    anilist_id=123456,
                    source="local",
                    is_local=True,
                    file_path=Path("/home/user/.local/share/ani-tupi/anime/Dandadan/5.mkv"),
                )

                assert result is True

                # Verify all steps happened
                mock_save.assert_called_once()
                mock_sync.assert_called_once()
                mock_service.delete_episode.assert_called_once()
