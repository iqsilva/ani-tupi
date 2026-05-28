"""Title formatting utilities for AniList data.

Handles conversion of AniList title objects to display and search strings.
"""

import re

from models.models import AniListTitle


def _normalize_title_for_compare(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def format_title(title_obj: AniListTitle | dict) -> str:
    """Format title object to single string.

    Shows romaji + english when both available.

    Args:
        title_obj: AniListTitle model or dict with romaji/english/native fields

    Returns:
        Formatted title string
    """
    # Handle both Pydantic model and dict for backward compatibility
    if isinstance(title_obj, dict):
        romaji = title_obj.get("romaji")
        english = title_obj.get("english")
        native = title_obj.get("native")
    else:
        romaji = title_obj.romaji
        english = title_obj.english
        native = title_obj.native

    # If both romaji and english exist and are different after normalization
    if (
        romaji
        and english
        and _normalize_title_for_compare(romaji) != _normalize_title_for_compare(english)
    ):
        return f"{romaji} / {english}"
    # If only romaji
    if romaji:
        return romaji
    # If only english
    if english:
        return english
    # Fallback to native
    return native or "Unknown"


def get_search_title(title_obj: AniListTitle | dict) -> str:
    """Extract title for scraper search (English only).

    Returns English title if available, otherwise romaji or native.
    Used for scraper queries to ensure consistent results.

    Args:
        title_obj: AniListTitle model or dict with romaji/english/native fields

    Returns:
        Search-optimized title string (English preferred)
    """
    # Handle both Pydantic model and dict for backward compatibility
    if isinstance(title_obj, dict):
        english = title_obj.get("english")
        romaji = title_obj.get("romaji")
        native = title_obj.get("native")
    else:
        english = title_obj.english
        romaji = title_obj.romaji
        native = title_obj.native

    # Prefer English for scraper searches (most reliable for searches)
    if english:
        return english
    # If only romaji
    if romaji:
        return romaji
    # Fallback to native
    return native or "Unknown"
