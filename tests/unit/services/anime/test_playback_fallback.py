"""Tests for automatic source fallback during episode playback."""

from unittest.mock import Mock
from services.anime.playback_fallback import (
    play_episode_with_fallback,
    PlaybackFallbackResult,
    MPV_USER_ABORT_CODE,
)
from utils.video_player import VideoPlaybackResult
from models.models import SkipTimes


class TestPlaybackFallbackResult:
    """Test PlaybackFallbackResult NamedTuple."""

    def test_result_creation(self):
        """Test creating a result with all fields."""
        playback_result = VideoPlaybackResult(exit_code=0, action="quit", data=None)
        sources_tried = [("anitube", 2), ("animefire", 0)]

        result = PlaybackFallbackResult(
            playback_result=playback_result,
            source_used="animefire",
            sources_tried=sources_tried,
            all_failed=False,
        )

        assert result.playback_result == playback_result
        assert result.source_used == "animefire"
        assert result.sources_tried == sources_tried
        assert result.all_failed is False


class TestPlayEpisodeWithFallback:
    """Test fallback logic."""

    def create_mock_player(self, exit_codes: list[int]):
        """Create a mock VideoPlayer that returns specified exit codes in sequence."""
        player = Mock()
        results = [
            VideoPlaybackResult(exit_code=code, action="quit", data=None) for code in exit_codes
        ]
        player.play_episode.side_effect = results
        return player

    def test_empty_sources_list(self):
        """Test when no sources are available."""
        player = Mock()
        sources = []

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is True
        assert result.source_used is None
        assert result.sources_tried == []
        assert result.playback_result.exit_code == 2

    def test_first_source_succeeds(self):
        """Test when first source succeeds (exit code 0)."""
        player = self.create_mock_player([0])  # First source succeeds
        sources = [("https://url1.mp4", "anitube"), ("https://url2.mp4", "animefire")]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is False
        assert result.source_used == "anitube"
        assert len(result.sources_tried) == 1
        assert result.sources_tried[0] == ("anitube", 0)
        # play_episode should only be called once
        assert player.play_episode.call_count == 1

    def test_first_source_fails_second_succeeds(self):
        """Test when first source fails but second succeeds."""
        player = self.create_mock_player([2, 0])  # First fails, second succeeds
        sources = [("https://url1.mp4", "anitube"), ("https://url2.mp4", "animefire")]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is False
        assert result.source_used == "animefire"
        assert len(result.sources_tried) == 2
        assert result.sources_tried[0] == ("anitube", 2)
        assert result.sources_tried[1] == ("animefire", 0)
        # play_episode should be called twice
        assert player.play_episode.call_count == 2

    def test_all_sources_fail(self):
        """Test when all sources fail."""
        player = self.create_mock_player([2, 1, 4])  # All fail
        sources = [
            ("https://url1.mp4", "anitube"),
            ("https://url2.mp4", "animefire"),
            ("https://url3.mp4", "animesonlinecc"),
        ]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is True
        assert result.source_used is None
        assert len(result.sources_tried) == 3
        assert result.sources_tried[0] == ("anitube", 2)
        assert result.sources_tried[1] == ("animefire", 1)
        assert result.sources_tried[2] == ("animesonlinecc", 4)

    def test_user_abort_stops_immediately(self):
        """Test that user abort (exit code 3) stops fallback immediately."""
        player = self.create_mock_player([MPV_USER_ABORT_CODE])  # User aborts
        sources = [("https://url1.mp4", "anitube"), ("https://url2.mp4", "animefire")]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        # Should NOT fallback, just return the result
        assert result.all_failed is False
        assert result.source_used == "anitube"
        assert len(result.sources_tried) == 1
        # play_episode should only be called once (no fallback)
        assert player.play_episode.call_count == 1

    def test_action_next_without_fallback(self):
        """Test that actions like 'next' (exit code 0) don't trigger fallback."""
        playback_result = VideoPlaybackResult(exit_code=0, action="next", data={"episode": 2})
        player = Mock()
        player.play_episode.return_value = playback_result
        sources = [("https://url1.mp4", "anitube"), ("https://url2.mp4", "animefire")]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is False
        assert result.source_used == "anitube"
        # Should only try first source
        assert player.play_episode.call_count == 1

    def test_single_source_no_retry_message(self):
        """Test that with single source, fallback progress messages are skipped."""
        player = self.create_mock_player([0])
        sources = [("https://url1.mp4", "anitube")]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
        )

        assert result.all_failed is False
        assert result.source_used == "anitube"
        # player.play_episode should be called with correct arguments
        call_args = player.play_episode.call_args
        assert call_args[1]["url"] == "https://url1.mp4"
        assert call_args[1]["source"] == "anitube"

    def test_skip_times_passed_to_player(self):
        """Test that skip times are properly passed to player.play_episode."""
        player = self.create_mock_player([0])
        sources = [("https://url1.mp4", "anitube")]
        skip_times = SkipTimes(
            id="123", episode=1, intro_start=10, intro_end=30, outro_start=1410, outro_end=1430
        )

        play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
            skip_times=skip_times,
        )

        # Verify skip_times were passed
        call_args = player.play_episode.call_args
        assert call_args[1]["skip_times"] == skip_times

    def test_anilist_params_passed_to_player(self):
        """Test that AniList parameters are properly passed."""
        player = self.create_mock_player([0])
        sources = [("https://url1.mp4", "anitube")]

        play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=5,
            total_episodes=12,
            anilist_id=12345,
            anilist_episodes=13,
        )

        call_args = player.play_episode.call_args
        assert call_args[1]["anilist_id"] == 12345
        assert call_args[1]["anilist_episodes"] == 13
        assert call_args[1]["episode_number"] == 5


class TestPlayEpisodeWithFallbackIntegration:
    """Integration tests for fallback flow."""

    def test_fallback_with_three_sources_two_fail(self):
        """Test realistic scenario: 3 sources, first 2 fail, 3rd succeeds."""
        player = Mock()
        # Simulate: anitube fails (403), animefire fails (timeout), animesonlinecc succeeds
        player.play_episode.side_effect = [
            VideoPlaybackResult(exit_code=2, action="quit", data=None),  # anitube fails
            VideoPlaybackResult(exit_code=2, action="quit", data=None),  # animefire fails
            VideoPlaybackResult(exit_code=0, action="quit", data=None),  # animesonlinecc succeeds
        ]

        sources = [
            ("https://anitube.com/video", "anitube"),
            ("https://animefire.com/video", "animefire"),
            ("https://animesonlinecc.com/video", "animesonlinecc"),
        ]

        result = play_episode_with_fallback(
            player=player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=11,
            total_episodes=12,
            anilist_id=9999,
        )

        assert result.all_failed is False
        assert result.source_used == "animesonlinecc"
        assert len(result.sources_tried) == 3
        assert player.play_episode.call_count == 3
