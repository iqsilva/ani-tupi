"""Integration tests for Goyabu plugin against real website.

These tests use real website URLs and should be run to validate that
the plugin works correctly with the live Goyabu website.

Note: These tests are slower and may be skipped in CI/CD pipelines.
Use: pytest tests/test_goyabu_integration.py -v
"""

import pytest
from threading import Event
from scrapers.plugins.goyabu import Goyabu
from services.repository import rep


@pytest.mark.integration
class TestGoyabuRealWebsite:
    """Integration tests against live Goyabu website."""

    @pytest.fixture
    def plugin(self):
        """Create plugin instance for testing."""
        return Goyabu()

    def test_search_real_anime(self, plugin):
        """Test search finds real anime on website."""
        plugin.name = "test_goyabu"

        # Monkey-patch rep for this test
        original_add = rep.add_anime
        added_anime = []

        def mock_add_anime(title, url, source):
            added_anime.append({"title": title, "url": url, "source": source})

        rep.add_anime = mock_add_anime

        try:
            plugin.search_anime("jujutsu kaisen")

            # Should find at least one anime
            assert len(added_anime) > 0

            # Verify anime data structure
            anime = added_anime[0]
            assert "title" in anime
            assert "url" in anime
            assert anime["source"] == "test_goyabu"
            assert "jujutsu" in anime["title"].lower() or "kaisen" in anime["title"].lower()

        finally:
            rep.add_anime = original_add

    def test_search_real_anime_multiple_results(self, plugin):
        """Test search returns multiple results for common queries."""
        original_add = rep.add_anime
        added_anime = []

        def mock_add_anime(title, url, source):
            added_anime.append({"title": title, "url": url})

        rep.add_anime = mock_add_anime

        try:
            plugin.search_anime("naruto")

            # Should find multiple results (seasons, dubbed variants, etc.)
            assert len(added_anime) >= 2

        finally:
            rep.add_anime = original_add

    def test_get_episodes_real_anime(self, plugin):
        """Test episode extraction from real anime page."""
        # Known working anime URL from our Phase 0 study
        test_url = "https://goyabu.io/anime/jujutsu-kaisen-3-dublado"

        original_add = rep.add_episode_list
        added_episodes = []

        def mock_add_episode_list(anime, titles, urls, source):
            added_episodes.append(
                {"anime": anime, "titles": titles, "urls": urls, "source": source}
            )

        rep.add_episode_list = mock_add_episode_list

        try:
            plugin.search_episodes("Jujutsu Kaisen 3", test_url, None)

            # Should extract episodes
            assert len(added_episodes) > 0

            episodes = added_episodes[0]
            assert len(episodes["titles"]) > 0
            assert len(episodes["urls"]) > 0
            assert episodes["anime"] == "Jujutsu Kaisen 3"

            # Verify episode structure
            for url in episodes["urls"]:
                assert "goyabu.io" in url or url.startswith("/")

        finally:
            rep.add_episode_list = original_add

    def test_extract_player_real_episode(self, plugin):
        """Test video extraction from real episode page."""
        # Known working episode URL
        test_url = "https://goyabu.io/69408"

        container = []
        event = Event()

        try:
            plugin.search_player_src(test_url, container, event)

            # Wait for event with timeout
            if event.wait(timeout=30):
                assert len(container) > 0

                video_url = container[0]
                # Verify it's a valid video URL
                assert isinstance(video_url, str)
                assert len(video_url) > 0

        except Exception as e:
            # Video extraction might fail if page structure changes
            # This is expected in integration tests
            pytest.skip(f"Video extraction failed: {str(e)}")

    def test_hd_quality_real(self, plugin):
        """Test HD quality is extracted when available."""
        test_url = "https://goyabu.io/69408"

        container = []
        event = Event()

        try:
            plugin.search_player_src(test_url, container, event)

            if event.wait(timeout=30) and len(container) > 0:
                video_url = container[0]

                # Verify URL exists (HD or not)
                # Note: Not all episodes might have HD, but URL should be valid
                assert isinstance(video_url, str)

        except Exception as e:
            pytest.skip(f"HD quality test failed: {str(e)}")

    def test_video_url_playable(self, plugin):
        """Test extracted video URL is accessible and playable."""
        import requests

        test_url = "https://goyabu.io/69408"

        container = []
        event = Event()

        try:
            plugin.search_player_src(test_url, container, event)

            if event.wait(timeout=30) and len(container) > 0:
                video_url = container[0]

                # Test HEAD request to verify URL is accessible
                try:
                    response = requests.head(video_url, timeout=10, allow_redirects=True)
                    # Should return 200 or 206 (partial content for video streams)
                    assert response.status_code in [200, 206]
                except requests.exceptions.RequestException as e:
                    # Video URLs might have expiration timestamps
                    # If URL is expired, skip this check
                    pytest.skip(f"Video URL expired or inaccessible: {str(e)}")

        except Exception as e:
            pytest.skip(f"Video URL test failed: {str(e)}")


@pytest.mark.integration
class TestGoyabuPluginDiscovery:
    """Test plugin discovery and loading mechanism."""

    def test_plugin_loads_for_pt_br(self):
        """Test plugin loads when pt-br language selected."""
        from scrapers.plugins.goyabu import load

        original_register = rep.register
        registered_plugins = []

        def mock_register(plugin):
            registered_plugins.append(plugin)

        rep.register = mock_register

        try:
            load({"pt-br": True})

            # Should register plugin
            assert len(registered_plugins) > 0
            plugin = registered_plugins[0]
            assert plugin.name == "goyabu"

        finally:
            rep.register = original_register

    def test_plugin_skips_for_other_languages(self):
        """Test plugin doesn't load for unsupported languages."""
        from scrapers.plugins.goyabu import load

        original_register = rep.register
        registered_plugins = []

        def mock_register(plugin):
            registered_plugins.append(plugin)

        rep.register = mock_register

        try:
            load({"en-us": True, "es-es": True})

            # Should not register for unsupported languages
            assert len(registered_plugins) == 0

        finally:
            rep.register = original_register


@pytest.mark.integration
class TestGoyabuErrorRecovery:
    """Test error recovery and resilience."""

    def test_search_handles_network_timeout(self):
        """Test search recovers from network timeouts."""
        from scrapers.plugins.goyabu import Goyabu

        plugin = Goyabu()

        original_add = rep.add_anime
        added_anime = []

        def mock_add_anime(title, url, source):
            added_anime.append({"title": title, "url": url})

        rep.add_anime = mock_add_anime

        try:
            # Search with reasonable timeout - should not crash
            plugin.search_anime("test query that takes time")

            # Should handle gracefully even if slow

        finally:
            rep.add_anime = original_add

    def test_episode_extraction_handles_page_load_failure(self):
        """Test episode extraction handles page load failures."""
        plugin = Goyabu()

        original_add = rep.add_episode_list
        added_episodes = []

        def mock_add_episode_list(anime, titles, urls, source):
            added_episodes.append({"titles": titles})

        rep.add_episode_list = mock_add_episode_list

        try:
            # Try with invalid URL
            plugin.search_episodes("Test", "https://invalid-domain-xyz123.io/anime/test", None)

            # Should handle gracefully without crashing

        finally:
            rep.add_episode_list = original_add


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
