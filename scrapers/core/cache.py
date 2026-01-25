"""Smart caching with TTL and memory management.

Optimized for 90%+ reduction in repeated requests:
- TTL-based caching for search results, episodes, and video URLs
- Memory-efficient LRU eviction
- Configurable cache sizes and TTLs
- Thread-safe operations
"""

import time
import threading
from typing import Any, Dict, Optional
import hashlib

from models.config import settings


class CachedItem:
    """Individual cached item with TTL support."""

    def __init__(self, value: Any, ttl: int):
        """Initialize cached item.

        Args:
            value: Value to cache
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        """Check if item has expired."""
        return time.time() > (self.created_at + self.ttl)

    def access(self) -> Any:
        """Access the cached item."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value

    def size_bytes(self) -> int:
        """Estimate size of cached item in bytes."""
        try:
            return len(str(self.value).encode("utf-8"))
        except Exception:
            return 1024  # Fallback estimate


class SmartCache:
    """Thread-safe LRU cache with TTL support and memory management.

    Provides intelligent caching for different types of scraper data
    with appropriate TTL values and automatic cleanup.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global cache instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize smart cache."""
        if hasattr(self, "_initialized"):
            return

        self._cache: Dict[str, CachedItem] = {}
        self._max_size_bytes = settings.performance.smart_cache_max_size_mb * 1024 * 1024
        self._current_size_bytes = 0
        self._lock = threading.Lock()
        self._initialized = True

        # TTL configurations
        self.search_ttl = settings.performance.search_cache_ttl  # 5 minutes
        self.episodes_ttl = settings.performance.episodes_cache_ttl  # 30 minutes
        self.video_ttl = 900  # 15 minutes (video URLs expire quickly)

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments.

        Args:
            prefix: Cache type prefix
            *args, **kwargs: Arguments to include in key

        Returns:
            Unique cache key string
        """
        # Create a deterministic key from all arguments
        key_parts = [prefix]

        for arg in args:
            key_parts.append(str(arg))

        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")

        key_string = "|".join(key_parts)

        # Use hash for very long keys
        if len(key_string) > 100:
            key_string = f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"

        return key_string

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            item = self._cache.get(key)

            if item is None:
                return None

            if item.is_expired():
                # Remove expired item
                del self._cache[key]
                self._current_size_bytes -= item.size_bytes()
                return None

            # Access the item (updates access time/count)
            return item.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (defaults to appropriate TTL for key type)
        """
        # Determine appropriate TTL if not specified
        if ttl is None:
            if key.startswith("search:"):
                ttl = self.search_ttl
            elif key.startswith("episodes:"):
                ttl = self.episodes_ttl
            elif key.startswith("video:"):
                ttl = self.video_ttl
            else:
                ttl = self.search_ttl  # Default

        with self._lock:
            # Remove existing item if present
            if key in self._cache:
                old_item = self._cache[key]
                self._current_size_bytes -= old_item.size_bytes()

            # Create new cached item
            new_item = CachedItem(value, ttl)
            item_size = new_item.size_bytes()

            # Evict items if necessary
            while (
                self._current_size_bytes + item_size > self._max_size_bytes and len(self._cache) > 0
            ):
                self._evict_lru()

            # Add new item
            self._cache[key] = new_item
            self._current_size_bytes += item_size

    def _evict_lru(self) -> None:
        """Evict least recently used item from cache."""
        if not self._cache:
            return

        # Find LRU item (lowest last_accessed time)
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        lru_item = self._cache[lru_key]

        # Remove it
        del self._cache[lru_key]
        self._current_size_bytes -= lru_item.size_bytes()

    def cache_search(self, query: str, results: Dict[str, Any]) -> None:
        """Cache search results.

        Args:
            query: Search query
            results: Search results to cache
        """
        key = self._make_key("search", query.lower())
        self.set(key, results, self.search_ttl)

    def get_search(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached search results.

        Args:
            query: Search query

        Returns:
            Cached search results or None
        """
        key = self._make_key("search", query.lower())
        return self.get(key)

    def cache_episodes(self, anime_url: str, episodes: list) -> None:
        """Cache episode list for an anime.

        Args:
            anime_url: URL of the anime page
            episodes: List of episodes to cache
        """
        key = self._make_key("episodes", anime_url)
        self.set(key, episodes, self.episodes_ttl)

    def get_episodes(self, anime_url: str) -> Optional[list]:
        """Get cached episode list.

        Args:
            anime_url: URL of the anime page

        Returns:
            Cached episode list or None
        """
        key = self._make_key("episodes", anime_url)
        return self.get(key)

    def cache_video_url(self, episode_url: str, video_url: str) -> None:
        """Cache video URL for an episode.

        Note: Video URLs have short TTL due to token expiration.

        Args:
            episode_url: Episode page URL
            video_url: Video stream URL
        """
        key = self._make_key("video", episode_url)
        self.set(key, video_url, self.video_ttl)

    def get_video_url(self, episode_url: str) -> Optional[str]:
        """Get cached video URL.

        Args:
            episode_url: Episode page URL

        Returns:
            Cached video URL or None
        """
        key = self._make_key("video", episode_url)
        return self.get(key)

    def cleanup_expired(self) -> None:
        """Remove all expired items from cache."""
        with self._lock:
            expired_keys = [key for key, item in self._cache.items() if item.is_expired()]

            for key in expired_keys:
                item = self._cache[key]
                del self._cache[key]
                self._current_size_bytes -= item.size_bytes()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "total_items": len(self._cache),
                "current_size_bytes": self._current_size_bytes,
                "max_size_bytes": self._max_size_bytes,
                "usage_percent": (self._current_size_bytes / self._max_size_bytes) * 100,
                "expired_items": sum(1 for item in self._cache.values() if item.is_expired()),
            }

    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            self._current_size_bytes = 0


# Global instance for easy import
smart_cache = SmartCache()
