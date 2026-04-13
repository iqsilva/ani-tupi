"""Tests for season selection functionality.

Tests cover:
- Season filtering and organization
- Season validation
- Integration with search and playback flows
"""

import pytest
from models.models import EpisodeData
from services.anime.season_service import (
    organize_episodes_by_season,
    get_available_seasons,
    filter_episodes_by_season,
    validate_season_exists,
    count_episodes_in_season,
)


class TestSeasonService:
    """Tests for season_service functions."""

    @pytest.fixture
    def sample_episodes(self):
        """Create sample episodes for testing."""
        return [
            EpisodeData(
                anime_title="Test Anime",
                episode_titles=["Ep 1", "Ep 2"],
                episode_urls=["http://ex.com/1", "http://ex.com/2"],
                source="source1",
                season=1,
            ),
            EpisodeData(
                anime_title="Test Anime",
                episode_titles=["Ep 3", "Ep 4"],
                episode_urls=["http://ex.com/3", "http://ex.com/4"],
                source="source1",
                season=2,
            ),
        ]

    def test_organize_episodes_by_season(self, sample_episodes):
        """Test organizing episodes by season."""
        organized = organize_episodes_by_season(sample_episodes)
        assert 1 in organized
        assert 2 in organized
        assert len(organized[1]) == 1
        assert len(organized[2]) == 1

    def test_get_available_seasons(self, sample_episodes):
        """Test extracting available seasons."""
        seasons = get_available_seasons(sample_episodes)
        assert seasons == [1, 2]

    def test_get_available_seasons_single(self):
        """Test extracting seasons with single season."""
        episodes = [
            EpisodeData(
                anime_title="Test",
                episode_titles=["Ep 1"],
                episode_urls=["http://ex.com/1"],
                source="source1",
                season=1,
            ),
        ]
        seasons = get_available_seasons(episodes)
        assert seasons == [1]

    def test_filter_episodes_by_season(self, sample_episodes):
        """Test filtering episodes by season."""
        filtered = filter_episodes_by_season(sample_episodes, 1)
        assert len(filtered) == 1
        assert filtered[0].season == 1

    def test_filter_episodes_by_season_not_found(self, sample_episodes):
        """Test filtering with non-existent season raises error."""
        with pytest.raises(ValueError, match="Season 3 not found"):
            filter_episodes_by_season(sample_episodes, 3)

    def test_filter_episodes_invalid_season_number(self, sample_episodes):
        """Test filtering with invalid season number raises error."""
        with pytest.raises(ValueError, match="Season number must be positive"):
            filter_episodes_by_season(sample_episodes, 0)

    def test_validate_season_exists(self, sample_episodes):
        """Test season existence validation."""
        assert validate_season_exists(sample_episodes, 1) is True
        assert validate_season_exists(sample_episodes, 2) is True
        assert validate_season_exists(sample_episodes, 3) is False

    def test_count_episodes_in_season(self, sample_episodes):
        """Test counting episodes in a season."""
        count = count_episodes_in_season(sample_episodes, 1)
        assert count == 1
        count = count_episodes_in_season(sample_episodes, 2)
        assert count == 1
        count = count_episodes_in_season(sample_episodes, 3)
        assert count == 0


class TestEpisodeDataSeasonField:
    """Tests for season field in EpisodeData model."""

    def test_episode_data_default_season(self):
        """Test that season defaults to 1."""
        ep = EpisodeData(
            anime_title="Test",
            episode_titles=["Ep 1"],
            episode_urls=["http://ex.com/1"],
            source="test",
        )
        assert ep.season == 1

    def test_episode_data_custom_season(self):
        """Test setting custom season number."""
        ep = EpisodeData(
            anime_title="Test",
            episode_titles=["Ep 1"],
            episode_urls=["http://ex.com/1"],
            source="test",
            season=2,
        )
        assert ep.season == 2

    def test_episode_data_invalid_season(self):
        """Test that invalid season raises validation error."""
        with pytest.raises(ValueError):
            EpisodeData(
                anime_title="Test",
                episode_titles=["Ep 1"],
                episode_urls=["http://ex.com/1"],
                source="test",
                season=0,  # Invalid: must be positive
            )

    def test_episode_data_season_boundary(self):
        """Test season field with boundary values."""
        # Season 1 should work
        ep = EpisodeData(
            anime_title="Test",
            episode_titles=["Ep 1"],
            episode_urls=["http://ex.com/1"],
            source="test",
            season=1,
        )
        assert ep.season == 1

        # Large season number should work
        ep = EpisodeData(
            anime_title="Test",
            episode_titles=["Ep 1"],
            episode_urls=["http://ex.com/1"],
            source="test",
            season=10,
        )
        assert ep.season == 10


class TestSeasonIntegration:
    """Integration tests for season functionality."""

    def test_single_season_anime_no_menu(self):
        """Test that single-season anime doesn't show menu."""
        episodes = [
            EpisodeData(
                anime_title="Test",
                episode_titles=[f"Ep {i}" for i in range(1, 13)],
                episode_urls=[f"http://ex.com/{i}" for i in range(1, 13)],
                source="source1",
                season=1,
            ),
        ]
        seasons = get_available_seasons(episodes)
        assert len(seasons) == 1

    def test_multi_season_anime_show_menu(self):
        """Test that multi-season anime triggers menu."""
        episodes = [
            EpisodeData(
                anime_title="Test",
                episode_titles=[f"Ep {i}" for i in range(1, 13)],
                episode_urls=[f"http://ex.com/s1/{i}" for i in range(1, 13)],
                source="source1",
                season=1,
            ),
            EpisodeData(
                anime_title="Test",
                episode_titles=[f"Ep {i}" for i in range(1, 14)],
                episode_urls=[f"http://ex.com/s2/{i}" for i in range(1, 14)],
                source="source1",
                season=2,
            ),
        ]
        seasons = get_available_seasons(episodes)
        assert len(seasons) == 2
        assert 1 in seasons
        assert 2 in seasons
