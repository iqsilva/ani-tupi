import importlib
import logging
import sys
from os import listdir
from os.path import abspath, dirname, isfile, join
from typing import Protocol

from scrapling.fetchers import StealthyFetcher


class PluginProtocol(Protocol):
    """Protocol for anime scraper plugins.

    Plugins implementing this protocol provide anime search and playback functionality.
    Uses structural typing (duck typing) - no inheritance required.
    """

    name: str  # Plugin identifier (e.g., "animefire")
    languages: list[str]  # Supported languages (e.g., ["pt-br"])

    def search_anime(self, query: str) -> None:
        """Search for anime by title.

        Args:
            query: Search query string

        Must call: Repository.add_anime(title, url, source, params)
        """
        ...

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list for anime.

        Args:
            anime: Anime title
            url: Anime URL from search_anime
            params: Optional extra parameters from search_anime

        Must call: Repository.add_episode_list(anime, titles, urls, source)
        """
        ...

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video playback URL from episode URL.

        Args:
            url: Episode URL from search_episodes
            container: List to append video URL to
            event: asyncio.Event to signal completion

        Implementation:
            1. Extract video URL (m3u8 or mp4)
            2. container.append(url)
            3. event.set()
            4. Return immediately (runs in thread pool)
        """
        ...


# For backwards compatibility with existing code
# Note: PluginInterface alias removed to enforce structural typing


def get_resource_path(relative_path: str) -> str:
    """Get the path to resources, whether running as script or executable."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller executable
        meipass = getattr(sys, "_MEIPASS", "")
        return join(meipass, relative_path)
    # Use directory where this file is located (works for both dev and installed)
    return join(dirname(abspath(__file__)), relative_path)


def load_plugins(languages: dict, plugins: list[str] | None = None) -> None:
    """Load plugins based on preferences and language filters.

    Respects plugin priority order from preferences if configured.
    Plugins are loaded in priority order (highest priority first).

    Args:
        languages: Dict of supported languages (e.g., {"pt-br"})
        plugins: Optional list of specific plugins to load (overrides preferences)
                 If None, loads all plugins except disabled ones
    """
    # Configure StealthyFetcher globally once before loading any plugins
    # This enables adaptive mode for future-proof scraping
    StealthyFetcher.adaptive = True

    # Suppress the Scrapling deprecation warning about __init__ logic
    # This warning is unavoidable in v0.2.x and will be removed in v0.3
    logging.getLogger("scrapling").setLevel(logging.ERROR)

    path = get_resource_path("plugins/")
    system = {"__init__.py", "utils.py"}

    # Get all available plugin files
    all_plugin_files = [
        file[:-3] for file in listdir(path) if isfile(join(path, file)) and file not in system
    ]

    # Apply filtering based on configuration
    if plugins is None:
        # Get disabled plugins and priority order from settings
        from models.config import settings

        disabled_plugins = set(settings.plugins.disabled_plugins)

        # Filter out disabled plugins
        plugins = [p for p in all_plugin_files if p not in disabled_plugins]

        # Apply priority ordering if configured
        priority_order = settings.plugins.priority_order
        if priority_order:
            # Sort plugins by priority order
            # Plugins in priority_order come first (in order), others come after
            def priority_key(plugin):
                if plugin in priority_order:
                    return (0, priority_order.index(plugin))
                else:
                    return (1, plugin)

            plugins = sorted(plugins, key=priority_key)
    else:
        # Use explicit plugin list (for debug mode)
        pass

    # Load each enabled plugin
    for plugin in plugins:
        plugin_module = importlib.import_module("scrapers.plugins." + plugin)
        plugin_module.load(languages)
