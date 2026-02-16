"""Tests for AnimesDigital audio type filtering (Dublado vs Legendado).

Verifies that homepage search correctly filters results based on audio type
when both dubbed and subtitled versions of the same anime exist.
"""

from unittest.mock import MagicMock, patch

from scrapers.plugins.animesdigital import AnimesDigital


class TestAnimesDigitalAudioFilter:
    """Tests for audio type filtering in homepage search."""

    def setup_method(self):
        """Set up test scraper."""
        self.scraper = AnimesDigital()

    def _create_html_for_episode(self, title_text: str, episode_url: str) -> str:
        """Helper to create HTML for a single episode link."""
        return f'''
        <a href="{episode_url}">
            <img src="image.jpg" title="{title_text}" />
            HD
        </a>
        '''

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_filters_legendado_when_searching_dublado(self, mock_get):
        """When searching for "Dublado", should exclude "Legendado" episodes."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Dublado Episódio 7",
                "https://animesdigital.org/video/a/123456/",
            )
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Legendado Episódio 7",
                "https://animesdigital.org/video/a/123457/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental(
            "Vigilante Boku no Hero Academia Illegals 2", audio_type="dublado"
        )

        # Should only find the Dublado episode
        assert len(result) == 1
        assert "Dublado" in result[0]["anime_title"]
        assert "Legendado" not in result[0]["anime_title"]

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_filters_dublado_when_searching_legendado(self, mock_get):
        """When searching for "Legendado", should exclude "Dublado" episodes."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Dublado Episódio 7",
                "https://animesdigital.org/video/a/123456/",
            )
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Legendado Episódio 7",
                "https://animesdigital.org/video/a/123457/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental(
            "Vigilante Boku no Hero Academia Illegals 2", audio_type="legendado"
        )

        # Should only find the Legendado episode
        assert len(result) == 1
        assert "Legendado" in result[0]["anime_title"]
        assert "Dublado" not in result[0]["anime_title"]

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_accepts_unmarked_episodes_as_legendado(self, mock_get):
        """Unmarked episodes are treated as Legendado (default).

        In practice:
        - Dublado episodes ALWAYS have "Dublado" in title
        - Legendado episodes usually DON'T have "Legendado" in title (it's the default)
        """
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Jujutsu Kaisen Season 2 Episódio 25",  # No audio marker
                "https://animesdigital.org/video/a/123456/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        # Unmarked episodes are treated as Legendado (default)
        result_legendado = self.scraper.search_homepage_incremental(
            "Jujutsu Kaisen", audio_type="legendado"
        )
        result_dublado = self.scraper.search_homepage_incremental(
            "Jujutsu Kaisen", audio_type="dublado"
        )

        # Legendado accepts unmarked episodes (default behavior)
        assert len(result_legendado) == 1
        # Dublado requires explicit "Dublado" marker (rejects unmarked)
        assert len(result_dublado) == 0

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_prefers_explicit_marker_over_unmarked(self, mock_get):
        """When both marked and unmarked episodes exist, prefer explicit marker."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Dublado Episódio 7",
                "https://animesdigital.org/video/a/123456/",
            )
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Episódio 8",  # Unmarked
                "https://animesdigital.org/video/a/123458/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental(
            "Vigilante Boku no Hero Academia Illegals 2", audio_type="dublado"
        )

        # Should only include the explicitly marked Dublado episode
        assert len(result) == 1
        assert "Dublado" in result[0]["anime_title"]

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_returns_empty_when_no_matching_audio_type(self, mock_get):
        """When only wrong audio type exists, return empty list."""
        html = (
            "<html><body>"
            + self._create_html_for_episode(
                "Vigilante Boku no Hero Academia Illegals 2 Legendado Episódio 7",
                "https://animesdigital.org/video/a/123457/",
            )
            + "</body></html>"
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html
        mock_get.return_value = mock_response

        result = self.scraper.search_homepage_incremental(
            "Vigilante Boku no Hero Academia Illegals 2", audio_type="dublado"
        )

        # Should not return Legendado episode when searching for Dublado
        assert len(result) == 0
