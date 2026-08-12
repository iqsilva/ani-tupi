"""History management service."""

import time

from models.config import get_data_path
from services.repository import rep
from utils.persistence import JSONStore
from utils.exceptions import PersistenceError
from utils.logging import get_logger
from models.models import HistoryEntry

logger = get_logger(__name__)

HISTORY_PATH = get_data_path()
_history_store = JSONStore(HISTORY_PATH / "history.json")


def save_history(
    anime: str,
    episode: int,
    source: str | None = None,
    total_episodes: int | None = None,
    anime_urls: dict[str, str] | None = None,
    position: float | None = None,
    duration: float | None = None,
) -> None:
    """Save watch history with timestamp, source, and total episodes.

    Format: {"anime_name": [timestamp, episode_idx, None, source, total_episodes, anime_urls, position, duration], ...}
    - source is the scraper name (e.g., "animefire", "sushianimes")
    - total_episodes is the known total count of episodes (auto-detected if not provided)
    - position/duration store in-episode playback progress in seconds (optional)
    """
    if total_episodes is None:
        episode_list = rep.get_episode_list(anime)
        if episode_list:
            total_episodes = len(episode_list)

    if anime_urls is None:
        anime_urls = {}
        for url, url_source, _ in rep.anime_to_urls.get(anime, []):
            anime_urls[url_source] = url

        if not anime_urls and source:
            anime_list = rep.anime_to_urls.get(anime, [])
            for url, url_source, _ in anime_list:
                if url_source == source:
                    anime_urls[url_source] = url
                    break

    try:
        entry = HistoryEntry(
            timestamp=int(time.time()),
            episode_idx=episode,
            source=source,
            total_episodes=total_episodes,
            urls=anime_urls or {},
            position=position,
            duration=duration,
        )
        _history_store.set(anime, entry.to_list())
    except PersistenceError as e:
        logger.error(f"Failed to save history: {e}")


def save_history_from_event(
    anime_title: str,
    episode_idx: int,
    action: str = "watched",
    source: str | None = None,
) -> None:
    """Save watch history from IPC keybinding event.

    This function is called when the user triggers episode navigation via
    keybindings (Shift+N, Shift+M, etc.) during MPV playback.

    Args:
        anime_title: Anime name
        episode_idx: 0-based episode index
        action: Action type - "watched" (marked as watched), "started" (began watching),
                "skipped" (skipped episode)
        source: Scraper source name (e.g., "animefire")
    """
    total_episodes = None
    episode_list = rep.get_episode_list(anime_title)
    if episode_list:
        total_episodes = len(episode_list)

    save_history(anime_title, episode_idx, source, total_episodes)
    logger.info(f"Saved history for '{anime_title}' Ep {episode_idx + 1} (action: {action})")


def reset_history(anime: str) -> None:
    """Remove anime from watch history (reset to episode 0).

    Args:
        anime: Anime title to reset
    """
    try:
        _history_store.delete(anime)
        logger.info(f"Reset history for '{anime}'")
    except PersistenceError as e:
        logger.error(f"Failed to reset history for '{anime}': {e}")
