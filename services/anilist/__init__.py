"""AniList service modules - GraphQL API client and operations.

This package provides:
- AniList API client (auth, queries, mutations)
- Title formatting utilities
- Anime operations (trending, lists, search, sync)
- Manga operations (trending, lists, search, sync)
"""

from .formatters import format_title, get_search_title

__all__ = ["format_title", "get_search_title"]
