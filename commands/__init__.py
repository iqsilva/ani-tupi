"""Command handlers for ani-tupi CLI.

Each module handles a specific user interaction flow:
- anime.py: Anime search, selection, and playback
- sources.py: Plugin/source management
"""

from commands.anime import anime
from commands.config import config
from commands.update import update
from commands.sources import manage_sources

__all__ = ["anime", "config", "manage_sources", "update"]
