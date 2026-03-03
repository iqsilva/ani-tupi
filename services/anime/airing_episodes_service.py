"""Airing Episodes Service - fetches and filters anime with airing episodes.

This service supports the "Novos Episódios" (New Episodes) tab feature by:
- Fetching the user's watching list from AniList
- Filtering for anime with airing episode data (nextAiringEpisode not null)
- Filtering for only "awaiting" episodes (scheduled within 90 days, not yet aired)
- Calculating episode gaps (how many episodes behind)
- Sorting by urgency (most episodes behind first)
- Returning structured AiringAnimeEntry objects for display
"""

import logging
import time

from models.models import AiringAnimeEntry, AniListTitle
from services.anilist_service import anilist_client


logger = logging.getLogger(__name__)

# Time windows for episode status determination
NINETY_DAYS_SECONDS = 90 * 24 * 60 * 60  # 90 days in seconds


class AiringEpisodesService:
    """Service for fetching and managing airing episodes from user's watching list."""

    def __init__(self):
        """Initialize service with AniList client."""
        self.client = anilist_client

    @staticmethod
    def _is_awaiting_episode(airing_at: int | None) -> bool:
        """Check if an episode is awaiting (scheduled within 90 days, not yet aired).

        Args:
            airing_at: Unix timestamp of episode air time (or None if unknown)

        Returns:
            True if episode is awaiting (not yet aired, within 90 days),
            False if already aired or too far in future
        """
        if airing_at is None:
            return False

        now = int(time.time())

        # Episode must be in the future (not yet aired)
        if airing_at <= now:
            return False

        # Episode must be within 90 days (strictly less than)
        if airing_at >= now + NINETY_DAYS_SECONDS:
            return False

        return True

    def get_watching_with_airing_episodes(self) -> list[AiringAnimeEntry]:
        """Get user's watching anime with new AWAITING episodes, sorted by urgency.

        "Awaiting" means the next episode is scheduled to air within 90 days
        and hasn't aired yet. Excludes:
        - Anime already aired/completed (nextAiringEpisode.airingAt in past)
        - Anime on hiatus (nextAiringEpisode.airingAt more than 90 days away)
        - Anime without scheduled next episodes

        This method:
        1. Fetches user's CURRENT watching list from AniList
        2. Filters anime to only those with nextAiringEpisode data (actively airing)
        3. Filters anime to only those with awaiting episodes (within 90 days, not aired)
        4. Calculates episodes_behind (nextEpisode - userProgress)
        5. Sorts by episodes_behind descending (most urgent first)
        6. Returns structured AiringAnimeEntry objects

        Returns:
            List of AiringAnimeEntry objects sorted by urgency (most behind first),
            or empty list if not authenticated, no airing anime, or no awaiting episodes found
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

                # NEW: Filter for only "awaiting" episodes
                airing_at = next_airing.get("airingAt")
                if not self._is_awaiting_episode(airing_at):
                    logger.debug(
                        f"Skipping anime {media.get('id')}: episode not awaiting "
                        f"(airing_at={airing_at})"
                    )
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

                # Calculate gap: episodes behind = (last aired episode) - (user progress)
                # where last aired episode = next_episode_number - 1
                episodes_behind = max(0, (next_episode_number - 1) - progress)

                # Extract optional fields
                anilist_id = media.get("id", 0)
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
