"""Playback coordinator for video extraction and player search."""

import asyncio
from threading import Event
from collections import defaultdict

from models.config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


def safe_plugin_call(plugin_func, url, container: list, event: Event) -> bool:
    """Safely call a plugin function and return success/failure status.

    Args:
        plugin_func: The plugin's search_player_src method
        url: The episode/page URL
        container: List to store the video URL (modified by plugin)
        event: Event for synchronization

    Returns:
        True if extraction succeeded, False otherwise
    """
    try:
        plugin_func(url, container, event)
        return bool(container)
    except Exception:
        return False


class PlaybackCoordinator:
    """Coordinator for playback-related operations.

    Handles:
    - Extracting video URLs from scraper plugins
    - Detecting source from URL
    - Managing playback caching
    """

    def __init__(self, sources: dict):
        """Initialize coordinator with available scraper sources.

        Args:
            sources: Dict of {source_name: plugin} pairs
        """
        self.sources = sources
        self.anime_to_anilist_id = {}  # For cache key optimization

    def _detect_source_from_url(self, url: str) -> str | None:
        """Detect which scraper source a URL belongs to based on domain.

        Args:
            url: The anime page URL

        Returns:
            Source name (e.g., "animefire") or None if not detected
        """
        url_lower = url.lower()

        # Map domain patterns to scraper sources
        domain_mappings = {
            "animefire": "animefire",
            "animesdigital": "animesdigital",
            "animesonline": "sushianimes",
            "goyabu": "goyabu",
        }

        # Check each domain pattern
        for domain_pattern, source_name in domain_mappings.items():
            if domain_pattern in url_lower:
                return source_name

        # If not detected by domain, return None
        return None

    async def _search_player_impl(
        self,
        sources_with_urls: list[tuple],
        anime: str,
        episode_num: int,
        preferred_source: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Internal async implementation for searching video URLs.

        Cache video URLs to speed up rewatching (7-15s → 100ms!)
        Respects configured priority order for source selection. When
        preferred_source is given, it is tried first; other sources remain
        as fallback in priority order.

        Args:
            sources_with_urls: List of (url, source) tuples for the episode
            anime: Anime title
            episode_num: Episode number (1-indexed)
            preferred_source: Optional source name to try first

        Returns:
            Tuple of (video URL or None, winning source name or None)
        """

        # Get anilist_id for cache key (if already discovered)
        anilist_id = self.anime_to_anilist_id.get(anime)

        # Use anilist_id if available, fallback to anime title
        cache_key = anilist_id if anilist_id else anime

        # CACHE CHECK: Try to get video URL from cache first
        try:
            from utils.cache_manager import get_cache as get_dc

            dc = get_dc()
            cache_key_full = f"video:{cache_key}:ep:{episode_num}"
            if preferred_source:
                cache_key_full += f":src:{preferred_source}"
            cached = dc.get(cache_key_full)
            if cached:
                logger.info(
                    f"   ℹ️  Usando vídeo em cache (válido por {settings.performance.video_url_cache_ttl_seconds // 60} min)"
                )
                if isinstance(cached, dict):
                    return cached.get("url"), cached.get("source")
                # Legacy cache entries stored the raw URL string
                return cached, None
        except Exception:
            dc = None
            cache_key_full = None

        # Cache miss - search all sources in parallel
        async def search_all_sources():
            nonlocal sources_with_urls, cache_key, dc, cache_key_full
            container = []
            winner: dict = {"source": None}

            # Show which sources are being tried
            sources_list = [source for _, source in sources_with_urls]
            if len(sources_list) > 1:
                logger.info(f"   🔄 Tentando fontes: {', '.join(sources_list)}")

            # Organize URLs by source following priority order.
            # A preferred source (user's primary choice) always ranks first.
            priority_order = list(settings.plugins.priority_order)
            if preferred_source:
                priority_order = [preferred_source] + [
                    s for s in priority_order if s != preferred_source
                ]
            priority_map = {name: idx for idx, name in enumerate(priority_order)}

            # Group URLs by source
            sources_urls = defaultdict(list)
            for url, source in sources_with_urls:
                sources_urls[source].append((url, source))

            # Sort sources by priority
            sorted_sources = sorted(
                sources_urls.keys(),
                key=lambda s: priority_map.get(s, len(priority_order)),
            )

            # Try sources in configured priority order (SEQUENTIALLY to respect priority)
            for source_name in sorted_sources:
                if container:
                    # Already found a video, stop searching
                    break

                source_urls = sources_urls[source_name]
                is_priority = priority_map.get(source_name, len(priority_order)) < len(
                    priority_order
                )

                # For each source, try each URL in sequence
                for url, source in source_urls:
                    if container:
                        # Already found a video, stop searching
                        break

                    try:
                        # Run each attempt in its own thread so a stalled source
                        # does not block later fallback attempts.
                        event = Event()
                        result_container = []

                        def run_plugin():
                            success = safe_plugin_call(
                                self.sources[source].search_player_src,
                                url,
                                result_container,
                                event,
                            )
                            if success:
                                video_url = result_container[0]
                                # Truncate very long URLs in display
                                display_url = (
                                    video_url[:80] + "..." if len(video_url) > 80 else video_url
                                )
                                logger.info(f"   ✅ Vídeo encontrado em: {source}")
                                logger.info(f"      URL: {display_url}")
                                container.extend(result_container)
                                winner["source"] = source
                            else:
                                logger.info(f"   ❌ {source} falhou ao extrair vídeo")
                            return success

                        # Wait with timeout (longer for priority sources)
                        timeout = 15 if is_priority else 10
                        task = asyncio.to_thread(run_plugin)
                        await asyncio.wait_for(task, timeout=timeout)

                        # If we got here and container has content, we found a video
                        if container:
                            break

                    except TimeoutError:
                        # This source timed out, try next
                        logger.info(f"   ⏱️  {source} timeout (> {timeout}s)")
                        continue
                    except Exception:
                        # This source failed, try next
                        continue

            # Get video URL if found, otherwise return None
            video_url = container[0] if container else None

            # CACHE SAVE: Save video URL (and winning source) to cache with TTL
            if video_url and dc and cache_key_full:
                try:
                    dc.set(
                        cache_key_full,
                        {"url": video_url, "source": winner["source"]},
                        ttl=settings.performance.video_url_cache_ttl_seconds,
                    )
                except Exception:
                    pass

            return video_url, winner["source"]

        return await search_all_sources()

    def search_player(
        self, sources_with_urls: list[tuple], anime: str, episode_num: int
    ) -> str | None:
        """Search for video URLs (sync version for CLI use).

        Args:
            sources_with_urls: List of (url, source) tuples for the episode
            anime: Anime title
            episode_num: Episode number (1-indexed)

        Returns:
            Video URL or None if not found
        """
        if not sources_with_urls:
            logger.info(f"   ❌ Episódio {episode_num} não disponível nas fontes ativas.")
            return None

        try:
            asyncio.get_running_loop()
            raise RuntimeError("Use search_player_async in async context")
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                raise
            url, _ = asyncio.run(
                self._search_player_impl(sources_with_urls, anime, episode_num)
            )
            return url

    async def search_player_async(
        self,
        sources_with_urls: list[tuple],
        anime: str,
        episode_num: int,
        preferred_source: str | None = None,
    ) -> str | None:
        """Async version of search_player for use in FastAPI routes.

        Args:
            sources_with_urls: List of (url, source) tuples for the episode
            anime: Anime title
            episode_num: Episode number (1-indexed)
            preferred_source: Optional source name to try first (others as fallback)

        Returns:
            Video URL or None if not found
        """
        url, _ = await self.search_player_with_source_async(
            sources_with_urls, anime, episode_num, preferred_source
        )
        return url

    async def search_player_with_source_async(
        self,
        sources_with_urls: list[tuple],
        anime: str,
        episode_num: int,
        preferred_source: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Async search returning both the video URL and the winning source.

        Args:
            sources_with_urls: List of (url, source) tuples for the episode
            anime: Anime title
            episode_num: Episode number (1-indexed)
            preferred_source: Optional source name to try first (others as fallback)

        Returns:
            Tuple of (video URL or None, source name that produced it or None)
        """
        if not sources_with_urls:
            logger.info(f"   ❌ Episódio {episode_num} não disponível nas fontes ativas.")
            return None, None

        return await self._search_player_impl(
            sources_with_urls, anime, episode_num, preferred_source
        )

    def search_player_from_page(self, page_url: str, source_name: str) -> list[str]:
        """Extract candidate video URLs from an episode page for a specific source.

        Args:
            page_url: URL of the episode page (e.g., https://animesdigital.org/video/a/134940/)
            source_name: Name of the source (e.g., "animesdigital")

        Returns:
            Ordered list of candidate video URLs, or an empty list if extraction fails
        """
        if source_name not in self.sources:
            logger.warning(f"Source '{source_name}' not registered, cannot extract video")
            return []

        try:
            container = []
            event = Event()

            success = safe_plugin_call(
                self.sources[source_name].search_player_src,
                page_url,
                container,
                event,
            )

            if success and container:
                return list(container)
            if not success:
                logger.debug(f"No video URL extracted for {source_name}")
            return []
        except Exception as e:
            logger.warning(f"Exception extracting video from {source_name}: {e}")
            return []
