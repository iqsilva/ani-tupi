"""Episode repository for managing episode data and caching."""
from collections import defaultdict
from models.models import EpisodeData


class EpisodeRepository:
    """Manages episode lists and episode state for anime.

    Single responsibility: track episode metadata, cache, and state management
    for all registered anime.
    """

    _instance = None

    def __new__(cls):
        """Enforce singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._anime_episodes_titles = defaultdict(list)
            cls._instance._anime_episodes_urls = defaultdict(list)
        return cls._instance

    def add_episode_list(
        self, anime: str, title_list: list[str], url_list: list[str], source: str
    ) -> None:
        """Add episode list with validation.

        Args:
            anime: Anime title
            title_list: List of episode titles
            url_list: List of episode URLs
            source: Plugin source name

        Raises:
            ValueError: If title_list and url_list have different lengths.
        """
        # Validate using EpisodeData model
        episode_data = EpisodeData(
            anime_title=anime,
            episode_titles=title_list,
            episode_urls=url_list,
            source=source,
        )

        self._anime_episodes_titles[anime].append(episode_data.episode_titles)
        self._anime_episodes_urls[anime].append((episode_data.episode_urls, source))

    def get_episode_list(self, anime: str) -> list[str]:
        """Get episode list for anime (returns longest list if multiple sources).

        Args:
            anime: Anime title

        Returns:
            List of episode titles from source with most episodes
        """
        episodes = self._anime_episodes_titles[anime]
        if not episodes:
            return []
        episode_list = sorted(episodes, key=lambda title_list: len(title_list))[-1]
        return episode_list

    def get_episode_url(self, anime: str, episode_idx: int) -> str | None:
        """Get episode URL for a specific episode (0-indexed).

        Args:
            anime: Anime title
            episode_idx: Episode index (0-indexed)

        Returns:
            Episode URL or None if not found
        """
        # Convert from 0-indexed to 1-indexed
        episode_num = episode_idx + 1
        result = self.get_episode_url_and_source(anime, episode_num)
        if result:
            return result[0]
        return None

    def get_episode_url_and_source(self, anime: str, episode_num: int) -> tuple[str, str] | None:
        """Get episode URL and source name for a specific episode.

        Args:
            anime: Anime title
            episode_num: Episode number (1-indexed)

        Returns:
            Tuple of (episode_url, source_name) or None if not found
        """
        # Validate episode_num
        if episode_num < 1:
            return None

        for urls, source in self._anime_episodes_urls[anime]:
            if len(urls) >= episode_num:
                return (urls[episode_num - 1], source)

        return None

    def save_episode_state(self, anime: str) -> dict:
        """Save the current episode state for an anime.

        Used by source switching to preserve episode data across searches.

        Args:
            anime: Anime title

        Returns:
            Dict with keys 'urls' and 'titles' containing episode data
        """
        return {
            "urls": list(self._anime_episodes_urls[anime]),
            "titles": list(self._anime_episodes_titles[anime]),
        }

    def restore_episode_state(self, anime: str, state: dict) -> None:
        """Restore previously saved episode state for an anime.

        Used by source switching to restore episode data after search.

        Args:
            anime: Anime title
            state: Dict with 'urls' and 'titles' keys
        """
        self._anime_episodes_urls[anime] = state["urls"]
        self._anime_episodes_titles[anime] = state["titles"]

    def load_from_cache(self, anime: str, cache_data) -> None:
        """Populate repository from cached data.

        Cache-first approach: When anime is found in cache, load its data
        directly into the repository without searching scrapers.

        Args:
            anime: Anime title
            cache_data: ScraperCacheData model or dict with keys 'episode_urls' and 'episode_count'
        """
        if not cache_data:
            return

        # Handle both Pydantic models and dicts
        if hasattr(cache_data, "episode_urls"):
            # It's a Pydantic model
            episode_urls = cache_data.episode_urls
        else:
            # It's a dict
            episode_urls = cache_data.get("episode_urls", [])

        if not episode_urls:
            return

        # Generate episode titles from URLs (format: "Episódio 1", "Episódio 2", etc)
        episode_titles = [f"Episódio {i + 1}" for i in range(len(episode_urls))]

        # Add to repository as if it came from a "cache" source
        self._anime_episodes_titles[anime].append(episode_titles)
        self._anime_episodes_urls[anime].append((episode_urls, "cache"))

        # Note: We don't add a "dummy" entry to anime_to_urls here because:
        # 1. It's not a real scraper source - just cached episode data
        # 2. It would appear as "[cached]" in user-facing source lists
        # 3. search_anime() is called later to discover real sources for display

    def get_next_available_episode(self, anime: str, from_episode: int) -> tuple[int, str] | None:
        """Get next available episode from a given episode number.

        Searches all sources for the next available episode after the given one.

        Args:
            anime: Anime title
            from_episode: Episode number to search from (1-indexed)

        Returns:
            Tuple of (episode_number, url) or None if no more episodes
        """
        if from_episode < 1:
            from_episode = 1

        # Search all sources to find the highest available episode
        max_episode = 0
        best_url = None

        for urls, source in self._anime_episodes_urls.get(anime, []):
            # Check if this source has more episodes after from_episode
            if len(urls) > from_episode:
                # Has next episode
                max_episode = max(max_episode, len(urls))
                if not best_url:
                    best_url = urls[from_episode]  # Get next episode (0-indexed)

        if best_url:
            return (from_episode + 1, best_url)  # Return 1-indexed episode number

        return None

    def clear_episode_state(self, anime: str) -> None:
        """Clear episode state for a specific anime.

        Args:
            anime: Anime title
        """
        self._anime_episodes_titles[anime] = []
        self._anime_episodes_urls[anime] = []

    @classmethod
    def reset_singleton(cls) -> None:
        """Reset singleton instance for testing.

        Use only in test fixtures.
        """
        cls._instance = None
