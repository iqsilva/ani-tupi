"""Startup check for Scrapling browser dependencies.

Only the anroll and animesdigital plugins require the browsers installed
via `scrapling install`. This check emits a friendly warning instead of
letting those plugins fail with an obscure error at fetch time.
"""

from __future__ import annotations

import functools

from utils.logging import get_logger

logger = get_logger(__name__)

INSTALL_HINT = (
    "Browsers do Scrapling não encontrados. As fontes 'anroll' e 'animesdigital' "
    "precisam deles. Execute: just scrapling-install (ou: uv run scrapling install)"
)


def _camoufox_installed() -> bool:
    """Check if the Camoufox browser (used by StealthyFetcher) is installed."""
    try:
        from camoufox.pkgman import installed_verstr

        installed_verstr()
        return True
    except Exception:
        return False


def _playwright_chromium_installed() -> bool:
    """Check if the Playwright Chromium browser (used by DynamicFetcher) is installed."""
    try:
        from pathlib import Path

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            executable = p.chromium.executable_path
            return bool(executable) and Path(executable).exists()
    except Exception:
        return False


@functools.cache
def browsers_available() -> bool:
    """Return True if the dynamic-fetcher browsers are installed (cached)."""
    return _camoufox_installed() and _playwright_chromium_installed()


def warn_if_browsers_missing() -> None:
    """Log a friendly warning when Scrapling browsers are not installed."""
    if not browsers_available():
        logger.warning(f"⚠️  {INSTALL_HINT}")
