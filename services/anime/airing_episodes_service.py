"""Airing Episodes Service - fetches and filters anime with airing episodes.

This service supports the "Novos Episódios" (New Episodes) tab feature by:
- Fetching the user's watching list from AniList
- Filtering for anime with airing episode data (nextAiringEpisode not null)
- Calculating episode gaps (how many episodes behind)
- Sorting by urgency (most episodes behind first)
- Returning structured AiringAnimeEntry objects for display
"""

import logging

from models.models import AiringAnimeEntry, AniListTitle
from services.anilist_service import anilist_client


logger = logging.getLogger(__name__)


class AiringEpisodesService:
    """Service for fetching and managing airing episodes from user's watching list."""

    def __init__(self):
        """Initialize service with AniList client."""
        self.client = anilist_client

    def get_watching_with_airing_episodes(self) -> list[AiringAnimeEntry]:
        """Get user's watching anime with new airing episodes, sorted by urgency.

        This method:
        1. Fetches user's CURRENT watching list from AniList
        2. Filters anime to only those with nextAiringEpisode data (actively airing)
        3. Calculates episodes_behind (nextEpisode - userProgress)
        4. Sorts by episodes_behind descending (most urgent first)
        5. Returns structured AiringAnimeEntry objects

        Returns:
            List of AiringAnimeEntry objects sorted by urgency (most behind first),
            or empty list if not authenticated or no airing anime found
        """
        # Fetch raw API entries
        entries = self.client.get_airing_episodes_for_watching()

        if not entries:
            return []

        # Filter and transform entries
        airing_anime: list[AiringAnimeEntry] = []

        for entry in entries:
            try:
                # Extract fields from API response
                progress = entry.get("progress", 0)
                media = entry.get("media")

                if not media:
                    continue

                # Skip if no airing episode data
                next_airing = media.get("nextAiringEpisode")
                if not next_airing:
                    continue

                # Extract title
                title_obj = media.get("title", {})
                if isinstance(title_obj, dict):
                    title = (
                        title_obj.get("romaji")
                        or title_obj.get("english")
                        or title_obj.get("native")
                        or "Unknown"
                    )
                elif isinstance(title_obj, AniListTitle):
                    title = title_obj.romaji or title_obj.english or title_obj.native or "Unknown"
                else:
                    title = str(title_obj)

                # Extract next episode number
                next_episode_number = next_airing.get("episode", 0)
                if next_episode_number <= 0:
                    continue

                # Calculate gap
                episodes_behind = max(0, next_episode_number - progress)

                # Extract optional fields
                anilist_id = media.get("id", 0)
                airing_at = next_airing.get("airingAt")
                average_score = media.get("averageScore")

                # Create AiringAnimeEntry
                entry_obj = AiringAnimeEntry(
                    anilist_id=anilist_id,
                    title=title,
                    progress=progress,
                    next_episode_number=next_episode_number,
                    episodes_behind=episodes_behind,
                    airing_at=airing_at,
                    average_score=average_score,
                )

                airing_anime.append(entry_obj)

            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Error processing airing episode entry: {e}")
                continue

        # Sort by episodes_behind descending (most urgent first)
        airing_anime.sort(key=lambda x: x.episodes_behind, reverse=True)

        return airing_anime
