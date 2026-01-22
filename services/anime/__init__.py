"""Anime service modules - business logic for anime operations.

This package provides:
- Title normalization and search helpers
- AniList integration flows
- Source management
- Episode navigation
- Mapping persistence
"""

from .title_normalization import normalize_anime_title
from .mappings import (
    load_anilist_mapping,
    save_anilist_mapping,
    load_anilist_search_title,
)
from .episode_context import get_next_episode_context
from .anilist_integration import (
    offer_sequel_and_continue,
    anilist_anime_flow,
)
from .source_management import switch_anime_source
from .search import search_anime_flow

__all__ = [
    "normalize_anime_title",
    "load_anilist_mapping",
    "save_anilist_mapping",
    "load_anilist_search_title",
    "get_next_episode_context",
    "offer_sequel_and_continue",
    "anilist_anime_flow",
    "switch_anime_source",
    "search_anime_flow",
]
