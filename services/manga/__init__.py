"""Manga service modules.

Split from manga_tupi.py monolith for better maintainability.
"""

from services.manga.anilist_lists import handle_anilist_list
from services.manga.download import (
    download_chapter,
    download_chapters_batch,
    prompt_download_range,
)

__all__ = [
    "handle_anilist_list",
    "download_chapter",
    "download_chapters_batch",
    "prompt_download_range",
]
