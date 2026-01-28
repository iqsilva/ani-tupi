"""Tests for SearchRepository class."""
import pytest
from services.search_repository import SearchRepository
from models.models import SearchResults, AnimeSearchResult


@pytest.fixture
def search_repo():
    """Create a fresh search repository for each test."""
    SearchRepository.reset_singleton()
    return SearchRepository()


class TestSearchRepository:
    """Test SearchRepository class."""

    def test_singleton_pattern(self):
        """SearchRepository should be a singleton."""
        repo1 = SearchRepository()
        repo2 = SearchRepository()
        assert repo1 is repo2

    def test_add_anime_single(self, search_repo):
        """Should add a single anime."""
        search_repo.add_anime("Naruto", "http://example.com", "animefire", None)

        titles = search_repo.get_anime_titles()
        assert "Naruto" in titles

    def test_add_anime_multiple(self, search_repo):
        """Should add multiple anime."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", None)
        search_repo.add_anime("One Piece", "http://ex2.com", "animefire", None)

        titles = search_repo.get_anime_titles()
        assert "Naruto" in titles
        assert "One Piece" in titles

    def test_add_anime_consolidation_exact_match(self, search_repo):
        """Should consolidate anime with exact normalized title match."""
        # Both should normalize to "naruto"
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", None)
        search_repo.add_anime("Naruto", "http://ex2.com", "animesonline", None)

        titles = search_repo.get_anime_titles()
        # Should only have one title (consolidation)
        naruto_count = sum(1 for t in titles if "naruto" in t.lower())
        assert naruto_count == 1

    def test_get_anime_titles_sorted(self, search_repo):
        """Should return titles sorted alphabetically."""
        search_repo.add_anime("Zebra", "http://ex1.com", "animefire", None)
        search_repo.add_anime("Alpha", "http://ex2.com", "animefire", None)
        search_repo.add_anime("Mike", "http://ex3.com", "animefire", None)

        titles = search_repo.get_anime_titles()
        assert titles == ["Alpha", "Mike", "Zebra"]

    def test_get_anime_titles_empty(self, search_repo):
        """Should return empty list when no anime added."""
        titles = search_repo.get_anime_titles()
        assert titles == []

    def test_get_anime_titles_with_filter(self, search_repo):
        """Should filter titles by substring."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", None)
        search_repo.add_anime("Naruto Shippuden", "http://ex2.com", "animefire", None)
        search_repo.add_anime("One Piece", "http://ex3.com", "animefire", None)

        titles = search_repo.get_anime_titles(filter_by_query="Naruto")
        assert len(titles) == 2
        assert all("Naruto" in t for t in titles)

    def test_clear_search_results(self, search_repo):
        """Should clear all search results."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", None)
        assert len(search_repo.get_anime_titles()) > 0

        search_repo.clear_search_results()

        assert len(search_repo.get_anime_titles()) == 0

    def test_build_search_results_empty(self, search_repo):
        """Should build empty SearchResults when no anime added."""
        results = search_repo.build_search_results("test")

        assert isinstance(results, SearchResults)
        assert results.query == "test"
        assert results.results == ()
        assert isinstance(results.metadata, dict)

    def test_build_search_results_with_anime(self, search_repo):
        """Should build SearchResults with added anime."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", {})

        results = search_repo.build_search_results("naruto")

        assert isinstance(results, SearchResults)
        assert results.query == "naruto"
        assert len(results.results) == 1
        assert results.results[0].title == "Naruto"

    def test_normalize_for_filter(self, search_repo):
        """Should normalize text for filtering."""
        normalized = search_repo.normalize_for_filter("Naruto: Shippuden (2007)")

        # Should lowercase, remove punctuation, collapse spaces
        assert normalized == "naruto shippuden 2007"

    def test_normalize_removes_special_chars(self, search_repo):
        """Should remove various special characters and normalize spaces."""
        test_cases = [
            ("Jujutsu-Kaisen", "jujutsu kaisen"),  # Removes -, keeps space
            ("Code:Geass", "code geass"),  # Removes :, adds space
            ("Fruits!", "fruits"),  # Removes !
            ("What?", "what"),  # Removes ?
            ("Test.Series", "test series"),  # Removes ., adds space
        ]

        for input_str, expected in test_cases:
            result = search_repo.normalize_for_filter(input_str)
            assert result == expected, f"Failed for {input_str}: got {result}, expected {expected}"

    def test_get_anime_titles_with_sources(self, search_repo):
        """Should return titles with source indicators."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", None)
        search_repo.add_anime("Naruto", "http://ex2.com", "animesonline", None)
        search_repo.add_anime("One Piece", "http://ex3.com", "animefire", None)

        titles = search_repo.get_anime_titles_with_sources()

        assert len(titles) == 2
        # Titles should include source info in brackets
        assert any("animefire" in t for t in titles)

    def test_search_results_are_immutable(self, search_repo):
        """SearchResults should be immutable (frozen)."""
        search_repo.add_anime("Naruto", "http://ex1.com", "animefire", {})
        results = search_repo.build_search_results("naruto")

        # Should not be able to modify results
        with pytest.raises(Exception):  # Pydantic raises ValidationError on frozen modification
            results.results = ()

    def test_get_anime_titles_exact_match_consolidation(self, search_repo):
        """Should use exact normalized title matching for consolidation."""
        # Same exact title added twice from different sources should consolidate
        search_repo.add_anime("Naruto", "http://ex1.com", "source1", None)
        search_repo.add_anime("Naruto", "http://ex2.com", "source2", None)

        titles = search_repo.get_anime_titles()
        # After consolidation, should have 1 title
        assert len(titles) == 1
        assert titles[0] == "Naruto"

    def test_reset_singleton(self):
        """Should clear singleton instance on reset."""
        repo1 = SearchRepository()
        repo1.add_anime("Naruto", "http://ex1.com", "animefire", None)

        SearchRepository.reset_singleton()

        repo2 = SearchRepository()
        assert len(repo2.get_anime_titles()) == 0
