"""
Unit tests for anitube scraper episode ordering with ?ord=1 parameter.
"""

from unittest.mock import MagicMock, patch
from scrapers.plugins.anitube import AniTube


class TestAnitubeEpisodeOrdering:
    """Test anitube scraper's handling of ?ord=1 parameter for episode ordering."""

    def test_ord_parameter_appended_to_clean_url(self):
        """Verify that ?ord=1 is appended to URLs without existing query parameters."""
        scraper = AniTube()

        with (
            patch("scrapers.plugins.anitube.SeleniumWebDriver") as mock_selenium,
            patch("scrapers.plugins.anitube.rep"),
        ):
            # Setup mock driver and page
            mock_driver = MagicMock()
            mock_page = MagicMock()

            # Mock the context manager
            mock_selenium.return_value.__enter__ = MagicMock(return_value=mock_driver)
            mock_selenium.return_value.__exit__ = MagicMock(return_value=None)
            mock_driver.fetch.return_value = mock_page
            mock_page.select.return_value = []

            # Call search_episodes with a clean URL
            base_url = "https://www.anitube.news/video/1030751/"
            scraper.search_episodes("Test Anime", base_url, None)

            # Verify that driver.fetch was called with the URL + ?ord=1
            expected_url = "https://www.anitube.news/video/1030751/?ord=1"
            mock_driver.fetch.assert_called_once_with(expected_url)

    def test_ord_parameter_appended_with_ampersand_to_existing_params(self):
        """Verify that ?ord=1 is appended with & when URL has existing query params."""
        scraper = AniTube()

        with (
            patch("scrapers.plugins.anitube.SeleniumWebDriver") as mock_selenium,
            patch("scrapers.plugins.anitube.rep"),
        ):
            # Setup mock driver and page
            mock_driver = MagicMock()
            mock_page = MagicMock()

            # Mock the context manager
            mock_selenium.return_value.__enter__ = MagicMock(return_value=mock_driver)
            mock_selenium.return_value.__exit__ = MagicMock(return_value=None)
            mock_driver.fetch.return_value = mock_page
            mock_page.select.return_value = []

            # Call search_episodes with a URL that already has query params
            base_url = "https://www.anitube.news/video/1030751/?existing=param"
            scraper.search_episodes("Test Anime", base_url, None)

            # Verify that driver.fetch was called with & separator
            expected_url = "https://www.anitube.news/video/1030751/?existing=param&ord=1"
            mock_driver.fetch.assert_called_once_with(expected_url)

    def test_episode_extraction_works_with_ord_parameter(self):
        """Verify that episode extraction still works correctly with ?ord=1."""
        scraper = AniTube()

        with (
            patch("scrapers.plugins.anitube.SeleniumWebDriver") as mock_selenium,
            patch("scrapers.plugins.anitube.rep") as mock_rep,
        ):
            # Setup mock driver and page with episode elements
            mock_driver = MagicMock()
            mock_page = MagicMock()

            # Mock the context manager
            mock_selenium.return_value.__enter__ = MagicMock(return_value=mock_driver)
            mock_selenium.return_value.__exit__ = MagicMock(return_value=None)
            mock_driver.fetch.return_value = mock_page

            # Create mock episode links
            mock_link1 = MagicMock()
            mock_link1.get.side_effect = lambda attr: {
                "href": "https://www.anitube.news/video/123/episode-1",
                "title": "Test Anime – Episódio 1",
            }.get(attr)

            mock_link2 = MagicMock()
            mock_link2.get.side_effect = lambda attr: {
                "href": "https://www.anitube.news/video/123/episode-2",
                "title": "Test Anime – Episódio 2",
            }.get(attr)

            mock_page.select.return_value = [mock_link1, mock_link2]

            # Call search_episodes
            base_url = "https://www.anitube.news/video/123/"
            scraper.search_episodes("Test Anime", base_url, None)

            # Verify that add_episode_list was called with extracted episodes
            mock_rep.add_episode_list.assert_called_once()
            call_args = mock_rep.add_episode_list.call_args

            # Check that titles and URLs were extracted
            assert len(call_args[0]) == 4  # anime, titles, urls, scraper_name
            assert isinstance(call_args[0][1], list)  # titles list
            assert isinstance(call_args[0][2], list)  # urls list
            assert len(call_args[0][1]) == 2  # 2 episodes
            assert len(call_args[0][2]) == 2  # 2 episodes  # 2 episodes
