"""Cache manager using unified cache system (backward compatibility).

DEPRECATED: This module is kept for backward compatibility only.
New code should use utils.cache directly.

Provides backward-compatible functions:
- Video URLs (biggest performance win: 7-15s → 100ms)
- Episode URLs
- Search results
- AniList metadata
"""

from typing import Optional

from utils.cache import (
    get_cache as _get_unified_cache,
    clear_cache_all as _clear_all,
    clear_cache_by_prefix as _clear_by_prefix,
)
from models.config import settings
from models.models import CacheStats


def get_cache():
    """Backward compatibility wrapper for unified cache."""
    return _get_unified_cache()


def default_ttl() -> int:
    """Default TTL in seconds."""
    return settings.performance.default_ttl_hours * 3600


def get_cached_video_url(cache_key, episode: int, source: Optional[str] = None) -> str | None:
    """Direct cache lookup for video URLs (without calling scraper)."""
    cache = _get_unified_cache()
    key = f"video:{cache_key}:{episode}:{source or 'any'}"
    return cache.get(key)


def save_video_url(cache_key, episode: int, source: str, url: str) -> None:
    """Manually save video URL to cache."""
    cache = _get_unified_cache()
    key = f"video:{cache_key}:{episode}:{source}"
    cache.set(key, url, ttl=default_ttl())


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


def get_cache_stats() -> CacheStats:
    """Get cache statistics."""
    cache = _get_unified_cache()
    return cache.get_stats()
