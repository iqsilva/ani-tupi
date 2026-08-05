"""Playback service - orchestrates the full playback flow.

This service coordinates:
- Preparing playback context from search or history
- Getting episode URLs
- Episode navigation

All results are returned as immutable dataclasses.
All errors are handled gracefully - functions never raise exceptions.
"""

from dataclasses import dataclass
from utils.logging import get_logger

from services.history_service import load_history
from services.repository import rep

logger = get_logger(__name__)


# =============================================================================
# Immutable Data Types
# =============================================================================


@dataclass(frozen=True)
class PlaybackContext:
    """Immutable context for anime playback session.

    Attributes:
        anime_title: Selected anime title
        episode_idx: Current episode index (0-indexed)
        source: Video source/scraper name
        anilist_id: AniList ID if discovered
        anilist_title: Formatted AniList title if found
        total_episodes_anilist: Total episodes from AniList
        num_episodes: Total episodes from scraper
        episode_list: List of episode strings for menu display
    """

    anime_title: str
    episode_idx: int
    source: str | None
    num_episodes: int
    episode_list: tuple[str, ...]
    anilist_id: int | None = None
    anilist_title: str | None = None
    total_episodes_anilist: int | None = None


@dataclass(frozen=True)
class EpisodePlaybackResult:
    """Immutable result from episode video URL extraction.

    Attributes:
        player_url: Video URL for playback
        source: Source that provided the video
        success: Whether video URL was found
        error_message: Error message if failed
    """

    player_url: str | None
    source: str | None
    success: bool
    error_message: str | None


# =============================================================================
# Playback Preparation Functions
# =============================================================================


def prepare_playback_from_search(
    selected_anime: str,
    episode_idx: int,
    source: str | None,
) -> PlaybackContext | None:
    """Prepare playback context after anime search.

    This function:
    1. Gets episode list from repository
    2. Builds immutable PlaybackContext

    All errors are handled gracefully - the function never raises exceptions.

    Args:
        selected_anime: The anime title selected from search results
        episode_idx: The episode index to start from (0-indexed)
        source: The scraper source name

    Returns:
        PlaybackContext with all fields populated, or None on critical failure
    """
    # Get episode list from repository
    episode_list_raw = rep.get_episode_list(selected_anime)
    episode_list = tuple(episode_list_raw) if episode_list_raw else ()
    num_episodes = len(episode_list)

    return PlaybackContext(
        anime_title=selected_anime,
        episode_idx=episode_idx,
        source=source,
        num_episodes=num_episodes,
        episode_list=episode_list,
    )


def prepare_playback_from_history() -> PlaybackContext | None:
    """Prepare playback context from continue watching history.

    This function:
    1. Loads history using history_service
    2. Gets episode list from repository
    3. Builds immutable PlaybackContext

    All errors are handled gracefully.

    Returns:
        PlaybackContext with all fields populated, or None if history load fails
    """
    # Load history
    history_result = load_history()
    if history_result is None:
        return None

    anime_title, episode_idx, anilist_id, anilist_title = history_result

    # Get episode list from repository
    episode_list_raw = rep.get_episode_list(anime_title)
    episode_list = tuple(episode_list_raw) if episode_list_raw else ()
    num_episodes = len(episode_list)

    return PlaybackContext(
        anime_title=anime_title,
        episode_idx=episode_idx,
        source=None,  # Source not stored in history
        anilist_id=anilist_id,
        anilist_title=anilist_title,
        num_episodes=num_episodes,
        episode_list=episode_list,
    )


# =============================================================================
# Episode URL Retrieval
# =============================================================================


def get_episode_url_and_source(
    anime_title: str,
    episode: int,
    current_player_url: str | None = None,
) -> EpisodePlaybackResult:
    """Get video URL for an episode.

    This function:
    1. If current_player_url is provided, tries to derive the episode URL via
       pattern substitution (fast HEAD request) before falling back to scraping
    2. Checks if this is an awaiting episode with direct URL from homepage search
    3. Uses repository to search for video URL (regular path)
    4. Handles errors gracefully
    5. Returns immutable result

    Args:
        anime_title: The anime title
        episode: The episode number (1-indexed)
        current_player_url: Currently playing URL; used to attempt URL pattern
            derivation before scraping (optional)

    Returns:
        EpisodePlaybackResult with video URL or error message
    """
    try:
        # Fast path: try URL pattern derivation when we have an existing player URL
        if current_player_url:
            try:
                from services.anime.episode_url_pattern import (
                    derive_episode_url,
                    detect_episode_pattern,
                    validate_episode_url,
                )

                if detect_episode_pattern(current_player_url):
                    logger.info(
                        f"[URL-PATTERN] Tentando derivar ep {episode} de: {current_player_url[:80]}"
                    )
                    derived_url = derive_episode_url(current_player_url, episode)
                    if derived_url and validate_episode_url(derived_url):
                        logger.debug(
                            "Episode URL pattern hit for %s ep %d: %s",
                            anime_title,
                            episode,
                            derived_url,
                        )
                        return EpisodePlaybackResult(
                            player_url=derived_url,
                            source="pattern",
                            success=True,
                            error_message=None,
                        )
                    else:
                        logger.debug(
                            "Episode URL pattern miss for %s ep %d, falling back to scraping",
                            anime_title,
                            episode,
                        )
            except Exception as e:
                logger.debug("Episode URL pattern error for %s ep %d: %s", anime_title, episode, e)

        # Regular path: Get episode URL and source info
        episode_info = rep.get_episode_url_and_source(anime_title, episode)
        source = episode_info[1] if episode_info else None

        # Search for video player URL
        player_url = rep.search_player(anime_title, episode)

        if player_url:
            return EpisodePlaybackResult(
                player_url=player_url,
                source=source,
                success=True,
                error_message=None,
            )
        else:
            return EpisodePlaybackResult(
                player_url=None,
                source=source,
                success=False,
                error_message="Nenhuma fonte conseguiu extrair o video.",
            )
    except Exception as e:
        logger.error("Failed to get episode URL for '%s' ep %d: %s", anime_title, episode, e)
        return EpisodePlaybackResult(
            player_url=None,
            source=None,
            success=False,
            error_message=f"Erro ao buscar video: {str(e)}",
        )


# =============================================================================
# Episode Navigation
# =============================================================================


def navigate_episodes(
    ctx: PlaybackContext,
    action: str,
    target_idx: int | None = None,
) -> PlaybackContext:
    """Navigate to a different episode.

    This function creates a new PlaybackContext with updated episode_idx.
    The original context is never modified (immutability).

    Args:
        ctx: Current playback context
        action: Navigation action - "next", "previous", "replay", "choose"
        target_idx: Target episode index for "choose" action (0-indexed)

    Returns:
        New PlaybackContext with updated episode_idx
    """
    new_idx = ctx.episode_idx

    if action == "next":
        # Go to next episode if not at the end
        if ctx.episode_idx < ctx.num_episodes - 1:
            new_idx = ctx.episode_idx + 1
    elif action == "previous":
        # Go to previous episode if not at the beginning
        if ctx.episode_idx > 0:
            new_idx = ctx.episode_idx - 1
    elif action == "replay":
        # Keep same episode
        new_idx = ctx.episode_idx
    elif action == "choose":
        # Jump to specific episode
        if target_idx is not None:
            # Clamp to valid range
            if target_idx < 0:
                new_idx = 0
            elif target_idx >= ctx.num_episodes:
                new_idx = max(0, ctx.num_episodes - 1)
            else:
                new_idx = target_idx
    # For unknown actions, keep current episode

    # Return new context with updated episode_idx
    return PlaybackContext(
        anime_title=ctx.anime_title,
        episode_idx=new_idx,
        source=ctx.source,
        anilist_id=ctx.anilist_id,
        anilist_title=ctx.anilist_title,
        total_episodes_anilist=ctx.total_episodes_anilist,
        num_episodes=ctx.num_episodes,
        episode_list=ctx.episode_list,
    )


def build_episode_sources(
    anime_title: str,
    episode: int,
    url_result: "EpisodePlaybackResult",
) -> list[tuple[str, str, str | None]]:
    """Build ordered playback sources for an episode.

    Keeps any direct/fast-path URL as the first candidate, but still collects
    all remaining repository-backed sources so playback fallback can continue
    when the first source fails.
    """
    sources: list[tuple[str, str, str | None]] = []
    seen_sources: set[str] = set()

    if url_result.success and url_result.player_url:
        direct_source = url_result.source or "unknown"
        sources.append((url_result.player_url, direct_source, None))
        seen_sources.add(direct_source)
        logger.debug(
            "Using direct URL from get_episode_url_and_source: %s...", url_result.player_url[:80]
        )
    else:
        logger.debug(
            "get_episode_url_and_source failed (success=%s), using fallback", url_result.success
        )

    page_sources = rep.get_all_episode_sources(anime_title, episode)
    logger.debug("Found %d page sources", len(page_sources))

    for page_url, source_name in page_sources:
        if source_name in seen_sources:
            logger.debug("Skipping duplicate source already queued: %s", source_name)
            continue

        logger.debug("Extracting video URL from %s page: %s...", source_name, page_url[:80])
        try:
            video_urls = rep.search_player_from_page(page_url, source_name)
            if video_urls:
                logger.debug(
                    "Got %d candidate URL(s) from %s (first: %s...)",
                    len(video_urls),
                    source_name,
                    video_urls[0][:80],
                )
                for video_url in video_urls:
                    sources.append((video_url, source_name, page_url))
                seen_sources.add(source_name)
            else:
                logger.debug("search_player_from_page returned no URLs for %s", source_name)
        except Exception as e:
            logger.debug("Exception extracting from %s: %s", source_name, e)
            continue

    return [(url, source, referrer) for url, source, referrer in sources if url and source]
