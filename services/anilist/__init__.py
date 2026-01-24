"""AniList service modules - GraphQL API client and operations.

This package provides:
- AniListClient: Complete GraphQL client with auth and operations
- Title formatting utilities
- Anime operations (trending, lists, search, sync)
- Manga operations (trending, lists, search, sync)
"""

from .client import AniListClient
from .formatters import format_title, get_search_title

# Global singleton instance for backward compatibility
anilist_client = AniListClient()

__all__ = ["AniListClient", "anilist_client", "format_title", "get_search_title"]
