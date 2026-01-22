"""Anime service layer - business logic for anime search, selection, and playback.

This module contains the core business logic for:
- Title normalization and search
- AniList integration and mapping
- Sequel detection and continuation
- Source switching
- Anime flow orchestration

Used by: main.py, ui modules
"""

import json
import re
from typing import Optional

from models.config import get_data_path, settings
from services.anilist_service import anilist_client
from services.history_service import save_history
from services.repository import rep
from ui.components import loading, menu_navigate
from utils.exceptions import PersistenceError
from utils.logging import get_logger
from utils.persistence import JSONStore
from utils.video_player import play_episode
from models import EpisodeContext
from scrapers import loader
from models.models import Status
from services.anime.title_normalization import normalize_anime_title
from services.anime.mappings import (
    load_anilist_mapping,
    save_anilist_mapping,
    load_anilist_search_title,
)
from services.anime.episode_context import get_next_episode_context
from services.anime.anilist_integration import (
    offer_sequel_and_continue,
    anilist_anime_flow,
)


logger = get_logger(__name__)

# Use centralized path function from config
HISTORY_PATH = get_data_path()

# offer_sequel_and_continue and anilist_anime_flow are now imported from services.anime.anilist_integration


def switch_anime_source(
    current_anime: str, args, anilist_id: int | None = None, display_title: str | None = None
) -> tuple[str, int] | tuple[None, None]:
    """Allow user to switch to a different anime source/title.

    Shows all available variations (dubbed/subtitled/different scrapers) found
    using the SAME search criteria as the original search.
    Maintains progress from local history and AniList (as fallback).

    Args:
        current_anime: Current anime title being watched
        args: CLI arguments
        anilist_id: Optional AniList ID for progress fallback
        display_title: Optional original display title from AniList (for search)

    Returns: (new_anime_title, episode_idx) or (None, None) if cancelled
    """
    # SAVE: Preserve current anime's episode data (search_anime will destroy it)
    saved_episode_data = None
    if current_anime in rep.anime_episodes_urls:
        # Store shallow copies of the data structures for restoration
        saved_episode_data = {
            "urls": list(rep.anime_episodes_urls[current_anime]),
            "titles": list(rep.anime_episodes_titles[current_anime]),
        }

    # 1. Use saved search title from AniList if available (same title as original search)
    # Otherwise fall back to display_title or current_anime
    if anilist_id:
        search_title = load_anilist_search_title(anilist_id)
    else:
        search_title = None
    search_title = search_title or display_title or current_anime

    # Generate title variations using the search title (same as original search)
    title_variations = normalize_anime_title(search_title)
    current_variant_idx = 0
    selected_anime = None

    # 2. Interactive search loop - same as normal search flow
    while selected_anime is None and current_variant_idx < len(title_variations):
        variant = title_variations[current_variant_idx]

        # Search with current variation
        with loading(f"Buscando '{variant}'..."):
            # Use new progressive search (starts with initial_search_words, increases while >10 results)
            rep.search_anime(variant, verbose=True)

        # Get results with sources
        search_metadata = rep.get_search_metadata()
        used_query = search_metadata.used_query or variant
        titles_with_sources = rep.get_anime_titles_with_sources(
            filter_by_query=variant, original_query=used_query
        )

        # If found results, show interactive menu
        if titles_with_sources:
            # Build menu with "Continue searching" option if more variations available
            menu_title = f"🔄 Trocar fonte para '{current_anime}'\n"
            menu_title += f"🔍 Busca: '{used_query}'\n"
            menu_title += f"Encontrados {len(titles_with_sources)} resultados. Escolha:"

            CONTINUE_BUTTON = "🔍 Continuar buscando (menos palavras)"
            menu_options = []

            if current_variant_idx < len(title_variations) - 1:
                menu_options.append(CONTINUE_BUTTON)
            menu_options.extend(titles_with_sources)

            selected_anime_with_source = menu_navigate(menu_options, msg=menu_title)

            if not selected_anime_with_source:
                # User cancelled
                if saved_episode_data:
                    rep.anime_episodes_urls[current_anime] = saved_episode_data["urls"]
                    rep.anime_episodes_titles[current_anime] = saved_episode_data["titles"]
                return None, None

            # Check if user wants to continue searching
            if selected_anime_with_source == CONTINUE_BUTTON:
                current_variant_idx += 1
                continue  # Try next variation

            # User selected an anime
            selected_anime = selected_anime_with_source.split(" [")[0]
        else:
            # No results with this variation, try next
            current_variant_idx += 1

    # 3. If no results found with any variation
    if not selected_anime:
        # RESTORE: Return episode data so user can continue watching current source
        if saved_episode_data:
            rep.anime_episodes_urls[current_anime] = saved_episode_data["urls"]
            rep.anime_episodes_titles[current_anime] = saved_episode_data["titles"]
            print("⚠️  Nenhuma variação encontrada")
            print("   💡 Mantendo fonte atual...")
        else:
            print("⚠️  Nenhuma variação encontrada")
        return None, None

    # 5. Load episodes from new source
    with loading("Carregando episódios..."):
        rep.search_episodes(selected_anime)

    # 6. Get episode list from new source
    episode_list = rep.get_episode_list(selected_anime)

    # 7. Check progress from both sources (AniList as primary source of truth)
    local_progress = 0
    anilist_progress = 0
    progress_source = ""

    # First check local history
    try:
        history_file = HISTORY_PATH / "history.json"
        with history_file.open() as f:
            history_data = json.load(f)
            if selected_anime in history_data:
                # history stores episode_idx (0-based), progress is 1-based
                local_progress = history_data[selected_anime][1] + 1
    except (FileNotFoundError, KeyError, IndexError):
        pass  # No local history

    # 8. If have anilist_id, always check AniList (source of truth)
    # Use AniList as primary when available (you might have watched via web/mobile)
    if anilist_id:
        if anilist_client.is_authenticated():
            # Get media list entry for this anime
            entry = anilist_client.get_media_list_entry(anilist_id)
            if entry and entry.progress:
                anilist_progress = entry.progress

    # Use maximum progress available, preferring AniList when it's ahead
    max_progress = max(local_progress, anilist_progress)
    if max_progress > 0:
        if anilist_progress > local_progress:
            # AniList is ahead - user probably watched on web/mobile
            progress_source = "AniList"
        elif anilist_progress == local_progress and anilist_progress > 0:
            # Both equal and from AniList source
            progress_source = "AniList"
        else:
            # Local is ahead or AniList not available
            progress_source = "Local"

    # 9. If user has progress, offer -1/0/+1 options
    if max_progress > 0 and max_progress <= len(episode_list):
        options = []
        option_to_idx = {}

        # Previous episode (-1)
        if max_progress > 1:
            prev_ep = f"◀️  Episódio {max_progress - 1} (anterior)"
            options.append(prev_ep)
            option_to_idx[prev_ep] = max_progress - 2

        # Current episode
        current_ep = f"▶️  Episódio {max_progress} ({progress_source})"
        options.append(current_ep)
        option_to_idx[current_ep] = max_progress - 1

        # Next episode (+1)
        if max_progress < len(episode_list):
            next_ep = f"⏭️  Episódio {max_progress + 1} (próximo)"
            options.append(next_ep)
            option_to_idx[next_ep] = max_progress

        # Add option to choose any episode
        options.append("📋 Escolher outro episódio")

        choice = menu_navigate(options, msg=f"{selected_anime} - De onde quer continuar?")

        if not choice:
            return None, None  # User cancelled

        if choice == "📋 Escolher outro episódio":
            # Let user choose from full episode list
            selected_episode = menu_navigate(episode_list, msg="Escolha o episódio.")
            if not selected_episode:
                return None, None
            episode_idx = episode_list.index(selected_episode)
        else:
            episode_idx = option_to_idx[choice]
    else:
        # No progress - show full episode list
        selected_episode = menu_navigate(episode_list, msg="Escolha o episódio.")

        if not selected_episode:
            return None, None  # User cancelled

        episode_idx = episode_list.index(selected_episode)

    return selected_anime, episode_idx


# get_next_episode_context is now imported from services.anime.episode_context


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
