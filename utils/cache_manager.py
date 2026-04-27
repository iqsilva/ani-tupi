"""Cache manager using unified cache system (backward compatibility).

DEPRECATED: This module is kept for backward compatibility only.
New code should use utils.cache directly.

Provides backward-compatible functions:
- Video URLs (biggest performance win: 7-15s → 100ms)
- Episode URLs
- Search results
- AniList metadata
"""

from utils.cache import (
    get_cache as _get_unified_cache,
    clear_cache_all as _clear_all,
    clear_cache_by_prefix as _clear_by_prefix,
)


def get_cache():
    """Backward compatibility wrapper for unified cache."""
    return _get_unified_cache()


def clear_cache_all() -> None:
    """Clear entire cache and saved AniList mapping state."""
    # Use unified cache clear
    _clear_all()

    from services.anime.mappings import clear_anilist_mapping

    clear_anilist_mapping()


def clear_cache_by_prefix(prefix: str) -> None:
    """Clear cache entries by prefix."""
    # Use unified cache prefix clear
    _clear_by_prefix(prefix)
