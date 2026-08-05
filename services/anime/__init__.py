"""Anime service modules - business logic for anime operations."""

from .title_normalization import normalize_anime_title
from .mappings import (
    load_anilist_mapping,
    save_anilist_mapping,
    load_anilist_search_title,
)
from .episode_context import get_next_episode_context
from .source_management import switch_anime_source
from .search import search_anime_flow
from .progress_service import (
    EpisodeProgressInfo,
    ProgressContext,
    get_episode_progress_info,
    calculate_watch_context,
)
from .playback_service import (
    PlaybackContext,
    EpisodePlaybackResult,
    prepare_playback_from_search,
    prepare_playback_from_history,
    get_episode_url_and_source,
    navigate_episodes,
)

__all__ = [
    'normalize_anime_title',
    'load_anilist_mapping',
    'save_anilist_mapping',
    'load_anilist_search_title',
    'get_next_episode_context',
    'switch_anime_source',
    'search_anime_flow',
    'EpisodeProgressInfo',
    'ProgressContext',
    'get_episode_progress_info',
    'calculate_watch_context',
    'PlaybackContext',
    'EpisodePlaybackResult',
    'prepare_playback_from_search',
    'prepare_playback_from_history',
    'get_episode_url_and_source',
    'navigate_episodes',
]
