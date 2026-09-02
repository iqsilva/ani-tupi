"""Tests for the Scrapling browser availability startup check."""

from unittest.mock import patch

from scrapers.core import browser_check


def setup_function():
    browser_check.browsers_available.cache_clear()


def test_warns_when_camoufox_missing():
    with (
        patch.object(browser_check, "_camoufox_installed", return_value=False),
        patch.object(browser_check.logger, "warning") as mock_warn,
    ):
        browser_check.warn_if_browsers_missing()

    mock_warn.assert_called_once()
    assert browser_check.INSTALL_HINT in mock_warn.call_args.args[0]


def test_warns_when_chromium_missing():
    with (
        patch.object(browser_check, "_camoufox_installed", return_value=True),
        patch.object(browser_check, "_playwright_chromium_installed", return_value=False),
        patch.object(browser_check.logger, "warning") as mock_warn,
    ):
        browser_check.warn_if_browsers_missing()

    mock_warn.assert_called_once()


def test_silent_when_browsers_present():
    with (
        patch.object(browser_check, "_fetchers_extra_installed", return_value=True),
        patch.object(browser_check, "_camoufox_installed", return_value=True),
        patch.object(browser_check, "_playwright_chromium_installed", return_value=True),
        patch.object(browser_check.logger, "warning") as mock_warn,
    ):
        browser_check.warn_if_browsers_missing()

    mock_warn.assert_not_called()


def test_result_is_cached():
    with (
        patch.object(browser_check, "_fetchers_extra_installed", return_value=True),
        patch.object(
            browser_check, "_camoufox_installed", return_value=True
        ) as mock_camoufox,
        patch.object(browser_check, "_playwright_chromium_installed", return_value=True),
    ):
        browser_check.browsers_available()
        browser_check.browsers_available()

    mock_camoufox.assert_called_once()
