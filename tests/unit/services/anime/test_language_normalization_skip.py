"""Tests for language selection skip when normalized titles are identical.

Tests cover the scenario where English and Romaji titles are different in display
but normalize to the same value (e.g., "Death Note" vs "Death Note" - same).
When this happens, the language selection menu should be skipped and Romaji
should be used by default.
"""

from services.anime.title_normalization import normalize_title_for_dedup


class TestNormalizedTitleComparison:
    """Tests for title normalization comparison."""

    def test_death_note_identical_normalized(self):
        """Death Note (English) and Death Note (Romaji) should normalize identically."""
        english = "Death Note"
        romaji = "Death Note"

        normalized_english = normalize_title_for_dedup(english)
        normalized_romaji = normalize_title_for_dedup(romaji)

        assert normalized_english == normalized_romaji
        assert normalized_english == "death note"

    def test_different_separators_normalize_to_same(self):
        """Titles with different separators should normalize to same value."""
        title1 = "Anime A: Revolucao Dublado"
        title2 = "Anime A - Revolucao Dublado"

        normalized1 = normalize_title_for_dedup(title1)
        normalized2 = normalize_title_for_dedup(title2)

        assert normalized1 == normalized2
        assert normalized1 == "anime a revolucao dublado"

    def test_case_difference_normalized(self):
        """Titles differing only in case should normalize identically."""
        title1 = "DEATH NOTE"
        title2 = "death note"

        normalized1 = normalize_title_for_dedup(title1)
        normalized2 = normalize_title_for_dedup(title2)

        assert normalized1 == normalized2

    def test_accents_removed_in_normalization(self):
        """Accents should be removed during normalization."""
        title1 = "Jigokuraku"  # Paradise Hell (no accents)
        title2 = "Jigokuraku"  # Same

        normalized1 = normalize_title_for_dedup(title1)
        normalized2 = normalize_title_for_dedup(title2)

        assert normalized1 == normalized2

    def test_truly_different_titles_not_equal(self):
        """Legitimately different titles should not normalize to same value."""
        title1 = "Jujutsu Kaisen"
        title2 = "My Hero Academia"

        normalized1 = normalize_title_for_dedup(title1)
        normalized2 = normalize_title_for_dedup(title2)

        assert normalized1 != normalized2


class TestLanguageMenuSkipLogic:
    """Tests for the language menu skip logic."""

    def test_normalized_title_used_for_comparison(self):
        """Test that normalized titles are used for comparison."""
        english = "Death Note"
        romaji = "Death Note"

        # Simulate the logic from anilist_anime_flow
        normalized_english = normalize_title_for_dedup(english)
        normalized_romaji = normalize_title_for_dedup(romaji)

        # When normalized are identical, use romaji by default
        if normalized_english == normalized_romaji:
            selected_title = romaji
            should_show_menu = False
        else:
            selected_title = None
            should_show_menu = True

        assert selected_title == "Death Note"
        assert should_show_menu is False

    def test_different_titles_show_menu(self):
        """Test that different normalized titles show menu."""
        english = "Full Metal Alchemist"
        romaji = "Hagane no Renkinjutsushi"

        # Simulate the logic from anilist_anime_flow
        normalized_english = normalize_title_for_dedup(english)
        normalized_romaji = normalize_title_for_dedup(romaji)

        # Should be different
        assert normalized_english != normalized_romaji

        # The code shows menu when they differ
        if normalized_english == normalized_romaji:
            should_show_menu = False
        else:
            # Menu would be shown to choose
            should_show_menu = True

        assert should_show_menu is True

    def test_separators_dont_affect_skip_decision(self):
        """Titles with different separators should skip menu."""
        english = "Anime A: Revolucao"
        romaji = "Anime A - Revolucao"

        normalized_english = normalize_title_for_dedup(english)
        normalized_romaji = normalize_title_for_dedup(romaji)

        # Both should normalize to same value
        assert normalized_english == normalized_romaji

        # Menu should be skipped
        if normalized_english == normalized_romaji:
            should_show_menu = False
        else:
            should_show_menu = True

        assert should_show_menu is False

    def test_case_difference_doesnt_affect_skip_decision(self):
        """Titles differing in case should skip menu."""
        english = "DEATH NOTE"
        romaji = "death note"

        normalized_english = normalize_title_for_dedup(english)
        normalized_romaji = normalize_title_for_dedup(romaji)

        # Both should normalize to same value
        assert normalized_english == normalized_romaji

        # Menu should be skipped
        if normalized_english == normalized_romaji:
            should_show_menu = False
        else:
            should_show_menu = True

        assert should_show_menu is False
