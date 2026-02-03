"""Tests for Repository cache integration with normalized keys.

Verifies that Repository uses normalized cache keys for search results.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.repository import Repository
from services.anime.title_normalization import normalize_search_cache_key


@pytest.fixture
def repo():
    """Create and reset Repository singleton for each test."""
    Repository.reset_singleton()
    repo = Repository()
    yield repo
    Repository.reset_singleton()


@pytest.fixture
def mock_cache():
    """Create a mock cache object."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    return cache


class TestRepositoryCacheIntegration:
    """Test Repository integration with normalized cache keys."""

    def test_cache_key_normalization_on_retrieval(self, repo, mock_cache):
        """Cache retrieval should use normalized keys."""
        with patch("utils.cache_manager.get_cache") as mock_get_cache:
            mock_get_cache.return_value = mock_cache

            # Register a mock plugin
            plugin = Mock()
            plugin.name = "test_source"
            plugin.search = Mock(return_value=[])
            repo.register(plugin)

            # Search with a query
            repo.search_anime("jigokuraku 2", verbose=False)

            # Verify cache.get was called with normalized key
            expected_key = normalize_search_cache_key("jigokuraku 2")
            mock_cache.get.assert_called()
            call_args = mock_cache.get.call_args[0][0]
            assert call_args == expected_key

    def test_cache_key_normalization_matches_queries(self):
        """Normalized cache keys should be consistent for equivalent queries."""
        # Different representations of the same query should produce same cache key
        queries = [
            "jigokuraku 2",
            "Jigokuraku 2nd Season",
            "JIGOKURAKU S2",
            "jigokuraku season 2",
        ]

        keys = [normalize_search_cache_key(q) for q in queries]
        # All should produce same normalized key
        assert all(k == keys[0] for k in keys)

    def test_different_queries_normalize_to_same_key(self, repo, mock_cache):
        """Different query variations should normalize to same cache key."""
        with patch("utils.cache_manager.get_cache") as mock_get_cache:
            mock_cache_obj = Mock()
            mock_cache_obj.get = Mock(return_value=None)
            mock_get_cache.return_value = mock_cache_obj

            plugin = Mock()
            plugin.name = "test_source"
            plugin.search = Mock(return_value=[])
            repo.register(plugin)

            queries = [
                "jigokuraku 2",
                "Jigokuraku 2nd Season",
                "JIGOKURAKU S2",
            ]

            keys_accessed = []
            for query in queries:
                Repository.reset_singleton()
                repo = Repository()
                repo.register(plugin)

                with patch("utils.cache_manager.get_cache") as mg:
                    mg.return_value = mock_cache_obj
                    repo.search_anime(query, verbose=False)
                    keys_accessed.append(normalize_search_cache_key(query))

            # All keys should be identical
            assert len(set(keys_accessed)) == 1

    def test_cache_hit_returns_cached_data(self, repo, mock_cache):
        """When cache hits, repository should return cached data."""
        # Prepare cached data
        cached_data = {"Jigokuraku": [("http://example.com/jigokuraku", "test_source", {})]}

        with patch("utils.cache_manager.get_cache") as mock_get_cache:
            mock_cache.get = Mock(return_value=cached_data)
            mock_get_cache.return_value = mock_cache

            plugin = Mock()
            plugin.name = "test_source"
            plugin.search = Mock()  # Should not be called on cache hit
            repo.register(plugin)

            # Search
            result = repo.search_anime("jigokuraku 2", verbose=False)

            # Plugin search should not be called (cache hit)
            plugin.search.assert_not_called()

            # Result should contain cached anime
            assert len(result.results) == 1
            assert result.results[0].title == "Jigokuraku"

    def test_language_code_in_cache_key(self):
        """Cache keys should include language code."""
        key_pt = normalize_search_cache_key("dandadan", "pt-br")
        key_en = normalize_search_cache_key("dandadan", "en-us")

        # Different language codes should produce different keys
        assert key_pt != key_en
        assert key_pt.endswith(":pt-br")
        assert key_en.endswith(":en-us")

    def test_normalized_key_format(self, repo):
        """Normalized cache keys should have expected format."""
        key = normalize_search_cache_key("Jigokuraku Season 2")

        # Format: search:{normalized}:{language}
        assert key.startswith("search:")
        assert key.endswith(":pt-br")
        assert key.count(":") == 2
