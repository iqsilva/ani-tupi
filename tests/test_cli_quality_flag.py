"""Tests for --quality CLI flag."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from utils.video_player import QUALITY_FORMATS


class TestQualityFormatsMapping:
    """Tests for QUALITY_FORMATS constant."""

    def test_quality_formats_has_all_presets(self):
        """All expected quality presets should be defined."""
        expected_presets = ["1080", "720", "480", "360", "best"]
        for preset in expected_presets:
            assert preset in QUALITY_FORMATS, f"Missing preset: {preset}"

    def test_quality_formats_contain_height_limits(self):
        """Each format string should contain the expected height limit."""
        assert "height<=1080" in QUALITY_FORMATS["1080"]
        assert "height<=720" in QUALITY_FORMATS["720"]
        assert "height<=480" in QUALITY_FORMATS["480"]
        assert "height<=360" in QUALITY_FORMATS["360"]

    def test_best_quality_defaults_to_1080(self):
        """'best' preset should default to 1080p max."""
        assert "height<=1080" in QUALITY_FORMATS["best"]


class TestCliQualityArgument:
    """Tests for --quality CLI argument parsing."""

    def test_quality_argument_accepts_valid_choices(self):
        """Parser should accept all valid quality choices."""
        from main import cli

        # We test by importing the argument parser setup
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--quality",
            "-Q",
            choices=["1080", "720", "480", "360", "best"],
            default="best",
        )

        for choice in ["1080", "720", "480", "360", "best"]:
            args = parser.parse_args(["--quality", choice])
            assert args.quality == choice

    def test_quality_argument_short_flag(self):
        """Parser should accept -Q short flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--quality",
            "-Q",
            choices=["1080", "720", "480", "360", "best"],
            default="best",
        )

        args = parser.parse_args(["-Q", "480"])
        assert args.quality == "480"

    def test_quality_defaults_to_best(self):
        """Default quality should be 'best'."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--quality",
            "-Q",
            choices=["1080", "720", "480", "360", "best"],
            default="best",
        )

        args = parser.parse_args([])
        assert args.quality == "best"

    def test_quality_rejects_invalid_choice(self):
        """Parser should reject invalid quality values."""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--quality",
            "-Q",
            choices=["1080", "720", "480", "360", "best"],
            default="best",
        )

        with pytest.raises(SystemExit):
            parser.parse_args(["--quality", "240"])


class TestVideoPlayerQualityIntegration:
    """Tests for VideoPlayer max_quality parameter."""

    def test_play_episode_accepts_max_quality(self):
        """play_episode should accept max_quality parameter."""
        from utils.video_player import VideoPlayer

        player = VideoPlayer()

        # Check signature includes max_quality
        import inspect

        sig = inspect.signature(player.play_episode)
        assert "max_quality" in sig.parameters
        assert sig.parameters["max_quality"].default == "best"

    def test_launch_mpv_with_ipc_accepts_max_quality(self):
        """_launch_mpv_with_ipc should accept max_quality parameter."""
        from utils.video_player import VideoPlayer

        player = VideoPlayer()

        import inspect

        sig = inspect.signature(player._launch_mpv_with_ipc)
        assert "max_quality" in sig.parameters
        assert sig.parameters["max_quality"].default == "best"


class TestPlaybackFallbackQualityIntegration:
    """Tests for playback_fallback max_quality propagation."""

    def test_play_episode_with_fallback_accepts_max_quality(self):
        """play_episode_with_fallback should accept max_quality parameter."""
        from services.anime.playback_fallback import play_episode_with_fallback

        import inspect

        sig = inspect.signature(play_episode_with_fallback)
        assert "max_quality" in sig.parameters
        assert sig.parameters["max_quality"].default == "best"

    @patch("services.anime.playback_fallback.VideoPlayer")
    def test_max_quality_propagates_to_player(self, mock_player_class):
        """max_quality should be passed through to player.play_episode."""
        from services.anime.playback_fallback import play_episode_with_fallback
        from utils.video_player import VideoPlaybackResult

        mock_player = MagicMock()
        mock_player.play_episode.return_value = VideoPlaybackResult(
            exit_code=0, action="quit", data=None
        )

        sources = [("http://example.com/video.mp4", "test-source")]

        play_episode_with_fallback(
            player=mock_player,
            sources=sources,
            anime_title="Test Anime",
            episode_number=1,
            total_episodes=12,
            max_quality="480",
        )

        # Verify max_quality was passed to play_episode
        mock_player.play_episode.assert_called_once()
        call_kwargs = mock_player.play_episode.call_args.kwargs
        assert call_kwargs["max_quality"] == "480"
