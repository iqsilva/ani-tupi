"""Auto-discover AniList IDs for scraped anime using fuzzy matching.

When user does manual search without AniList, automatically match results
against AniList API to get anilist_id. This enables better caching and
metadata enrichment.
"""

from fuzzywuzzy import fuzz

from models.models import AniListAnime, AniListSearchResult
from models.config import settings
from utils.cache_manager import get_cache


def auto_discover_anilist_id(scraper_title: str) -> list[AniListSearchResult]:
    """Auto-discover AniList ID via API using fuzzy matching.

    Tries to find best match in AniList for the scraper title.
    Only accepts strong matches (score >= threshold from config).
    Results are cached to avoid repeated API calls.

    Args:
        scraper_title: Anime title from scraper (possibly normalized)

    Returns:
        A list of AniListSearchResult, sorted by score descending.
    """

    try:
        # Check cache first
        cache = get_cache()
        cache_key = f"anilist_id:{scraper_title.lower()}"

        cached = cache.get(cache_key)
        if cached is not None:
            # Handle backward compatibility with old cache format (int)
            if isinstance(cached, list):
                try:
                    return [AniListSearchResult(**item) for item in cached]
                except TypeError:
                    # In case of malformed list, treat as a cache miss
                    pass
            # Old format or malformed, fall through to re-fetch

        # Query AniList API
        from services.anilist_service import anilist_client

        results = anilist_client.search_anime(scraper_title)

        if not results:
            # Cache "not found" result for 1 day to avoid repeated API calls
            cache.set(cache_key, [], expire=86400)
            return []

        # Fuzzy match against scraper title
        matches = []
        for anime in results:
            title_romaji = anime.title.romaji or ""
            title_english = anime.title.english or ""

            # Skip if no titles available
            if not title_romaji and not title_english:
                continue

            # Check both titles using token_sort_ratio for better word order tolerance
            score_romaji = (
                fuzz.token_sort_ratio(scraper_title.lower(), title_romaji.lower())
                if title_romaji
                else 0
            )
            score_english = (
                fuzz.token_sort_ratio(scraper_title.lower(), title_english.lower())
                if title_english
                else 0
            )
            score = max(score_romaji, score_english)

            threshold = settings.cache.anilist_fuzzy_threshold
            if score >= threshold:
                matches.append(
                    AniListSearchResult(
                        anilist_id=anime.id,
                        score=score,
                        title=title_romaji or title_english,
                    )
                )

        # Sort by score descending
        sorted_matches = sorted(matches, key=lambda x: x.score, reverse=True)

        # Cache for 30 days
        cache.set(cache_key, [match.model_dump() for match in sorted_matches], expire=2592000)
        return sorted_matches

    except Exception as e:
        print(f"⚠️  Erro ao buscar AniList ID para '{scraper_title}': {e}")
        return []


def get_anilist_id_from_title(anime_title: str) -> int | None:
    """Wrapper around auto_discover_anilist_id for single best match."""
    results = auto_discover_anilist_id(anime_title)
    if results:
        return results[0].anilist_id
    return None


def get_anilist_metadata(anilist_id: int) -> AniListAnime | None:
    """Fetch and cache complete AniList metadata (title, cover, etc).

    Args:
        anilist_id: AniList ID

    Returns:
        AniListAnime with metadata or None if fetch fails
    """

    cache = get_cache()
    cache_key = f"anilist_meta:{anilist_id}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached is not None:
        # Handle both dict (cached) and AniListAnime (new format)
        if isinstance(cached, dict):
            return AniListAnime.model_validate(cached)
        if isinstance(cached, AniListAnime):
            return cached
        # Invalid cache entry - fall through to re-fetch

    try:
        from services.anilist_service import anilist_client

        # Fetch from AniList API
        metadata = anilist_client.get_anime_by_id(anilist_id)

        if metadata:
            # Cache as dict for compatibility
            cache.set(cache_key, metadata.model_dump(), expire=2592000)
            return metadata

        return None

    except Exception as e:
        print(f"⚠️  Erro ao buscar metadata do AniList ID {anilist_id}: {e}")
        return None
