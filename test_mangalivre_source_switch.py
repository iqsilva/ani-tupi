#!/usr/bin/env python3
"""Test script for MangaLivre source switching.

This script tests the complete flow:
1. Search for manga on MugiwarasOficial
2. Switch source to MangaLivre
3. Get chapters from MangaLivre
4. Download first chapter to PDF
"""

import sys
from pathlib import Path

from models.config import settings
from services.unified_manga_service import UnifiedMangaService
from services.manga.download import download_chapter
from services.manga_service import DownloadedChaptersTracker


def test_source_switching():
    """Test switching from MugiwarasOficial to MangaLivre source."""
    print("=" * 80)
    print("MangaLivre Source Switching Test")
    print("=" * 80)
    print()

    # Initialize service
    try:
        service = UnifiedMangaService(settings.manga)
        print("✓ Service initialized")
        print(f"  Available sources: {service.get_available_sources()}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize service: {e}")
        return False

    # Test 1: Search on Mugiwaras
    print("TEST 1: Search manga on MugiwarasOficial")
    print("-" * 80)
    try:
        service.set_source("mugiwaras")
        results = service.search_manga("jujutsu kaisen")

        if results:
            manga = results[0]
            print(f"✓ Found {len(results)} manga")
            print(f"  Selected: {manga.title}")
            print(f"  ID: {manga.id}")
            print()

            # Save for next test
            manga_id = manga.id
            manga_title = manga.title
        else:
            print("✗ No results found")
            return False
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

    # Test 2: Get chapters from Mugiwaras
    print("TEST 2: Get chapters from MugiwarasOficial")
    print("-" * 80)
    try:
        chapters_mugiwaras = service.get_chapters(manga_id, source="mugiwaras")

        if chapters_mugiwaras:
            print(f"✓ Found {len(chapters_mugiwaras)} chapters")
            print(f"  First chapter: {chapters_mugiwaras[0].display_name()}")
            if chapters_mugiwaras[0].url:
                print(f"  URL: {chapters_mugiwaras[0].url[:60]}...")
            else:
                print(f"  URL: <none>")
            print()
        else:
            print("✗ No chapters found")
            return False
    except Exception as e:
        print(f"✗ Get chapters failed: {e}")
        return False

    # Test 3: Switch to MangaLivre and get chapters with same manga_id
    print("TEST 3: Switch to MangaLivre and get chapters")
    print("-" * 80)
    try:
        service.set_source("mangalivre")
        print(f"✓ Switched to MangaLivre source")
        print()

        chapters_mangalivre = service.get_chapters(manga_id, source="mangalivre")

        if chapters_mangalivre:
            print(f"✓ Found {len(chapters_mangalivre)} chapters")
            print(f"  First chapter: {chapters_mangalivre[0].display_name()}")
            if chapters_mangalivre[0].url:
                print(f"  URL: {chapters_mangalivre[0].url[:60]}...")
            else:
                print(f"  URL: <none>")
            print()

            # Save for next test
            first_chapter = chapters_mangalivre[0]
        else:
            print("✗ No chapters found on MangaLivre")
            print("  Note: This might mean the manga is not on MangaLivre")
            return False
    except Exception as e:
        print(f"✗ Get chapters from MangaLivre failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Get chapter pages
    print("TEST 4: Get chapter pages from MangaLivre")
    print("-" * 80)
    try:
        pages = service.get_chapter_pages(
            first_chapter.id,
            chapter_url=first_chapter.url,
            source="mangalivre",
        )

        if pages:
            print(f"✓ Found {len(pages)} pages")
            print(f"  First page: {pages[0][:80]}...")
            print()
            return True  # Success!
        else:
            print("✗ No pages found")
            return False
    except Exception as e:
        print(f"✗ Get chapter pages failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    success = test_source_switching()
    print()
    print("=" * 80)
    if success:
        print("✅ ALL TESTS PASSED - Source switching works!")
        print()
        print("Summary:")
        print("  ✓ Service initialized")
        print("  ✓ Searched manga on MugiwarasOficial")
        print("  ✓ Switched to MangaLivre source")
        print("  ✓ Got chapters from MangaLivre with manga_id from Mugiwaras")
        print("  ✓ Retrieved page images")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED - Check errors above")
        sys.exit(1)
