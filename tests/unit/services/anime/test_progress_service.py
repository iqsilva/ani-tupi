"""Tests for ProgressService - TDD approach.

Tests are written BEFORE implementation following the TDD cycle:
1. RED - Write failing tests
2. GREEN - Implement minimal code to pass
3. REFACTOR - Improve code quality

This service extracts progress calculation logic from commands/anime.py
and provides immutable data types for episode progress information.
"""

import pytest

from services.anime.anilist_discovery_service import AniListDiscoveryResult


class TestEpisodeProgressInfoDataclass:
    """Tests for the immutable EpisodeProgressInfo dataclass."""

    def test_dataclass_is_frozen(self):
        """EpisodeProgressInfo should be immutable (frozen)."""
        from services.anime.progress_service import EpisodeProgressInfo

        info = EpisodeProgressInfo(
            current_episode=1,
            scraper_total=12,
            anilist_total=None,
            progress_str="1/12",
        )

        # Should raise error when trying to modify
        with pytest.raises(AttributeError):
            info.current_episode = 2

    def test_dataclass_with_all_fields(self):
        """Should create result with all fields populated."""
        from services.anime.progress_service import EpisodeProgressInfo

        info = EpisodeProgressInfo(
            current_episode=5,
            scraper_total=24,
            anilist_total=24,
            progress_str="5/24",
        )

        assert info.current_episode == 5
        assert info.scraper_total == 24
        assert info.anilist_total == 24
        assert info.progress_str == "5/24"

    def test_dataclass_with_none_anilist_total(self):
        """Should create result with None anilist_total."""
        from services.anime.progress_service import EpisodeProgressInfo

        info = EpisodeProgressInfo(
            current_episode=3,
            scraper_total=12,
            anilist_total=None,
            progress_str="3/12",
        )

        assert info.anilist_total is None


class TestProgressContextDataclass:
    """Tests for the immutable ProgressContext dataclass."""

    def test_dataclass_is_frozen(self):
        """ProgressContext should be immutable (frozen)."""
        from services.anime.progress_service import ProgressContext

        ctx = ProgressContext(
            anime_title="Dandadan",
            episode_number=1,
            source=None,
            anilist_id=None,
            num_episodes=12,
        )

        # Should raise error when trying to modify
        with pytest.raises(AttributeError):
            ctx.episode_number = 2

    def test_dataclass_with_all_fields(self):
        """Should create context with all fields populated."""
        from services.anime.progress_service import ProgressContext

        ctx = ProgressContext(
            anime_title="Dandadan",
            episode_number=5,
            source="animefire",
            anilist_id=12345,
            num_episodes=24,
        )

        assert ctx.anime_title == "Dandadan"
        assert ctx.episode_number == 5
        assert ctx.source == "animefire"
        assert ctx.anilist_id == 12345
        assert ctx.num_episodes == 24

    def test_dataclass_with_optional_fields_none(self):
        """Should create context with optional fields as None."""
        from services.anime.progress_service import ProgressContext

        ctx = ProgressContext(
            anime_title="Test Anime",
            episode_number=1,
            source=None,
            anilist_id=None,
            num_episodes=0,
        )

        assert ctx.source is None
        assert ctx.anilist_id is None


class TestGetEpisodeProgressInfo:
    """Tests for get_episode_progress_info function."""

    def test_basic_progress_without_anilist(self):
        """Test 1: Basic Progress Without AniList.

        Input: episode=1, scraper_total=12, no AniList
        Expected: progress_str="1/12", anilist_total=None
        """
        from services.anime.progress_service import get_episode_progress_info

        # No mocking needed - no AniList info
        result = get_episode_progress_info(
            episode_number=1,
            scraper_total=12,
            anilist_discovery=None,
        )

        assert result.current_episode == 1
        assert result.scraper_total == 12
        assert result.anilist_total is None
        assert result.progress_str == "1/12"

    def test_progress_with_anilist_match(self):
        """Test 2: Progress With AniList Match.

        Input: episode=5, scraper_total=24, anilist_total=24
        Expected: progress_str="5/24", anilist_total=24
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=24,
            found=True,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=24,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 24
        assert result.anilist_total == 24
        assert result.progress_str == "5/24"

    def test_progress_discrepancy_scraper_vs_anilist(self):
        """Test 3: Progress Discrepancy (Scraper vs AniList).

        Input: scraper_total=24, AniList has 25 episodes
        Expected: progress_str shows both like "5/24 (AniList: 25)"
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=25,  # Different from scraper
            found=True,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=24,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 24
        assert result.anilist_total == 25
        assert result.progress_str == "5/24 (AniList: 25)"

    def test_unknown_episode_count(self):
        """Test 4: Unknown Episode Count.

        Input: scraper_total=0 (unknown), episode=5, no AniList
        Expected: progress_str="5/?"
        """
        from services.anime.progress_service import get_episode_progress_info

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=0,
            anilist_discovery=None,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 0
        assert result.anilist_total is None
        assert result.progress_str == "5/?"

    def test_unknown_with_anilist_fallback(self):
        """Test 5: Unknown With AniList Fallback.

        Input: scraper_total=0, AniList has 24 episodes
        Expected: progress_str="5/24", uses AniList total as fallback
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes=24,
            found=True,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=0,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 0
        assert result.anilist_total == 24
        # When scraper doesn't know but AniList does, use AniList
        assert result.progress_str == "5/24"

    def test_final_episode_detection(self):
        """Test 6: Final Episode Detection.

        Input: episode=24, scraper_total=24
        Expected: progress_str="24/24"
        """
        from services.anime.progress_service import get_episode_progress_info

        result = get_episode_progress_info(
            episode_number=24,
            scraper_total=24,
            anilist_discovery=None,
        )

        assert result.current_episode == 24
        assert result.scraper_total == 24
        assert result.progress_str == "24/24"

    def test_anilist_not_found(self):
        """Test 7: AniList Discovery Found Nothing.

        Input: AniList search returned no match
        Expected: Falls back to scraper_total only
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            found=False,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=24,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 24
        assert result.anilist_total is None
        assert result.progress_str == "5/24"

    def test_no_anilist_authentication(self):
        """Test 8: No AniList Authentication.

        Input: AniList was not authenticated
        Expected: Uses only scraper info
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            found=False,
            authenticated=False,
        )

        result = get_episode_progress_info(
            episode_number=5,
            scraper_total=24,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 5
        assert result.scraper_total == 24
        assert result.anilist_total is None
        assert result.progress_str == "5/24"

    def test_both_scraper_and_anilist_unknown(self):
        """Test 9: Both scraper and AniList have unknown episode count.

        Input: scraper_total=0, anilist_total=None
        Expected: progress_str="5/?"
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=21,
            anilist_title="One Piece",
            total_episodes=None,  # Unknown for ongoing series
            found=True,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=1100,
            scraper_total=0,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 1100
        assert result.scraper_total == 0
        assert result.anilist_total is None
        assert result.progress_str == "1100/?"

    def test_anilist_partial_result_no_episodes(self):
        """Test 10: AniList found but no episode count available.

        Input: AniList found ID but total_episodes is None
        Expected: Uses scraper total
        """
        from services.anime.progress_service import get_episode_progress_info

        discovery_result = AniListDiscoveryResult(
            anilist_id=12345,
            anilist_title="Some Anime",
            total_episodes=None,  # Partial result - no episodes
            found=True,
            authenticated=True,
        )

        result = get_episode_progress_info(
            episode_number=3,
            scraper_total=12,
            anilist_discovery=discovery_result,
        )

        assert result.current_episode == 3
        assert result.scraper_total == 12
        assert result.anilist_total is None
        assert result.progress_str == "3/12"


class TestCalculateWatchContext:
    """Tests for calculate_watch_context function."""

    def test_build_complete_progress_context(self):
        """Test: Build Complete Progress Context.

        Input: All parameters provided
        Expected: Returns ProgressContext with all fields populated
        """
        from services.anime.progress_service import calculate_watch_context

        ctx = calculate_watch_context(
            anime_title="Dandadan",
            episode_number=5,
            source="animefire",
            anilist_id=12345,
            num_episodes=24,
        )

        assert ctx.anime_title == "Dandadan"
        assert ctx.episode_number == 5
        assert ctx.source == "animefire"
        assert ctx.anilist_id == 12345
        assert ctx.num_episodes == 24

    def test_build_context_with_optional_fields_none(self):
        """Test: Build context with optional fields as None.

        Input: source and anilist_id are None
        Expected: Returns ProgressContext with None values
        """
        from services.anime.progress_service import calculate_watch_context

        ctx = calculate_watch_context(
            anime_title="Test Anime",
            episode_number=1,
            source=None,
            anilist_id=None,
            num_episodes=12,
        )

        assert ctx.anime_title == "Test Anime"
        assert ctx.episode_number == 1
        assert ctx.source is None
        assert ctx.anilist_id is None
        assert ctx.num_episodes == 12

    def test_build_context_unknown_episodes(self):
        """Test: Build context with unknown episode count.

        Input: num_episodes=0 (unknown)
        Expected: Returns ProgressContext with num_episodes=0
        """
        from services.anime.progress_service import calculate_watch_context

        ctx = calculate_watch_context(
            anime_title="Ongoing Anime",
            episode_number=100,
            source="animesdigital",
            anilist_id=None,
            num_episodes=0,
        )

        assert ctx.anime_title == "Ongoing Anime"
        assert ctx.episode_number == 100
        assert ctx.num_episodes == 0
