"""Tests to verify that disabled plugins are not loaded or called.

This test suite ensures that when a plugin is disabled through config settings,
it is not loaded by the loader and is not called during search operations.
"""

import pytest
from models.config import settings

from scrapers import loader
from services.repository import Repository


class TestDisabledPluginsNotLoaded:
    """Tests that disabled plugins are not loaded."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Reset repository and plugin settings before each test."""
        Repository.reset_singleton()
        # Reset to enable all plugins by default
        monkeypatch.setattr(settings.plugins, "disabled_plugins", [])
        yield
        Repository.reset_singleton()

    def test_disabled_plugin_not_in_loaded_sources(self, monkeypatch):
        """Verify that a disabled plugin is not loaded into the repository."""
        # Disable animesdigital via config
        monkeypatch.setattr(settings.plugins, "disabled_plugins", ["animesdigital"])

        # Load plugins
        loader.load_plugins({"pt-br"})

        # Get repository instance
        repo = Repository()

        # Get active sources
        active_sources = repo.get_active_sources()

        # animesdigital should NOT be in active sources
        assert "animesdigital" not in active_sources, (
            f"AnimesDigital should be disabled but is in: {active_sources}"
        )

    def test_settings_config_applied(self, monkeypatch):
        """Verify that disabled_plugins from settings are applied."""
        # Set disabled plugins via config
        monkeypatch.setattr(
            settings.plugins, "disabled_plugins", ["animesdigital", "animesonlinecc"]
        )

        # Load plugins
        loader.load_plugins({"pt-br"})

        # Get active sources
        repo = Repository()
        active_sources = repo.get_active_sources()

        # Verify disabled plugins are not present
        assert "animesdigital" not in active_sources
        assert "animesonlinecc" not in active_sources

    def test_multiple_plugins_can_be_disabled(self, monkeypatch):
        """Verify that multiple plugins can be disabled simultaneously."""
        # Disable multiple plugins via config
        monkeypatch.setattr(
            settings.plugins, "disabled_plugins", ["animesdigital", "animefire", "animesonlinecc"]
        )

        # Load plugins
        loader.load_plugins({"pt-br"})

        # Get active sources
        repo = Repository()
        active_sources = repo.get_active_sources()

        # None of the disabled ones should be present
        for disabled in ["animesdigital", "animefire", "animesonlinecc"]:
            assert disabled not in active_sources, (
                f"{disabled} should be disabled but is in: {active_sources}"
            )


class TestPluginStateManagement:
    """Tests for managing plugin state across operations."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Reset repository before each test."""
        Repository.reset_singleton()
        # Re-enable all plugins for test isolation
        monkeypatch.setattr(settings.plugins, "disabled_plugins", [])
        yield
        Repository.reset_singleton()

    def test_disabled_plugin_survives_repository_reset(self, monkeypatch):
        """Verify that disabled plugin setting from config survives repository reset."""
        # Disable plugin via config
        monkeypatch.setattr(settings.plugins, "disabled_plugins", ["animesdigital"])

        # Load initial plugins
        loader.load_plugins({"pt-br"})

        # Reset repository
        Repository.reset_singleton()

        # Load plugins again (config is unchanged, settings still applies)
        loader.load_plugins({"pt-br"})

        # Verify plugin is still disabled
        repo = Repository()
        active_sources = repo.get_active_sources()
        assert "animesdigital" not in active_sources
