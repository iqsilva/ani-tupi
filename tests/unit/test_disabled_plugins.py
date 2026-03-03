"""Tests to verify that disabled plugins are not loaded or called.

This test suite ensures that when a plugin is disabled through config settings,
it is not loaded by the loader and is not called during search operations.
"""

import pytest
from unittest.mock import Mock, patch
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

    def test_disabled_plugin_excluded_from_search(self, monkeypatch):
        """Verify that disabled plugins are not called during search."""
        # Disable animesdigital via config
        monkeypatch.setattr(settings.plugins, "disabled_plugins", ["animesdigital"])

        # Load plugins
        loader.load_plugins({"pt-br"})

        # Get repository instance
        repo = Repository()

        # Search for anime
        results = repo.search_anime("test", verbose=False)

        # Check scraper reports - animesdigital should not appear
        scraper_names = [report.name for report in results.scraper_reports]
        assert "animesdigital" not in scraper_names, (
            f"AnimesDigital was called despite being disabled. Reports: {scraper_names}"
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

    def test_search_with_all_plugins_disabled_fails_gracefully(self, monkeypatch):
        """Verify that search fails gracefully when all plugins are disabled."""
        # Disable all plugins via config
        monkeypatch.setattr(
            settings.plugins,
            "disabled_plugins",
            ["anitube", "animesdigital", "animefire", "animesonlinecc"],
        )

        # Load plugins (should load none)
        loader.load_plugins({"pt-br"})

        # Search should fail gracefully
        repo = Repository()
        results = repo.search_anime("test", verbose=False)

        # Should return empty results with no scraper reports
        assert len(results.results) == 0
        assert len(results.scraper_reports) == 0

    def test_disabled_plugin_not_instantiated(self, monkeypatch):
        """Verify that disabled plugin code is not instantiated."""
        # Disable animesdigital via config
        monkeypatch.setattr(settings.plugins, "disabled_plugins", ["animesdigital"])

        # Mock the import to track if animesdigital is loaded
        with patch("importlib.import_module") as mock_import:
            # Set up return value for non-disabled modules
            mock_module = Mock()
            mock_module.load = Mock()
            mock_import.return_value = mock_module

            # Load plugins
            loader.load_plugins({"pt-br"})

            # Verify animesdigital was not imported
            call_names = [
                call[0][0]
                for call in mock_import.call_args_list
                if "scrapers.plugins" in call[0][0]
            ]

            # animesdigital should not be in the imported modules
            assert not any("animesdigital" in call for call in call_names), (
                f"AnimesDigital was imported despite being disabled: {call_names}"
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
