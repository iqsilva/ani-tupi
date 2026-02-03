"""Tests for AnimesDigital scraper with browser pool integration.

Verifies that:
- AnimesDigital uses browser pool instead of creating raw WebDriver
- Pool allocation errors are handled gracefully
- Browser reuse improves resource efficiency
"""

from unittest.mock import patch, MagicMock

from scrapers.plugins.animesdigital import AnimesDigital
from scrapers.core.browser_pool import browser_pool, BrowserPoolExhausted


class TestAnimesDigitalPoolIntegration:
    """Test AnimesDigital integration with browser pool."""

    def test_search_uses_browser_pool(self):
        """AnimesDigital search uses browser pool context manager."""
        scraper = AnimesDigital()

        # Mock the browser pool to verify it's being called
        with patch.object(browser_pool, "get_chrome") as mock_get_chrome:
            mock_driver = MagicMock()
            mock_driver.page_source = "<html></html>"
            mock_get_chrome.return_value.__enter__.return_value = mock_driver
            mock_get_chrome.return_value.__exit__.return_value = None

            # Call _search_with_selenium
            scraper._search_with_selenium("test query", "http://example.com")

            # Verify browser_pool.get_chrome was called
            mock_get_chrome.assert_called_once()
            call_kwargs = mock_get_chrome.call_args[1]
            assert call_kwargs.get("timeout") == 10

    def test_search_handles_pool_exhaustion(self):
        """AnimesDigital gracefully handles pool exhaustion."""
        scraper = AnimesDigital()

        # Mock pool to raise BrowserPoolExhausted
        with patch.object(
            browser_pool, "get_chrome", side_effect=BrowserPoolExhausted("Pool full")
        ):
            results = scraper._search_with_selenium("test query", "http://example.com")

            # Should return empty list on pool exhaustion
            assert results == []

    def test_search_handles_selenium_errors(self):
        """AnimesDigital handles Selenium errors gracefully."""
        scraper = AnimesDigital()

        # Mock driver to raise error
        with patch.object(browser_pool, "get_chrome") as mock_get_chrome:
            mock_driver = MagicMock()
            mock_driver.get.side_effect = Exception("Selenium error")
            mock_get_chrome.return_value.__enter__.return_value = mock_driver
            mock_get_chrome.return_value.__exit__.return_value = None

            results = scraper._search_with_selenium("test query", "http://example.com")

            # Should return empty list on error
            assert results == []

    def test_search_anime_uses_selenium_search(self):
        """search_anime uses _search_with_selenium with browser pool."""
        scraper = AnimesDigital()

        with patch.object(scraper, "_search_with_selenium", return_value=[]) as mock_search:
            with patch("scrapers.plugins.animesdigital.rep"):
                scraper.search_anime("test anime")

                # Verify _search_with_selenium was called for each URL
                assert mock_search.call_count == 2  # Two search URLs

    def test_pool_reuse_across_calls(self):
        """Multiple search calls reuse browser pool."""
        scraper = AnimesDigital()

        with patch.object(browser_pool, "get_chrome") as mock_get_chrome:
            mock_driver = MagicMock()
            mock_driver.page_source = "<html></html>"
            mock_get_chrome.return_value.__enter__.return_value = mock_driver
            mock_get_chrome.return_value.__exit__.return_value = None

            # Make multiple searches
            scraper._search_with_selenium("query1", "http://example.com")
            scraper._search_with_selenium("query2", "http://example.com")

            # Both should use get_chrome from pool
            assert mock_get_chrome.call_count == 2
            # Verify same context manager interface used
            assert mock_get_chrome.return_value.__enter__.call_count == 2


class TestAnimesDigitalErrorHandling:
    """Test error handling in AnimesDigital with pool."""

    def test_network_error_recovery(self):
        """Network errors don't crash the scraper."""
        scraper = AnimesDigital()

        with patch.object(browser_pool, "get_chrome") as mock_get_chrome:
            # Simulate network timeout
            mock_driver = MagicMock()
            mock_driver.get.side_effect = TimeoutError("Connection timeout")
            mock_get_chrome.return_value.__enter__.return_value = mock_driver
            mock_get_chrome.return_value.__exit__.return_value = None

            # Should not raise, just return empty list
            results = scraper._search_with_selenium("test", "http://example.com")
            assert isinstance(results, list)

    def test_page_load_error_recovery(self):
        """Page load errors are handled gracefully."""
        scraper = AnimesDigital()

        with patch.object(browser_pool, "get_chrome") as mock_get_chrome:
            mock_driver = MagicMock()
            # Simulate page element not found
            from selenium.common.exceptions import TimeoutException

            mock_driver.get.side_effect = TimeoutException("Element not found")
            mock_get_chrome.return_value.__enter__.return_value = mock_driver
            mock_get_chrome.return_value.__exit__.return_value = None

            results = scraper._search_with_selenium("test", "http://example.com")
            # Should return empty list, not crash
            assert results == []
