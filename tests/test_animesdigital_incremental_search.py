"""Tests for AnimesDigital incremental search on homepage.

Tests cover:
- Homepage parsing of episode links
- Title extraction from HTML
- Episode number parsing
- Incremental search with fuzzy matching
- Timeout and error handling
"""

from unittest.mock import MagicMock, patch

import requests

from scrapers.plugins.animesdigital import AnimesDigital


class TestAnimesDigitalIncrementalSearch:
    """Tests for AnimesDigital.search_homepage_incremental method."""

    def setup_method(self):
        """Set up test scraper."""
        self.scraper = AnimesDigital()

    def _create_html_for_episode(self, title_text: str, episode_url: str) -> str:
        """Helper to create HTML for a single episode link."""
        return f"""
        <a href="{episode_url}">
            <img src="image.jpg" title="{title_text}" />
            HD
        </a>
        """

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_single_word_search(self, mock_get):
        """Test search with single-word title."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Jujutsu Kaisen Season 2 Episódio 25",
                "https://animesdigital.org/video/a/123456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu")

        assert len(result) == 1
        assert result[0]["anime_title"] == "Jujutsu Kaisen Season 2"
        assert result[0]["episode_number"] == 25

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_multi_word_incremental_search(self, mock_get):
        """Test incremental search with multi-word title."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Jujutsu Kaisen Season 2 Episódio 25",
                "https://animesdigital.org/video/a/123456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu Kaisen Season 2")

        assert len(result) == 1
        assert result[0]["anime_title"] == "Jujutsu Kaisen Season 2"

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_no_matches_returns_empty(self, mock_get):
        """Test that unmatched search returns empty list."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Dandadan Episódio 18",
                "https://animesdigital.org/video/a/123456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Completely Different")

        assert result == []

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_no_episode_links_returns_empty(self, mock_get):
        """Test that empty episode list returns empty result."""
        html = "<html><body><p>No episodes</p></body></html>"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Any Title")

        assert result == []

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_multiple_episodes_same_anime(self, mock_get):
        """Test that multiple episodes of same anime are included."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Jujutsu Kaisen Season 2 Episódio 24",
                "https://animesdigital.org/video/a/123455/",
            )
            + self._create_html_for_episode(
                "Jujutsu Kaisen Season 2 Episódio 25",
                "https://animesdigital.org/video/a/123456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu Kaisen")

        assert len(result) == 2
        episodes = {ep["episode_number"] for ep in result}
        assert 24 in episodes and 25 in episodes

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_timeout_returns_empty(self, mock_get):
        """Test that timeout returns empty list gracefully."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = self.scraper.search_homepage_incremental("Any Title")

        assert result == []

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_general_exception_returns_empty(self, mock_get):
        """Test that general errors return empty list gracefully."""
        mock_get.side_effect = Exception("Test error")

        result = self.scraper.search_homepage_incremental("Any Title")

        assert result == []

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_missing_img_tag_skipped(self, mock_get):
        """Test that links without img tags are skipped."""
        html = (
            "<html><body>"
            '<a href="https://animesdigital.org/video/a/123/">'
            "  <span>No image</span>"
            "</a>"
            + self._create_html_for_episode(
                "Jujutsu Kaisen Episódio 25",
                "https://animesdigital.org/video/a/456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu")

        assert len(result) == 1
        assert result[0]["episode_number"] == 25

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_missing_episode_number_skipped(self, mock_get):
        """Test that links without valid episode numbers are skipped."""
        html = (
            "<html><body>"
            '<a href="https://animesdigital.org/video/a/123/">'
            '<img title="Jujutsu Kaisen (no episode number)" />'
            "</a>"
            "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu")

        assert result == []

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_limits_results_to_five(self, mock_get):
        """Test that results are limited to 5 when many matches exist."""
        links_html = "".join(
            [
                self._create_html_for_episode(
                    f"Attack on Titan Episódio {i}",
                    f"https://animesdigital.org/video/a/{1000 + i}/",
                )
                for i in range(1, 11)
            ]
        )
        html = f"<html><body>{links_html}</body></html>"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Attack")

        # Should be limited to 5
        assert len(result) <= 5

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_relative_url_conversion(self, mock_get):
        """Test that relative URLs are converted to absolute."""
        html = (
            "<html><body>"
            '<a href="/video/a/123456/">'
            '<img title="Jujutsu Kaisen Episódio 25" />'
            "</a>"
            "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental("Jujutsu")

        assert len(result) == 1
        assert result[0]["episode_url"].startswith("https://animesdigital.org")

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_filters_duplicate_anime_versions(self, mock_get):
        """Test that when same anime exists in both dubbed and subtitled versions,
        only the best-matching version is returned.

        This prevents duplicates when searching for "Anime Title Dublado" returns
        both the dubbed and subtitled versions.
        """
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Seihantai na Kimi to Boku Dublado Episódio 6",
                "https://animesdigital.org/video/a/123456/",
            )
            + self._create_html_for_episode(
                "Seihantai na Kimi to Boku Episódio 6",
                "https://animesdigital.org/video/a/654321/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        # Search for the dubbed version
        result = self.scraper.search_homepage_incremental(
            "Seihantai na Kimi to Boku Dublado", audio_type="dublado"
        )

        # Should return only 1 episode (the dubbed version, filtered by audio_type)
        assert len(result) == 1
        assert "Dublado" in result[0]["anime_title"]
        assert result[0]["episode_number"] == 6
