"""Tests for RecentEpisodeData and RecentEpisodeMatch models.

Tests cover:
- Model instantiation with valid data
- Field validation (invalid URLs, episode numbers)
- Serialization/deserialization
"""

from datetime import datetime

import pytest

from models.models import RecentEpisodeData, RecentEpisodeMatch


class TestRecentEpisodeData:
    """Tests for RecentEpisodeData model."""

    def test_valid_instantiation(self):
        """Test creating RecentEpisodeData with valid data."""
        data = RecentEpisodeData(
            anime_title="Jujutsu Kaisen Season 2",
            episode_number=25,
            episode_url="https://animesdigital.org/video/a/12345/",
        )

        assert data.anime_title == "Jujutsu Kaisen Season 2"
        assert data.episode_number == 25
        assert data.episode_url == "https://animesdigital.org/video/a/12345/"
        assert data.source == "animesdigital"
        assert isinstance(data.fetched_at, datetime)

    def test_invalid_episode_number_zero(self):
        """Test that episode_number must be > 0."""
        with pytest.raises(ValueError):
            RecentEpisodeData(
                anime_title="Test Anime",
                episode_number=0,
                episode_url="https://animesdigital.org/video/a/123/",
            )

    def test_invalid_episode_number_negative(self):
        """Test that episode_number must be > 0."""
        with pytest.raises(ValueError):
            RecentEpisodeData(
                anime_title="Test Anime",
                episode_number=-5,
                episode_url="https://animesdigital.org/video/a/123/",
            )

    def test_invalid_url_http(self):
        """Test that URLs must start with http:// or https://."""
        with pytest.raises(ValueError, match="must be http\\(s\\)"):
            RecentEpisodeData(
                anime_title="Test Anime",
                episode_number=5,
                episode_url="ftp://animesdigital.org/video/a/123/",
            )

    def test_invalid_url_no_protocol(self):
        """Test that URLs must have protocol."""
        with pytest.raises(ValueError, match="must be http\\(s\\)"):
            RecentEpisodeData(
                anime_title="Test Anime",
                episode_number=5,
                episode_url="animesdigital.org/video/a/123/",
            )

    def test_empty_anime_title(self):
        """Test that anime_title cannot be empty."""
        with pytest.raises(ValueError):
            RecentEpisodeData(
                anime_title="",
                episode_number=5,
                episode_url="https://animesdigital.org/video/a/123/",
            )

    def test_empty_episode_url(self):
        """Test that episode_url cannot be empty."""
        with pytest.raises(ValueError):
            RecentEpisodeData(
                anime_title="Test Anime",
                episode_number=5,
                episode_url="",
            )

    def test_custom_source(self):
        """Test that source can be customized."""
        data = RecentEpisodeData(
            anime_title="Test Anime",
            episode_number=5,
            episode_url="https://animesdigital.org/video/a/123/",
            source="custom_source",
        )

        assert data.source == "custom_source"

    def test_custom_fetched_at(self):
        """Test that fetched_at can be customized."""
        now = datetime(2025, 2, 5, 12, 0, 0)
        data = RecentEpisodeData(
            anime_title="Test Anime",
            episode_number=5,
            episode_url="https://animesdigital.org/video/a/123/",
            fetched_at=now,
        )

        assert data.fetched_at == now

    def test_serialization(self):
        """Test model serialization to dict."""
        data = RecentEpisodeData(
            anime_title="Jujutsu Kaisen",
            episode_number=25,
            episode_url="https://animesdigital.org/video/a/123/",
        )

        dumped = data.model_dump()
        assert dumped["anime_title"] == "Jujutsu Kaisen"
        assert dumped["episode_number"] == 25
        assert dumped["episode_url"] == "https://animesdigital.org/video/a/123/"
        assert dumped["source"] == "animesdigital"

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data_dict = {
            "anime_title": "Dandadan",
            "episode_number": 18,
            "episode_url": "https://animesdigital.org/video/a/456/",
            "source": "animesdigital",
            "fetched_at": "2025-02-05T10:00:00",
        }

        data = RecentEpisodeData.model_validate(data_dict)
        assert data.anime_title == "Dandadan"
        assert data.episode_number == 18


class TestRecentEpisodeMatch:
    """Tests for RecentEpisodeMatch model."""

    def test_valid_instantiation(self):
        """Test creating RecentEpisodeMatch with valid data."""
        match = RecentEpisodeMatch(
            anilist_id=1234,
            anilist_title="Jujutsu Kaisen Season 2",
            animesdigital_title="Jujutsu Kaisen Season 2",
            episode_number=25,
            episode_url="https://animesdigital.org/video/a/123/",
            matched_confidence=0.95,
        )

        assert match.anilist_id == 1234
        assert match.anilist_title == "Jujutsu Kaisen Season 2"
        assert match.animesdigital_title == "Jujutsu Kaisen Season 2"
        assert match.episode_number == 25
        assert match.matched_confidence == 0.95

    def test_perfect_match_confidence(self):
        """Test confidence score of 1.0 (perfect match)."""
        match = RecentEpisodeMatch(
            anilist_id=1,
            anilist_title="Test",
            animesdigital_title="Test",
            episode_number=1,
            episode_url="https://example.com/123",
            matched_confidence=1.0,
        )

        assert match.matched_confidence == 1.0

    def test_zero_confidence(self):
        """Test confidence score of 0.0 (worst match)."""
        match = RecentEpisodeMatch(
            anilist_id=1,
            anilist_title="Test",
            animesdigital_title="Completely Different",
            episode_number=1,
            episode_url="https://example.com/123",
            matched_confidence=0.0,
        )

        assert match.matched_confidence == 0.0

    def test_invalid_confidence_above_one(self):
        """Test that confidence cannot exceed 1.0."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="Test",
                animesdigital_title="Test",
                episode_number=1,
                episode_url="https://example.com/123",
                matched_confidence=1.1,
            )

    def test_invalid_confidence_negative(self):
        """Test that confidence cannot be negative."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="Test",
                animesdigital_title="Test",
                episode_number=1,
                episode_url="https://example.com/123",
                matched_confidence=-0.1,
            )

    def test_invalid_anilist_id_zero(self):
        """Test that anilist_id must be > 0."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=0,
                anilist_title="Test",
                animesdigital_title="Test",
                episode_number=1,
                episode_url="https://example.com/123",
                matched_confidence=0.9,
            )

    def test_invalid_episode_number_zero(self):
        """Test that episode_number must be >= 1."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="Test",
                animesdigital_title="Test",
                episode_number=0,
                episode_url="https://example.com/123",
                matched_confidence=0.9,
            )

    def test_invalid_url(self):
        """Test that episode_url must be http(s)."""
        with pytest.raises(ValueError, match="must be http\\(s\\)"):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="Test",
                animesdigital_title="Test",
                episode_number=1,
                episode_url="ftp://example.com/123",
                matched_confidence=0.9,
            )

    def test_empty_anilist_title(self):
        """Test that anilist_title cannot be empty."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="",
                animesdigital_title="Test",
                episode_number=1,
                episode_url="https://example.com/123",
                matched_confidence=0.9,
            )

    def test_empty_animesdigital_title(self):
        """Test that animesdigital_title cannot be empty."""
        with pytest.raises(ValueError):
            RecentEpisodeMatch(
                anilist_id=1,
                anilist_title="Test",
                animesdigital_title="",
                episode_number=1,
                episode_url="https://example.com/123",
                matched_confidence=0.9,
            )

    def test_serialization(self):
        """Test model serialization to dict."""
        match = RecentEpisodeMatch(
            anilist_id=1234,
            anilist_title="Jujutsu Kaisen",
            animesdigital_title="Jujutsu Kaisen Season 2",
            episode_number=25,
            episode_url="https://animesdigital.org/video/a/123/",
            matched_confidence=0.92,
        )

        dumped = match.model_dump()
        assert dumped["anilist_id"] == 1234
        assert dumped["matched_confidence"] == 0.92
        assert dumped["episode_number"] == 25

    def test_deserialization(self):
        """Test model deserialization from dict."""
        match_dict = {
            "anilist_id": 5678,
            "anilist_title": "Dandadan",
            "animesdigital_title": "Dandadan",
            "episode_number": 18,
            "episode_url": "https://animesdigital.org/video/a/456/",
            "matched_confidence": 0.98,
        }

        match = RecentEpisodeMatch.model_validate(match_dict)
        assert match.anilist_id == 5678
        assert match.matched_confidence == 0.98
