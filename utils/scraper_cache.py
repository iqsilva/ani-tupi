"""Cache system for scraper results (wrapper for backward compatibility).

DEPRECATED: This module is kept for backward compatibility only.
New code should use utils.cache instead.

Cache settings (location, duration) are configured in config.py
"""

from utils.cache import get_cache as _get_unified_cache, clear_cache_all, clear_cache_by_prefix
from utils.anilist_discovery import get_anilist_id_from_title
from models.models import ScraperCacheData


def get_cache(anime_title: str) -> ScraperCacheData | None:
    """Get cached scraper data for an anime (backward compatibility wrapper).

    Args:
        anime_title: Normalized anime title

    Returns:
        ScraperCacheData with episode_urls and episode_count or None if not found

    """
    from models.config import settings

    # Check if episodes cache is enabled
    if not settings.cache.episodes_cache_enabled:
        return None

    try:
        # Try to discover AniList ID for better cache lookup
        anilist_id = get_anilist_id_from_title(anime_title)

        if anilist_id:
            cache_key = f"episodes:{anilist_id}"
        else:
            cache_key = f"episodes:{anime_title}"

        # Get from unified cache system
        cache_obj = _get_unified_cache()
        cached_urls = cache_obj.get(cache_key)

        if cached_urls and isinstance(cached_urls, list):
            return ScraperCacheData(
                episode_urls=cached_urls,  # type: ignore[arg-type]  # unified cache returns Any
                episode_count=len(cached_urls),
                timestamp=0,  # Not used in new system
            )

        return None

    except Exception:
        return None


def set_cache(anime_title: str, episode_count: int, episode_urls: list[str]) -> None:
    """Save scraper results to cache (backward compatibility wrapper).

    Args:
        anime_title: Normalized anime title
        episode_count: Number of episodes found
        episode_urls: List of episode URLs

    """
    from models.config import settings

    # Check if episodes cache is enabled
    if not settings.cache.episodes_cache_enabled:
        return

    try:
        cache_obj = _get_unified_cache()

        # Try to discover AniList ID for better cache key
        anilist_id = get_anilist_id_from_title(anime_title)

        if anilist_id:
            cache_key = f"episodes:{anilist_id}"
        else:
            cache_key = f"episodes:{anime_title}"

        # Save to unified cache system
        cache_obj.set(cache_key, episode_urls, ttl=settings.performance.default_ttl_hours * 3600)

    except Exception:
        pass  # Silent fail - cache is optional


def clear_cache(anime_title: str | None = None) -> None:
    """Clear cache for specific anime or all cache (backward compatibility wrapper).

    Args:
        anime_title: Anime to clear, or None to clear all

    """
    try:
        if anime_title is None:
            # Clear all cache
            clear_cache_all()
        else:
            # Try to discover AniList ID for precise clearing
            anilist_id = get_anilist_id_from_title(anime_title)

            if anilist_id:
                clear_cache_by_prefix(f":{anilist_id}:")
            else:
                clear_cache_by_prefix(f":{anime_title}:")

    except Exception:
        pass  # Silent fail
