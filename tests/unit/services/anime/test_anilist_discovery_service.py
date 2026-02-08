"""Tests for AniListDiscoveryService - TDD approach.

Tests are written BEFORE implementation following the TDD cycle:
1. RED - Write failing tests
2. GREEN - Implement minimal code to pass
3. REFACTOR - Improve code quality
"""

from unittest.mock import patch
import pytest

from models.models import AniListAnime, AniListSearchResult, AniListTitle


class TestAniListDiscoveryResult:
    """Tests for the immutable AniListDiscoveryResult dataclass."""

    def test_result_is_frozen_dataclass(self):
        """AniListDiscoveryResult should be immutable (frozen)."""
        from services.anime.anilist_discovery_service import AniListDiscoveryResult

        result = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=False,
        )

        # Should raise error when trying to modify
        with pytest.raises(AttributeError):
            result.found = True

    def test_result_with_all_fields_populated(self):
        """Should create result with all fields populated."""
        from services.anime.anilist_discovery_service import AniListDiscoveryResult

        result = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=12,
            mal_id=54321,
            found=True,
            authenticated=True,
        )

        assert result.anilist_id == 12345
        assert result.anilist_title == "Dandadan"
        assert result.total_episodes == 12
        assert result.mal_id == 54321
        assert result.found is True
        assert result.authenticated is True

    def test_result_not_found_case(self):
        """Should create result for not found case."""
        from services.anime.anilist_discovery_service import AniListDiscoveryResult

        result = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=True,
        )

        assert result.anilist_id is None
        assert result.anilist_title is None
        assert result.total_episodes is None
        assert result.found is False
        assert result.authenticated is True


class TestDiscoverAnilistInfo:
    """Tests for discover_anilist_info function."""

    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_not_authenticated_returns_empty_result(self, mock_anilist):
        """When not authenticated, should return result with authenticated=False."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: AniList not authenticated
        mock_anilist.is_authenticated.return_value = False

        # Execute
        result = discover_anilist_info("Dandadan")

        # Verify
        assert result.authenticated is False
        assert result.found is False
        assert result.anilist_id is None
        assert result.anilist_title is None
        assert result.total_episodes is None

    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_authenticated_no_match_found(self, mock_anilist, mock_auto_discover, mock_normalize):
        """When authenticated but no match found, return found=False."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "nonexistent anime"
        mock_auto_discover.return_value = []  # Empty results

        # Execute
        result = discover_anilist_info("Nonexistent Anime (Dublado)")

        # Verify
        assert result.authenticated is True
        assert result.found is False
        assert result.anilist_id is None
        assert result.anilist_title is None
        mock_normalize.assert_called_once_with("Nonexistent Anime (Dublado)")

    @patch("services.anime.anilist_discovery_service.get_anilist_metadata")
    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_authenticated_exact_match(
        self, mock_anilist, mock_auto_discover, mock_normalize, mock_get_metadata
    ):
        """When authenticated and match found, return complete result."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "dandadan"
        mock_auto_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=95, title="Dandadan")
        ]
        mock_get_metadata.return_value = AniListAnime(
            id=12345,
            title=AniListTitle(romaji="Dandadan", english="Dandadan", native=None),
            episodes=12,
            averageScore=85,
            seasonYear=2024,
            season="FALL",
            type="ANIME",
        )
        mock_anilist.format_title.return_value = "Dandadan"

        # Execute
        result = discover_anilist_info("Dandadan")

        # Verify
        assert result.authenticated is True
        assert result.found is True
        assert result.anilist_id == 12345
        assert result.anilist_title == "Dandadan"
        assert result.total_episodes == 12

    @patch("services.anime.anilist_discovery_service.get_anilist_metadata")
    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_authenticated_fuzzy_match_with_normalization(
        self, mock_anilist, mock_auto_discover, mock_normalize, mock_get_metadata
    ):
        """When title has Portuguese suffix, should normalize before search."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: Title with Portuguese suffix
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "dandadan"  # Normalized title
        mock_auto_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=90, title="Dandadan")
        ]
        mock_get_metadata.return_value = AniListAnime(
            id=12345,
            title=AniListTitle(romaji="Dandadan", english="Dandadan", native=None),
            episodes=12,
            averageScore=85,
            seasonYear=2024,
            season="FALL",
            type="ANIME",
        )
        mock_anilist.format_title.return_value = "Dandadan"

        # Execute with title containing suffix
        result = discover_anilist_info("dandadan (Dublado)")

        # Verify normalization was called with original title
        mock_normalize.assert_called_once_with("dandadan (Dublado)")
        # Verify auto_discover was called with normalized title
        mock_auto_discover.assert_called_once_with("dandadan")
        assert result.found is True

    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_api_error_returns_graceful_result(
        self, mock_anilist, mock_auto_discover, mock_normalize
    ):
        """When API call fails, should return graceful result, not raise exception."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: API raises exception
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "dandadan"
        mock_auto_discover.side_effect = Exception("Network error")

        # Execute - should NOT raise exception
        result = discover_anilist_info("Dandadan")

        # Verify graceful degradation
        assert result.authenticated is True
        assert result.found is False
        assert result.anilist_id is None
        assert result.anilist_title is None

    @patch("services.anime.anilist_discovery_service.get_anilist_metadata")
    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_metadata_error_returns_partial_result(
        self, mock_anilist, mock_auto_discover, mock_normalize, mock_get_metadata
    ):
        """When auto_discover works but get_metadata fails, return partial result."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: Discovery works but metadata fetch fails
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "dandadan"
        mock_auto_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=95, title="Dandadan")
        ]
        mock_get_metadata.side_effect = Exception("Metadata fetch failed")

        # Execute
        result = discover_anilist_info("Dandadan")

        # Verify partial result (has ID but no title/episodes)
        assert result.authenticated is True
        assert result.found is True
        assert result.anilist_id == 12345
        assert result.anilist_title is None
        assert result.total_episodes is None

    @patch("services.anime.anilist_discovery_service.get_anilist_metadata")
    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_metadata_returns_none(
        self, mock_anilist, mock_auto_discover, mock_normalize, mock_get_metadata
    ):
        """When get_metadata returns None, return partial result with ID only."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: Discovery works but metadata returns None
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "dandadan"
        mock_auto_discover.return_value = [
            AniListSearchResult(anilist_id=12345, score=95, title="Dandadan")
        ]
        mock_get_metadata.return_value = None

        # Execute
        result = discover_anilist_info("Dandadan")

        # Verify partial result
        assert result.authenticated is True
        assert result.found is True
        assert result.anilist_id == 12345
        assert result.anilist_title is None
        assert result.total_episodes is None

    @patch("services.anime.anilist_discovery_service.get_anilist_metadata")
    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.auto_discover_anilist_id")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_anime_with_unknown_episode_count(
        self, mock_anilist, mock_auto_discover, mock_normalize, mock_get_metadata
    ):
        """When anime episodes count is unknown (None), result should have None."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: Ongoing anime with unknown episode count
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = "one piece"
        mock_auto_discover.return_value = [
            AniListSearchResult(anilist_id=21, score=95, title="One Piece")
        ]
        mock_get_metadata.return_value = AniListAnime(
            id=21,
            title=AniListTitle(romaji="One Piece", english="One Piece", native=None),
            episodes=None,  # Unknown for ongoing series
            averageScore=87,
            seasonYear=1999,
            season="FALL",
            type="ANIME",
        )
        mock_anilist.format_title.return_value = "One Piece"

        # Execute
        result = discover_anilist_info("One Piece")

        # Verify
        assert result.found is True
        assert result.anilist_id == 21
        assert result.anilist_title == "One Piece"
        assert result.total_episodes is None

    @patch("services.anime.anilist_discovery_service.normalize_title_for_search")
    @patch("services.anime.anilist_discovery_service.anilist_client")
    def test_empty_title_returns_not_found(self, mock_anilist, mock_normalize):
        """When title is empty after normalization, should return not found."""
        from services.anime.anilist_discovery_service import discover_anilist_info

        # Setup: Title normalizes to empty string
        mock_anilist.is_authenticated.return_value = True
        mock_normalize.return_value = ""

        # Execute
        result = discover_anilist_info("(Dublado)")

        # Verify - should not attempt search with empty title
        assert result.authenticated is True
        assert result.found is False
        assert result.anilist_id is None
