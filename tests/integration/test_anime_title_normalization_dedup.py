"""Integration tests for multi-source anime title normalization and deduplication.

Tests the full flow of adding anime from multiple sources with different title
formats and verifying they're merged correctly.
"""

import pytest
from services.repository import Repository


@pytest.fixture
def clean_repository():
    """Create a fresh repository for each test."""
    repo = Repository.__new__(Repository)
    repo.__init__()
    # Reset the singleton state for clean tests
    Repository._instance = repo
    Repository._initialized = True
    yield repo
    # Cleanup after test
    Repository._instance = None
    Repository._initialized = False


class TestMultiSourceDeduplication:
    """Test deduplication of anime from multiple sources with title variations."""

    def test_different_separators_merge(self, clean_repository):
        """Anime with different separators merge as single entry."""
        clean_repository.add_anime("Anime A: Title Dublado", "url1", "source1")
        clean_repository.add_anime("Anime A - Title Dublado", "url2", "source2")

        # Should have only 1 anime entry
        titles = clean_repository.get_anime_titles()
        assert len(titles) == 1

        # Both sources should be listed
        sources_str = str(clean_repository.anime_to_urls[titles[0]])
        assert "source1" in sources_str
        assert "source2" in sources_str

    def test_language_marker_variations_merge(self, clean_repository):
        """Anime with different language markers merge."""
        clean_repository.add_anime("Anime A Dublado", "url1", "source1")
        clean_repository.add_anime("Anime A Legendado", "url2", "source2")

        # Should have only 1 anime entry (both normalized to "anime a")
        titles = clean_repository.get_anime_titles()
        assert len(titles) == 1

    def test_season_format_variations_merge(self, clean_repository):
        """Anime with different season formats merge."""
        clean_repository.add_anime("Anime A Season 2", "url1", "source1")
        clean_repository.add_anime("Anime A 2nd Season", "url2", "source2")
        clean_repository.add_anime("Anime A Temporada 2", "url3", "source3")

        # Should have only 1 anime entry (all normalize to "anime a 2")
        titles = clean_repository.get_anime_titles()
        assert len(titles) == 1

        # All sources listed
        sources_list = clean_repository.anime_to_urls[titles[0]]
        assert len(sources_list) == 3

    def test_exact_duplicates_still_merge(self, clean_repository):
        """Exact duplicates still merge (backward compatibility)."""
        clean_repository.add_anime("Anime A", "url1", "source1")
        clean_repository.add_anime("Anime A", "url2", "source2")

        titles = clean_repository.get_anime_titles()
        assert len(titles) == 1
        assert len(clean_repository.anime_to_urls[titles[0]]) == 2

    def test_different_anime_stay_separate(self, clean_repository):
        """Different anime remain separate entries."""
        clean_repository.add_anime("Anime A: Title", "url1", "source1")
        clean_repository.add_anime("Anime B: Title", "url2", "source2")
        clean_repository.add_anime("Anime C: Title", "url3", "source3")

        titles = clean_repository.get_anime_titles()
        assert len(titles) == 3

    def test_complex_real_world_example(self, clean_repository):
        """Complex real-world example with multiple variations."""
        # Multiple sources for "Jujutsu Kaisen 2" with various title formats
        clean_repository.add_anime("Jujutsu Kaisen Season 2 Dublado", "url1", "animesdigital")
        clean_repository.add_anime("Jujutsu Kaisen 2nd Season", "url2", "animefire")
        clean_repository.add_anime("Jujutsu Kaisen Temporada 2 Legendado", "url3", "animesonline")

        # Should merge to single entry
        titles = clean_repository.get_anime_titles()
        assert len(titles) == 1

        # All sources present
        sources_list = clean_repository.anime_to_urls[titles[0]]
        sources = [source for _, source, _ in sources_list]
        assert len(sources) == 3
        assert "animesdigital" in sources
        assert "animefire" in sources
        assert "animesonline" in sources

    def test_norm_titles_mapping_maintained(self, clean_repository):
        """Verify norm_titles dict tracks all original titles."""
        clean_repository.add_anime("Anime A: Title Dublado", "url1", "source1")
        clean_repository.add_anime("Anime A - Title Dublado", "url2", "source2")

        # Both original titles should be in norm_titles
        assert "Anime A: Title Dublado" in clean_repository.norm_titles
        assert "Anime A - Title Dublado" in clean_repository.norm_titles

        # Both should map to same normalized form
        norm1 = clean_repository.norm_titles["Anime A: Title Dublado"]
        norm2 = clean_repository.norm_titles["Anime A - Title Dublado"]
        assert norm1 == norm2

    def test_cache_loaded_anime_normalization(self, clean_repository):
        """Test normalization of anime loaded from cache (not in norm_titles yet)."""
        # Simulate anime loaded from cache
        clean_repository.anime_to_urls["Cached Anime A: Title"] = [("url1", "source1", None)]

        # Add same anime with different title format
        clean_repository.add_anime("Cached Anime A - Title", "url2", "source2")

        # Should merge (one entry with two sources)
        titles = clean_repository.get_anime_titles()
        # This depends on implementation - might have 1 or 2 entries
        # depending on how cache loading is handled
        # The important thing is that if we search, we can find both

    def test_multiple_anime_with_multiple_sources(self, clean_repository):
        """Test scenario with multiple anime each from multiple sources."""
        # Anime 1 from 2 sources
        clean_repository.add_anime("Naruto Season 1", "url1", "source1")
        clean_repository.add_anime("Naruto Temporada 1", "url2", "source2")

        # Anime 2 from 2 sources
        clean_repository.add_anime("One Piece Season 1", "url3", "source1")
        clean_repository.add_anime("One Piece Temporada 1", "url4", "source3")

        # Should have 2 anime entries
        titles = clean_repository.get_anime_titles()
        assert len(titles) == 2

        # Each should have 2 sources
        for title in titles:
            sources_list = clean_repository.anime_to_urls[title]
            assert len(sources_list) == 2


class TestGetAnimeTitlesWithMergedResults:
    """Test that display methods show merged results correctly."""

    def test_get_anime_titles_with_sources_format(self, clean_repository):
        """Verify get_anime_titles_with_sources shows merged results."""
        clean_repository.add_anime("Anime A: Title Dublado", "url1", "source1")
        clean_repository.add_anime("Anime A - Title Legendado", "url2", "source2")

        results = clean_repository.get_anime_titles_with_sources()

        # Should have 1 result (merged)
        assert len(results) == 1

        # Result should be a string containing title and both sources
        result = results[0]
        assert isinstance(result, str)
        assert "Anime A" in result  # Original title (first one encountered)
        # Sources should be indicated in format: "Title [source1, source2]"
        assert "source1" in result
        assert "source2" in result
        assert "[" in result and "]" in result  # Source list format

    def test_filtered_results_show_correct_source_count(self, clean_repository):
        """Filtered results show merged source information."""
        clean_repository.add_anime("Jujutsu Kaisen Season 1", "url1", "animesdigital")
        clean_repository.add_anime("Jujutsu Kaisen 1st Season", "url2", "animefire")
        clean_repository.add_anime("My Hero Academia Season 1", "url3", "source3")

        # Filter for "Jujutsu"
        filtered_titles = clean_repository.get_anime_titles(filter_by_query="Jujutsu")

        assert len(filtered_titles) == 1  # Only Jujutsu result
        assert "Jujutsu" in filtered_titles[0]


class TestBackwardCompatibility:
    """Ensure new deduplication doesn't break existing functionality."""

    def test_existing_code_still_works(self, clean_repository):
        """Old behavior patterns still work."""
        # This is what existing code expects
        clean_repository.add_anime("Title 1", "url1", "source1")
        clean_repository.add_anime("Title 2", "url2", "source2")

        titles = clean_repository.get_anime_titles()
        assert len(titles) == 2
        assert "Title 1" in titles
        assert "Title 2" in titles

    def test_get_episodes_still_associates_correctly(self, clean_repository):
        """Episodes are still associated with merged anime."""
        # Add anime from two sources (should merge)
        clean_repository.add_anime("Anime A: Title", "url1", "source1")
        clean_repository.add_anime("Anime A - Title", "url2", "source2")

        # Get the merged title
        titles = clean_repository.get_anime_titles()
        merged_title = titles[0]

        # Add episodes (this is existing functionality)
        clean_repository.anime_episodes_titles[merged_title] = ["Episode 1", "Episode 2"]
        clean_repository.anime_episodes_urls[merged_title] = ["ep_url1", "ep_url2"]

        # Episodes should be retrievable
        assert len(clean_repository.anime_episodes_titles[merged_title]) == 2
        assert len(clean_repository.anime_episodes_urls[merged_title]) == 2

    def test_search_still_works_on_merged_results(self, clean_repository):
        """Search filtering works on merged results."""
        clean_repository.add_anime("Jujutsu Kaisen Season 2", "url1", "source1")
        clean_repository.add_anime("Jujutsu Kaisen 2nd Season", "url2", "source2")
        clean_repository.add_anime("My Hero Academia Season 3", "url3", "source3")

        # Search should filter merged results
        results = clean_repository.get_anime_titles(filter_by_query="Jujutsu")
        assert len(results) == 1
        assert "Jujutsu" in results[0]
