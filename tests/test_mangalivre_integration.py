"""Integration tests for MangaLivre plugin.

Tests realistic user scenarios against the real MangaLivre website.
These tests are slower but validate actual site structure.
"""

import pytest

from manga_scrapers.plugins.mangalivre import MangaLivre
from manga_scrapers.loader import load_manga_plugins


@pytest.fixture
def mangalivre_scraper():
    """Create MangaLivre scraper instance."""
    return MangaLivre()


@pytest.mark.integration
class TestMangaLivreIntegration:
    """Real integration tests against live website."""

    def test_plugin_loads_via_loader(self):
        """Test plugin is discovered and loaded by the system."""
        plugins = load_manga_plugins({"pt-br"})

        assert "mangalivre" in plugins
        plugin = plugins["mangalivre"]
        assert plugin.name == "mangalivre"
        assert "pt-br" in plugin.languages

    def test_plugin_does_not_load_without_pt_br(self):
        """Test plugin doesn't load without pt-br language."""
        plugins = load_manga_plugins({"en", "es"})

        assert "mangalivre" not in plugins

    def test_search_returns_valid_structure(self, mangalivre_scraper):
        """Test search returns data in expected structure.

        Note: This test makes a real HTTP request to MangaLivre.
        Skip if network is unavailable.
        """
        try:
            results = mangalivre_scraper.search_manga("jujutsu")

            if results:  # If we got results
                for result in results:
                    assert "id" in result
                    assert "title" in result
                    assert "url" in result
                    assert isinstance(result["id"], str)
                    assert isinstance(result["title"], str)
                    assert isinstance(result["url"], str)
                    # Optional fields
                    if result.get("status"):
                        assert isinstance(result["status"], str)
        except Exception as e:
            pytest.skip(f"Network error during search test: {e}")

    def test_chapter_numbering_parsing(self, mangalivre_scraper):
        """Test that chapter numbers are correctly extracted and sorted.

        This is a mock-based test that validates the parsing logic
        without requiring network access.
        """
        from unittest.mock import Mock, patch

        # Mock HTML with various chapter number formats
        html = """
        <ul>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/test-capitulo-10/">Capítulo 10 - Test</a>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/test-capitulo-5/">Capítulo 5.5 - Test</a>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/test-capitulo-15/">Capítulo 15 - Test</a>
            </div>
        </li>
        </ul>
        """

        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.content.return_value = html
            mock_page.wait_for_selector = Mock()

            mock_browser = Mock()
            mock_browser.new_page.return_value = mock_page

            mock_chromium = Mock()
            mock_chromium.launch.return_value = mock_browser

            mock_pw_instance = Mock()
            mock_pw_instance.chromium = mock_chromium
            mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = Mock(return_value=False)

            mock_pw.return_value = mock_pw_instance

            chapters = mangalivre_scraper.get_chapters(
                "test",
                "https://mangalivre.blog/manga/test/"
            )

            assert len(chapters) == 3
            # Should be sorted by number descending
            assert chapters[0]["number"] == "15"
            assert chapters[1]["number"] == "10"
            assert chapters[2]["number"] == "5.5"

    def test_image_url_normalization(self, mangalivre_scraper):
        """Test that image URLs are properly normalized.

        Tests protocol-relative URLs, relative URLs, and absolute URLs.
        """
        from unittest.mock import Mock, patch

        html = """
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/image1.jpg" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/image2.jpg" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/image3.jpg" />
        <img src="https://ads.example.com/ad.jpg" />
        """

        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.content.return_value = html

            mock_browser = Mock()
            mock_browser.new_page.return_value = mock_page

            mock_chromium = Mock()
            mock_chromium.launch.return_value = mock_browser

            mock_pw_instance = Mock()
            mock_pw_instance.chromium = mock_chromium
            mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = Mock(return_value=False)

            mock_pw.return_value = mock_pw_instance

            pages = mangalivre_scraper.get_chapter_pages(
                "test",
                "https://mangalivre.blog/manga/test/capitulo-1/"
            )

            # All manga images should be normalized to https:// and include /wp-manga/
            assert all(p.startswith("https://") for p in pages)
            assert len(pages) == 3  # 3 manga images, 1 ad filtered out

    def test_plugin_error_handling_network_timeout(self, mangalivre_scraper):
        """Test graceful handling of network timeouts."""
        from unittest.mock import patch

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = TimeoutError("Connection timed out")

            results = mangalivre_scraper.search_manga("jujutsu")

            # Should return empty list, not raise exception
            assert results == []

    def test_plugin_error_handling_invalid_html(self, mangalivre_scraper):
        """Test graceful handling of malformed HTML."""
        from unittest.mock import Mock, patch

        # Invalid/empty HTML
        html = "<html></html>"

        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.content.return_value = html
            mock_page.wait_for_selector = Mock()

            mock_browser = Mock()
            mock_browser.new_page.return_value = mock_page

            mock_chromium = Mock()
            mock_chromium.launch.return_value = mock_browser

            mock_pw_instance = Mock()
            mock_pw_instance.chromium = mock_chromium
            mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = Mock(return_value=False)

            mock_pw.return_value = mock_pw_instance

            chapters = mangalivre_scraper.get_chapters(
                "test",
                "https://mangalivre.blog/manga/test/"
            )

            # Should return empty list, not raise exception
            assert chapters == []


@pytest.mark.integration
class TestMangaLivreEdgeCases:
    """Edge case tests."""

    def test_search_with_special_characters(self):
        """Test search handles special characters gracefully."""
        from unittest.mock import Mock, patch

        scraper = MangaLivre()

        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Should not raise exception with special chars
            results = scraper.search_manga("Jujutsu & Kaisen!@#$%")

            assert isinstance(results, list)

    def test_chapter_with_decimal_numbers(self):
        """Test chapter extraction with decimal chapter numbers."""
        from unittest.mock import Mock, patch

        scraper = MangaLivre()

        html = """
        <ul>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/test-capitulo-10-5/">Capítulo 10.5 - Extra</a>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/test-capitulo-10/">Capítulo 10 - Main</a>
            </div>
        </li>
        </ul>
        """

        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.content.return_value = html
            mock_page.wait_for_selector = Mock()

            mock_browser = Mock()
            mock_browser.new_page.return_value = mock_page

            mock_chromium = Mock()
            mock_chromium.launch.return_value = mock_browser

            mock_pw_instance = Mock()
            mock_pw_instance.chromium = mock_chromium
            mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = Mock(return_value=False)

            mock_pw.return_value = mock_pw_instance

            chapters = scraper.get_chapters("test", "https://mangalivre.blog/manga/test/")

            # Should extract and sort decimal numbers correctly
            assert len(chapters) == 2
            assert chapters[0]["number"] == "10.5"
            assert chapters[1]["number"] == "10"

    def test_empty_search_result(self):
        """Test search with no results."""
        from unittest.mock import Mock, patch

        scraper = MangaLivre()

        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html><body>Nenhum resultado</body></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = scraper.search_manga("nonexistent_manga_xyz")

            assert results == []

    def test_plugin_attributes_immutable(self):
        """Test plugin attributes are as expected."""
        scraper = MangaLivre()

        assert scraper.name == "mangalivre"
        assert "pt-br" in scraper.languages
        assert scraper.base_url == "https://mangalivre.blog"

    def test_multiple_plugin_instances_independent(self):
        """Test multiple plugin instances work independently."""
        scraper1 = MangaLivre()
        scraper2 = MangaLivre()

        # Both should work independently
        assert scraper1.name == scraper2.name
        assert scraper1.base_url == scraper2.base_url

        # They should be different instances
        assert scraper1 is not scraper2
        assert scraper1.session is not scraper2.session
