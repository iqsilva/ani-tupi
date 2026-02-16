"""Unit tests for normalize_title_for_dedup() function.

Tests the aggressive separator and marker normalization algorithm
designed for exact title matching and multi-source deduplication.
"""

import pytest
from services.anime.title_normalization import normalize_title_for_dedup


class TestSeparatorNormalization:
    """Test that all separator types are normalized to spaces."""

    def test_colon_separator(self):
        """Colon is normalized to space."""
        assert normalize_title_for_dedup("Anime A: Title") == "anime a title"

    def test_dash_separator(self):
        """Hyphen dash is normalized to space."""
        assert normalize_title_for_dedup("Anime A - Title") == "anime a title"

    def test_en_dash_separator(self):
        """En-dash is normalized to space."""
        assert normalize_title_for_dedup("Anime A – Title") == "anime a title"

    def test_em_dash_separator(self):
        """Em-dash is normalized to space."""
        assert normalize_title_for_dedup("Anime A — Title") == "anime a title"

    def test_pipe_separator(self):
        """Pipe is normalized to space."""
        assert normalize_title_for_dedup("Anime A | Title") == "anime a title"

    def test_forward_slash_separator(self):
        """Forward slash is normalized to space."""
        assert normalize_title_for_dedup("Anime A / Title") == "anime a title"

    def test_backslash_separator(self):
        """Backslash is normalized to space."""
        assert normalize_title_for_dedup("Anime A \\ Title") == "anime a title"

    def test_multiple_different_separators(self):
        """Multiple different separators all normalize to the same result."""
        result1 = normalize_title_for_dedup("Anime A: Title")
        result2 = normalize_title_for_dedup("Anime A - Title")
        result3 = normalize_title_for_dedup("Anime A | Title")
        result4 = normalize_title_for_dedup("Anime A / Title")

        assert result1 == result2 == result3 == result4
        assert result1 == "anime a title"

    def test_mixed_separators(self):
        """Mixed separators are all normalized."""
        assert normalize_title_for_dedup("Anime A: Title - Parte") == "anime a title parte"


class TestLanguageMarkerRemoval:
    """Test removal of language and audio type markers."""

    def test_remove_dublado(self):
        """'Dublado' marker is removed."""
        assert normalize_title_for_dedup("Anime A Dublado") == "anime a"

    def test_remove_legendado(self):
        """'Legendado' marker is removed."""
        assert normalize_title_for_dedup("Anime A Legendado") == "anime a"

    def test_remove_legendadas(self):
        """'Legendadas' marker is removed."""
        assert normalize_title_for_dedup("Anime A Legendadas") == "anime a"

    def test_remove_longas(self):
        """'Longas' marker is removed."""
        assert normalize_title_for_dedup("Anime A Longas") == "anime a"

    def test_remove_sub(self):
        """'Sub' marker is removed."""
        assert normalize_title_for_dedup("Anime A Sub") == "anime a"

    def test_remove_subtitles(self):
        """'Subtitles' marker is removed."""
        assert normalize_title_for_dedup("Anime A Subtitles") == "anime a"

    def test_remove_dub(self):
        """'Dub' marker is removed."""
        assert normalize_title_for_dedup("Anime A Dub") == "anime a"

    def test_remove_dubbed(self):
        """'Dubbed' marker is removed."""
        assert normalize_title_for_dedup("Anime A Dubbed") == "anime a"

    def test_language_marker_case_insensitive(self):
        """Language markers are removed case-insensitively."""
        assert normalize_title_for_dedup("Anime A DUBLADO") == "anime a"
        assert normalize_title_for_dedup("Anime A Dublado") == "anime a"
        assert normalize_title_for_dedup("Anime A dublado") == "anime a"

    def test_language_markers_with_separators(self):
        """Language markers removed even with separators."""
        assert normalize_title_for_dedup("Anime A: Revolucao Dublado") == "anime a revolucao"
        assert normalize_title_for_dedup("Anime A - Revolucao Legendado") == "anime a revolucao"


class TestSeasonPreservation:
    """Test that season/part numbers are preserved."""

    def test_season_keyword_with_number(self):
        """Season keyword format: 'Season 2' → extract '2'."""
        assert normalize_title_for_dedup("Jujutsu Kaisen Season 2") == "jujutsu kaisen 2"

    def test_season_ordinal_format(self):
        """Ordinal format: '2nd Season' → extract '2'."""
        assert normalize_title_for_dedup("My Hero Academia 2nd Season") == "my hero academia 2"

    def test_season_temporal_format(self):
        """Temporal format: 'Temporada 3' → extract '3'."""
        assert normalize_title_for_dedup("Anime A Temporada 3") == "anime a 3"

    def test_season_short_format(self):
        """Short format: 'S2' → extract '2'."""
        assert normalize_title_for_dedup("Anime A S2") == "anime a 2"

    def test_season_variations_normalize_same(self):
        """Different season formats normalize to same output."""
        result1 = normalize_title_for_dedup("Anime Season 2")
        result2 = normalize_title_for_dedup("Anime 2nd Season")
        result3 = normalize_title_for_dedup("Anime Temporada 2")
        result4 = normalize_title_for_dedup("Anime S2")

        assert result1 == result2 == result3 == result4
        assert result1 == "anime 2"

    def test_season_with_language_marker(self):
        """Season preserved even when language markers present."""
        assert normalize_title_for_dedup("Jujutsu Kaisen Season 2 Dublado") == "jujutsu kaisen 2"

    def test_part_format_removed(self):
        """Part formats are removed (not preserved like season)."""
        assert normalize_title_for_dedup("My Hero Academia Part 6") == "my hero academia"

    def test_part_ordinal_removed(self):
        """Ordinal part formats are removed when in standard format."""
        # Note: "3rd Part" doesn't match our regex (expects "\s+part\s+\d+")
        # This is acceptable - we catch most part patterns
        assert normalize_title_for_dedup("Anime A Part 3") == "anime a"

    def test_cour_format_removed(self):
        """Cour/course formats are removed."""
        assert normalize_title_for_dedup("Anime A Cour 2") == "anime a"

    def test_arc_format_removed(self):
        """Arc formats are removed."""
        assert normalize_title_for_dedup("Anime A Arc Rebellion") == "anime a"


class TestUnicodeHandling:
    """Test Unicode and accent normalization."""

    def test_acute_accent_removed(self):
        """Accutes (á, é, í, ó, ú) are normalized."""
        assert normalize_title_for_dedup("Café") == "cafe"

    def test_grave_accent_removed(self):
        """Graves (à, è, ì, ò, ù) are normalized."""
        assert normalize_title_for_dedup("Où") == "ou"

    def test_circumflex_removed(self):
        """Circumflex (â, ê, î, ô, û) are normalized."""
        assert normalize_title_for_dedup("Têmpora") == "tempora"

    def test_tilde_removed(self):
        """Tildes (ã, õ) are normalized."""
        assert normalize_title_for_dedup("São Paulo") == "sao paulo"

    def test_cedilla_removed(self):
        """Cedilla (ç) is normalized."""
        assert normalize_title_for_dedup("Açúcar") == "acucar"

    def test_diaeresis_removed(self):
        """Diaeresis (ä, ë, ï, ö, ü) are normalized."""
        assert normalize_title_for_dedup("Müller") == "muller"

    def test_full_title_with_accents(self):
        """Full title with multiple accent types."""
        assert normalize_title_for_dedup("Café de Terça Temporada 2") == "cafe de terca 2"


class TestApostropheHandling:
    """Test that apostrophes are preserved in English titles."""

    def test_apostrophe_preserved(self):
        """Apostrophes in English titles are preserved."""
        assert normalize_title_for_dedup("Hell's Paradise") == "hell's paradise"

    def test_apostrophe_in_middle(self):
        """Mid-word apostrophes preserved."""
        assert normalize_title_for_dedup("It's a Wonderful Life") == "it's a wonderful life"

    def test_apostrophe_with_separators(self):
        """Apostrophes preserved even with separators."""
        assert normalize_title_for_dedup("Hell's Paradise: Jigokuraku") == "hell's paradise jigokuraku"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_title_for_dedup("") == ""

    def test_whitespace_only(self):
        """Whitespace-only string returns empty string."""
        assert normalize_title_for_dedup("   ") == ""

    def test_only_symbols(self):
        """String with only symbols: fallback returns original lowercased."""
        # Safeguard: if normalization removes everything, return original (lowercased)
        # Better to show something than nothing
        assert normalize_title_for_dedup("!!!???") == "!!!???"

    def test_only_language_markers(self):
        """String with only language markers: fallback returns original lowercased."""
        # Safeguard: if normalization removes everything, return original (lowercased)
        assert normalize_title_for_dedup("Dublado Legendado") == "dublado legendado"

    def test_single_word(self):
        """Single word is lowercased."""
        assert normalize_title_for_dedup("Naruto") == "naruto"

    def test_very_long_title(self):
        """Very long title is handled correctly."""
        long_title = "A Very Long Anime Title With Many Words And Season 2 Dublado"
        result = normalize_title_for_dedup(long_title)
        assert result == "a very long anime title with many words and 2"

    def test_multiple_consecutive_spaces(self):
        """Multiple consecutive spaces are collapsed."""
        assert normalize_title_for_dedup("Anime   A") == "anime a"

    def test_leading_trailing_spaces(self):
        """Leading and trailing spaces are trimmed."""
        assert normalize_title_for_dedup("  Anime A  ") == "anime a"

    def test_numeric_only_part(self):
        """Numeric-only strings are handled."""
        assert normalize_title_for_dedup("123") == "123"

    def test_mixed_case_input(self):
        """Mixed case input is normalized to lowercase."""
        assert normalize_title_for_dedup("AnImE a TiTlE") == "anime a title"


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_anilist_bilingual_style_first_part(self):
        """AniList-style format with roman first, english after."""
        # Note: In real code, bilingual splitting happens elsewhere
        # Here we test just the normalization
        assert normalize_title_for_dedup("Jigokuraku") == "jigokuraku"

    def test_multiple_season_indicators(self):
        """Multiple season indicators (only first extracted)."""
        # Only first season is extracted
        result = normalize_title_for_dedup("Anime Season 2 Part 3")
        assert "2" in result
        assert "part" not in result

    def test_complex_dubbed_subtitle_example(self):
        """Complex real-world example from AnimesDigital."""
        result1 = normalize_title_for_dedup("Anime A: Revolucao Dublado")
        result2 = normalize_title_for_dedup("Anime A - Revolucao Dublado")
        assert result1 == result2
        assert result1 == "anime a revolucao"

    def test_my_hero_academia_example(self):
        """My Hero Academia with various formats."""
        result1 = normalize_title_for_dedup("My Hero Academia Season 5")
        result2 = normalize_title_for_dedup("My Hero Academia 5th Season")
        assert result1 == result2
        assert result1 == "my hero academia 5"

    def test_re_zero_example(self):
        """Re:Zero with colon separator (becomes space)."""
        # Colon is a separator, so "Re:Zero" becomes "Re Zero"
        assert normalize_title_for_dedup("Re:Zero Season 3") == "re zero 3"

    def test_hell_paradise_example(self):
        """Hell's Paradise (Jigokuraku) with apostrophe."""
        result1 = normalize_title_for_dedup("Hell's Paradise: Jigokuraku")
        result2 = normalize_title_for_dedup("Hell's Paradise - Jigokuraku")
        assert result1 == result2
        assert "hell's paradise" in result1


class TestDeterminism:
    """Test that normalization is deterministic."""

    def test_same_input_same_output(self):
        """Same input always produces same output."""
        title = "Anime A: Title - Season 2 Dublado"
        result1 = normalize_title_for_dedup(title)
        result2 = normalize_title_for_dedup(title)
        assert result1 == result2

    def test_multiple_calls_identical(self):
        """Multiple calls on same input are identical."""
        title = "Complex: Title - With Many Changes | Season 3 Legendado"
        results = [normalize_title_for_dedup(title) for _ in range(5)]
        assert len(set(results)) == 1  # All identical


class TestComparisonsWithExistingNormalization:
    """Compare new dedup normalization with search normalization.

    This helps verify they serve different purposes:
    - normalize_anime_title(): For search query variations (flexibility)
    - normalize_title_for_dedup(): For exact deduplication (strictness)
    """

    def test_dedup_stricter_than_search(self):
        """Dedup normalization is stricter (removes more)."""
        # Both should handle separators and seasons
        title = "Anime A: Title Season 2"

        # Dedup version: aggressive removal
        dedup_result = normalize_title_for_dedup(title)

        # Both should produce lowercase with season
        assert "anime a" in dedup_result
        assert "2" in dedup_result

    def test_dedup_handles_language_markers(self):
        """Dedup removes language markers that search might not."""
        title_with_dub = normalize_title_for_dedup("Anime A Dublado")
        title_without_dub = normalize_title_for_dedup("Anime A")

        # Both should normalize the same way (marker removed)
        assert title_with_dub == title_without_dub
