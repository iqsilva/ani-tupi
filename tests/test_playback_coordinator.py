"""Tests for PlaybackCoordinator."""

from unittest.mock import Mock
from services.playback_coordinator import PlaybackCoordinator, safe_plugin_call
from threading import Event


class TestSafePluginCall:
    """Test safe_plugin_call utility function."""

    def test_successful_extraction(self):
        """Test successful video extraction."""

        def mock_plugin(url, container, event):
            container.append("http://video.url")

        container = []
        event = Event()
        result = safe_plugin_call(mock_plugin, "http://page.url", container, event)

        assert result is True
        assert container == ["http://video.url"]

    def test_failed_extraction(self):
        """Test failed extraction returns False."""

        def mock_plugin(url, container, event):
            # Returns empty container
            pass

        container = []
        event = Event()
        result = safe_plugin_call(mock_plugin, "http://page.url", container, event)

        assert result is False
        assert container == []

    def test_exception_handling(self):
        """Test exception in plugin is caught."""

        def mock_plugin(url, container, event):
            raise ValueError("Plugin error")

        container = []
        event = Event()
        result = safe_plugin_call(mock_plugin, "http://page.url", container, event)

        assert result is False
        assert container == []


class TestPlaybackCoordinator:
    """Test PlaybackCoordinator functionality."""

    def test_initialization(self):
        """Initialize coordinator with sources."""
        sources = {
            "animefire": Mock(),
            "animesdigital": Mock(),
        }
        coordinator = PlaybackCoordinator(sources)

        assert coordinator.sources == sources

    def test_detect_source_from_url_animefire(self):
        """Detect animefire source from URL."""
        coordinator = PlaybackCoordinator({})
        url = "https://animefire.net/video/anime/123"

        source = coordinator._detect_source_from_url(url)

        assert source == "animefire"

    def test_detect_source_from_url_animesdigital(self):
        """Detect animesdigital source from URL."""
        coordinator = PlaybackCoordinator({})
        url = "https://animesdigital.org/video/a/134940/"

        source = coordinator._detect_source_from_url(url)

        assert source == "animesdigital"

    def test_detect_source_from_url_sushianimes(self):
        """Detect sushianimes source from URL."""
        coordinator = PlaybackCoordinator({})
        url = "https://www.animesonline.cc/watch/123"

        source = coordinator._detect_source_from_url(url)

        assert source == "sushianimes"

    def test_detect_source_from_url_goyabu(self):
        """Detect goyabu source from URL."""
        coordinator = PlaybackCoordinator({})
        url = "https://goyabu.net/anime/123"

        source = coordinator._detect_source_from_url(url)

        assert source == "goyabu"

    def test_detect_source_from_url_unknown(self):
        """Return None for unknown source."""
        coordinator = PlaybackCoordinator({})
        url = "https://unknown-anime.com/video/123"

        source = coordinator._detect_source_from_url(url)

        assert source is None

    def test_search_player_from_page_success(self):
        """Extract video URL from page."""

        def mock_search(url, container, event):
            container.append("http://video.url")

        mock_source = Mock()
        mock_source.search_player_src = mock_search
        sources = {"animesdigital": mock_source}

        coordinator = PlaybackCoordinator(sources)
        result = coordinator.search_player_from_page("http://page.url", "animesdigital")

        assert result == ["http://video.url"]

    def test_search_player_from_page_unknown_source(self):
        """Return empty list for unknown source."""
        coordinator = PlaybackCoordinator({})
        result = coordinator.search_player_from_page("http://page.url", "unknown")

        assert result == []

    def test_search_player_from_page_extraction_fails(self):
        """Return empty list if extraction fails."""

        def mock_search(url, container, event):
            # Empty container = failure
            pass

        mock_source = Mock()
        mock_source.search_player_src = mock_search
        sources = {"animesdigital": mock_source}

        coordinator = PlaybackCoordinator(sources)
        result = coordinator.search_player_from_page("http://page.url", "animesdigital")

        assert result == []

    def test_search_player_empty_sources_returns_none(self):
        """Return None when no sources provided."""
        coordinator = PlaybackCoordinator({})
        result = coordinator.search_player([], "Anime Title", 1)

        assert result is None


class TestPreferredSource:
    """Test preferred (primary) source selection with fallback."""

    @staticmethod
    def _make_source(video_url=None):
        def search(url, container, event):
            if video_url:
                container.append(video_url)

        src = Mock()
        src.search_player_src = search
        return src

    def _run(self, coro):
        import asyncio

        return asyncio.run(coro)

    def test_preferred_source_tried_first(self, monkeypatch):
        """Preferred source wins even when lower in global priority."""
        from services import playback_coordinator as pc

        monkeypatch.setattr(
            pc.settings.plugins, "priority_order", ["animefire", "goyabu"], raising=False
        )
        sources = {
            "animefire": self._make_source("http://video.animefire"),
            "goyabu": self._make_source("http://video.goyabu"),
        }
        coordinator = PlaybackCoordinator(sources)
        # Avoid cache interference
        monkeypatch.setattr(
            "utils.cache_manager.get_cache", lambda: (_ for _ in ()).throw(Exception())
        )

        url, source = self._run(
            coordinator.search_player_with_source_async(
                [("http://p1", "animefire"), ("http://p2", "goyabu")],
                "Anime",
                1,
                preferred_source="goyabu",
            )
        )

        assert url == "http://video.goyabu"
        assert source == "goyabu"

    def test_preferred_source_falls_back_on_failure(self, monkeypatch):
        """Failing preferred source falls back to next by priority."""
        from services import playback_coordinator as pc

        monkeypatch.setattr(
            pc.settings.plugins, "priority_order", ["animefire", "goyabu"], raising=False
        )
        sources = {
            "animefire": self._make_source("http://video.animefire"),
            "goyabu": self._make_source(None),  # fails
        }
        coordinator = PlaybackCoordinator(sources)
        monkeypatch.setattr(
            "utils.cache_manager.get_cache", lambda: (_ for _ in ()).throw(Exception())
        )

        url, source = self._run(
            coordinator.search_player_with_source_async(
                [("http://p1", "animefire"), ("http://p2", "goyabu")],
                "Anime",
                1,
                preferred_source="goyabu",
            )
        )

        assert url == "http://video.animefire"
        assert source == "animefire"

    def test_no_preference_uses_priority_order(self, monkeypatch):
        """Without preference, global priority order decides."""
        from services import playback_coordinator as pc

        monkeypatch.setattr(
            pc.settings.plugins, "priority_order", ["animefire", "goyabu"], raising=False
        )
        sources = {
            "animefire": self._make_source("http://video.animefire"),
            "goyabu": self._make_source("http://video.goyabu"),
        }
        coordinator = PlaybackCoordinator(sources)
        monkeypatch.setattr(
            "utils.cache_manager.get_cache", lambda: (_ for _ in ()).throw(Exception())
        )

        url, source = self._run(
            coordinator.search_player_with_source_async(
                [("http://p2", "goyabu"), ("http://p1", "animefire")],
                "Anime",
                1,
            )
        )

        assert url == "http://video.animefire"
        assert source == "animefire"
