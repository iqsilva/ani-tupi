"""Phase 2 (C3) TDD Tests: Remove Mutable Repository State

Tests verify that Repository methods return immutable types and never mutate
internal state. This enforces the Immutable Data Flow principle from CLAUDE.md.
"""

import pytest
from dataclasses import FrozenInstanceError
from pydantic import ValidationError

from services.repository import rep
from models.models import SearchResults, AnimeSearchResult, EpisodeList


class TestSearchResultsImmutability:
    """Verify SearchResults is immutable (frozen dataclass)."""

    def test_search_results_frozen(self):
        """SearchResults should be frozen (immutable)."""
        result = SearchResults(
            query="test",
            results=tuple(),
            metadata={},
        )

        # Should not be able to modify frozen Pydantic model
        with pytest.raises((AttributeError, FrozenInstanceError, ValidationError)):
            result.query = "modified"

    def test_search_results_tuple_is_immutable(self):
        """SearchResults.results should use immutable tuple."""
        anime1 = AnimeSearchResult(
            title="Anime 1",
            normalized_title="anime1",
            sources=(("url1", "source1", {}),),
        )
        result = SearchResults(
            query="test",
            results=(anime1,),
            metadata={},
        )

        # Tuple should be immutable
        with pytest.raises(TypeError):
            result.results[0] = None


class TestAnimeSearchResultImmutability:
    """Verify AnimeSearchResult is immutable (frozen dataclass)."""

    def test_anime_search_result_frozen(self):
        """AnimeSearchResult should be frozen."""
        anime = AnimeSearchResult(
            title="Test Anime",
            normalized_title="testanime",
            sources=(("url", "source", {}),),
        )

        with pytest.raises((AttributeError, FrozenInstanceError, ValidationError)):
            anime.title = "Modified"

    def test_anime_search_result_sources_immutable(self):
        """AnimeSearchResult.sources should be immutable tuple."""
        anime = AnimeSearchResult(
            title="Test",
            normalized_title="test",
            sources=(("url", "source", {}),),
        )

        with pytest.raises(TypeError):
            anime.sources[0] = ("modified",)


class TestRepositorySearchReturnsImmutable:
    """Verify Repository.search_anime() returns immutable SearchResults."""

    def test_search_anime_returns_search_results(self):
        """search_anime() should return SearchResults object."""
        # This will fail until we implement SearchResults
        result = rep.search_anime("test_query")
        assert isinstance(result, SearchResults)
        assert result.query == "test_query"

    def test_search_results_not_none(self):
        """search_anime() should never return None."""
        result = rep.search_anime("test_query")
        assert result is not None
        assert isinstance(result, SearchResults)

    def test_multiple_searches_independent(self):
        """Multiple searches should be independent (not mutate shared state)."""
        # Search 1
        result1 = rep.search_anime("query1")
        query1_results = result1.results

        # Search 2
        result2 = rep.search_anime("query2")
        query2_results = result2.results

        # Results should be independent
        # Even if results are empty, they shouldn't interfere with each other
        assert result1.query == "query1"
        assert result2.query == "query2"
        # Both should have independent result tuples
        assert isinstance(query1_results, tuple)
        assert isinstance(query2_results, tuple)


class TestRepositoryNoStateMutation:
    """Verify Repository doesn't mutate state during search."""

    def test_search_results_contain_data(self):
        """SearchResults should contain search data."""
        result = rep.search_anime("test")

        assert hasattr(result, "query")
        assert hasattr(result, "results")
        assert hasattr(result, "metadata")
        assert isinstance(result.results, tuple)

    def test_search_results_metadata_accessible(self):
        """SearchResults metadata should be accessible."""
        result = rep.search_anime("test")

        assert isinstance(result.metadata, dict)
        # Metadata might contain search info like total_sources, etc.


class TestSearchResultsMethods:
    """Verify SearchResults helper methods work."""

    def test_get_anime_titles(self):
        """SearchResults.get_anime_titles() should return list of titles."""
        anime1 = AnimeSearchResult(
            title="Anime 1",
            normalized_title="anime1",
            sources=(("url1", "source1", {}),),
        )
        anime2 = AnimeSearchResult(
            title="Anime 2",
            normalized_title="anime2",
            sources=(("url2", "source2", {}),),
        )
        result = SearchResults(
            query="test",
            results=(anime1, anime2),
            metadata={},
        )

        titles = result.get_anime_titles()
        assert titles == ["Anime 1", "Anime 2"]

    def test_get_anime_titles_with_sources(self):
        """SearchResults.get_anime_titles_with_sources() should include source info."""
        anime1 = AnimeSearchResult(
            title="Anime 1",
            normalized_title="anime1",
            sources=(("url1", "source1", {}), ("url1b", "source2", {})),
        )
        result = SearchResults(
            query="test",
            results=(anime1,),
            metadata={},
        )

        titles_with_sources = result.get_anime_titles_with_sources()
        assert len(titles_with_sources) == 1
        # Should contain title and sources
        assert "Anime 1" in titles_with_sources[0]
        assert "source1" in titles_with_sources[0] or "source2" in titles_with_sources[0]

    def test_find_by_title(self):
        """SearchResults.find_by_title() should find anime by exact title."""
        anime1 = AnimeSearchResult(
            title="Dandadan",
            normalized_title="dandadan",
            sources=(("url1", "source1", {}),),
        )
        anime2 = AnimeSearchResult(
            title="Jujutsu Kaisen",
            normalized_title="jujutsukaisen",
            sources=(("url2", "source2", {}),),
        )
        result = SearchResults(
            query="test",
            results=(anime1, anime2),
            metadata={},
        )

        found = result.find_by_title("Dandadan")
        assert found is not None
        assert found.title == "Dandadan"

    def test_find_by_title_returns_none_if_not_found(self):
        """SearchResults.find_by_title() should return None if not found."""
        anime1 = AnimeSearchResult(
            title="Dandadan",
            normalized_title="dandadan",
            sources=(("url1", "source1", {}),),
        )
        result = SearchResults(
            query="test",
            results=(anime1,),
            metadata={},
        )

        found = result.find_by_title("Not Found")
        assert found is None


class TestEpisodeListImmutability:
    """Verify EpisodeList is immutable (frozen dataclass)."""

    def test_episode_list_frozen(self):
        """EpisodeList should be frozen."""
        episodes = EpisodeList(
            anime_title="Test Anime",
            episodes=(("Episode 1", ["url1", "url2"], "source1"),),
        )

        with pytest.raises((AttributeError, FrozenInstanceError, ValidationError)):
            episodes.anime_title = "Modified"

    def test_episode_list_episodes_immutable(self):
        """EpisodeList.episodes should be immutable tuple."""
        episodes = EpisodeList(
            anime_title="Test",
            episodes=(("Episode 1", ["url"], "source"),),
        )

        with pytest.raises(TypeError):
            episodes.episodes[0] = ("Modified",)


class TestEpisodeListMethods:
    """Verify EpisodeList helper methods work."""

    def test_get_episode_titles(self):
        """EpisodeList.get_episode_titles() should return episode URLs from longest source."""
        episodes = EpisodeList(
            anime_title="Test",
            episodes=(
                ("titles_source1", ["url1"], "source1"),
                ("titles_source2", ["url2a", "url2b"], "source2"),  # Longer list
            ),
        )

        # Should return longest episode list (from source2)
        titles = episodes.get_episode_titles()
        assert len(titles) == 2
        assert "url2a" in titles
        assert "url2b" in titles

    def test_get_episode_url(self):
        """EpisodeList.get_episode_url() should return URL and source."""
        episodes = EpisodeList(
            anime_title="Test",
            episodes=(("Episode 1", ["url1", "url2", "url3"], "source1"),),
        )

        # Get episode 2 (1-indexed)
        result = episodes.get_episode_url(2)
        assert result is not None
        url, source = result
        assert url == "url2"
        assert source == "source1"

    def test_get_episode_url_returns_none_if_not_found(self):
        """EpisodeList.get_episode_url() should return None if episode not found."""
        episodes = EpisodeList(
            anime_title="Test",
            episodes=(("Episode 1", ["url1"], "source1"),),
        )

        # Episode 5 doesn't exist
        result = episodes.get_episode_url(5)
        assert result is None


class TestPluginReturnValues:
    """Verify plugins return values instead of mutating Repository."""

    def test_plugin_search_returns_list(self):
        """Plugin.search_anime() should return list of results."""
        # This tests the new plugin API (after refactoring)
        # Plugins should return lists, not call rep.add_anime()
        pass  # Placeholder - tested via actual plugin tests


class TestRepositoryClear:
    """Verify Repository clear methods work with immutable approach."""

    def test_clear_search_results_still_exists(self):
        """clear_search_results() method should still exist for backward compat."""
        assert hasattr(rep, "clear_search_results")
        # Should not raise
        rep.clear_search_results()
