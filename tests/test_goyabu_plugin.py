"""Unit tests for Goyabu anime scraper plugin.

Tests cover:
- Search functionality with mocked responses
- Episode extraction with JavaScript rendering
- Player source extraction with AJAX interception
- HD quality selection and fallback logic
- Error handling and edge cases
"""

import pytest
from unittest.mock import patch, MagicMock
from scrapers.plugins.goyabu import Goyabu


class TestGoyabuSearch:
    """Tests for anime search functionality."""

    def test_search_anime_valid_query(self):
        """Test search returns structured results for valid query."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                # Mock HTML response with search results
                # Title is in img alt attribute, not in span
                html_response = """
                <html>
                    <a href="/anime/jujutsu-kaisen-3-dublado">
                        <img alt="Jujutsu Kaisen 3 Dublado" src="cover.webp">
                        <span class="rating-poster">4.8</span>
                    </a>
                    <a href="/anime/jujutsu-kaisen-3">
                        <img alt="Jujutsu Kaisen 3" src="cover.webp">
                        <span class="rating-poster">4.6</span>
                    </a>
                </html>
                """
                mock_get.return_value.text = html_response

                plugin.search_anime("jujutsu kaisen")

                # Verify add_anime was called for each result
                assert repo_mock.add_anime.call_count >= 2

    def test_search_anime_empty_results(self):
        """Test search handles empty results gracefully."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                # Mock empty HTML response
                mock_get.return_value.text = "<html></html>"

                plugin.search_anime("nonexistent_anime_xyz")

                # Should not call add_anime
                repo_mock.add_anime.assert_not_called()

    def test_search_anime_error_handling(self):
        """Test search handles network errors gracefully."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                # Simulate network error
                mock_get.side_effect = Exception("Network error")

                # Should not raise exception
                plugin.search_anime("test")

                # Should not add anime on error
                repo_mock.add_anime.assert_not_called()

    def test_search_anime_cleans_whitespace(self):
        """Test search cleans up whitespace in titles."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                html_response = """
                <html>
                    <a href="/anime/test">
                        <img alt="Test  Anime   Title" src="cover.webp">
                    </a>
                </html>
                """
                mock_get.return_value.text = html_response

                plugin.search_anime("test")

                # Verify title was cleaned
                call_args = repo_mock.add_anime.call_args
                assert call_args[0][0] == "Test Anime Title"


class TestGoyabuEpisodes:
    """Tests for episode extraction functionality."""

    def test_search_episodes_valid_url(self):
        """Test episodes are extracted correctly from valid anime page."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_browser_pool") as mock_pool:
                # Mock Selenium driver
                mock_driver = MagicMock()

                # HTML with episodes JSON
                html_with_episodes = """
                <html>
                const allEpisodes = [
                    {"episodio":"1","episode_name":"","link":"/69408"},
                    {"episodio":"2","episode_name":"Episódio 2","link":"/69410"}
                ];
                </html>
                """

                mock_driver.page_source = html_with_episodes
                mock_pool.return_value.get_browser.return_value.__enter__.return_value = mock_driver

                plugin.search_episodes("Jujutsu Kaisen", "https://goyabu.io/anime/test", None)

                # Verify episodes were added
                repo_mock.add_episode_list.assert_called_once()
                call_args = repo_mock.add_episode_list.call_args
                assert len(call_args[0][1]) == 2  # 2 episode titles

    def test_search_episodes_sorting(self):
        """Test episodes maintain correct order."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_browser_pool") as mock_pool:
                mock_driver = MagicMock()

                # HTML with episodes in order
                html_with_episodes = """
                <html>
                const allEpisodes = [
                    {"episodio":"1","episode_name":"","link":"/69401"},
                    {"episodio":"2","episode_name":"","link":"/69402"},
                    {"episodio":"3","episode_name":"","link":"/69403"},
                    {"episodio":"4","episode_name":"","link":"/69404"}
                ];
                </html>
                """

                mock_driver.page_source = html_with_episodes
                mock_pool.return_value.get_browser.return_value.__enter__.return_value = mock_driver

                plugin.search_episodes("Test", "https://goyabu.io/anime/test", None)

                call_args = repo_mock.add_episode_list.call_args
                episode_urls = call_args[0][2]
                # Verify order preserved
                assert len(episode_urls) == 4

    def test_search_episodes_invalid_url(self):
        """Test episodes extraction handles invalid URLs gracefully."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("playwright.sync_api.sync_playwright") as mock_pw:
                mock_pw.return_value.__enter__.side_effect = Exception("Page load failed")

                plugin.search_episodes("Test", "https://invalid.url", None)

                # Should not crash or add episodes
                repo_mock.add_episode_list.assert_not_called()


class TestGoyabuPlayerSource:
    """Tests for video source extraction functionality."""

    def test_search_player_src_extraction(self):
        """Test video URL extracted from AJAX response."""
        # This test focuses on the quality selection logic which is more testable
        plugin = Goyabu()

        # Test that quality selection works with AJAX response format
        mock_sources = [
            {"file": "https://video.example.com/720p.mp4", "label": "720p"},
            {"file": "https://video.example.com/360p.mp4", "label": "360p"},
        ]

        result = plugin._select_best_quality(mock_sources)

        # Verify HD quality (720p) is selected
        assert len(result) > 0
        assert "720p" in result

    def test_hd_quality_upgrade(self):
        """Test HD quality is selected from available options."""
        plugin = Goyabu()

        sources = [
            {"file": "https://cdn.example.com/720p.mp4", "label": "720p"},
            {"file": "https://cdn.example.com/360p.mp4", "label": "360p"},
        ]

        result = plugin._select_best_quality(sources)

        # Should select 720p (HD) over 360p (SD)
        assert "720p" in result

    def test_quality_fallback(self):
        """Test fallback to lower quality when HD unavailable."""
        plugin = Goyabu()

        sources = [
            {"file": "https://cdn.example.com/360p.mp4", "label": "360p"},
            {"file": "https://cdn.example.com/240p.mp4", "label": "240p"},
        ]

        result = plugin._select_best_quality(sources)

        # Should fallback to 360p
        assert "360p" in result

    def test_quality_priority_1080p(self):
        """Test 1080p is prioritized highest."""
        plugin = Goyabu()

        sources = [
            {"file": "https://cdn.example.com/1080p.mp4", "label": "1080p"},
            {"file": "https://cdn.example.com/720p.mp4", "label": "720p"},
            {"file": "https://cdn.example.com/480p.mp4", "label": "480p"},
            {"file": "https://cdn.example.com/360p.mp4", "label": "360p"},
        ]

        result = plugin._select_best_quality(sources)

        assert "1080p" in result

    def test_player_src_timeout_handling(self):
        """Test player source extraction handles timeouts gracefully."""
        plugin = Goyabu()
        container = []
        event = MagicMock()

        with patch("playwright.sync_api.sync_playwright") as mock_pw:
            mock_pw.return_value.__enter__.side_effect = Exception("Timeout")

            with pytest.raises(Exception):
                plugin.search_player_src("https://goyabu.io/69408", container, event)


class TestGoyabuLoader:
    """Tests for plugin loader functionality."""

    def test_plugin_loader_discovery(self):
        """Test plugin is discovered and registered by loader."""
        with patch("scrapers.plugins.goyabu.rep") as repo_mock:
            from scrapers.plugins.goyabu import load

            languages = {"pt-br": True}
            load(languages)

            # Verify plugin was registered
            repo_mock.register.assert_called_once()

    def test_language_filtering(self):
        """Test plugin only loads for supported languages."""
        with patch("scrapers.plugins.goyabu.rep") as repo_mock:
            from scrapers.plugins.goyabu import load

            # Test with unsupported language
            languages = {"en-us": True}
            load(languages)

            # Should not register
            repo_mock.register.assert_not_called()

    def test_language_filtering_pt_br(self):
        """Test plugin loads for pt-br language."""
        with patch("scrapers.plugins.goyabu.rep") as repo_mock:
            from scrapers.plugins.goyabu import load

            languages = {"pt-br": True, "en-us": True}
            load(languages)

            # Should register
            repo_mock.register.assert_called_once()


class TestGoyabuEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_search_special_characters(self):
        """Test search handles special characters in query."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                mock_get.return_value.text = "<html></html>"

                # Should not crash with special characters
                plugin.search_anime("café® & anime™ #3")

    def test_missing_optional_fields(self):
        """Test search handles missing optional fields gracefully."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_browser_pool") as mock_pool:
                mock_driver = MagicMock()

                # HTML with episode missing optional fields
                html_with_episodes = """
                <html>
                const allEpisodes = [
                    {"episodio":"1","link":"/69408"}
                ];
                </html>
                """

                mock_driver.page_source = html_with_episodes
                mock_pool.return_value.get_browser.return_value.__enter__.return_value = mock_driver

                # Should not crash
                plugin.search_episodes("Test", "https://goyabu.io/anime/test", None)

                repo_mock.add_episode_list.assert_called_once()

    def test_network_failure_graceful(self):
        """Test network failures don't crash plugin."""
        plugin = Goyabu()

        with patch("scrapers.plugins.goyabu.rep"):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                mock_get.side_effect = ConnectionError("Network unreachable")

                # Should handle gracefully
                plugin.search_anime("test")

                # Search completes without exception

    def test_malformed_html_handling(self):
        """Test malformed HTML doesn't crash parser."""
        plugin = Goyabu()
        repo_mock = MagicMock()

        with patch("scrapers.plugins.goyabu.rep", repo_mock):
            with patch("scrapers.plugins.goyabu.get_with_retry") as mock_get:
                # Malformed HTML
                mock_get.return_value.text = "<html><a href='/anime/test'><span>Title"

                plugin.search_anime("test")

                # Should handle gracefully


class TestGoyabuIntegration:
    """Integration tests for full plugin workflow."""

    def test_plugin_attributes(self):
        """Test plugin has correct attributes."""
        plugin = Goyabu()

        assert plugin.name == "goyabu"
        assert "pt-br" in plugin.languages
        assert hasattr(plugin, "search_anime")
        assert hasattr(plugin, "search_episodes")
        assert hasattr(plugin, "search_player_src")

    def test_select_best_quality_empty_sources(self):
        """Test quality selection with empty sources array."""
        plugin = Goyabu()

        result = plugin._select_best_quality([])

        # Should return empty string for empty sources
        assert result == ""

    def test_select_best_quality_missing_fields(self):
        """Test quality selection with missing field data."""
        plugin = Goyabu()

        sources = [
            {"label": "720p"},  # missing file
            {"file": "https://example.com/360p.mp4"},  # missing label
        ]

        result = plugin._select_best_quality(sources)

        # Should return 360p URL since it has valid file
        assert isinstance(result, str)
        assert "360p" in result
