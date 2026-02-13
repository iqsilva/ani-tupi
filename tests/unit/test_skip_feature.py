"""Tests for the skip times feature integration."""

import pytest
from commands.anime import format_episode_list_with_skip, format_playback_menu_option
from services.anime.playback_service import PlaybackContext


class TestFormatEpisodeListWithSkip:
    """Test the episode list formatting with skip time indicators."""

    def test_format_with_mixed_skip_availability(self):
        """Test formatting with both skip and non-skip episodes."""
        episodes = ("Ep. 1", "Ep. 2", "Ep. 3", "Ep. 4", "Ep. 5")
        skip_available = {1: True, 2: False, 3: True, 4: False, 5: True}

        result = format_episode_list_with_skip(episodes, skip_available)

        assert result[0] == "Ep. 1 ⏭️ (skip)"
        assert result[1] == "Ep. 2"
        assert result[2] == "Ep. 3 ⏭️ (skip)"
        assert result[3] == "Ep. 4"
        assert result[4] == "Ep. 5 ⏭️ (skip)"

    def test_format_with_no_skip_available(self):
        """Test formatting when no skip times are available."""
        episodes = ("Ep. 1", "Ep. 2", "Ep. 3")
        skip_available = {}

        result = format_episode_list_with_skip(episodes, skip_available)

        assert result == ["Ep. 1", "Ep. 2", "Ep. 3"]

    def test_format_with_all_skip_available(self):
        """Test formatting when all episodes have skip times."""
        episodes = ("Ep. 1", "Ep. 2", "Ep. 3")
        skip_available = {1: True, 2: True, 3: True}

        result = format_episode_list_with_skip(episodes, skip_available)

        assert all("⏭️ (skip)" in ep for ep in result)

    def test_format_empty_list(self):
        """Test formatting empty episode list."""
        episodes = ()
        skip_available = {}

        result = format_episode_list_with_skip(episodes, skip_available)

        assert result == []

    def test_format_single_episode(self):
        """Test formatting single episode."""
        episodes = ("Ep. 1",)
        skip_available = {1: True}

        result = format_episode_list_with_skip(episodes, skip_available)

        assert result == ["Ep. 1 ⏭️ (skip)"]

    def test_format_preserves_order(self):
        """Test that formatting preserves episode order."""
        episodes = ("Ep. 1", "Ep. 2", "Ep. 3", "Ep. 4", "Ep. 5")
        skip_available = {2: True, 4: True}

        result = format_episode_list_with_skip(episodes, skip_available)

        # Check order is preserved
        assert "Ep. 1" in result[0]
        assert "Ep. 2" in result[1]
        assert "Ep. 3" in result[2]
        assert "Ep. 4" in result[3]
        assert "Ep. 5" in result[4]


class TestFormatPlaybackMenuOption:
    """Test formatting of playback menu options with skip indicators."""

    def test_format_menu_option_with_skip(self):
        """Test menu option when episode has skip times."""
        result = format_playback_menu_option("▶️  Próximo", 5, {5: True})
        assert result == "▶️  Próximo ⏭️"

    def test_format_menu_option_without_skip(self):
        """Test menu option when episode has no skip times."""
        result = format_playback_menu_option("▶️  Próximo", 5, {5: False})
        assert result == "▶️  Próximo"

    def test_format_menu_option_missing_episode(self):
        """Test menu option when episode is not in skip dict."""
        result = format_playback_menu_option("◀️  Anterior", 3, {})
        assert result == "◀️  Anterior"

    def test_format_replay_with_skip(self):
        """Test replay menu option with skip indicator."""
        result = format_playback_menu_option("🔁 Replay", 7, {7: True})
        assert result == "🔁 Replay ⏭️"

    def test_format_multiple_options(self):
        """Test formatting multiple menu options."""
        skip_available = {1: True, 2: False, 3: True}

        next_opt = format_playback_menu_option("▶️  Próximo", 2, skip_available)
        prev_opt = format_playback_menu_option("◀️  Anterior", 1, skip_available)
        replay_opt = format_playback_menu_option("🔁 Replay", 3, skip_available)

        assert next_opt == "▶️  Próximo"  # ep 2 has no skip
        assert prev_opt == "◀️  Anterior ⏭️"  # ep 1 has skip
        assert replay_opt == "🔁 Replay ⏭️"  # ep 3 has skip


class TestPlaybackContextWithSkipData:
    """Test PlaybackContext with skip time data."""

    def test_context_with_skip_data(self):
        """Test PlaybackContext can store skip data."""
        ctx = PlaybackContext(
            anime_title="Test Anime",
            episode_idx=0,
            source="test_source",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=3,
            episode_list=("Ep. 1", "Ep. 2", "Ep. 3"),
            skip_enabled=False,
            mal_id=12345,
            episode_skip_available={1: True, 2: False, 3: True},
        )

        assert ctx.episode_skip_available == {1: True, 2: False, 3: True}
        assert ctx.mal_id == 12345
        assert ctx.num_episodes == 3

    def test_context_skip_data_none_defaults_to_empty_dict(self):
        """Test PlaybackContext with None skip data defaults to empty dict."""
        ctx = PlaybackContext(
            anime_title="Test Anime",
            episode_idx=0,
            source="test_source",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=3,
            episode_list=("Ep. 1", "Ep. 2", "Ep. 3"),
            skip_enabled=False,
            mal_id=12345,
            episode_skip_available=None,
        )

        assert ctx.episode_skip_available == {}

    def test_context_frozen_immutability(self):
        """Test that PlaybackContext is frozen and immutable."""
        ctx = PlaybackContext(
            anime_title="Test Anime",
            episode_idx=0,
            source="test_source",
            anilist_id=None,
            anilist_title=None,
            total_episodes_anilist=None,
            num_episodes=3,
            episode_list=("Ep. 1", "Ep. 2", "Ep. 3"),
            skip_enabled=False,
            mal_id=12345,
            episode_skip_available={1: True},
        )

        # Should raise because dataclass is frozen
        with pytest.raises(AttributeError):
            ctx.episode_skip_available = {2: True}
