"""Integration tests for Mugiwaras manga workflow.

Tests realistic user scenarios using Mugiwaras API for Brazilian Portuguese manga.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from manga_scrapers.plugins.mugiwaras import MugiwarasOficial


@pytest.fixture
def temp_manga_dir():
    """Create temporary directory for manga storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mugiwaras_scraper():
    """Create Mugiwaras scraper instance."""
    return MugiwarasOficial()


@pytest.fixture
def mock_mugiwaras_search_response():
    """Mock HTML response from Mugiwaras search."""
    return """
    <html>
        <div class="row c-tabs-item__content">
            <div class="post-title">
                <a href="https://mugiwarasoficial.com/manga/dandadan/">Dandadan</a>
            </div>
            <span class="chapter">
                <a>Capítulo 50</a>
            </span>
        </div>
        <div class="row c-tabs-item__content">
            <div class="post-title">
                <a href="https://mugiwarasoficial.com/manga/jujutsu-kaisen/">Jujutsu Kaisen</a>
            </div>
            <span class="chapter">
                <a>Capítulo 271</a>
            </span>
        </div>
        <div class="row c-tabs-item__content">
            <div class="post-title">
                <a href="https://mugiwarasoficial.com/manga/blue-lock/">Blue Lock</a>
            </div>
            <span class="chapter">
                <a>Capítulo 240</a>
            </span>
        </div>
    </html>
    """


@pytest.fixture
def mock_mugiwaras_chapters_html():
    """Mock HTML response from Mugiwaras chapter list."""
    return """
    <html>
        <li class="wp-manga-chapter">
            <a href="https://mugiwarasoficial.com/manga/dandadan/capitulo-50-dandadan/">
                Capítulo 50 PT-BR
            </a>
        </li>
        <li class="wp-manga-chapter">
            <a href="https://mugiwarasoficial.com/manga/dandadan/capitulo-49-dandadan/">
                Capítulo 49 - As Aventuras PT-BR
            </a>
        </li>
        <li class="wp-manga-chapter">
            <a href="https://mugiwarasoficial.com/manga/dandadan/capitulo-48-dandadan/">
                Capítulo 48 PT-BR
            </a>
        </li>
    </html>
    """


@pytest.fixture
def mock_mugiwaras_pages_html():
    """Mock HTML response from Mugiwaras chapter pages."""
    return """
    <html>
        <img data-src="https://mugiwarasoficial.com/WP-manga/page1.webp" />
        <img data-src="https://mugiwarasoficial.com/WP-manga/page2.webp" />
        <img data-src="https://mugiwarasoficial.com/WP-manga/page3.webp" />
        <img src="https://mugiwarasoficial.com/logo.png" />
    </html>
    """


class TestMugiwarasSearchWorkflow:
    """Test manga search with Mugiwaras API."""

    def test_search_manga_returns_results(
        self, mugiwaras_scraper, mock_mugiwaras_search_response
    ):
        """Search should parse Mugiwaras HTML and return manga results."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mugiwaras_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mugiwaras_scraper.search_manga("Dandadan")

            assert len(results) == 3
            assert results[0]["title"] == "Dandadan"
            assert results[0]["id"] == "dandadan"
            assert results[1]["title"] == "Jujutsu Kaisen"
            assert results[2]["title"] == "Blue Lock"

    def test_search_manga_extracts_metadata(
        self, mugiwaras_scraper, mock_mugiwaras_search_response
    ):
        """Search results should contain required metadata."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mugiwaras_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mugiwaras_scraper.search_manga("test")

            for result in results:
                assert "id" in result
                assert "title" in result
                assert "url" in result
                assert "status" in result

    def test_search_manga_handles_empty_results(
        self, mugiwaras_scraper, mock_mugiwaras_search_response
    ):
        """Search should handle empty results gracefully."""
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = "<html></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mugiwaras_scraper.search_manga("NonexistentManga2025")

            assert results == []

    def test_search_manga_handles_network_error(self, mugiwaras_scraper):
        """Search should handle network errors gracefully."""
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            results = mugiwaras_scraper.search_manga("test")

            assert results == []


class TestMugiwarasChapterSelectionWorkflow:
    """Test chapter selection and fetching."""

    def test_get_chapters_parses_list(
        self, mugiwaras_scraper, mock_mugiwaras_chapters_html
    ):
        """get_chapters should parse chapter list from rendered HTML."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_chapters_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            chapters = mugiwaras_scraper.get_chapters(
                "dandadan", "https://mugiwarasoficial.com/manga/dandadan/"
            )

            assert len(chapters) == 3
            assert chapters[0]["number"] == "50"
            assert chapters[1]["number"] == "49"
            assert chapters[2]["number"] == "48"

    def test_get_chapters_sorts_descending(
        self, mugiwaras_scraper, mock_mugiwaras_chapters_html
    ):
        """Chapters should be sorted by number descending (latest first)."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_chapters_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            chapters = mugiwaras_scraper.get_chapters(
                "dandadan", "https://mugiwarasoficial.com/manga/dandadan/"
            )

            chapter_numbers = [float(ch["number"]) for ch in chapters]
            assert chapter_numbers == sorted(chapter_numbers, reverse=True)

    def test_get_chapters_extracts_chapter_id(
        self, mugiwaras_scraper, mock_mugiwaras_chapters_html
    ):
        """Chapters should have extracted IDs from URLs."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_chapters_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            chapters = mugiwaras_scraper.get_chapters(
                "dandadan", "https://mugiwarasoficial.com/manga/dandadan/"
            )

            for chapter in chapters:
                assert "id" in chapter
                assert chapter["id"] != ""

    def test_get_chapters_handles_playwright_timeout(self, mugiwaras_scraper):
        """get_chapters should handle Playwright timeouts gracefully."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.wait_for_selector.side_effect = TimeoutError()
            mock_page.content.return_value = "<html></html>"
            mock_page.goto = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            chapters = mugiwaras_scraper.get_chapters(
                "dandadan", "https://mugiwarasoficial.com/manga/dandadan/"
            )

            # Should return empty list instead of crashing
            assert isinstance(chapters, list)


class TestMugiwarasPageFetchingWorkflow:
    """Test chapter page image fetching."""

    def test_get_chapter_pages_extracts_images(
        self, mugiwaras_scraper, mock_mugiwaras_pages_html
    ):
        """get_chapter_pages should extract image URLs from HTML."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_pages_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()
            mock_page.query_selector = Mock(return_value=None)
            mock_page.evaluate = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            pages = mugiwaras_scraper.get_chapter_pages(
                "capitulo-50-dandadan",
                "https://mugiwarasoficial.com/manga/dandadan/capitulo-50-dandadan/",
            )

            assert len(pages) == 3
            assert all("mugiwarasoficial.com" in url for url in pages)

    def test_get_chapter_pages_filters_noise(
        self, mugiwaras_scraper, mock_mugiwaras_pages_html
    ):
        """get_chapter_pages should filter out logos and non-manga images."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_pages_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()
            mock_page.query_selector = Mock(return_value=None)
            mock_page.evaluate = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            pages = mugiwaras_scraper.get_chapter_pages(
                "capitulo-50-dandadan",
                "https://mugiwarasoficial.com/manga/dandadan/capitulo-50-dandadan/",
            )

            # Logo should be filtered out
            assert not any("logo" in url for url in pages)

    def test_get_chapter_pages_handles_age_verification(
        self, mugiwaras_scraper, mock_mugiwaras_pages_html
    ):
        """get_chapter_pages should handle age verification modal."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_pages_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()
            mock_page.query_selector = Mock(return_value=None)
            mock_page.evaluate = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            pages = mugiwaras_scraper.get_chapter_pages(
                "capitulo-50-dandadan",
                "https://mugiwarasoficial.com/manga/dandadan/capitulo-50-dandadan/",
            )

            # Should still return pages even if modal handling is attempted
            assert isinstance(pages, list)

    def test_get_chapter_pages_handles_playwright_error(self, mugiwaras_scraper):
        """get_chapter_pages should handle Playwright errors gracefully."""
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_pw.side_effect = Exception("Playwright error")

            pages = mugiwaras_scraper.get_chapter_pages(
                "capitulo-50", "https://example.com/chapter"
            )

            assert pages == []


class TestMugiwarasCompleteWorkflow:
    """End-to-end realistic manga reading scenarios."""

    def test_user_searches_and_gets_chapters(
        self,
        mugiwaras_scraper,
        mock_mugiwaras_search_response,
        mock_mugiwaras_chapters_html,
    ):
        """User searches for manga and fetches chapter list."""
        # Step 1: Search
        with patch("requests.Session.get") as mock_get:
            mock_response = Mock()
            mock_response.text = mock_mugiwaras_search_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            results = mugiwaras_scraper.search_manga("Dandadan")
            assert len(results) > 0

            selected_manga = results[0]
            assert selected_manga["title"] == "Dandadan"

            # Step 2: Get chapters
            with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
                mock_context = Mock()
                mock_browser = Mock()
                mock_page = Mock()
                mock_page.content.return_value = mock_mugiwaras_chapters_html
                mock_page.wait_for_selector = Mock()
                mock_page.goto = Mock()

                mock_browser.new_page.return_value = mock_page
                mock_browser.close = Mock()

                mock_context.chromium.launch.return_value = mock_browser
                mock_pw.return_value.__enter__.return_value = mock_context

                chapters = mugiwaras_scraper.get_chapters(
                    selected_manga["id"], selected_manga["url"]
                )
                assert len(chapters) > 0
                assert chapters[0]["number"] == "50"

    def test_user_reads_chapter_flow(
        self,
        mugiwaras_scraper,
        mock_mugiwaras_chapters_html,
        mock_mugiwaras_pages_html,
        temp_manga_dir,
    ):
        """Complete flow: get chapters and fetch pages."""
        # Get chapters
        with patch("manga_scrapers.plugins.mugiwaras.sync_playwright") as mock_pw:
            mock_context = Mock()
            mock_browser = Mock()
            mock_page = Mock()
            mock_page.content.return_value = mock_mugiwaras_chapters_html
            mock_page.wait_for_selector = Mock()
            mock_page.goto = Mock()
            mock_page.query_selector = Mock(return_value=None)
            mock_page.evaluate = Mock()

            mock_browser.new_page.return_value = mock_page
            mock_browser.close = Mock()

            mock_context.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__enter__.return_value = mock_context

            chapters = mugiwaras_scraper.get_chapters(
                "dandadan", "https://mugiwarasoficial.com/manga/dandadan/"
            )
            assert len(chapters) == 3

            # User selects chapter 50
            selected_chapter = chapters[0]
            assert selected_chapter["number"] == "50"

            # Fetch pages for selected chapter
            mock_page.content.return_value = mock_mugiwaras_pages_html
            pages = mugiwaras_scraper.get_chapter_pages(
                selected_chapter["id"], selected_chapter["url"]
            )

            assert len(pages) == 3
            assert all(url.startswith("http") for url in pages)


class TestMugiwarasPluginLoading:
    """Test plugin loading functionality."""

    def test_plugin_has_required_attributes(self, mugiwaras_scraper):
        """Plugin should have required attributes."""
        assert hasattr(mugiwaras_scraper, "name")
        assert hasattr(mugiwaras_scraper, "languages")
        assert mugiwaras_scraper.name == "mugiwaras"
        assert "pt-br" in mugiwaras_scraper.languages

    def test_plugin_has_required_methods(self, mugiwaras_scraper):
        """Plugin should implement required methods."""
        assert hasattr(mugiwaras_scraper, "search_manga")
        assert hasattr(mugiwaras_scraper, "get_chapters")
        assert hasattr(mugiwaras_scraper, "get_chapter_pages")
        assert callable(mugiwaras_scraper.search_manga)
        assert callable(mugiwaras_scraper.get_chapters)
        assert callable(mugiwaras_scraper.get_chapter_pages)

    def test_load_function_returns_plugin_for_pt_br(self):
        """Plugin loader should return plugin for pt-br language."""
        from manga_scrapers.plugins.mugiwaras import load

        plugin = load(set("pt-br"))
        assert plugin is not None
        assert isinstance(plugin, MugiwarasOficial)

    def test_load_function_returns_none_for_other_languages(self):
        """Plugin loader should return None for non-pt-br languages."""
        from manga_scrapers.plugins.mugiwaras import load

        plugin = load({"en", "ja"})
        assert plugin is None
