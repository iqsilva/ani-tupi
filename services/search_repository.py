"""Search repository for anime search and deduplication across sources."""

import time
import re
from typing import Optional
from collections import defaultdict
from os import cpu_count
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from models.config import settings
from models.models import SearchResults, SearchMetadata, AnimeSearchResult
from services.anime.title_normalization import (
    are_language_version_markers_compatible,
    are_season_markers_compatible,
    get_compact_normalized_title_key,
    normalize_search_cache_key,
    normalize_title_for_dedup,
)
from utils.logging import get_logger

logger = get_logger(__name__)


class SearchRepository:
    """Singleton repository for anime search and deduplication.

    Handles:
    - Registering scraper plugins
    - Searching anime across multiple sources
    - Deduplicating results by title normalization
    - Caching search results
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if not SearchRepository._instance:
            SearchRepository._instance = super().__new__(cls)
            SearchRepository._initialized = False
        return SearchRepository._instance

    def __init__(self) -> None:
        # Only initialize once to prevent resetting state on subsequent calls
        if SearchRepository._initialized:
            return

        self.sources = {}
        self.anime_to_urls = defaultdict(list)
        self.norm_titles = {}
        self._last_search_metadata = {}

        SearchRepository._initialized = True

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance for testing. Use only in test fixtures."""
        cls._instance = None
        cls._initialized = False

    def register(self, plugin) -> None:
        """Register a scraper plugin."""
        self.sources[plugin.name] = plugin

    def get_active_sources(self) -> list[str]:
        """Get list of currently registered plugin names.

        Returns:
            List of plugin names (e.g., ["animefire", "sushianimes"])
        """
        return sorted(list(self.sources.keys()))

    def clear_search_results(self) -> None:
        """Clear all search results, keeping registered plugins."""
        self.anime_to_urls = defaultdict(list)
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
            # Normalize sources: ensure params is always a dict (not None or int)
            normalized_sources = []
            for url, source, params in sources_list:
                # Params should be dict at this point (enforced in add_anime)
                if isinstance(params, dict):
                    normalized_sources.append((url, source, params))
                else:
                    normalized_sources.append((url, source, {}))

            anime = AnimeSearchResult(
                title=title,
                normalized_title=self.norm_titles.get(title, title),
                sources=tuple(normalized_sources),
            )
            results.append(anime)

        ranked_results = self._rank_search_results(results, query)
        return SearchResults(query=query, results=tuple(ranked_results), metadata={})

    @staticmethod
    def _normalize_for_similarity(text: str) -> str:
        """Normalize text for similarity ranking."""
        text = SearchRepository._normalize_for_filter(text)
        text = text.replace(" dublado ", " ").replace(" dublado", "").replace("dublado ", "")
        return get_compact_normalized_title_key(text)

    @staticmethod
    def _normalize_words_for_similarity(text: str) -> list[str]:
        normalized = SearchRepository._normalize_for_filter(text)
        normalized = (
            normalized.replace(" dublado ", " ").replace(" dublado", "").replace("dublado ", "")
        )
        return normalized.split()

    @staticmethod
    def _contains_word_sequence(haystack: list[str], needle: list[str]) -> bool:
        if not needle:
            return True
        it = iter(haystack)
        return all(any(word == candidate for candidate in it) for word in needle)

    @staticmethod
    def _extract_numeric_tokens(text: str) -> list[str]:
        return re.findall(r"\d+", text)

    @staticmethod
    def _rank_search_results(
        results: list[AnimeSearchResult], query: str
    ) -> list[AnimeSearchResult]:
        """Rank search results by similarity to the full query.

        Keeps grouped sources intact and preserves deterministic tie-breaking.
        """
        from fuzzywuzzy import fuzz

        normalized_query = SearchRepository._normalize_for_filter(query)
        compact_query = SearchRepository._normalize_for_similarity(query)
        query_words = SearchRepository._normalize_words_for_similarity(query)

        scored_results = []
        for result in results:
            if hasattr(result, "title"):
                title = result.title
            else:
                title = result[1]

            normalized_title = SearchRepository._normalize_for_filter(title)
            compact_title = SearchRepository._normalize_for_similarity(title)
            title_words = SearchRepository._normalize_words_for_similarity(title)

            score = max(
                fuzz.ratio(normalized_query, normalized_title),
                fuzz.partial_ratio(normalized_query, normalized_title),
                fuzz.token_sort_ratio(normalized_query, normalized_title),
                fuzz.ratio(compact_query, compact_title),
            )

            if query_words and title_words[: len(query_words)] == query_words:
                score = min(100, score + 45)
            elif query_words and all(word in title_words for word in query_words):
                score = min(100, score + 25)
            elif normalized_query in normalized_title:
                score = min(100, score + 15)
            elif compact_query in compact_title:
                score = min(100, score + 10)

            if len(title_words) < len(query_words):
                if title_words == query_words[: len(title_words)]:
                    score = 0
                else:
                    score = max(0, score - 50)
            elif len(title_words) > len(query_words):
                score = min(100, score + min(30, (len(title_words) - len(query_words)) * 5))

            scored_results.append((result, score, len(title_words), title))

        scored_results.sort(key=lambda item: (-item[1], item[2], item[3]))
        return [item[0] for item in scored_results]

    @staticmethod
    def _rank_search_results_with_reference(
        results: list[AnimeSearchResult | tuple[str, str]], reference_title: str
    ) -> list[AnimeSearchResult | tuple[str, str]]:
        """Rank results using a canonical reference title when available."""
        from fuzzywuzzy import fuzz

        reference_title = reference_title.split(" / ")[0]
        reference_normalized = SearchRepository._normalize_for_filter(reference_title)
        reference_compact = SearchRepository._normalize_for_similarity(reference_title)
        reference_words = SearchRepository._normalize_words_for_similarity(reference_title)
        reference_numbers = SearchRepository._extract_numeric_tokens(reference_title)

        scored_results = []
        for result in results:
            if hasattr(result, "title"):
                title = result.title
            else:
                title = result[1]

            normalized_title = SearchRepository._normalize_for_filter(title)
            compact_title = SearchRepository._normalize_for_similarity(title)
            title_words = SearchRepository._normalize_words_for_similarity(title)
            title_numbers = SearchRepository._extract_numeric_tokens(title)

            score = max(
                fuzz.ratio(reference_normalized, normalized_title),
                fuzz.partial_ratio(reference_normalized, normalized_title),
                fuzz.token_sort_ratio(reference_normalized, normalized_title),
                fuzz.ratio(reference_compact, compact_title),
            )

            if reference_words and title_words[: len(reference_words)] == reference_words:
                score = min(100, score + 40)
            elif reference_normalized in normalized_title:
                score = min(100, score + 20)
            elif reference_compact in compact_title:
                score = min(100, score + 10)

            if SearchRepository._contains_word_sequence(title_words, reference_words):
                score = min(100, score + 25)
            else:
                score = max(0, score - 25)

            if reference_numbers:
                if all(number in title_numbers for number in reference_numbers):
                    score = min(100, score + 25)
                elif any(number in title_numbers for number in reference_numbers):
                    score = min(100, score + 10)
                else:
                    score = max(0, score - 15)

            if len(title_words) < len(reference_words):
                if title_words == reference_words[: len(title_words)]:
                    score = 0
                else:
                    score = max(0, score - 50)
            elif len(title_words) > len(reference_words):
                score = min(100, score + min(30, (len(title_words) - len(reference_words)) * 5))

            scored_results.append((result, score, len(title_words), title))

        scored_results.sort(key=lambda item: (-item[1], item[2], item[3]))
        return [item[0] for item in scored_results]

    @staticmethod
    def _normalize_for_filter(text: str) -> str:
        """Normalize text for filtering (same logic as add_anime).

        Removes punctuation, converts to lowercase, removes multiple spaces.
        Used for both queries and titles before comparison.
        """
        text = text.lower()
        # Remove punctuation and special characters (including em-dash and en-dash)
        for char in ["-", ":", "(", ")", "!", "?", ".", "–", "—"]:
            text = text.replace(char, " ")
        # Remove multiple spaces
        text = " ".join(text.split())
        return text

    @staticmethod
    def _matches_filter_query(title: str, filter_by_query: str) -> bool:
        """Match filter query against titles using normalized and compact forms."""
        query_normalized = SearchRepository._normalize_for_filter(filter_by_query)
        title_normalized = SearchRepository._normalize_for_filter(title)

        query_compact = get_compact_normalized_title_key(query_normalized)
        title_compact = get_compact_normalized_title_key(title_normalized)

        query_words = query_normalized.split()
        title_words = title_normalized.split()

        return (
            query_normalized in title_normalized
            or query_compact in title_compact
            or all(word in title_words for word in query_words)
        )

    def _search_with_incremental_results(self, query: str, verbose: bool = True) -> None:
        """Search anime with incremental results respecting configured priority order."""

        if verbose:
            logger.info(f"⠼ Buscando '{query}'...")

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

            # Wait for all tasks to complete with timeout
            # Timeout for concurrent scraper requests: 6x http timeout to account for multiple parallel requests
            timeout = settings.performance.http_timeout * 6
            done, not_done = wait(
                future_to_source.keys(),
                timeout=timeout,
                return_when=ALL_COMPLETED,
            )

            # Handle timeout: cancel pending tasks and show partial results
            if not_done:
                timed_out_sources = [future_to_source[f] for f in not_done]
                if verbose:
                    logger.info(
                        f"\n⚠️  Timeout em {len(timed_out_sources)} fonte(s): {', '.join(timed_out_sources)}"
                    )
                    logger.info(f"   Usando resultados parciais de {len(done)} fonte(s)")

                # Cancel pending tasks to free resources
                for future in not_done:
                    future.cancel()

            # Process completed futures
            for future in done:
                source = future_to_source[future]
                try:
                    future.result()
                    if verbose and len(self.sources) > 1:
                        count = len(self.anime_to_urls)
                        logger.info(f"✓ {source} ({count} resultados)", end="\r")
                except Exception as e:
                    if verbose:
                        logger.info(f"❌ Erro em {source}: {e}")

            # Clear progress line and show summary
            if verbose and len(self.sources) > 1:
                logger.info(" " * 70 + "\r", end="")

            if verbose:
                count = len(self.anime_to_urls)
                total = len(self.sources)
                if total > 1 and count > 0:
                    logger.info(f"✓ {count} resultado(s) de {total} fonte(s)")

        finally:
            # Shutdown executor and wait for all tasks
            executor.shutdown(wait=True)

    def add_anime(self, title: str, url: str, source: str, params: dict | None = None) -> None:
        """Add anime with intelligent multi-source deduplication.

        Uses normalize_title_for_dedup() to recognize when the same anime appears
        from multiple sources with different title formats. This enables merging of:
        - Different separators: "Anime A: Title" and "Anime A - Title"
        - Different language markers: "Anime A Dublado" and "Anime A Legendado"
        - Different season formats: "Season 2" and "2nd Season" and "Temporada 2"

        Args:
            title: Original title from scraper
            url: Episode/anime URL
            source: Source plugin name
            params: Optional parameters dict (default: {})
        """
        # Enforce params as dict at entry point
        params = params or {}

        # Normalize the new title using aggressive deduplication normalization
        normalized_new = normalize_title_for_dedup(title)
        compact_new = get_compact_normalized_title_key(normalized_new)
        self.norm_titles[title] = normalized_new

        # Check if this anime (by normalized title) already exists
        for existing_title in self.anime_to_urls:
            # Get normalized form of existing title
            existing_normalized = self.norm_titles.get(existing_title)
            if existing_normalized is None:
                # Anime was loaded from cache, compute normalization now
                existing_normalized = normalize_title_for_dedup(existing_title)
                self.norm_titles[existing_title] = existing_normalized

            # Primary path: strict normalized-title equality
            if normalized_new == existing_normalized:
                self.anime_to_urls[existing_title].append((url, source, params))
                return

            # Fallback path: compact key match, guarded by compatibility checks
            if (
                compact_new == get_compact_normalized_title_key(existing_normalized)
                and are_language_version_markers_compatible(normalized_new, existing_normalized)
                and are_season_markers_compatible(normalized_new, existing_normalized)
            ):
                self.anime_to_urls[existing_title].append((url, source, params))
                return

        # No match found, create new entry using original title
        self.anime_to_urls[title].append((url, source, params))

    def search_anime(self, query: str, verbose: bool = True) -> SearchResults:
        """Search for anime across all registered sources.

        Uses progressive search: starts with full query, decreases words if no results.
        Caches results for faster retrieval on subsequent queries.

        Args:
            query: Anime search query
            verbose: Show progress messages

        Returns:
            Immutable SearchResults with anime matches
        """
        search_start_time = time.time()

        if not self.sources:
            logger.info("\n❌ Erro: Nenhum plugin carregado!")
            logger.info("Verifique se os plugins estão instalados em plugins/")
            return SearchResults(query=query, results=(), metadata={})

        # CACHE CHECK: Try to get search results from cache first
        cache_key = normalize_search_cache_key(query)
        cache_check_start = time.time()
        try:
            from utils.cache_manager import get_cache as get_dc

            dc = get_dc()
            cached_results = dc.get(cache_key)
        except Exception as e:
            if verbose:
                logger.info(f"⚠️  Erro ao acessar cache: {e}")
            cached_results = None
        cache_check_time_ms = int((time.time() - cache_check_start) * 1000)

        if cached_results and isinstance(cached_results, dict):
            # Cache hit! Load results directly without scraping
            if verbose:
                logger.info(f"ℹ️  Usando cache para '{query}' ({len(cached_results)} animes)")

            for anime_title, sources_list in cached_results.items():
                for url, source, params in sources_list:
                    self.add_anime(anime_title, url, source, params)

            total_time_ms = int((time.time() - search_start_time) * 1000)
            # Set search metadata for consistency
            self._last_search_metadata = {
                "original_query": query,
                "used_query": query,
                "used_words": len(query.split()),
                "total_words": len(query.split()),
                "min_words": settings.search.progressive_search_min_words,
                "source": "cache",
                "cache_hit": True,
                "cache_age_seconds": 0,
                "scraper_sources": [],
                "cache_check_time_ms": cache_check_time_ms,
                "scraper_execution_time_ms": 0,
                "total_execution_time_ms": total_time_ms,
            }
            # Convert results to immutable SearchResults
            return self._build_search_results(query)

        # Progressive search: start with all words, decrease if no results
        words = query.split()
        min_words = settings.search.progressive_search_min_words
        scraper_execution_start = time.time()

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
                    logger.info(
                        f"ℹ️  Busca com: '{partial_query}' ({num_words}/{len(words)} palavras)"
                    )
                # Store metadata about the search
                scraper_execution_time_ms = int((time.time() - scraper_execution_start) * 1000)
                total_time_ms = int((time.time() - search_start_time) * 1000)

                # Extract unique scraper sources from results
                scraper_sources = set()
                for sources_list in self.anime_to_urls.values():
                    for url, source, params in sources_list:
                        scraper_sources.add(source)

                self._last_search_metadata = {
                    "original_query": query,
                    "used_query": partial_query,
                    "used_words": num_words,
                    "total_words": len(words),
                    "min_words": min_words,
                    "source": "scraper",
                    "cache_hit": False,
                    "cache_age_seconds": None,
                    "scraper_sources": sorted(list(scraper_sources)),
                    "cache_check_time_ms": cache_check_time_ms,
                    "scraper_execution_time_ms": scraper_execution_time_ms,
                    "total_execution_time_ms": total_time_ms,
                }
                break
            elif verbose and num_words < len(words):
                # No results with this word count, will try fewer words
                logger.info(
                    f"ℹ️  0 resultados com '{partial_query}' ({num_words} palavras) → tentando com menos..."
                )

        # CACHE SAVE: Save search results to cache
        if len(self.anime_to_urls) > 0:
            try:
                from utils.cache_manager import get_cache as get_dc

                dc = get_dc()
                cache_key = normalize_search_cache_key(query)
                # Convert anime_to_urls to dict format for caching
                cache_data = dict(self.anime_to_urls)
                # Use configurable search cache TTL from settings
                ttl_seconds = settings.cache.search_cache_ttl_seconds
                dc.set(cache_key, cache_data, ttl=ttl_seconds)
            except Exception as e:
                if verbose:
                    logger.info(f"⚠️  Erro ao salvar cache: {e}")

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
        """
        if not self.sources:
            logger.info("\n❌ Erro: Nenhum plugin carregado!")
            logger.info("Verifique se os plugins estão instalados em plugins/")
            return SearchResults(query=query, results=(), metadata={})

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
            return SearchMetadata(
                original_query=None,
                used_query=None,
                used_words=None,
                total_words=None,
                min_words=None,
                variant_tested=None,
                variant_index=None,
                total_variants=None,
                source=None,
            )
        return SearchMetadata.model_validate(self._last_search_metadata)

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
        titles = list(self.anime_to_urls.keys())

        if filter_by_query:
            titles = [
                title
                for title in titles
                if SearchRepository._matches_filter_query(title, filter_by_query)
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
        if anilist_results:
            result = [
                item[0]
                for item in self._rank_search_results_with_reference(
                    result, anilist_results[0].title
                )
            ]
        elif original_query and " / " in original_query:
            result = [
                item[0] for item in self._rank_search_results_with_reference(result, original_query)
            ]
        elif original_query:
            result = [item[0] for item in self._rank_search_results(result, original_query)]
        else:
            # Default: sort alphabetically by title
            result = [item[0] for item in sorted(result, key=lambda x: x[1])]

        return result
