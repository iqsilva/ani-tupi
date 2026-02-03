"""Title normalization utilities for anime search.

Handles title cleaning, variation generation, and bilingual title processing
for improved search results across different anime sources.
"""

import re
import unicodedata


def normalize_anime_title(title: str, is_english: bool = False):
    """Generate sensible title variations for searching.

    For AniList titles with format "Romaji / English", extracts just the english part.
    Example: "Kimetsu no Yaiba: Hashira Geiko-hen / Demon Slayer: Hashira Training Arc"
             → ["demon slayer hashira training arc", "demon slayer hashira training", "demon slayer hashira", "demon slayer"]

    Args:
        title: Title to normalize
        is_english: If True, preserves apostrophes (for English titles like "Hell's Paradise")

    Returns variations in lowercase, from most specific to most generic.
    """
    # 1. Handle AniList bilingual format "Romaji / English"
    # Take only the english part (after the " / ")
    if " / " in title:
        parts = title.split(" / ")
        # Use english if available (after " / "), otherwise keep original
        title = parts[1] if len(parts) > 1 else parts[0]
        is_english = True  # Auto-detect: if we split, second part is English

    # 2. Extract season numbers BEFORE removing season patterns
    # This preserves "2" from "2nd Season" or "Season 2"
    extracted_season = None
    season_match = re.search(
        r"(?:Season\s+|Temporada\s+)(\d+)|(\d+)(?:st|nd|rd|th)?\s+Season", title, re.IGNORECASE
    )
    if season_match:
        extracted_season = season_match.group(1) or season_match.group(2)

    # 3. Remove season/part/episode suffixes
    season_patterns = [
        r"\s+Season\s+\d+",
        r"\s+\d+(?:st|nd|rd|th)\s+Season",
        r"\s+Temporada\s+\d+",
        r"\s+S\d+",
        r"\s+Part\s+\d+",
        r"\s+Cour\s+\d+",
        r"\s+Arc\s+[^:]+",
        r"\s+Final\s+Season",
        r"\s+2nd\s+Season",
        r"[:−-]\s*Season\s+\d+",
        r"\s+Dublado.*$",
    ]

    cleaned = title
    for pattern in season_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # If we extracted a season number, append it to preserve it
    if extracted_season:
        cleaned = f"{cleaned} {extracted_season}"

    # 3. Keep only letters, numbers, spaces (and apostrophes if English)
    if is_english:
        # Preserve apostrophes for English titles (e.g., "Hell's Paradise")
        cleaned = re.sub(r"[^A-Za-z0-9\s']", " ", cleaned)
    else:
        # Remove all special characters including apostrophes for Romaji
        cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", cleaned)
    # Remove multiple spaces and trim
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return [title.strip().lower()]  # fallback

    # 4. Convert to lowercase
    cleaned = cleaned.lower()

    # 5. Get words
    words = cleaned.split()

    # 6. Generate variations intelligently
    # For AniList with progressive search: only use full query
    # Let progressive search handle the word reduction automatically
    variations = []

    if len(words) > 0:
        # Always include full query first
        variations.append(" ".join(words))

    # Only generate shorter variations if disabled (for compatibility)
    # With progressive search enabled, let the search function handle word count
    use_progressive_search = len(words) > 3  # Same logic as repository

    if not use_progressive_search:
        # Then progressively shorter versions (fallback for short queries)
        if len(words) > 3:
            # Medium: try 3 words
            variations.append(" ".join(words[:3]))
        if len(words) > 2:
            # Shorter: try 2 words
            variations.append(" ".join(words[:2]))
        if len(words) > 1:
            # Minimal: try 1 word
            variations.append(" ".join(words[:1]))

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            result.append(v)

    return result


def normalize_search_cache_key(query: str, language: str = "pt-br") -> str:
    """Normalize query into a consistent cache key.

    Ensures that different variations of the same query produce identical cache keys.
    This enables:
    - "jigokuraku 2" == "Jigokuraku 2nd Season" == "JIGOKURAKU 2"
    - Multi-language support with separate cache entries
    - Consistent cache hits across different search attempts

    Args:
        query: Raw search query from user
        language: Language code (default: "pt-br")

    Returns:
        Normalized cache key in format: "search:{normalized}:{language}"

    Examples:
        >>> normalize_search_cache_key("jigokuraku 2")
        "search:jigokuraku-pt-br"
        >>> normalize_search_cache_key("Jigokuraku 2nd Season", "pt-br")
        "search:jigokuraku-pt-br"
        >>> normalize_search_cache_key("DANDADAN", "en-us")
        "search:dandadan-en-us"
    """
    if not query or not query.strip():
        return f"search:empty-{language}"

    # Step 1: Normalize unicode (decompose accents, etc.)
    normalized = unicodedata.normalize("NFKD", query)
    # Remove combining marks (accents)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Step 2: Convert to lowercase
    normalized = normalized.lower()

    # Step 3: Extract season numbers BEFORE removing season patterns
    # This preserves "2" from "2nd Season" or "Season 2"
    extracted_season = None
    season_match = re.search(
        r"(?:season\s+|temporada\s+|s)(\d+)|(\d+)(?:st|nd|rd|th)?\s+season",
        normalized,
        re.IGNORECASE,
    )
    if season_match:
        extracted_season = season_match.group(1) or season_match.group(2)

    # Step 4: Remove season/part/episode/language suffixes
    season_patterns = [
        r"\s+season\s+\d+",
        r"\s+\d+(?:st|nd|rd|th)?\s+season",
        r"\s+temporada\s+\d+",
        r"\s+s\d+",
        r"\s+part\s+\d+(?:st|nd|rd|th)?",
        r"\s+cour\s+\d+",
        r"\s+arc\s+[^:]+",
        r"\s+final\s+season",
        r"\s+dublado.*$",
        r"\s+legenda.*$",
        r"\s+sub.*$",
    ]

    for pattern in season_patterns:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

    # Step 5: If we extracted a season number, append it to preserve it
    if extracted_season:
        normalized = f"{normalized} {extracted_season}"

    # Step 6: Keep only letters, numbers, spaces, and apostrophes
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)

    # Step 7: Remove multiple spaces and strip
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Step 8: Replace remaining spaces with dashes
    normalized = normalized.replace(" ", "-")

    # Fallback: if everything was removed, use original query hash
    if not normalized:
        normalized = "empty"

    return f"search:{normalized}:{language}"
