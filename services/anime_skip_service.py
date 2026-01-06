"""Anime Skip API integration service.

GraphQL client for anime-skip.com API to fetch intro/outro timestamps.
Provides automatic skip functionality for anime playback.

API Documentation: https://anime-skip.com/docs/api
"""

import httpx
from loguru import logger

from models.config import settings
from models.models import SkipInterval
from utils.cache_manager import get_cache


class AnimeSkipService:
    """Client for Anime Skip API (anime-skip.com).

    Provides methods to:
    - Search for shows by AniList ID or title
    - Fetch skip timestamps for specific episodes
    - Cache results for offline playback
    """

    def __init__(self) -> None:
        """Initialize Anime Skip service with configuration."""
        self.api_url = settings.skip.api_url
        self.client_id = settings.skip.api_client_id
        self.cache = get_cache()
        self.cache_ttl = settings.skip.cache_duration_days * 24 * 3600  # days to seconds
        self.timeout = 5.0  # 5 second timeout for API requests

        logger.debug(f"Initialized AnimeSkipService with API: {self.api_url}")

    def _graphql_request(self, query: str, variables: dict | None = None) -> dict | None:
        """Execute GraphQL request to Anime Skip API.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Response data dict or None on error
        """
        headers = {
            "Content-Type": "application/json",
            "X-Client-ID": self.client_id,
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    logger.warning(f"GraphQL errors: {data['errors']}")
                    return None

                return data.get("data")

        except httpx.TimeoutException:
            logger.warning(f"Anime Skip API timeout after {self.timeout}s")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Anime Skip API rate limit exceeded")
            else:
                logger.warning(f"Anime Skip API error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Anime Skip API request failed: {e}")
            return None

    def search_show(self, search_query: str, limit: int = 5) -> list[dict] | None:
        """Search for anime shows by title.

        Args:
            search_query: Anime title to search
            limit: Maximum results to return

        Returns:
            List of show dicts with id, name, originalName, externalIds
            or None on error
        """
        query = """
        query SearchShows($search: String!, $limit: Int!) {
            searchShows(search: $search, limit: $limit) {
                id
                name
                originalName
                externalIds {
                    source
                    id
                }
            }
        }
        """

        variables = {"search": search_query, "limit": limit}
        logger.debug(f"Searching Anime Skip for: {search_query}")

        data = self._graphql_request(query, variables)
        if not data:
            return None

        shows = data.get("searchShows", [])
        logger.debug(f"Found {len(shows)} shows on Anime Skip")
        return shows

    def map_anilist_to_show(
        self, anilist_id: int | None = None, anime_title: str | None = None
    ) -> str | None:
        """Map AniList ID or anime title to Anime Skip show ID.

        Args:
            anilist_id: AniList anime ID
            anime_title: Anime title for fuzzy matching fallback

        Returns:
            Anime Skip show UUID or None if not found
        """
        if not anilist_id and not anime_title:
            logger.debug("No AniList ID or title provided for mapping")
            return None

        # Check cache first
        cache_key = f"show_map:{anilist_id or anime_title}"
        cached_show_id = self.cache.get(cache_key)
        if cached_show_id:
            logger.debug(f"Found cached show mapping: {cached_show_id}")
            return cached_show_id

        # Try search by title (required for AniList mapping)
        if not anime_title:
            logger.debug("No anime title provided for search")
            return None

        shows = self.search_show(anime_title)
        if not shows:
            return None

        # Try exact AniList ID match first
        if anilist_id:
            for show in shows:
                external_ids = show.get("externalIds", [])
                for ext_id in external_ids:
                    if ext_id.get("source") == "anilist" and str(ext_id.get("id")) == str(
                        anilist_id
                    ):
                        show_id = show["id"]
                        logger.info(f"Mapped AniList {anilist_id} → Anime Skip {show_id}")
                        # Cache mapping with longer TTL (90 days)
                        self.cache.set(cache_key, show_id, expire=90 * 24 * 3600)
                        return show_id

        # Fallback to first search result (fuzzy title match)
        if shows:
            show_id = shows[0]["id"]
            show_name = shows[0].get("name", "Unknown")
            logger.info(f"Fuzzy mapped '{anime_title}' → {show_name} ({show_id})")
            # Cache with shorter TTL since it's fuzzy match
            self.cache.set(cache_key, show_id, expire=self.cache_ttl)
            return show_id

        logger.debug(f"No Anime Skip show found for: {anime_title}")
        return None

    def fetch_timestamps(
        self, anilist_id: int | None, episode_number: int, anime_title: str | None = None
    ) -> list[SkipInterval]:
        """Fetch skip timestamps for specific episode.

        Args:
            anilist_id: AniList anime ID
            episode_number: Episode number (1-indexed)
            anime_title: Anime title for fallback mapping

        Returns:
            List of SkipInterval objects, empty list on error
        """
        # Check cache first
        cache_key = f"skip:{anilist_id}:{episode_number}"
        cached_intervals = self.cache.get(cache_key)
        if cached_intervals is not None:
            logger.debug(f"Cache hit for skip intervals: {cache_key}")
            return cached_intervals

        # Map to Anime Skip show ID
        show_id = self.map_anilist_to_show(anilist_id, anime_title)
        if not show_id:
            logger.debug(f"Cannot fetch timestamps: no show mapping for AniList {anilist_id}")
            return []

        # Fetch timestamps from API
        query = """
        query GetTimestamps($showId: UUID!, $episodeNumber: Float!) {
            show(id: $showId) {
                episodes(episodeNumber: $episodeNumber) {
                    timestamps {
                        typeId
                        at
                        episodeId
                    }
                }
            }
        }
        """

        variables = {"showId": show_id, "episodeNumber": float(episode_number)}
        logger.debug(f"Fetching timestamps for show {show_id}, episode {episode_number}")

        data = self._graphql_request(query, variables)
        if not data or not data.get("show"):
            logger.debug("No timestamp data returned from API")
            # Cache empty result to avoid repeated API calls
            self.cache.set(cache_key, [], expire=self.cache_ttl)
            return []

        episodes = data["show"].get("episodes", [])
        if not episodes:
            logger.debug(f"No episodes found for episode number {episode_number}")
            self.cache.set(cache_key, [], expire=self.cache_ttl)
            return []

        # Parse timestamps into intervals
        timestamps = episodes[0].get("timestamps", [])
        intervals = self._parse_timestamps(timestamps)

        # Filter by enabled types
        intervals = self._filter_intervals(intervals)

        logger.info(f"Found {len(intervals)} skip intervals for episode {episode_number}")
        for interval in intervals:
            logger.debug(
                f"  {interval.type}: {interval.start:.1f}s - {interval.end:.1f}s ({interval.type_label})"
            )

        # Cache results
        self.cache.set(cache_key, intervals, expire=self.cache_ttl)
        return intervals

    def _parse_timestamps(self, timestamps: list[dict]) -> list[SkipInterval]:
        """Parse API timestamps into SkipInterval objects.

        Timestamps come in pairs with same typeId:
        [{"typeId": "op", "at": 90}, {"typeId": "op", "at": 210}]
        → SkipInterval(type="op", start=90, end=210)

        Args:
            timestamps: List of timestamp dicts from API

        Returns:
            List of validated SkipInterval objects
        """
        if not timestamps:
            return []

        # Group timestamps by type
        by_type: dict[str, list[float]] = {}
        for ts in timestamps:
            type_id = ts.get("typeId")
            at = ts.get("at")
            if type_id and at is not None:
                if type_id not in by_type:
                    by_type[type_id] = []
                by_type[type_id].append(float(at))

        # Create intervals from consecutive pairs
        intervals = []
        for type_id, times in by_type.items():
            times.sort()  # Ensure chronological order
            # Take consecutive pairs (start, end)
            for i in range(0, len(times) - 1, 2):
                try:
                    interval = SkipInterval(type=type_id, start=times[i], end=times[i + 1])
                    intervals.append(interval)
                except Exception as e:
                    logger.warning(f"Invalid skip interval {type_id} {times[i]}-{times[i+1]}: {e}")

        return intervals

    def _filter_intervals(self, intervals: list[SkipInterval]) -> list[SkipInterval]:
        """Filter intervals by user settings.

        Args:
            intervals: All parsed intervals

        Returns:
            Filtered intervals based on settings.skip_intros, etc.
        """
        filtered = []
        for interval in intervals:
            skip_type = interval.type
            # Map type to setting
            if skip_type in ("op", "mixed-op") and settings.skip.skip_intros:
                filtered.append(interval)
            elif skip_type in ("ed", "mixed-ed") and settings.skip.skip_outros:
                filtered.append(interval)
            elif skip_type == "recap" and settings.skip.skip_recaps:
                filtered.append(interval)
            elif skip_type == "preview" and settings.skip.skip_previews:
                filtered.append(interval)

        return filtered


# Singleton instance
anime_skip_service = AnimeSkipService()
