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
                try:
                    error_detail = e.response.json()
                    logger.warning(
                        f"Anime Skip API error {e.response.status_code}: {error_detail}"
                    )
                except Exception:
                    logger.warning(
                        f"Anime Skip API error: {e.response.status_code} - {e.response.text}"
                    )
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

        # Use first search result (fuzzy title match)
        # Note: Anime Skip test API doesn't support externalLinks for AniList ID matching
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
        query GetTimestamps($showId: ID!) {
            findShow(showId: $showId) {
                episodes {
                    number
                    timestamps {
                        type {
                            name
                        }
                        at
                    }
                }
            }
        }
        """

        variables = {"showId": show_id}
        logger.debug(f"Fetching timestamps for show {show_id}, episode {episode_number}")

        data = self._graphql_request(query, variables)
        if not data or not data.get("findShow"):
            logger.debug("No timestamp data returned from API")
            # Cache empty result to avoid repeated API calls
            self.cache.set(cache_key, [], expire=self.cache_ttl)
            return []

        all_episodes = data["findShow"].get("episodes", [])
        if not all_episodes:
            logger.debug(f"No episodes found for show {show_id}")
            self.cache.set(cache_key, [], expire=self.cache_ttl)
            return []

        # Find the specific episode by number
        target_episode_str = str(episode_number)
        timestamps = []
        for episode in all_episodes:
            if episode.get("number") == target_episode_str:
                timestamps = episode.get("timestamps", [])
                break

        if not timestamps:
            logger.debug(f"No timestamps found for episode {episode_number}")
            self.cache.set(cache_key, [], expire=self.cache_ttl)
            return []

        # Parse timestamps into intervals
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

        Timestamps come with type objects and mark segment boundaries:
        Canon → Intro → Canon → Credits (opening/ending segments between Canon markers)

        Args:
            timestamps: List of timestamp dicts from API

        Returns:
            List of validated SkipInterval objects
        """
        if not timestamps:
            return []

        # Extract segments between Canon markers
        intervals = []
        i = 0
        while i < len(timestamps) - 1:
            current = timestamps[i]
            next_ts = timestamps[i + 1]

            current_type = current.get("type", {}).get("name", "")
            next_type = next_ts.get("type", {}).get("name", "")
            current_at = current.get("at")
            next_at = next_ts.get("at")

            # Skip if data is incomplete
            if not current_type or not next_type or current_at is None or next_at is None:
                i += 1
                continue

            # Check if this is a skippable segment (Intro, Credits, Preview, Mixed Credits)
            # Segments are typically between Canon markers
            if current_type in ("Intro", "Credits", "Preview", "Mixed Credits", "Title Card"):
                # Find the end of this segment (next Canon or end)
                if i + 1 < len(timestamps):
                    end_marker = timestamps[i + 1]
                    end_type = end_marker.get("type", {}).get("name", "")
                    end_at = end_marker.get("at")

                    if end_at and end_at > current_at:
                        # Map type names to our internal types
                        skip_type = self._map_type_name(current_type)
                        try:
                            interval = SkipInterval(
                                type=skip_type, start=float(current_at), end=float(end_at)
                            )
                            intervals.append(interval)
                        except Exception as e:
                            logger.warning(f"Invalid skip interval {skip_type}: {e}")

            i += 1

        return intervals

    def _map_type_name(self, type_name: str) -> str:
        """Map Anime Skip type names to our internal types.

        Args:
            type_name: Type name from Anime Skip API

        Returns:
            Internal type code (op, ed, recap, preview)
        """
        mapping = {
            "Intro": "op",
            "Credits": "ed",
            "Mixed Credits": "mixed-ed",
            "Preview": "preview",
            "Recap": "recap",
            "Title Card": "op",  # Treat title cards as part of intro
        }
        return mapping.get(type_name, type_name.lower())

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
