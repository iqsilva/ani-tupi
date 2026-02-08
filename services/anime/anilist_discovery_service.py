"""AniList discovery service - find AniList IDs for scraped anime titles.

This service eliminates duplicate AniList discovery logic by providing
a single, reusable function that handles:
- Authentication check
- Title normalization
- AniList search
- Metadata fetching
- Error handling

All results are returned as immutable dataclasses.
"""

from dataclasses import dataclass
import logging

from services.anilist_service import anilist_client
from utils.anilist_discovery import auto_discover_anilist_id, get_anilist_metadata
from utils.title_utils import normalize_title_for_search


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AniListDiscoveryResult:
    """Immutable result from AniList discovery.

    Attributes:
        anilist_id: The AniList ID if found, None otherwise
        anilist_title: The formatted AniList title if found, None otherwise
        total_episodes: Total episodes from AniList if found, None otherwise
        mal_id: MyAnimeList ID if found (for AniSkip), None otherwise
        found: Whether a match was found
        authenticated: Whether AniList was authenticated
    """

    anilist_id: int | None
    anilist_title: str | None
    total_episodes: int | None
    mal_id: int | None
    found: bool
    authenticated: bool


def discover_anilist_info(anime_title: str) -> AniListDiscoveryResult:
    """Discover AniList information for an anime title.

    This function:
    1. Checks if AniList is authenticated
    2. Normalizes the title (removes Portuguese suffixes like Dublado, Legendado)
    3. Searches AniList for matches
    4. Fetches metadata if found
    5. Returns an immutable result

    All errors are handled gracefully - the function never raises exceptions.

    Args:
        anime_title: The anime title to search for (may include suffixes)

    Returns:
        AniListDiscoveryResult with discovery results
    """
    # Check authentication first
    if not anilist_client.is_authenticated():
        return AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=False,
        )

    # Normalize title
    normalized_title = normalize_title_for_search(anime_title)

    # Handle empty title after normalization
    if not normalized_title:
        return AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=True,
        )

    # Search AniList
    try:
        anilist_results = auto_discover_anilist_id(normalized_title)
    except Exception as e:
        logger.warning("AniList search failed for '%s': %s", anime_title, e)
        return AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=True,
        )

    # No match found
    if not anilist_results:
        return AniListDiscoveryResult(
            anilist_id=None,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=False,
            authenticated=True,
        )

    # Get the best match (first result, sorted by score)
    best_match = anilist_results[0]
    anilist_id = best_match.anilist_id

    # Fetch metadata
    try:
        metadata = get_anilist_metadata(anilist_id)
    except Exception as e:
        logger.warning("AniList metadata fetch failed for ID %d: %s", anilist_id, e)
        # Return partial result with ID but no title/episodes
        return AniListDiscoveryResult(
            anilist_id=anilist_id,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=True,
            authenticated=True,
        )

    # Metadata not found
    if metadata is None:
        return AniListDiscoveryResult(
            anilist_id=anilist_id,
            anilist_title=None,
            total_episodes=None,
            mal_id=None,
            found=True,
            authenticated=True,
        )

    # Format title and return complete result
    formatted_title = anilist_client.format_title(metadata.title)

    return AniListDiscoveryResult(
        anilist_id=anilist_id,
        anilist_title=formatted_title,
        total_episodes=metadata.episodes,
        mal_id=metadata.id_mal,
        found=True,
        authenticated=True,
    )
