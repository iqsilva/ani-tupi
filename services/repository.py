import asyncio
from typing import Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from os import cpu_count
from threading import Thread

from models.config import settings
from scrapers.loader import PluginInterface
from models.models import EpisodeData, SearchMetadata, SearchResults, AnimeSearchResult


class Repository:
    """SingletonRepository
    get for methods called by main that return some value
    search for methods called by main that don't return but affects state
    add for methods called by any plugin that affects state
    register should be called by a loader function.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if not Repository._instance:
            Repository._instance = super().__new__(cls)
            Repository._initialized = False
        return Repository._instance

    def __init__(self) -> None:
        # Only initialize once to prevent resetting state on subsequent calls
        if Repository._initialized:
            return

        self.sources = {}
        self.anime_to_urls = defaultdict(list)
        self.anime_episodes_titles = defaultdict(list)
        self.anime_episodes_urls = defaultdict(list)
        self.norm_titles = {}
        self._last_search_metadata = {}
        # Mapping from anime title to AniList ID (for cache key)
        self.anime_to_anilist_id = {}

        Repository._initialized = True

    def register(self, plugin: PluginInterface) -> None:
        self.sources[plugin.name] = plugin

    def get_active_sources(self) -> list[str]:
        """Get list of currently registered plugin names.

        Returns:
            List of plugin names (e.g., ["animefire", "animesonlinecc"])
        """
        return sorted(list(self.sources.keys()))

    def clear_search_results(self) -> None:
        """Clear all search results, keeping registered plugins."""
        self.anime_to_urls = defaultdict(list)
        self.anime_episodes_titles = defaultdict(list)
        self.anime_episodes_urls = defaultdict(list)
        self.norm_titles = {}

    def _build_search_results(self, query: str) -> SearchResults:
        """Build immutable SearchResults from current repository state.

        Converts the mutable anime_to_urls dictionary into an immutable
        SearchResults object with AnimeSearchResult tuples.

        Args:
            query: The search query used

        Returns:
            Immutable SearchResults with all current search results
        """
        results = []
        for title, sources_list in self.anime_to_urls.items():
            anime = AnimeSearchResult(
                title=title,
                normalized_title=self.norm_titles.get(title, title),
                sources=tuple(sources_list)
            )
            results.append(anime)

        return SearchResults(
            query=query,
            results=tuple(results),
            metadata=self._last_search_metadata or {}
        )

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance for testing. Use only in test fixtures."""
        cls._instance = None
        cls._initialized = False

    def search_anime(self, query: str, verbose: bool = True) -> SearchResults:
        if not self.sources:
            print("\n❌ Erro: Nenhum plugin carregado!")
            print("Verifique se os plugins estão instalados em plugins/")
            return SearchResults(query=query, results=(), metadata=None)

        # CACHE CHECK: Try to get search results from cache first
        cache_key = f"search:{query.lower()}"
        try:
            from utils.cache_manager import get_cache as get_dc

            dc = get_dc()
            cached_results = dc.get(cache_key)
        except Exception as e:
            if verbose:
                print(f"⚠️  Erro ao acessar cache: {e}")
            cached_results = None

        if cached_results and isinstance(cached_results, dict):
            # Cache hit! Load results directly without scraping
            if verbose:
                print(f"ℹ️  Usando cache para '{query}' ({len(cached_results)} animes)")

            for anime_title, sources_list in cached_results.items():
                for url, source, params in sources_list:
                    self.add_anime(anime_title, url, source, params)

            # AniList IDs are discovered on-demand in search_player() if needed
            # Avoid unnecessary API calls for cached results

            # Set search metadata for consistency
            self._last_search_metadata = {
                "original_query": query,
                "used_query": query,
                "used_words": len(query.split()),
                "total_words": len(query.split()),
                "min_words": settings.search.progressive_search_min_words,
                "source": "cache",
            }
            # Convert results to immutable SearchResults
            return self._build_search_results(query)

        # Progressive search: start with all words, decrease if no results
        words = query.split()
        min_words = settings.search.progressive_search_min_words

        # Store original query for later filtering
        self._last_query = query

        # Progressive search (DECRESCENTE): len(words), len(words)-1, ..., min_words
        # Tries full query first, then progressively removes words from the end
        for num_words in range(len(words), min_words - 1, -1):
            partial_query = " ".join(words[:num_words])

            # Clear previous attempt results
            self.clear_search_results()

            # Search with current query (incremental)
            self._search_with_incremental_results(partial_query, verbose=False)

            # If found results, stop
            results_found = len(self.anime_to_urls)
            if results_found > 0:
                if verbose and num_words < len(words):
                    print(f"ℹ️  Busca com: '{partial_query}' ({num_words}/{len(words)} palavras)")
                # Store metadata about the search
                self._last_search_metadata = {
                    "original_query": query,
                    "used_query": partial_query,
                    "used_words": num_words,
                    "total_words": len(words),
                    "min_words": min_words,
                }
                break
            elif verbose and num_words < len(words):
                # No results with this word count, will try fewer words
                print(
                    f"ℹ️  0 resultados com '{partial_query}' ({num_words} palavras) → tentando com menos..."
                )

        # Auto-discover AniList IDs only when needed (disabled for performance)
        # AniList IDs are discovered on-demand in search_player() if cache.anilist_auto_discover is enabled
        # Doing it for all search results here generates unnecessary API calls and logs

        # CACHE SAVE: Save search results to cache
        if len(self.anime_to_urls) > 0:
            try:
                from utils.cache_manager import get_cache as get_dc

                dc = get_dc()
                cache_key = f"search:{query.lower()}"
                # Convert anime_to_urls to dict format for caching
                cache_data = dict(self.anime_to_urls)
                dc.set(cache_key, cache_data, expire=settings.cache.duration_hours * 3600)
            except Exception as e:
                if verbose:
                    print(f"⚠️  Erro ao salvar cache: {e}")

        # Return immutable SearchResults
        return self._build_search_results(query)

    def search_anime_with_word_limit(
        self, query: str, word_limit: int, verbose: bool = True
    ) -> SearchResults:
        """Search anime with a word limit.

        Searches using only the first `word_limit` words of the query.
        Useful for progressive search where user wants to continue with fewer words.

        Args:
            query: Original query (may have more words than word_limit)
            word_limit: Number of words to use from the start of query
            verbose: Show progress messages

        Returns:
            Immutable SearchResults with search results

        Example:
            search_anime_with_word_limit("Dan Da Dan Season 2", 2)
            # Searches for "Dan Da"
        """
        if not self.sources:
            print("\n❌ Erro: Nenhum plugin carregado!")
            print("Verifique se os plugins estão instalados em plugins/")
            return SearchResults(query=query, results=(), metadata=None)

        words = query.split()
        min_words = settings.search.progressive_search_min_words

        # Ensure word_limit is within valid range
        word_limit = max(min_words, min(word_limit, len(words)))

        # Create limited query
        limited_query = " ".join(words[:word_limit])

        # Store metadata
        self._last_search_metadata = {
            "original_query": query,
            "used_query": limited_query,
            "used_words": word_limit,
            "total_words": len(words),
            "min_words": min_words,
        }

        # Clear previous results
        self.clear_search_results()

        # Execute search
        self._search_with_incremental_results(limited_query, verbose)

        # Return immutable SearchResults
        return self._build_search_results(query)

    def get_search_metadata(self) -> SearchMetadata:
        """Get metadata about the last search performed.

        Returns:
            SearchMetadata with search information.
            Returns empty SearchMetadata if no search has been performed yet.
        """
        if not self._last_search_metadata:
            return SearchMetadata()
        return SearchMetadata.model_validate(self._last_search_metadata)

    @staticmethod
    def _normalize_for_filter(text: str) -> str:
        """Normalize text for filtering (same logic as add_anime).

        Removes punctuation, converts to lowercase, removes multiple spaces.
        Used for both queries and titles before comparison.
        """
        text = text.lower()
        # Remove punctuation and special characters
        for char in ["-", ":", "(", ")", "!", "?", "."]:
            text = text.replace(char, " ")
        # Remove multiple spaces
        text = " ".join(text.split())
        return text

    def _search_with_incremental_results(self, query: str, verbose: bool = True) -> None:
        """Search anime with incremental results respecting configured priority order."""
        from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

        if verbose:
            print(f"⠼ Buscando '{query}'...")

        n_cpu = cpu_count()
        if not n_cpu:
            n_cpu = 10

        executor = ThreadPoolExecutor(max_workers=min(len(self.sources), n_cpu))

        try:
            # Get a snapshot of sources to avoid race conditions
            sources_list = list(self.sources.items())

            # Apply priority order from settings (agnóstico a nomes específicos)
            priority_order = settings.plugins.priority_order
            if priority_order:
                # Create a priority map based on configured order
                priority_map = {name: idx for idx, name in enumerate(priority_order)}

                # Sort sources: prioritized first, then others in alphabetical order
                def sort_priority(item):
                    source_name = item[0]
                    return priority_map.get(source_name, len(priority_order))

                sources_list.sort(key=sort_priority)
            else:
                # If no priority configured, use alphabetical ordering
                sources_list.sort(key=lambda x: x[0])

            # Submit all search tasks
            future_to_source = {}
            for source_name, plugin in sources_list:
                future = executor.submit(plugin.search_anime, query)
                future_to_source[future] = source_name

            # Wait for all tasks to complete
            done, _ = wait(future_to_source.keys(), return_when=ALL_COMPLETED)

            # Process completed futures
            for future in done:
                source = future_to_source[future]
                try:
                    future.result()
                    if verbose and len(self.sources) > 1:
                        count = len(self.anime_to_urls)
                        print(f"✓ {source} ({count} resultados)", end="\r")
                except Exception as e:
                    if verbose:
                        print(f"❌ Erro em {source}: {e}")

            # Clear progress line and show summary
            if verbose and len(self.sources) > 1:
                print(" " * 70 + "\r", end="")

            if verbose:
                count = len(self.anime_to_urls)
                total = len(self.sources)
                if total > 1 and count > 0:
                    print(f"✓ {count} resultado(s) de {total} fonte(s)")

        finally:
            # Shutdown executor and wait for all tasks
            executor.shutdown(wait=True)

    def add_anime(self, title: str, url: str, source: str, params=None) -> None:
        """Add anime with exact deduplication.

        This method assumes different seasons are different anime (like MAL).
        Plugin devs should scrape that way.

        Uses exact matching: only consolidates if normalized titles are 100% identical.
        This preserves dubbed/subbed/season distinctions.
        """
        title_ = title.lower()
        table = {
            "clássico": "",
            "classico": "",
            ":": "",
            "part": "season",
            "temporada": "season",
            "(": "",
            ")": "",
            " ": "",
        }

        for key, val in table.items():
            title_ = title_.replace(key, val)

        self.norm_titles[title] = title_

        # Exact matching: only consolidate if normalized titles are identical
        for key in self.anime_to_urls:
            # Handle case where anime was loaded from cache and not in norm_titles yet
            key_normalized = self.norm_titles.get(key, self._normalize_for_filter(key))
            if title_ == key_normalized:
                self.anime_to_urls[key].append((url, source, params))
                return
        self.anime_to_urls[title].append((url, source, params))

    def get_anime_titles(
        self, filter_by_query: Optional[str] = None, min_score: int | None = None
    ) -> list[str]:
        """Get anime titles, optionally filtered by exact match to query.

        Args:
            filter_by_query: If provided, only return titles matching query.
            min_score: Ignored (kept for API compatibility)

        Returns:
            Sorted list of anime titles, filtered if query provided.
        """
        titles = list(self.anime_to_urls.keys())

        if not filter_by_query:
            return sorted(titles)

        # Simple case-insensitive substring matching
        query_lower = filter_by_query.lower()
        filtered = [title for title in titles if query_lower in title.lower()]
        return sorted(filtered)

    def get_anime_titles_with_sources(
        self,
        filter_by_query: Optional[str] = None,
        original_query: Optional[str] = None,
        anilist_results: Optional[list] = None,
    ) -> list[str]:
        """Get anime titles with source indicators, ranked by relevance.
        Shows which sources have each anime, helpful for multi-source scenarios.
        Format: "Anime Title [source1, source2]"
        Args:
            filter_by_query: If provided, only return titles matching query.
            original_query: If provided, rank results by fuzzy matching score.
            anilist_results: Optional list of AniListSearchResult for score-based sorting.
        Returns:
            List of anime titles with source indicators, ranked by relevance
        """
        from fuzzywuzzy import fuzz

        titles = list(self.anime_to_urls.keys())

        if filter_by_query:
            # Improved filtering: normalize both query and titles before matching
            query_normalized = self._normalize_for_filter(filter_by_query)
            titles = [
                title for title in titles if query_normalized in self._normalize_for_filter(title)
            ]

        # Build titles with sources
        result = []
        for title in titles:
            urls_and_sources = self.anime_to_urls[title]
            # Filter out "cache" marker - only show real scraper sources
            sources = set(source for _url, source, _params in urls_and_sources if source != "cache")
            sources_str = ", ".join(sorted(sources)) if sources else "cached"
            result.append((f"{title} [{sources_str}]", title))

        # Rank by relevance if original_query provided
        if original_query:
            import re

            # Extract numeric tokens from query (e.g., "0" from "jujutsu kaisen 0")
            query_numbers = set(re.findall(r"\d+", original_query))

            # Calculate fuzzy matching score for each title against the original query
            scored_results = []
            for result_with_source, original_title in result:
                # Use token_sort_ratio for base matching
                base_score = fuzz.token_sort_ratio(original_query.lower(), original_title.lower())

                # Boost scoring if title contains the same numbers as query
                # Example: query="jujutsu kaisen 0" should prioritize titles with "0"
                if query_numbers:
                    title_numbers = set(re.findall(r"\d+", original_title))
                    if query_numbers.issubset(title_numbers):
                        # Strong boost: title has all the numbers from query
                        # This fixes "Jujutsu Kaisen 0 Movie" ranking below "Jujutsu Kaisen 2"
                        score = min(100, base_score + 15)
                    elif not query_numbers.intersection(title_numbers):
                        # Penalty: query has specific numbers but title doesn't have any of them
                        # This ensures "Jujutsu Kaisen 2" ranks below "Jujutsu Kaisen 0" variants
                        score = max(0, base_score - 20)
                    else:
                        # Partial match: title has some but not all numbers from query
                        score = base_score - 5
                else:
                    # No numbers in query, use base score
                    score = base_score

                scored_results.append((result_with_source, score, original_title))

            # Sort by score (descending), then by title length (shorter = more specific), then alphabetically
            scored_results.sort(key=lambda x: (-x[1], len(x[2]), x[0]))
            result = [item[0] for item in scored_results]
        else:
            # Default: sort alphabetically by title
            result = [item[0] for item in sorted(result, key=lambda x: x[1])]

        return result

    def search_episodes(self, anime: str, source_filter: str | None = None) -> None:
        """Search for episodes from all sources or a specific source.

        Args:
            anime: Anime title to search episodes for
            source_filter: Optional source name to search only that source (e.g., "animefire")
        """
        urls_and_scrapers = self.anime_to_urls[anime]

        # Filter by source if specified
        if source_filter:
            urls_and_scrapers = [
                (url, source, params)
                for url, source, params in urls_and_scrapers
                if source == source_filter
            ]

        # Build threads safely, avoiding potential race conditions
        threads = []
        for url, source, params in urls_and_scrapers:
            if source in self.sources:
                th = Thread(
                    target=self.sources[source].search_episodes,
                    args=(anime, url, params),
                )
                threads.append(th)

        for th in threads:
            th.start()

        for th in threads:
            th.join()
        return None

    def add_episode_list(
        self, anime: str, title_list: list[str], url_list: list[str], source: str
    ) -> None:
        """Add episode list with validation.

        Args:
            anime: Anime title
            title_list: List of episode titles
            url_list: List of episode URLs
            source: Plugin source name

        Raises:
            ValueError: If title_list and url_list have different lengths.
        """
        # Validate using EpisodeData model
        episode_data = EpisodeData(
            anime_title=anime,
            episode_titles=title_list,
            episode_urls=url_list,
            source=source,
        )

        self.anime_episodes_titles[anime].append(episode_data.episode_titles)
        self.anime_episodes_urls[anime].append((episode_data.episode_urls, source))

    def get_episode_list(self, anime: str):
        episodes = self.anime_episodes_titles[anime]
        if not episodes:
            return []
        episode_list = sorted(episodes, key=lambda title_list: len(title_list))[-1]
        return episode_list

    def load_from_cache(self, anime: str, cache_data) -> None:
        """Populate repository from cached data.

        Cache-first approach: When anime is found in cache, load its data
        directly into the repository without searching scrapers.

        Args:
            anime: Anime title
            cache_data: ScraperCacheData model or dict with keys 'episode_urls' and 'episode_count'
        """
        if not cache_data:
            return

        # Handle both Pydantic models and dicts
        if hasattr(cache_data, "episode_urls"):
            # It's a Pydantic model
            episode_urls = cache_data.episode_urls
        else:
            # It's a dict
            episode_urls = cache_data.get("episode_urls", [])
        if not episode_urls:
            return

        # Generate episode titles from URLs (format: "Episódio 1", "Episódio 2", etc)
        episode_titles = [f"Episódio {i + 1}" for i in range(len(episode_urls))]

        # Add to repository as if it came from a "cache" source
        self.anime_episodes_titles[anime].append(episode_titles)
        self.anime_episodes_urls[anime].append((episode_urls, "cache"))

        # Note: We don't add a "dummy" entry to anime_to_urls here because:
        # 1. It's not a real scraper source - just cached episode data
        # 2. It would appear as "[cached]" in user-facing source lists
        # 3. search_anime() is called later to discover real sources for display

    def get_episode_url_and_source(self, anime: str, episode_num: int) -> tuple[str, str] | None:
        """Get episode URL and source name for a specific episode.

        Args:
            anime: Anime title
            episode_num: Episode number (1-indexed)

        Returns:
            Tuple of (episode_url, source_name) or None if not found
        """
        # Validate episode_num
        if episode_num < 1:
            return None

        for urls, source in self.anime_episodes_urls[anime]:
            if len(urls) >= episode_num:
                return (urls[episode_num - 1], source)

        return None

    def get_episode_url(self, anime: str, episode_idx: int) -> str | None:
        """Get episode URL for a specific episode (0-indexed).

        Args:
            anime: Anime title
            episode_idx: Episode index (0-indexed)

        Returns:
            Episode URL or None if not found
        """
        # Convert from 0-indexed to 1-indexed
        episode_num = episode_idx + 1
        result = self.get_episode_url_and_source(anime, episode_num)
        if result:
            return result[0]
        return None

    def get_next_available_episode(self, anime: str, from_episode: int) -> tuple[int, str] | None:
        """Get next available episode from a given episode number.

        Searches all sources for the next available episode after the given one.

        Args:
            anime: Anime title
            from_episode: Episode number to search from (1-indexed)

        Returns:
            Tuple of (episode_number, url) or None if no more episodes
        """
        if from_episode < 1:
            from_episode = 1

        # Search all sources to find the highest available episode
        max_episode = 0
        best_url = None

        for urls, source in self.anime_episodes_urls.get(anime, []):
            # Check if this source has more episodes after from_episode
            if len(urls) > from_episode:
                # Has next episode
                max_episode = max(max_episode, len(urls))
                if not best_url:
                    best_url = urls[from_episode]  # Get next episode (0-indexed)

        if best_url:
            return (from_episode + 1, best_url)  # Return 1-indexed episode number

        return None

    def search_player(self, anime: str, episode_num: int) -> None:
        """Search for video URLs with caching.

        Cache video URLs to speed up rewatching (7-15s → 100ms!)
        Assumes all episode lists are the same size.
        Plugin devs should guarantee that OVAs are not considered.
        """
        selected_urls = []
        for urls, source in self.anime_episodes_urls[anime]:
            if len(urls) >= episode_num:
                # Skip "cache" marker - use actual scraper sources instead
                if source != "cache":
                    selected_urls.append((urls[episode_num - 1], source))

        # Defensive check: No sources have this episode available
        if not selected_urls:
            active_sources = self.get_active_sources()
            if active_sources:
                print(f"   ❌ Episódio {episode_num} não disponível nas fontes ativas.")
                print(f"   💡 Fontes ativas: {', '.join(active_sources)}")
            else:
                print(f"   ❌ Nenhuma fonte ativa para buscar episódio {episode_num}.")
            return None

        # Get anilist_id for cache key (if already discovered)
        anilist_id = self.anime_to_anilist_id.get(anime)

        # Use anilist_id if available, fallback to anime title
        cache_key = anilist_id if anilist_id else anime

        # CACHE DISABLED for video URLs - tokens expire too quickly
        # Blogger URLs with tokens expire in minutes, caching causes playback failures
        # Only episode lists are cached, not video stream URLs

        # Cache miss - search all sources in parallel
        async def search_all_sources():
            nonlocal selected_urls, self, cache_key
            event = asyncio.Event()
            container = []
            found_event = asyncio.Event()  # Signal when found in priority source
            loop = asyncio.get_running_loop()

            # Show which sources are being tried
            sources_list = [source for _, source in selected_urls]
            if len(sources_list) > 1:
                print(f"   🔄 Tentando fontes: {', '.join(sources_list)}")

            # Wrapper to catch exceptions from plugins
            def safe_plugin_call(plugin_func, url, source, is_priority=False):
                try:
                    plugin_func(url, container, event)
                    if container:  # Only print if this source succeeded
                        video_url = container[0]
                        # Truncate very long URLs in display
                        display_url = video_url[:80] + "..." if len(video_url) > 80 else video_url
                        print(f"   ✅ Vídeo encontrado em: {source}")
                        print(f"      URL: {display_url}")
                        # Signal priority source found to cancel other tasks
                        if is_priority:
                            found_event.set()
                except Exception as e:
                    # Extract just the first line of error (avoid huge stack traces)
                    error_msg = str(e).split("\n")[0]
                    print(f"   ❌ {source} falhou: {error_msg[:100]}")
                    # Don't re-raise - let other sources try

            # Organize URLs by source following priority order
            priority_order = settings.plugins.priority_order or []
            priority_map = {name: idx for idx, name in enumerate(priority_order)}

            # Group URLs by source
            sources_urls = defaultdict(list)
            for url, source in selected_urls:
                sources_urls[source].append((url, source))

            # Sort sources by priority
            sorted_sources = sorted(
                sources_urls.keys(), key=lambda s: priority_map.get(s, len(priority_order))
            )

            with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
                # Try sources in configured priority order
                for source_name in sorted_sources:
                    if container:
                        # Already found a video, stop searching
                        break

                    source_urls = sources_urls[source_name]
                    is_priority = priority_map.get(source_name, len(priority_order)) < len(
                        priority_order
                    )

                    # Create tasks for this source
                    source_tasks = [
                        loop.run_in_executor(
                            executor,
                            safe_plugin_call,
                            self.sources[source].search_player_src,
                            url,
                            source,
                            is_priority,
                        )
                        for url, source in source_urls
                    ]

                    # Wait for this source (with timeout for high-priority sources)
                    timeout = 15 if is_priority else None
                    pending = set(source_tasks)

                    while pending and not container:
                        try:
                            done, pending = await asyncio.wait(
                                pending, return_when=asyncio.FIRST_COMPLETED, timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            # Timeout reached, stop waiting for this source
                            break

                        # If found a video, break immediately
                        if container:
                            break

                # Get video URL if found, otherwise return None
                video_url = container[0] if container else None

                # Save to cache for future use
                # DON'T cache video URLs - they expire too quickly
                # Caching Blogger URLs causes playback failures due to token expiration
                return video_url

        return asyncio.run(search_all_sources())


rep = Repository()

if __name__ == "__main__":
    rep3, rep2 = Repository(), Repository()
