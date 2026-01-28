"""Tests for PluginRegistry class."""

import pytest
from services.plugin_registry import PluginRegistry


class MockPlugin:
    """Mock plugin for testing."""

    def __init__(self, name: str):
        self.name = name
        self.languages = ["pt-br"]

    def search_anime(self, query: str):
        pass

    def search_episodes(self, anime: str, url: str, params=None):
        pass

    def search_player_src(self, url: str, container: list, event):
        pass


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    PluginRegistry.reset_singleton()
    return PluginRegistry()


class TestPluginRegistry:
    """Test PluginRegistry class."""

    def test_singleton_pattern(self):
        """PluginRegistry should be a singleton."""
        registry1 = PluginRegistry()
        registry2 = PluginRegistry()
        assert registry1 is registry2

    def test_register_plugin(self, registry):
        """Should register a plugin."""
        plugin = MockPlugin("animefire")
        registry.register(plugin)

        assert registry.get_plugin("animefire") is plugin

    def test_register_multiple_plugins(self, registry):
        """Should register multiple plugins."""
        plugin1 = MockPlugin("animefire")
        plugin2 = MockPlugin("animesonlinecc")

        registry.register(plugin1)
        registry.register(plugin2)

        assert registry.get_plugin("animefire") is plugin1
        assert registry.get_plugin("animesonlinecc") is plugin2

    def test_get_active_sources(self, registry):
        """Should return sorted list of registered plugin names."""
        registry.register(MockPlugin("zulu"))
        registry.register(MockPlugin("alpha"))
        registry.register(MockPlugin("mike"))

        sources = registry.get_active_sources()

        assert sources == ["alpha", "mike", "zulu"]

    def test_get_active_sources_empty(self, registry):
        """Should return empty list when no plugins registered."""
        sources = registry.get_active_sources()
        assert sources == []

    def test_get_plugin_not_found(self, registry):
        """Should return None for non-existent plugin."""
        plugin = registry.get_plugin("nonexistent")
        assert plugin is None

    def test_get_all_plugins(self, registry):
        """Should return dict of all registered plugins."""
        plugin1 = MockPlugin("animefire")
        plugin2 = MockPlugin("animesonlinecc")

        registry.register(plugin1)
        registry.register(plugin2)

        all_plugins = registry.get_all_plugins()

        assert all_plugins == {
            "animefire": plugin1,
            "animesonlinecc": plugin2,
        }

    def test_get_all_plugins_empty(self, registry):
        """Should return empty dict when no plugins registered."""
        all_plugins = registry.get_all_plugins()
        assert all_plugins == {}

    def test_reset_singleton(self):
        """Should clear singleton instance on reset."""
        registry1 = PluginRegistry()
        registry1.register(MockPlugin("test"))

        PluginRegistry.reset_singleton()

        registry2 = PluginRegistry()
        assert registry2.get_plugin("test") is None

    def test_register_overwrites_existing(self, registry):
        """Registering same name twice should overwrite."""
        plugin1 = MockPlugin("animefire")
        plugin2 = MockPlugin("animefire")  # Same name

        registry.register(plugin1)
        registry.register(plugin2)

        assert registry.get_plugin("animefire") is plugin2
