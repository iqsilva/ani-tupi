"""Anime search flow with progressive search support.

Handles manual anime search with progressive word reduction,
cache integration, and scraper discovery.
"""

import time
from dataclasses import dataclass, field

from services.repository import rep
from ui.components import loading, menu_navigate
from utils.scraper_cache import get_cache
from services.anime.title_normalization import normalize_anime_title
from utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class SearchResultSet:
    """Represents a single search result set from an incremental search iteration.

    Tracks metadata about search results including word count, query used,
    and source distribution for UI display and navigation.
    """
    word_count: int
    query: str
    results: list[str]
    used_query: str | None = None  # Normalized query that was actually used for search
    timestamp: float = field(default_factory=time.time)
    source_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.word_count <= 0:
            raise ValueError(f"word_count must be positive, got {self.word_count}")
        # Default used_query to query if not provided
        if not self.used_query:
            self.used_query = self.query


class IncrementalSearchState:
    """Manages search history and navigation for incremental anime search.

    Tracks multiple search result sets as words are progressively added,
    allowing users to navigate backward/forward between result sets.

    Attributes:
        search_history: List of SearchResultSet objects in chronological order
        current_index: Current position in navigation history
    """

    def __init__(self):
        self.search_history: list[SearchResultSet] = []
        self.current_index: int = -1

    def add_result(self, word_count: int, query: str, results: list[str], source_counts: dict[str, int] | None = None, used_query: str | None = None) -> None:
        """Add a new search result set to the history.

        Args:
            word_count: Number of words used in this search
            query: The actual query string used (e.g., "boku no hero")
            results: List of anime titles with sources
            source_counts: Optional dict of source names to result counts
            used_query: The normalized query that was actually used for search (lowercase, no punctuation)
        """
        result_set = SearchResultSet(
            word_count=word_count,
            query=query,
            results=results,
            used_query=used_query or query,
            source_counts=source_counts or {}
        )
        # If we've navigated backward, discard forward history
        if self.current_index < len(self.search_history) - 1:
            self.search_history = self.search_history[:self.current_index + 1]

        self.search_history.append(result_set)
        self.current_index = len(self.search_history) - 1

    def go_back(self) -> SearchResultSet | None:
        """Navigate to the previous search result set.

        Returns:
            The previous SearchResultSet, or None if already at the beginning
        """
        if self.current_index > 0:
            self.current_index -= 1
            return self.search_history[self.current_index]
        return None

    def go_forward(self) -> SearchResultSet | None:
        """Navigate to the next search result set.

        Returns:
            The next SearchResultSet, or None if already at the end
        """
        if self.current_index < len(self.search_history) - 1:
            self.current_index += 1
            return self.search_history[self.current_index]
        return None

    def get_current(self) -> SearchResultSet | None:
        """Get the current search result set.

        Returns:
            The current SearchResultSet, or None if no results
        """
        if 0 <= self.current_index < len(self.search_history):
            return self.search_history[self.current_index]
        return None

    def has_previous(self) -> bool:
        """Check if there is a previous result set to navigate to."""
        return self.current_index > 0

    def has_next(self) -> bool:
        """Check if there is a next result set to navigate to."""
        return self.current_index < len(self.search_history) - 1

    def clear(self) -> None:
        """Clear all search history."""
        self.search_history = []
        self.current_index = -1

    def __repr__(self) -> str:
        current = self.get_current()
        current_str = f"{current.word_count} words, {len(current.results)} results" if current else "none"
        return f"IncrementalSearchState(current={current_str}, history_size={len(self.search_history)})"


def incremental_search_anime(query: str) -> tuple[IncrementalSearchState, list[str]]:
    """Perform incremental anime search starting with 3 words and adding progressively.

    Implements the incremental word addition strategy:
    1. Normalize query first (lowercase, remove season patterns, punctuation, etc)
    2. Start with first 3 words of normalized query (or all if fewer)
    3. Add words one at a time
    4. Stop when results ≤ 5
    5. Fallback if zero results to previous iteration

    Args:
        query: The user's search query (e.g., "Boku no Hero Academia Season 5")

    Returns:
        Tuple of (IncrementalSearchState, final_results_list)
        - State tracks all search iterations for navigation
        - Results are the final anime titles with sources to display
    """
    state = IncrementalSearchState()

    # Normalize query first (remove season patterns, punctuation, convert to lowercase, etc)
    # normalize_anime_title() returns a list of variations from most specific to least
    # The first variation is the fully normalized query (most specific)
    variations = normalize_anime_title(query, is_english=False)
    if not variations:
        variations = [query.lower()]

    # Use the first (most specific) normalized variation for incremental search
    normalized_query = variations[0]
    words = normalized_query.split()

    # Determine starting word count (min 3, or all words if fewer)
    start_word_count = min(3, len(words))
    current_word_count = start_word_count
    current_results: list[str] = []

    # Progressive search: add words until results ≤ 5
    while current_word_count <= len(words):
        # Build search query for this iteration
        partial_query = " ".join(words[:current_word_count])

        # Execute search
        rep.clear_search_results()
        try:
            with loading(f"Buscando '{partial_query}'..."):
                rep.search_anime(partial_query, verbose=False)

            # Get results from this iteration
            search_metadata = rep.get_search_metadata()
            used_query = search_metadata.used_query or partial_query

            # Try to get AniList match for ranking
            ranking_query = used_query
            try:
                from utils.anilist_discovery import auto_discover_anilist_id

                anilist_results = auto_discover_anilist_id(used_query)
                if anilist_results:
                    ranking_query = anilist_results[0].title
            except Exception:
                pass

            # Get anime titles with sources, ranked by AniList if available
            titles_with_sources = rep.get_anime_titles_with_sources(
                filter_by_query=used_query, original_query=ranking_query
            )

            # Count results from each source for metadata
            source_counts: dict[str, int] = {}
            for title_entry in titles_with_sources:
                # Parse "Title - Source" format
                if " - " in title_entry:
                    _, source = title_entry.rsplit(" - ", 1)
                    source_counts[source] = source_counts.get(source, 0) + 1

            # Store results in state (with normalized used_query)
            state.add_result(current_word_count, partial_query, titles_with_sources, source_counts, used_query=used_query)
            current_results = titles_with_sources

            # Check stopping condition
            if len(current_results) <= 5:
                # Good result set size - stop here
                break

        except Exception as e:
            logger.warning(f"Error during incremental search at word {current_word_count}: {e}")
            # Fall back to previous results if available
            if state.has_previous():
                state.go_back()
                current_results = state.get_current().results
                break
            raise

        # Continue adding words
        current_word_count += 1

    # Handle zero results: revert to previous iteration if available
    if not current_results and state.has_previous():
        state.go_back()
        current_results = state.get_current().results

    return state, current_results


def search_anime_flow(args):
    """Flow for searching and selecting an anime with progressive search support.

    Supports decreasing word count if user wants to see more results.
    Example: "Spy Family Season 2" (4 words) → Try 4 → 3 → 2 words progressively.

    Cache-first: Checks cache before searching scrapers to avoid unnecessary requests.
    """
    # Clear previous search results to avoid accumulating data from previous calls
    # (Repository is singleton, so it keeps data between calls)
    rep.clear_search_results()

    query = (
        (input("\n🔍 Pesquise anime: ") if not args.query else args.query)
        if not args.debug
        else "eva"
    )

    source = None

    # Cache-first: Check if query is in cache before searching scrapers
    cache_data = get_cache(query)
    selected_anime = None
    if cache_data:
        print(f"ℹ️  Usando cache ({cache_data.episode_count} eps disponíveis)")
        # Populate repository from cache
        rep.load_from_cache(query, cache_data)

        # Discover available sources for this anime (background search)
        rep.search_anime(query, verbose=False)

        selected_anime = query
    else:
        # Not in cache or expired: search scrapers normally
        # Start with full word count
        current_word_count = len(query.split())
        min_words = 1  # Minimum words to search (support single-word anime like "Dandadan")

        # Progressive search loop: try full query, then reduce words if user wants more
        while True:
            rep.clear_search_results()
            # Show what will actually be searched (may be reduced from full query)
            words = query.split()
            search_query = " ".join(words[:current_word_count])
            with loading(f"Buscando '{search_query}'..."):
                rep.search_anime_with_word_limit(query, current_word_count, verbose=False)

            # Get what query was actually used (may be reduced from original)
            search_metadata = rep.get_search_metadata()
            used_query = search_metadata.used_query or query

            # Try to get AniList match to rank results by romaji name
            ranking_query = used_query
            try:
                from utils.anilist_discovery import auto_discover_anilist_id

                anilist_results = auto_discover_anilist_id(used_query)
                if anilist_results:
                    # Use the best match's romaji name for ranking scraper results
                    ranking_query = anilist_results[0].title
            except Exception:
                # If AniList lookup fails, fall back to ranking by search query
                pass

            # Filter by what was actually searched for, rank by AniList romaji if available
            titles_with_sources = rep.get_anime_titles_with_sources(
                filter_by_query=used_query, original_query=ranking_query
            )

            # If no results, automatically try with fewer words
            if not titles_with_sources:
                current_word_count -= 1
                if current_word_count < min_words:
                    return None, None, None  # No results found at all
                continue

            # Add "Continue searching" button if we can reduce words further
            CONTINUE_BUTTON = "🔍 Continuar buscando (menos palavras)"
            if current_word_count > min_words:
                titles_with_button = [CONTINUE_BUTTON] + titles_with_sources
                show_continue_msg = f" (usando {current_word_count} palavras)"
            else:
                titles_with_button = titles_with_sources
                show_continue_msg = ""

            selected_anime_with_source = menu_navigate(
                titles_with_button,
                msg=f"Escolha o Anime.{show_continue_msg}",
            )

            if not selected_anime_with_source:
                return None, None, None  # User cancelled

            # Check if user selected "Continue searching"
            if selected_anime_with_source == CONTINUE_BUTTON:
                current_word_count -= 1
                if current_word_count < min_words:
                    current_word_count = min_words
                continue  # Loop back and search with fewer words

            # User selected an anime - break out of loop
            selected_anime = selected_anime_with_source.split(" [")[0]
            # Extract source (if present)
            source = None
            if " [" in selected_anime_with_source and selected_anime_with_source.endswith("]"):
                source = selected_anime_with_source.split(" [")[1].rstrip("]")
            break

    # At this point, selected_anime is set from either cache or scrapers
    with loading("Carregando episódios..."):
        rep.search_episodes(selected_anime)
    episode_list = rep.get_episode_list(selected_anime)
    selected_episode = menu_navigate(episode_list, msg="Escolha o episódio.")

    if not selected_episode:
        return None, None, None  # User cancelled

    episode_idx = episode_list.index(selected_episode)
    return selected_anime, episode_idx, source
