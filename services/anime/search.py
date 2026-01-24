"""Anime search flow with progressive search support.

Handles manual anime search with progressive word reduction,
cache integration, and scraper discovery.
"""

from services.repository import rep
from ui.components import loading, menu_navigate
from utils.scraper_cache import get_cache
from services.anime.title_normalization import normalize_anime_title
from scrapers import loader


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
    from utils.scraper_cache import get_cache

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
