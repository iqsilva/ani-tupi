"""Anime service layer - backward compatibility shim.

This module maintains backward compatibility by re-exporting functions
from the new modular anime service structure.

All business logic has been extracted to focused modules:
- anilist_integration.py: AniList anime flows and sequel detection
- source_management.py: Source switching logic
- search.py: Manual anime search
- episode_context.py: Episode navigation helpers
- title_normalization.py: Title processing
- mappings.py: AniList ID to scraper title mapping

New code should import from services.anime directly:
    from services.anime import anilist_anime_flow, search_anime_flow
"""

from services.anime.title_normalization import normalize_anime_title
from services.anime.mappings import (
    load_anilist_mapping,
    save_anilist_mapping,
    load_anilist_search_title,
)
from services.anime.episode_context import get_next_episode_context
from services.anime.anilist_integration import (
    offer_sequel_and_continue,
    anilist_anime_flow,
)
from services.anime.source_management import switch_anime_source
from services.anime.search import (
    search_anime_flow,
    SearchResultSet,
    IncrementalSearchState,
    incremental_search_anime,
)

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
    "SearchResultSet",
    "IncrementalSearchState",
    "incremental_search_anime",
]
