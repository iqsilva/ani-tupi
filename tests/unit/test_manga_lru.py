"""Tests for LRU caching in UnifiedMangaService."""

import pytest
from unittest.mock import MagicMock, patch
from services.manga_service import UnifiedMangaService
from models.config import MangaSettings


@pytest.fixture
def manga_service():
    """Create a manga service with mock plugins."""
    config = MangaSettings()
    with patch("services.manga_service.load_manga_plugins") as mock_load:
        mock_load.return_value = {"mock_plugin": MagicMock()}
        # Use a temporary metadata file
        with patch("services.manga_service.get_data_path") as mock_path:
            mock_path.return_value = MagicMock()
            service = UnifiedMangaService(config)
            # Ensure it's empty
            service.manga_plugin_map.clear()
            return service


class TestMangaLRUCache:
    """Test LRU cache functionality in UnifiedMangaService."""

    def test_record_manga_adds_to_map(self, manga_service):
        """Should add manga to plugin map."""
        manga_service._record_manga_in_plugin("m1", "p1")
        assert manga_service.manga_plugin_map["m1"] == "p1"
        assert len(manga_service.manga_plugin_map) == 1

    def test_lru_eviction(self, manga_service):
        """Should evict oldest entries when limit is reached."""
        # Add 1000 entries
        for i in range(1000):
            manga_service._record_manga_in_plugin(f"m{i}", f"p{i}")

        assert len(manga_service.manga_plugin_map) == 1000
        assert "m0" in manga_service.manga_plugin_map

        # Add one more
        manga_service._record_manga_in_plugin("m1000", "p1000")

        assert len(manga_service.manga_plugin_map) == 1000
        assert "m0" not in manga_service.manga_plugin_map  # Oldest should be gone
        assert "m1000" in manga_service.manga_plugin_map
        assert "m1" in manga_service.manga_plugin_map

    def test_lru_update_on_access(self, manga_service):
        """Should update entry position on access."""
        manga_service._record_manga_in_plugin("m1", "p1")
        manga_service._record_manga_in_plugin("m2", "p2")

        # Current order: m1, m2
        # Access m1
        manga_service._get_known_plugin_for_manga("m1")

        # Now order should be: m2, m1 (m1 is most recent)
        # Add many to reach 1000 limit
        for i in range(3, 1002):
            manga_service._record_manga_in_plugin(f"m{i}", f"p{i}")

        assert "m1" in manga_service.manga_plugin_map  # Should still be here
        assert "m2" not in manga_service.manga_plugin_map  # Should have been evicted first
