"""Tests for AnimesDigital scraper fallback logging behavior."""

import logging
from unittest.mock import MagicMock, patch

import requests

from scrapers.plugins.animesdigital import AnimesDigital


def _http_error_response() -> MagicMock:
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError(
        "500 Server Error: Internal Server Error for url: https://animesdigital.org/home"
    )
    return response


class TestAnimesDigitalFallbackLogging:
    def setup_method(self):
        self.scraper = AnimesDigital()

    @patch("scrapers.plugins.animesdigital.requests.get")
    def test_homepage_http_error_returns_empty_without_warning(self, mock_get, caplog):
        mock_get.return_value = _http_error_response()

        with caplog.at_level(logging.WARNING):
            result = self.scraper.search_homepage_incremental("Liar Game")

        assert result == []
        assert "Error searching AnimesDigital homepage" not in caplog.text

    @patch.object(AnimesDigital, "search_homepage_incremental", return_value=[])
    @patch.object(AnimesDigital, "_scrape_series_page")
    @patch("scrapers.plugins.animesdigital.rep")
    def test_search_episodes_uses_silent_fallback_logs(
        self, mock_rep, mock_scrape_series_page, mock_homepage_search, caplog
    ):
        mock_rep.anime_episodes_urls.get.return_value = []

        with caplog.at_level(logging.WARNING):
            self.scraper.search_episodes("Liar Game", "https://animesdigital.org/anime/a/liar-game", None)

        assert "No episodes found for 'Liar Game' in series page scraping" not in caplog.text
        assert "No episodes found for 'Liar Game' even with DynamicFetcher scraping" not in caplog.text
        mock_scrape_series_page.assert_called_once()
        mock_homepage_search.assert_called_once_with("Liar Game", audio_type="legendado")
