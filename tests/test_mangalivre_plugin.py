"""Unit tests for MangaLivre plugin.

Tests search, chapter extraction, and page extraction functionality.
Uses mocked HTTP responses for deterministic testing.
"""

from unittest.mock import Mock, patch

import pytest

from manga_scrapers.plugins.mangalivre import MangaLivre, load


@pytest.fixture
def mangalivre_scraper():
    """Create MangaLivre scraper instance."""
    return MangaLivre()


@pytest.fixture
def mock_mangalivre_search_response():
    """Mock HTML response from MangaLivre search."""
    return """
    <html>
        <div class="manga-card">
            <a href="/manga/jujutsu-kaisen/" class="manga-card-link">
                <h3 class="manga-card-title">Jujutsu Kaisen</h3>
                <p>Sinopse do manga Jujutsu Kaisen</p>
                <span>Status: Ongoing</span>
            </a>
        </div>
        <div class="manga-card">
            <a href="/manga/dandadan/" class="manga-card-link">
                <h3 class="manga-card-title">Dandadan</h3>
                <p>Sinopse do manga Dandadan</p>
                <span>Status: Ongoing</span>
            </a>
        </div>
        <div class="manga-card">
            <a href="/manga/jujutsu-kaisen-0/" class="manga-card-link">
                <h3 class="manga-card-title">Jujutsu Kaisen 0</h3>
                <p>Prequel to Jujutsu Kaisen</p>
                <span>Status: Completed</span>
            </a>
        </div>
    </html>
    """


@pytest.fixture
def mock_mangalivre_empty_search_response():
    """Mock empty search response from MangaLivre."""
    return "<html><body>Nenhum resultado encontrado</body></html>"


@pytest.fixture
def mock_mangalivre_chapter_html():
    """Mock HTML for manga page with chapters."""
    return """
    <html>
        <ul>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/jujutsu-kaisen-capitulo-287/">Capítulo 287 - Novo Arc</a>
                <span class="post-on">2024-01-26</span>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/jujutsu-kaisen-capitulo-286/">Capítulo 286 - Final Battle</a>
                <span class="post-on">2024-01-19</span>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/jujutsu-kaisen-capitulo-285/">Capítulo 285 - The End?</a>
                <span class="post-on">2024-01-12</span>
            </div>
        </li>
        <li class="chapter-item">
            <div class="chapter-info">
                <a href="/capitulo/jujutsu-kaisen-capitulo-1/">Capítulo 1 - Beginning</a>
                <span class="post-on">2018-03-05</span>
            </div>
        </li>
        </ul>
    </html>
    """


@pytest.fixture
def mock_mangalivre_chapter_pages_html():
    """Mock HTML for chapter page with images."""
    return """
    <html>
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/1-3c8d29bda7da9b01107848eeff3fabf0f3ea042dce6f86e.jpg" alt="Page 1" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/2-5fa08200d477376ff47b41498a7fe801b11ed43b79ea554.jpg" alt="Page 2" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/3-1e896f18df2846cc7a247383836ff528daa2883db7102b7.png" alt="Page 3" />
        <img src="https://mangalivre.blog/static/logo.png" alt="Logo" />
        <img src="https://ads.example.com/banner.webp" alt="Ad" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/4-example.webp" alt="Page 4" />
        <img src="https://mangalivre.blog/images/sidebar.gif" alt="Sidebar" />
        <img src="https://mangalivre.blog/wp-content/uploads/2025/03/5-example.jpg" alt="Page 5" />
    </html>
    """


class TestMangaLivreSearch:
    """Tests for search_manga method."""

    def test_search_manga_valid_query(self, mangalivre_scraper, mock_mangalivre_search_response):
        """Test search returns valid manga results."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mangalivre_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mangalivre_scraper.search_manga("jujutsu")

            assert len(results) == 3
            assert results[0]["title"] == "Jujutsu Kaisen"
            assert results[0]["id"] == "jujutsu-kaisen"
            assert results[0]["url"] == "/manga/jujutsu-kaisen/"
            assert "status:" in results[0]["status"] or results[0]["status"] == "status: ongoing"

    def test_search_manga_no_results(
        self, mangalivre_scraper, mock_mangalivre_empty_search_response
    ):
        """Test search handles no results gracefully."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mangalivre_empty_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mangalivre_scraper.search_manga("nonexistent")

            assert results == []

    def test_search_manga_network_error(self, mangalivre_scraper):
        """Test search handles network errors gracefully."""
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Connection timeout")

            results = mangalivre_scraper.search_manga("jujutsu")

            assert results == []

    def test_search_manga_empty_query(self, mangalivre_scraper, mock_mangalivre_search_response):
        """Test search handles empty query."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mangalivre_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mangalivre_scraper.search_manga("")

            assert isinstance(results, list)

    def test_search_manga_special_characters(
        self, mangalivre_scraper, mock_mangalivre_search_response
    ):
        """Test search handles special characters."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mangalivre_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mangalivre_scraper.search_manga("Jujutsu & Kaisen!")

            assert isinstance(results, list)

    def test_search_result_structure(self, mangalivre_scraper, mock_mangalivre_search_response):
        """Test search results have required fields."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mangalivre_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mangalivre_scraper.search_manga("jujutsu")

            for result in results:
                assert "id" in result
                assert "title" in result
                assert "url" in result
                assert "status" in result
                assert isinstance(result["id"], str)
                assert isinstance(result["title"], str)


class TestMangaLivreChapters:
    """Tests for get_chapters method."""

    def _create_playwright_context(self, html_content):
        """Helper to create properly mocked Playwright context."""
        mock_page = Mock()
        mock_page.content.return_value = html_content
        mock_page.wait_for_selector = Mock()

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page

        mock_chromium = Mock()
        mock_chromium.launch.return_value = mock_browser

        mock_pw_instance = Mock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
        mock_pw_instance.__exit__ = Mock(return_value=False)

        return mock_pw_instance

    def test_get_chapters_valid_url(self, mangalivre_scraper, mock_mangalivre_chapter_html):
        """Test chapter extraction from valid URL."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_html)
            mock_pw.return_value = mock_context

            chapters = mangalivre_scraper.get_chapters(
                "jujutsu-kaisen", "https://mangalivre.blog/manga/jujutsu-kaisen/"
            )

            assert len(chapters) == 4
            # Chapters should be sorted by number descending
            assert chapters[0]["number"] == "287"
            assert chapters[1]["number"] == "286"

    def test_get_chapters_chapter_numbering(self, mangalivre_scraper, mock_mangalivre_chapter_html):
        """Test chapter numbers are extracted correctly."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_html)
            mock_pw.return_value = mock_context

            chapters = mangalivre_scraper.get_chapters(
                "jujutsu-kaisen", "https://mangalivre.blog/manga/jujutsu-kaisen/"
            )

            assert all(isinstance(ch["number"], str) for ch in chapters)
            assert all(ch["number"].replace(".", "").isdigit() for ch in chapters)

    def test_get_chapters_sorting(self, mangalivre_scraper, mock_mangalivre_chapter_html):
        """Test chapters are sorted by number descending."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_html)
            mock_pw.return_value = mock_context

            chapters = mangalivre_scraper.get_chapters(
                "jujutsu-kaisen", "https://mangalivre.blog/manga/jujutsu-kaisen/"
            )

            # Verify descending order
            for i in range(len(chapters) - 1):
                current_num = float(chapters[i]["number"])
                next_num = float(chapters[i + 1]["number"])
                assert current_num > next_num

    def test_get_chapters_invalid_url(self, mangalivre_scraper):
        """Test chapter extraction handles invalid URLs gracefully."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.goto.side_effect = Exception("Invalid URL")

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
                "invalid", "https://invalid-url-that-does-not-exist.com"
            )

            assert chapters == []

    def test_get_chapters_result_structure(self, mangalivre_scraper, mock_mangalivre_chapter_html):
        """Test chapter results have required fields."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_html)
            mock_pw.return_value = mock_context

            chapters = mangalivre_scraper.get_chapters(
                "jujutsu-kaisen", "https://mangalivre.blog/manga/jujutsu-kaisen/"
            )

            for chapter in chapters:
                assert "id" in chapter
                assert "number" in chapter
                assert "url" in chapter
                assert isinstance(chapter["id"], str)
                assert isinstance(chapter["number"], str)


class TestMangaLivrePages:
    """Tests for get_chapter_pages method."""

    def _create_playwright_context(self, html_content):
        """Helper to create properly mocked Playwright context."""
        mock_page = Mock()
        mock_page.content.return_value = html_content

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page

        mock_chromium = Mock()
        mock_chromium.launch.return_value = mock_browser

        mock_pw_instance = Mock()
        mock_pw_instance.chromium = mock_chromium
        mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
        mock_pw_instance.__exit__ = Mock(return_value=False)

        return mock_pw_instance

    def test_get_chapter_pages_valid_url(
        self, mangalivre_scraper, mock_mangalivre_chapter_pages_html
    ):
        """Test page extraction from valid chapter URL."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_pages_html)
            mock_pw.return_value = mock_context

            pages = mangalivre_scraper.get_chapter_pages(
                "capitulo-287", "https://mangalivre.blog/manga/jujutsu-kaisen/capitulo-287/"
            )

            # Should include manga pages but exclude ads, logos, gifs
            assert len(pages) == 5  # page-1, page-2, page-3, page-4, page-5
            assert all(isinstance(p, str) for p in pages)
            assert all(p.startswith("http") for p in pages)

    def test_get_chapter_pages_image_filtering(
        self, mangalivre_scraper, mock_mangalivre_chapter_pages_html
    ):
        """Test that ads and logos are filtered out."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(mock_mangalivre_chapter_pages_html)
            mock_pw.return_value = mock_context

            pages = mangalivre_scraper.get_chapter_pages(
                "capitulo-287", "https://mangalivre.blog/manga/jujutsu-kaisen/capitulo-287/"
            )

            # Verify no logos, ads, or gifs are included
            # ads.example.com and sidebar.gif should be filtered
            assert not any("logo" in p.lower() for p in pages)
            assert not any("/ads/" in p.lower() for p in pages)
            assert not any(".gif" in p.lower() for p in pages)
            assert not any("sidebar" in p.lower() for p in pages)
            # Should not include ads from ads.example.com or sidebar.gif
            assert not any("ads.example.com" in p for p in pages)
            assert not any("sidebar.gif" in p for p in pages)

    def test_get_chapter_pages_invalid_url(self, mangalivre_scraper):
        """Test page extraction handles invalid URLs gracefully."""
        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_page = Mock()
            mock_page.goto.side_effect = Exception("Navigation failed")

            mock_browser = Mock()
            mock_browser.new_page.return_value = mock_page

            mock_chromium = Mock()
            mock_chromium.launch.return_value = mock_browser

            mock_pw_instance = Mock()
            mock_pw_instance.chromium = mock_chromium
            mock_pw_instance.__enter__ = Mock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = Mock(return_value=False)

            mock_pw.return_value = mock_pw_instance

            pages = mangalivre_scraper.get_chapter_pages("invalid", "https://invalid-url.com")

            assert pages == []

    def test_get_chapter_pages_no_images(self, mangalivre_scraper):
        """Test page extraction handles pages with no images."""
        html_no_images = "<html><body>No images here</body></html>"

        with patch("manga_scrapers.plugins.mangalivre.sync_playwright") as mock_pw:
            mock_context = self._create_playwright_context(html_no_images)
            mock_pw.return_value = mock_context

            pages = mangalivre_scraper.get_chapter_pages(
                "test", "https://mangalivre.blog/manga/test/capitulo-1/"
            )

            assert pages == []


class TestMangaLivreLoader:
    """Tests for plugin loader."""

    def test_load_with_pt_br_language(self):
        """Test plugin loads when pt-br is in languages."""
        plugin = load({"pt-br"})

        assert plugin is not None
        assert isinstance(plugin, MangaLivre)
        assert plugin.name == "mangalivre"
        assert "pt-br" in plugin.languages

    def test_load_with_other_languages(self):
        """Test plugin doesn't load when pt-br is not in languages."""
        plugin = load({"en", "es"})

        assert plugin is None

    def test_load_with_mixed_languages(self):
        """Test plugin loads when pt-br is mixed with other languages."""
        plugin = load({"en", "pt-br", "es"})

        assert plugin is not None
        assert isinstance(plugin, MangaLivre)

    def test_plugin_attributes(self):
        """Test plugin has required attributes."""
        plugin = load({"pt-br"})

        assert hasattr(plugin, "name")
        assert hasattr(plugin, "languages")
        assert hasattr(plugin, "search_manga")
        assert hasattr(plugin, "get_chapters")
        assert hasattr(plugin, "get_chapter_pages")
        assert plugin.name == "mangalivre"
        assert "pt-br" in plugin.languages
