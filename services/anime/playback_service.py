"""Playback service - orchestrates the full playback flow.

This service coordinates:
- Preparing playback context from search or history
- Getting episode URLs
- Syncing progress to AniList
- Episode navigation

All results are returned as immutable dataclasses.
All errors are handled gracefully - functions never raise exceptions.
"""

from dataclasses import dataclass
import logging

from models.models import Status
from services.anime.anilist_discovery_service import (
    discover_anilist_info,
)
from services.anilist_service import anilist_client
from services.history_service import load_history
from services.repository import rep


logger = logging.getLogger(__name__)


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
    anilist_id: int | None
    anilist_title: str | None
    total_episodes_anilist: int | None
    num_episodes: int
    episode_list: tuple[str, ...]


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
    1. Discovers AniList information for the anime
    2. Gets episode list from repository
    3. Builds immutable PlaybackContext

    All errors are handled gracefully - the function never raises exceptions.

    Args:
        selected_anime: The anime title selected from search results
        episode_idx: The episode index to start from (0-indexed)
        source: The scraper source name

    Returns:
        PlaybackContext with all fields populated, or None on critical failure
    """
    # Try to discover AniList info
    anilist_id: int | None = None
    anilist_title: str | None = None
    total_episodes_anilist: int | None = None

    try:
        anilist_result = discover_anilist_info(selected_anime)
        if anilist_result.found:
            anilist_id = anilist_result.anilist_id
            anilist_title = anilist_result.anilist_title
            total_episodes_anilist = anilist_result.total_episodes
    except Exception as e:
        logger.warning("Failed to discover AniList info for '%s': %s", selected_anime, e)
        # Continue without AniList info

    # Get episode list from repository
    episode_list_raw = rep.get_episode_list(selected_anime)
    episode_list = tuple(episode_list_raw) if episode_list_raw else ()
    num_episodes = len(episode_list)

    return PlaybackContext(
        anime_title=selected_anime,
        episode_idx=episode_idx,
        source=source,
        anilist_id=anilist_id,
        anilist_title=anilist_title,
        total_episodes_anilist=total_episodes_anilist,
        num_episodes=num_episodes,
        episode_list=episode_list,
    )


def prepare_playback_from_history() -> PlaybackContext | None:
    """Prepare playback context from continue watching history.

    This function:
    1. Loads history using history_service
    2. Discovers/enriches AniList information
    3. Gets episode list from repository
    4. Builds immutable PlaybackContext

    All errors are handled gracefully.

    Returns:
        PlaybackContext with all fields populated, or None if history load fails
    """
    # Load history
    history_result = load_history()
    if history_result is None:
        return None

    anime_title, episode_idx, anilist_id_from_history, anilist_title_from_history = history_result

    # Try to discover/enrich AniList info
    anilist_id: int | None = anilist_id_from_history
    anilist_title: str | None = anilist_title_from_history
    total_episodes_anilist: int | None = None

    try:
        anilist_result = discover_anilist_info(anime_title)
        if anilist_result.found:
            anilist_id = anilist_result.anilist_id
            anilist_title = anilist_result.anilist_title
            total_episodes_anilist = anilist_result.total_episodes
    except Exception as e:
        logger.warning("Failed to discover AniList info for '%s': %s", anime_title, e)
        # Continue with info from history

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
        total_episodes_anilist=total_episodes_anilist,
        num_episodes=num_episodes,
        episode_list=episode_list,
    )


# =============================================================================
# Episode URL Retrieval
# =============================================================================


def get_episode_url_and_source(
    anime_title: str,
    episode: int,
) -> EpisodePlaybackResult:
    """Get video URL for an episode.

    This function:
    1. Uses repository to search for video URL
    2. Handles errors gracefully
    3. Returns immutable result

    Args:
        anime_title: The anime title
        episode: The episode number (1-indexed)

    Returns:
        EpisodePlaybackResult with video URL or error message
    """
    try:
        # Get episode URL and source info
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
# AniList Progress Sync
# =============================================================================


def sync_progress_to_anilist(
    anilist_id: int | None,
    episode: int,
    num_episodes: int,
) -> bool:
    """Sync episode progress to AniList.

    This function:
    1. Checks if AniList is authenticated and has valid ID
    2. Adds anime to list if not present
    3. Promotes status if needed (PLANNING -> CURRENT)
    4. Updates episode progress
    5. Marks as COMPLETED if last episode

    All errors are handled gracefully - function never raises exceptions.

    Args:
        anilist_id: The AniList media ID (None = no sync)
        episode: The episode number watched (1-indexed)
        num_episodes: Total number of episodes

    Returns:
        True if sync was successful, False otherwise
    """
    # Check if we have an AniList ID
    if anilist_id is None:
        return False

    # Check if client is authenticated
    if not anilist_client.is_authenticated():
        return False

    try:
        # Check if anime is in any list
        if not anilist_client.is_in_any_list(anilist_id):
            logger.info("Adding anime %d to AniList CURRENT list", anilist_id)
            anilist_client.add_to_list(anilist_id, Status.CURRENT)
        else:
            # Check current status and promote if needed
            entry = anilist_client.get_media_list_entry(anilist_id)
            if entry:
                if entry.status == "PLANNING":
                    logger.info("Promoting anime %d from PLANNING to CURRENT", anilist_id)
                    anilist_client.add_to_list(anilist_id, Status.CURRENT)

        # Update progress
        success = anilist_client.update_progress(anilist_id, episode)
        if not success:
            logger.warning("Failed to update progress for anime %d ep %d", anilist_id, episode)
            return False

        # Check if last episode - mark as completed
        if episode == num_episodes and num_episodes > 0:
            entry = anilist_client.get_media_list_entry(anilist_id)
            if entry and entry.status == "CURRENT":
                logger.info("Marking anime %d as COMPLETED", anilist_id)
                anilist_client.change_status(anilist_id, Status.COMPLETED)

        return True

    except Exception as e:
        logger.error("Failed to sync progress to AniList for anime %d: %s", anilist_id, e)
        return False


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
