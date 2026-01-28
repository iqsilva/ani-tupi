"""Search repository for managing search results and caching."""
from collections import defaultdict
from models.models import SearchResults, AnimeSearchResult


class SearchRepository:
    """Manages search results and anime title consolidation.

    Single responsibility: track search results and perform deduplication
    of anime titles by normalized form.
    """

    _instance = None

    def __new__(cls):
        """Enforce singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._anime_to_urls = defaultdict(list)
            cls._instance._norm_titles = {}
            cls._instance._last_search_metadata = {}
        return cls._instance

    def add_anime(self, title: str, url: str, source: str, params=None) -> None:
        """Add anime with exact deduplication.

        This method assumes different seasons are different anime (like MAL).
        Plugin devs should scrape that way.

        Uses exact matching: only consolidates if normalized titles are 100% identical.
        This preserves dubbed/subbed/season distinctions.

        Args:
            title: Anime title
            url: Anime URL
            source: Source plugin name
            params: Optional extra parameters
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

        self._norm_titles[title] = title_

        # Exact matching: only consolidate if normalized titles are identical
        for key in self._anime_to_urls:
            # Handle case where anime was loaded from cache and not in norm_titles yet
            key_normalized = self._norm_titles.get(key, self.normalize_for_filter(key))
            if title_ == key_normalized:
                self._anime_to_urls[key].append((url, source, params))
                return

        self._anime_to_urls[title].append((url, source, params))

    def get_anime_titles(
        self, filter_by_query: str | None = None, min_score: int | None = None
    ) -> list[str]:
        """Get anime titles, optionally filtered by exact match to query.

        Args:
            filter_by_query: If provided, only return titles matching query.
            min_score: Ignored (kept for API compatibility)

        Returns:
            Sorted list of anime titles, filtered if query provided.
        """
        titles = list(self._anime_to_urls.keys())

        if not filter_by_query:
            return sorted(titles)

        # Simple case-insensitive substring matching
        query_lower = filter_by_query.lower()
        filtered = [title for title in titles if query_lower in title.lower()]
        return sorted(filtered)

    def get_anime_titles_with_sources(
        self,
        filter_by_query: str | None = None,
        original_query: str | None = None,
        anilist_results: list | None = None,
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
        import re

        titles = list(self._anime_to_urls.keys())

        if filter_by_query:
            # Improved filtering: normalize both query and titles before matching
            query_normalized = self.normalize_for_filter(filter_by_query)
            titles = [
                title
                for title in titles
                if query_normalized in self.normalize_for_filter(title)
            ]

        # Build titles with sources
        result = []
        for title in titles:
            urls_and_sources = self._anime_to_urls[title]
            # Filter out "cache" marker - only show real scraper sources
            sources = set(
                source for _url, source, _params in urls_and_sources if source != "cache"
            )
            sources_str = ", ".join(sorted(sources)) if sources else "cached"
            result.append((f"{title} [{sources_str}]", title))

        # Rank by relevance if original_query provided
        if original_query:
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

    def clear_search_results(self) -> None:
        """Clear all search results, keeping registered plugins."""
        self._anime_to_urls = defaultdict(list)
        self._norm_titles = {}

    def build_search_results(self, query: str) -> SearchResults:
        """Build immutable SearchResults from current repository state.

        Converts the mutable _anime_to_urls dictionary into an immutable
        SearchResults object with AnimeSearchResult tuples.

        Args:
            query: The search query used

        Returns:
            Immutable SearchResults with all current search results
        """
        results = []
        for title, sources_list in self._anime_to_urls.items():
            anime = AnimeSearchResult(
                title=title,
                normalized_title=self._norm_titles.get(title, title),
                sources=tuple(sources_list),
            )
            results.append(anime)

        return SearchResults(
            query=query, results=tuple(results), metadata=self._last_search_metadata or {}
        )

    @staticmethod
    def normalize_for_filter(text: str) -> str:
        """Normalize text for filtering (same logic as add_anime).

        Removes punctuation, converts to lowercase, removes multiple spaces.
        Used for both queries and titles before comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        text = text.lower()
        # Remove punctuation and special characters
        for char in ["-", ":", "(", ")", "!", "?", "."]:
            text = text.replace(char, " ")
        # Remove multiple spaces
        text = " ".join(text.split())
        return text

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance for testing.

        Use only in test fixtures.
        """
        cls._instance = None
