"""AniList ID to scraper title mapping persistence.

Handles saving and loading of mappings between AniList anime IDs
and scraper-specific titles for improved search accuracy.
"""

from models.config import get_data_path
from utils.exceptions import PersistenceError
from utils.logging import get_logger
from utils.persistence import JSONStore

logger = get_logger(__name__)

# Use centralized path function from config
HISTORY_PATH = get_data_path()

# AniList to scraper title mappings cache
_anilist_mappings_store = JSONStore(HISTORY_PATH / "anilist_mappings.json")


def load_anilist_mapping(
    anilist_id: int,
) -> tuple[str | None, str | None, str | None]:
    """Load saved scraper title, source, and URL for an AniList ID.

    Args:
        anilist_id: The AniList anime ID

    Returns:
        Tuple of (scraper_title, source, anime_url) or (None, None, None) if not found
    """
    mapping = _anilist_mappings_store.get(str(anilist_id))
    # Handle both old format (string) and new format (dict)
    if isinstance(mapping, dict):
        return (
            mapping.get("scraper_title"),
            mapping.get("source"),
            mapping.get("anime_url"),
        )
    # Old format only has title, no source or URL
    return mapping, None, None


def load_anilist_urls(anilist_id: int) -> dict[str, str]:
    """Load all saved anime URLs (source -> URL mapping) for an AniList ID.

    Args:
        anilist_id: The AniList anime ID

    Returns:
        Dict mapping sources to URLs (e.g., {"animefire": "https://...", "animesdigital": "https://..."})
    """
    mapping = _anilist_mappings_store.get(str(anilist_id))
    if isinstance(mapping, dict):
        return mapping.get("anime_urls", {})
    return {}


def load_anilist_search_title(anilist_id: int) -> str | None:
    """Load the original search/display title used for an AniList ID.

    Args:
        anilist_id: The AniList anime ID

    Returns:
        Original search title or None if not found
    """
    mapping = _anilist_mappings_store.get(str(anilist_id))
    # Only new format (dict) has search_title
    if isinstance(mapping, dict):
        return mapping.get("search_title")
    return None


def save_anilist_mapping(
    anilist_id: int,
    scraper_title: str,
    search_title: str | None = None,
    source: str | None = None,
    anime_url: str | None = None,
    language_choice: str | None = None,
    anime_urls: dict[str, str] | None = None,
) -> None:
    """Save scraper title choice, search title, source, URL(s), and language preference for an AniList ID.

    Args:
        anilist_id: The AniList ID
        scraper_title: The selected anime title from scraper
        search_title: The original search/display title used to find it
        source: The scraper source (e.g., "animefire", "animesdigital")
        anime_url: The anime page URL from the scraper (e.g., https://animefire.io/animes/...)
        language_choice: The language chosen ("romaji" or "english")
        anime_urls: Dict mapping sources to URLs (e.g., {"animefire": "https://...", "animesdigital": "https://..."})
    """
    try:
        mapping_id = str(anilist_id)
        # Preserve existing values if not provided
        existing = _anilist_mappings_store.get(mapping_id, {})
        if isinstance(existing, str):
            # Migrate old format to new format
            existing = {"scraper_title": existing}

        # Merge anime_urls with existing ones if not provided
        merged_urls = existing.get("anime_urls", {})
        if anime_urls:
            merged_urls.update(anime_urls)
        elif anime_url and source:
            # If single URL provided, add to urls dict
            merged_urls[source] = anime_url

        _anilist_mappings_store.set(
            mapping_id,
            {
                "scraper_title": scraper_title,
                "search_title": search_title or existing.get("search_title"),
                "source": source or existing.get("source"),
                "anime_url": anime_url or existing.get("anime_url"),
                "anime_urls": merged_urls,
                "language_choice": language_choice or existing.get("language_choice"),
            },
        )
    except PersistenceError as e:
        logger.error(f"Failed to save AniList mapping: {e}")


def load_language_preference(anilist_id: int) -> str | None:
    """Load the language preference (romaji or english) for an AniList ID.

    Args:
        anilist_id: The AniList anime ID

    Returns:
        "romaji", "english", or None if not found
    """
    mapping = _anilist_mappings_store.get(str(anilist_id))
    if isinstance(mapping, dict):
        return mapping.get("language_choice")
    return None


def save_language_preference(anilist_id: int, language_choice: str) -> None:
    """Save the language preference for an AniList ID.

    Args:
        anilist_id: The AniList anime ID
        language_choice: "romaji" or "english"
    """
    try:
        mapping_id = str(anilist_id)
        existing = _anilist_mappings_store.get(mapping_id, {})
        if isinstance(existing, str):
            existing = {"scraper_title": existing}

        existing["language_choice"] = language_choice
        _anilist_mappings_store.set(mapping_id, existing)
    except PersistenceError as e:
        logger.error(f"Failed to save language preference: {e}")
