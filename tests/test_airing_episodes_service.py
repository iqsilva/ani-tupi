"""Tests for AiringEpisodesService."""

import pytest
from unittest.mock import patch

from models.models import AiringAnimeEntry
from services.anime.airing_episodes_service import AiringEpisodesService


@pytest.fixture
def mock_anilist_client():
    """Mock AniList client for testing."""
    with patch("services.anime.airing_episodes_service.anilist_client") as mock:
        yield mock


@pytest.fixture
def airing_episodes_service(mock_anilist_client):
    """Create AiringEpisodesService with mocked client."""
    return AiringEpisodesService()


class TestAiringEpisodesServiceGapCalculation:
    """Test gap calculation logic."""

    def test_calculates_gap_correctly(self, airing_episodes_service, mock_anilist_client):
        """Test that gap is calculated as next_episode - progress."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 12,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": "Jujutsu Kaisen",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 15, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].episodes_behind == 2  # (15 - 1) - 12 = 2


class TestAiringEpisodesServiceFiltering:
    """Test filtering logic."""

    def test_filters_anime_without_airing_episodes(
        self, airing_episodes_service, mock_anilist_client
    ):
        """Test that anime without nextAiringEpisode are filtered out."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 12,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": "Finished Anime",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": None,  # No airing episode
                },
            },
            {
                "progress": 5,
                "media": {
                    "id": 2,
                    "title": {
                        "romaji": "Airing Anime",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 75,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            },
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].title == "Airing Anime"

    def test_filters_entries_without_media(self, airing_episodes_service, mock_anilist_client):
        """Test that entries without media object are filtered out."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {"progress": 12, "media": None},  # No media
            {
                "progress": 5,
                "media": {
                    "id": 2,
                    "title": {"romaji": "Valid Anime", "english": None, "native": None},
                    "averageScore": 75,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            },
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].title == "Valid Anime"

    def test_filters_anime_with_zero_episode_number(
        self, airing_episodes_service, mock_anilist_client
    ):
        """Test that anime with episode 0 are filtered out."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": "Invalid Episode",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 75,
                    "nextAiringEpisode": {"episode": 0, "airingAt": None},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 0


class TestAiringEpisodesServiceSorting:
    """Test sorting by episodes behind (descending)."""

    def test_sorts_by_episodes_behind_descending(
        self, airing_episodes_service, mock_anilist_client
    ):
        """Test that anime are sorted by episodes_behind descending (most urgent first)."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 15,
                "media": {
                    "id": 1,
                    "title": {"romaji": "Anime A", "english": None, "native": None},
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 18, "airingAt": 1775679377},
                },
            },
            {
                "progress": 10,
                "media": {
                    "id": 2,
                    "title": {"romaji": "Anime B", "english": None, "native": None},
                    "averageScore": 75,
                    "nextAiringEpisode": {"episode": 25, "airingAt": 1775679377},
                },
            },
            {
                "progress": 20,
                "media": {
                    "id": 3,
                    "title": {"romaji": "Anime C", "english": None, "native": None},
                    "averageScore": 80,
                    "nextAiringEpisode": {"episode": 21, "airingAt": 1775679377},
                },
            },
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        # Should be sorted by gap descending: B (15 gap), C (1 gap), A (3 gap)
        assert len(result) == 3
        assert result[0].title == "Anime B"  # gap = 15
        assert result[0].episodes_behind == 14
        assert result[1].title == "Anime A"  # gap = 3
        assert result[1].episodes_behind == 2
        assert result[2].title == "Anime C"  # gap = 1
        assert result[2].episodes_behind == 0


class TestAiringEpisodesServiceTitleExtraction:
    """Test title extraction from various formats."""

    def test_extracts_romaji_title_when_available(
        self, airing_episodes_service, mock_anilist_client
    ):
        """Test that english title is preferred when available, falling back to romaji."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": "Jujutsu Kaisen",
                        "english": "Sorcery Fight",
                        "native": "呪術廻戦",
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result[0].title == "Sorcery Fight"

    def test_falls_back_to_english_title(self, airing_episodes_service, mock_anilist_client):
        """Test fallback to english title when romaji is None."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": None,
                        "english": "Attack on Titan",
                        "native": None,
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result[0].title == "Attack on Titan"

    def test_falls_back_to_native_title(self, airing_episodes_service, mock_anilist_client):
        """Test fallback to native title when romaji and english are None."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {"romaji": None, "english": None, "native": "進撃の巨人"},
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result[0].title == "進撃の巨人"

    def test_uses_unknown_when_no_title_available(
        self, airing_episodes_service, mock_anilist_client
    ):
        """Test that 'Unknown' is used when no title is available."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {"romaji": None, "english": None, "native": None},
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result[0].title == "Unknown"


class TestAiringEpisodesServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_response(self, airing_episodes_service, mock_anilist_client):
        """Test handling of empty API response."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = []

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result == []

    def test_handles_none_response(self, airing_episodes_service, mock_anilist_client):
        """Test handling of None response (not authenticated)."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = []

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert result == []

    def test_handles_missing_optional_fields(self, airing_episodes_service, mock_anilist_client):
        """Test handling when optional fields are missing."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 5,
                "media": {
                    "id": 1,
                    "title": {"romaji": "Test Anime", "english": None, "native": None},
                    "averageScore": None,  # Missing score
                    "nextAiringEpisode": {
                        "episode": 10,
                        "airingAt": 1775679377,
                    },  # Has airingAt for awaiting filter
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].average_score is None
        assert result[0].airing_at == 1775679377

    def test_handles_zero_progress(self, airing_episodes_service, mock_anilist_client):
        """Test handling when progress is 0 (not started)."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 0,  # Not started
                "media": {
                    "id": 1,
                    "title": {"romaji": "New Anime", "english": None, "native": None},
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 5, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].progress == 0
        assert result[0].episodes_behind == 4

    def test_handles_caught_up_anime(self, airing_episodes_service, mock_anilist_client):
        """Test handling when user is caught up (gap = 0)."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 10,
                "media": {
                    "id": 1,
                    "title": {
                        "romaji": "Latest Anime",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        assert result[0].episodes_behind == 0

    def test_creates_valid_airing_anime_entry(self, airing_episodes_service, mock_anilist_client):
        """Test that AiringAnimeEntry objects are created with all fields."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 12,
                "media": {
                    "id": 165847,
                    "title": {
                        "romaji": "Jujutsu Kaisen",
                        "english": None,
                        "native": None,
                    },
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 15, "airingAt": 1775679377},
                },
            }
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 1
        entry = result[0]

        # Verify all fields are set correctly
        assert isinstance(entry, AiringAnimeEntry)
        assert entry.anilist_id == 165847
        assert entry.title == "Jujutsu Kaisen"
        assert entry.progress == 12
        assert entry.next_episode_number == 15
        assert entry.episodes_behind == 2
        assert entry.airing_at == 1775679377
        assert entry.average_score == 82


class TestAiringEpisodesServiceMultipleAnime:
    """Test handling of multiple anime."""

    def test_handles_multiple_airing_anime(self, airing_episodes_service, mock_anilist_client):
        """Test processing multiple anime in one response."""
        mock_anilist_client.get_airing_episodes_for_watching.return_value = [
            {
                "progress": 12,
                "media": {
                    "id": 1,
                    "title": {"romaji": "Anime 1", "english": None, "native": None},
                    "averageScore": 82,
                    "nextAiringEpisode": {"episode": 15, "airingAt": 1775679377},
                },
            },
            {
                "progress": 5,
                "media": {
                    "id": 2,
                    "title": {"romaji": "Anime 2", "english": None, "native": None},
                    "averageScore": 75,
                    "nextAiringEpisode": {"episode": 20, "airingAt": 1775679377},
                },
            },
            {
                "progress": 3,
                "media": {
                    "id": 3,
                    "title": {"romaji": "Anime 3", "english": None, "native": None},
                    "averageScore": 80,
                    "nextAiringEpisode": {"episode": 10, "airingAt": 1775679377},
                },
            },
        ]

        result = airing_episodes_service.get_watching_with_airing_episodes()

        assert len(result) == 3
        # Verify sorted by gap descending
        assert result[0].episodes_behind == 14  # Anime 2: 20 - 5 = 15
        assert result[1].episodes_behind == 6  # Anime 3: 10 - 3 = 7
        assert result[2].episodes_behind == 2  # Anime 1: 15 - 12 = 3
