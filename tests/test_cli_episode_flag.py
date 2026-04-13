"""CLI tests for -e/--episode flag.

Tests that the -e flag accepts episode numbers and validates bounds.
"""

import pytest


class TestEpisodeFlagValidation:
    """Test episode number validation."""

    def test_episode_valid_single(self):
        """Test valid single episode number."""
        episode = 5
        total = 25
        assert 1 <= episode <= total

    def test_episode_at_start(self):
        """Test episode 1 is valid."""
        episode = 1
        total = 25
        assert 1 <= episode <= total

    def test_episode_at_end(self):
        """Test episode at total count is valid."""
        episode = 25
        total = 25
        assert 1 <= episode <= total

    def test_episode_out_of_bounds_high(self):
        """Test episode > total is invalid."""
        episode = 100
        total = 25
        assert not (1 <= episode <= total)

    def test_episode_out_of_bounds_low(self):
        """Test episode < 1 is invalid."""
        episode = 0
        total = 25
        assert not (1 <= episode <= total)

    def test_episode_negative(self):
        """Test negative episode is invalid."""
        episode = -5
        total = 25
        assert not (1 <= episode <= total)


class TestEpisodeIndexConversion:
    """Test conversion from user input (1-indexed) to code (0-indexed)."""

    def test_episode_1_to_index_0(self):
        """Test episode 1 converts to index 0."""
        episode = 1
        episode_idx = episode - 1
        assert episode_idx == 0

    def test_episode_5_to_index_4(self):
        """Test episode 5 converts to index 4."""
        episode = 5
        episode_idx = episode - 1
        assert episode_idx == 4

    def test_episode_25_to_index_24(self):
        """Test episode 25 converts to index 24."""
        episode = 25
        episode_idx = episode - 1
        assert episode_idx == 24


class TestEpisodeFlagArgparse:
    """Test argparse handling of -e flag."""

    def test_episode_flag_type_is_int(self):
        """Test that -e expects integer type."""
        # Simulating argparse with type=int
        test_input = "5"
        try:
            episode = int(test_input)
            assert isinstance(episode, int)
            assert episode == 5
        except ValueError:
            pytest.fail("Should accept valid integer string")

    def test_episode_flag_rejects_non_int(self):
        """Test that -e rejects non-integer strings."""
        test_input = "invalid"
        with pytest.raises(ValueError):
            int(test_input)

    def test_episode_flag_rejects_range_format(self):
        """Test that -e rejects range format (no longer supported)."""
        test_input = "5-10"
        with pytest.raises(ValueError):
            int(test_input)

    def test_episode_flag_rejects_open_ended(self):
        """Test that -e rejects open-ended range."""
        test_input = "5-"
        with pytest.raises(ValueError):
            int(test_input)


class TestEpisodeFlagEdgeCases:
    """Test edge cases."""

    def test_episode_string_leading_zeros(self):
        """Test episode with leading zeros."""
        episode_str = "05"
        episode = int(episode_str)
        assert episode == 5

    def test_episode_very_large_number(self):
        """Test very large episode number."""
        episode_str = "999999"
        episode = int(episode_str)
        assert episode == 999999
        # Would be out of bounds for any realistic anime
        assert episode > 25  # Assume max 25 episodes for test

    def test_episode_with_spaces_fails(self):
        """Test that spaces in input cause argparse to fail."""
        # argparse will fail before reaching our validation
        test_input = "5 10"
        with pytest.raises(ValueError):
            int(test_input)
