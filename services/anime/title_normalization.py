"""Title normalization utilities for anime search.

Handles title cleaning, variation generation, and bilingual title processing
for improved search results across different anime sources.
"""

import re
import unicodedata


def normalize_title_for_dedup(title: str) -> str:
    """Normalize title for deduplication across multiple sources.

    This is an aggressive normalization designed for EXACT MATCHING and MERGING
    of results from multiple scrapers. It removes all separators, language markers,
    and part/season indicators to create a canonical form suitable for deduplication.

    Why separate from normalize_anime_title()?
    - normalize_anime_title(): For search queries (preserves flexibility for partial matches)
    - normalize_title_for_dedup(): For exact merging (removes everything except core title)

    Handles:
    - Unicode normalization (accents: á → a, ç → c)
    - Separator normalization (: - | / \\ → space)
    - Language marker removal (Dublado, Legendado, Sub, Dub, etc.)
    - Season/part number extraction and preservation
    - Whitespace cleanup
    - Case normalization

    Examples:
        "Anime A: Revolucao Dublado" → "anime a revolucao"
        "Anime A - Revolucao Dublado" → "anime a revolucao"
        "Jujutsu Kaisen Season 2 Dublado" → "jujutsu kaisen 2"
        "My Hero Academia Part 6 Legendado" → "my hero academia 6"
        "Hell's Paradise: Jigokuraku" → "hell's paradise jigokuraku"

    Args:
        title: Raw title from scraper (may include separators, language markers, etc.)

    Returns:
        Normalized lowercase form suitable for exact matching and deduplication.
        Returns empty string if title becomes empty after normalization.
    """
    if not title or not title.strip():
        return ""

    # Step 1: Normalize Unicode
    # Decompose accents: "Café" → "Cafe"
    normalized = unicodedata.normalize("NFKD", title)
    # Remove combining marks (accents)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Step 2: Normalize separators to spaces
    # Replace common separators with space
    for sep in [(":", " "), ("-", " "), ("–", " "), ("—", " "), ("|", " "), ("/", " "), ("\\", " ")]:
        normalized = normalized.replace(sep[0], sep[1])

    # Step 3: Extract season number BEFORE removing patterns
    # This preserves "2" from "2nd Season" or "Season 2" or "Temporada 2"
    extracted_season = None
    for pattern in [
        r"(?:season|temporada|s)\s*(\d+)",
        r"(\d+)(?:st|nd|rd|th)?\s+season",
    ]:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            extracted_season = match.group(1)
            break

    # Step 4: Remove language/audio type markers
    # These are format markers, not part of the anime identity
    for pattern in [
        r"\bdublado\b",
        r"\blegendado\b",
        r"\blegendadas\b",
        r"\blongas\b",
        r"\bsub(?:title)?s?\b",
        r"\bdub(?:bed)?\b",
    ]:
        normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)

    # Step 5: Remove season/part/cour/arc patterns
    # These are metadata markers, not part of core title
    for pattern in [
        r"\s+season\s+\d+",
        r"\s+\d+(?:st|nd|rd|th)?\s+season",
        r"\s+temporada\s+\d+",
        r"\s+s\d+",
        r"\s+part\s+\d+(?:st|nd|rd|th)?",
        r"\s+cour\s+\d+",
        r"\s+arc\s+[^:]+"
    ]:
        normalized = re.sub(pattern, " ", normalized, flags=re.IGNORECASE)

    # Step 6: Clean whitespace
    # Collapse multiple spaces from previous substitutions
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Step 7: Keep only alphanumerics, spaces, and apostrophes
    # (Apostrophes preserved for English titles like "Hell's Paradise")
    normalized = re.sub(r"[^A-Za-z0-9\s']", "", normalized)

    # Step 8: Clean whitespace again
    # Previous step may have created spaces where special chars were removed
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Step 9: Append extracted season number if present
    # Preserves season info while keeping core title unified
    if extracted_season:
        normalized = f"{normalized} {extracted_season}".strip()

    # Step 10: Convert to lowercase
    # Final normalized form for exact matching
    normalized = normalized.lower()

    # Return normalized form, or original title (lowercased) if everything was removed
    return normalized if normalized else title.lower()


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
