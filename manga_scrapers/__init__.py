"""Manga scraper plugin system.

Provides dynamic loading for manga sources with a plugin architecture.
"""

from .loader import MangaScraperProtocol, load_manga_plugins

__all__ = ["MangaScraperProtocol", "load_manga_plugins"]
