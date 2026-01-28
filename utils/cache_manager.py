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
from functools import wraps

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


def cache_video_url(func):
    """Decorator to cache video URLs (m3u8/mp4 streaming).

    This is BIGGEST performance win: 7-15 seconds → <100ms!
    """

    @wraps(func)
    def wrapper(cache_key, episode: int, source: Optional[str] = None):
        """Wrapper that checks cache before calling expensive Selenium.

        Args:
            cache_key: anilist_id (int) or anime_title (str) fallback
            episode: Episode number
            source: Scraper source (animefire, animesonlinecc, etc)

        Returns:
            Video URL (m3u8 or mp4)
        """
        cache = _get_unified_cache()
        key = f"video:{cache_key}:{episode}:{source or 'any'}"

        # Check cache first
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - run expensive Selenium operation
        result = func(cache_key, episode, source)

        if result:
            # Save to cache
            cache.set(key, result, ttl=default_ttl())

        return result

    return wrapper


def cache_episodes(func):
    """Decorator to cache episode URL lists."""

    @wraps(func)
    def wrapper(cache_key):
        """Wrapper for episode list caching.

        Args:
            cache_key: anilist_id (int) or anime_title (str)

        Returns:
            Tuple of (episode_titles, episode_urls)
        """
        cache = _get_unified_cache()
        key = f"episodes:{cache_key}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch from scrapers
        result = func(cache_key)

        if result:
            cache.set(key, result, ttl=default_ttl())

        return result

    return wrapper


def cache_search_results(func):
    """Decorator to cache anime search results."""

    @wraps(func)
    def wrapper(query: str):
        """Wrapper for search result caching.

        Args:
            query: Search query string

        Returns:
            Dict of {anime_title: [(url, source, params)]}
        """
        cache = _get_unified_cache()
        key = f"search:{query.lower()}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - search scrapers
        result = func(query)

        if result:
            cache.set(key, result, ttl=default_ttl())

        return result

    return wrapper


def cache_anilist_metadata(func):
    """Decorator to cache AniList metadata (avoiding API calls)."""

    @wraps(func)
    def wrapper(anilist_id: int):
        """Wrapper for AniList metadata caching.

        Args:
            anilist_id: AniList ID

        Returns:
            Dict with title, cover, description, score, etc
        """
        cache = _get_unified_cache()
        key = f"anilist_meta:{anilist_id}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch from AniList API
        result = func(anilist_id)

        if result:
            cache.set(key, result, ttl=2592000)  # 30 days for metadata

        return result

    return wrapper


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
    """Clear entire cache, including mappings and history."""
    # Use unified cache clear
    _clear_all()


def clear_cache_by_prefix(prefix: str) -> None:
    """Clear cache entries by prefix."""
    # Use unified cache prefix clear
    _clear_by_prefix(prefix)


def get_cache_stats() -> CacheStats:
    """Get cache statistics."""
    cache = _get_unified_cache()
    return cache.get_stats()
    return _cache


def default_ttl() -> int:
    """Default TTL in seconds."""
    return settings.performance.default_ttl_hours * 3600


def cache_video_url(func):
    """Decorator to cache video URLs (m3u8/mp4 streaming).

    This is the BIGGEST performance win: 7-15 seconds → <100ms!
    """

    def wrapper(cache_key, episode: int, source: Optional[str] = None):
        """Wrapper that checks cache before calling expensive Selenium.

        Args:
            cache_key: anilist_id (int) or anime_title (str) fallback
            episode: Episode number
            source: Scraper source (animefire, animesonlinecc, etc)

        Returns:
            Video URL (m3u8 or mp4)
        """
        cache = get_cache()
        key = f"video:{cache_key}:{episode}:{source or 'any'}"

        # Check cache first
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - run expensive Selenium operation
        result = func(cache_key, episode, source)

        if result:
            # Save to cache
            cache.set(key, result, expire=default_ttl())

        return result

    return wrapper


def cache_episodes(func):
    """Decorator to cache episode URL lists."""

    def wrapper(cache_key):
        """Wrapper for episode list caching.

        Args:
            cache_key: anilist_id (int) or anime_title (str)

        Returns:
            Tuple of (episode_titles, episode_urls)
        """
        cache = get_cache()
        key = f"episodes:{cache_key}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch from scrapers
        result = func(cache_key)

        if result:
            cache.set(key, result, expire=default_ttl())

        return result

    return wrapper


def cache_search_results(func):
    """Decorator to cache anime search results."""

    def wrapper(query: str):
        """Wrapper for search result caching.

        Args:
            query: Search query string

        Returns:
            Dict of {anime_title: [(url, source, params)]}
        """
        cache = get_cache()
        key = f"search:{query.lower()}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - search scrapers
        result = func(query)

        if result:
            cache.set(key, result, expire=default_ttl())

        return result

    return wrapper


def cache_anilist_metadata(func):
    """Decorator to cache AniList metadata (avoiding API calls)."""

    def wrapper(anilist_id: int):
        """Wrapper for AniList metadata caching.

        Args:
            anilist_id: AniList ID

        Returns:
            Dict with title, cover, description, score, etc
        """
        cache = get_cache()
        key = f"anilist_meta:{anilist_id}"

        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cache miss - fetch from AniList API
        result = func(anilist_id)

        if result:
            cache.set(key, result, expire=2592000)  # 30 days for metadata

        return result

    return wrapper


def get_cached_video_url(cache_key, episode: int, source: Optional[str] = None) -> str | None:
    """Direct cache lookup for video URLs (without calling scraper)."""
    cache = get_cache()
    key = f"video:{cache_key}:{episode}:{source or 'any'}"
    return cache.get(key)  # type: ignore[return-value]  # diskcache returns Any


def save_video_url(cache_key, episode: int, source: str, url: str) -> None:
    """Manually save video URL to cache."""
    cache = get_cache()
    key = f"video:{cache_key}:{episode}:{source}"
    cache.set(key, url, expire=default_ttl())


def clear_cache_all() -> None:
    """Clear entire cache, including mappings and history."""
    from models.config import get_data_path
    import os

    # Clear diskcache (SQLite files)
    cache = get_cache()
    cache.clear()

    # Delete JSON-based state files
    data_path = get_data_path()
    files_to_delete = [
        data_path / "anilist_mappings.json",
        data_path / "history.json",
    ]

    for file_path in files_to_delete:
        if file_path.exists():
            try:
                os.remove(file_path)
            except OSError:
                # Ignore errors if file is locked, etc.
                pass


def clear_cache_by_prefix(prefix: str) -> None:
    """Clear cache entries by prefix.

    Examples:
        clear_cache_by_prefix("video:123456:")  # Clear all videos for anilist_id
        clear_cache_by_prefix("episodes:123456:")  # Clear episodes
        clear_cache_by_prefix("search:")  # Clear all search results
    """
    cache = get_cache()
    keys_to_delete = []

    for key in cache.iterkeys():
        if key.startswith(prefix):
            keys_to_delete.append(key)

    for key in keys_to_delete:
        cache.delete(key)


def get_cache_stats() -> CacheStats:
    """Get cache statistics."""
    cache = get_cache()
    return CacheStats(
        size=len(cache),
        total_items=sum(1 for _ in cache.iterkeys()),
    )
