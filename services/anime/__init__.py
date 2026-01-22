"""Anime service modules - business logic for anime operations.

This package provides:
- Title normalization and search helpers
- AniList integration flows
- Source management
- Episode navigation
- Mapping persistence
"""

from .title_normalization import normalize_anime_title

__all__ = ["normalize_anime_title"]
