"""Anime title normalization and utility functions.

Consolidates all title normalization logic in a single module for consistency.
Used for improving search accuracy and handling title variations.
"""

import re


def normalize_title_for_search(title: str) -> str:
    """Normalize anime title for search operations.

    Removes common Portuguese suffixes and normalizes spacing.
    Used internally by search algorithms to improve matching.

    Args:
        title: Original anime title (may contain suffixes like Dublado, Legendado)

    Returns:
        Normalized title for search

    Examples:
        "Tougen Anki (Dublado)" -> "tougen anki"
        "Dandadan 2ª Temporada Legendado" -> "dandadan 2ª temporada"
    """
    # Remove common Portuguese suffixes in parentheses
    title = re.sub(
        r"\s*\((Dublado|Legendado|Completo|Dual Audio|PT-BR)\)\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    # Remove standalone suffixes at the end
    title = re.sub(
        r"\s+(Dublado|Legendado|Completo|Dual Audio|PT-BR)\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    # Normalize whitespace and convert to lowercase for comparison
    title = re.sub(r"\s+", " ", title.strip().lower())
    return title


def clean_title_for_display(title: str) -> str:
    """Clean title for display purposes (preserves case, removes only extra whitespace).

    Args:
        title: Original anime title

    Returns:
        Cleaned title with normalized whitespace
    """
    # Remove common Portuguese suffixes in parentheses
    title = re.sub(
        r"\s*\((Dublado|Legendado|Completo|Dual Audio|PT-BR)\)\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    # Remove standalone suffixes at the end
    title = re.sub(
        r"\s+(Dublado|Legendado|Completo|Dual Audio|PT-BR)\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    # Normalize whitespace (keep case)
    title = re.sub(r"\s+", " ", title.strip())
    return title
