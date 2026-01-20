"""Unit tests for DownloadedChaptersTracker.

Tests persistence layer for tracking downloaded manga chapters.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from services.manga_service import DownloadedChaptersTracker


@pytest.fixture
def temp_downloads_file():
    """Create temporary downloads file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def tracker_with_temp_file(temp_downloads_file):
    """Create tracker with temporary file."""
    with patch.object(DownloadedChaptersTracker, "_downloads_file", temp_downloads_file):
        yield DownloadedChaptersTracker


class TestDownloadedChaptersTrackerBasic:
    """Test basic tracker functionality."""

    def test_mark_downloaded(self, tracker_with_temp_file):
        """Mark a chapter as downloaded."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/to/file.pdf",
            file_size_mb=2.5,
        )

        assert tracker_with_temp_file.is_downloaded("manga123", "1")

    def test_is_downloaded_not_found(self, tracker_with_temp_file):
        """Check is_downloaded returns False for non-existent chapter."""
        assert not tracker_with_temp_file.is_downloaded("manga123", "1")

    def test_get_downloaded_chapters_empty(self, tracker_with_temp_file):
        """Get downloaded chapters when none exist."""
        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert result == {}

    def test_get_downloaded_chapters(self, tracker_with_temp_file):
        """Get downloaded chapters for a manga."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
        )
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="2",
            file_path="/path/2.pdf",
            file_size_mb=2.5,
        )

        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert len(result) == 2
        assert "1" in result
        assert "2" in result
        assert result["1"]["file_size_mb"] == 2.0
        assert result["2"]["file_size_mb"] == 2.5

    def test_get_download_path(self, tracker_with_temp_file):
        """Get file path for downloaded chapter."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/to/1.pdf",
            file_size_mb=2.0,
        )

        path = tracker_with_temp_file.get_download_path("manga123", "1")
        assert path == "/path/to/1.pdf"

    def test_get_download_path_not_found(self, tracker_with_temp_file):
        """Get file path for non-existent chapter."""
        path = tracker_with_temp_file.get_download_path("manga123", "1")
        assert path is None


class TestDownloadedChaptersTrackerMultipleManga:
    """Test tracker with multiple manga."""

    def test_multiple_manga_isolation(self, tracker_with_temp_file):
        """Downloads for different manga should be isolated."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga1",
            manga_title="Manga A",
            chapter_number="1",
            file_path="/path/a1.pdf",
            file_size_mb=2.0,
        )
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga2",
            manga_title="Manga B",
            chapter_number="1",
            file_path="/path/b1.pdf",
            file_size_mb=3.0,
        )

        assert tracker_with_temp_file.is_downloaded("manga1", "1")
        assert tracker_with_temp_file.is_downloaded("manga2", "1")
        assert not tracker_with_temp_file.is_downloaded("manga1", "2")
        assert not tracker_with_temp_file.is_downloaded("manga2", "2")

        result1 = tracker_with_temp_file.get_downloaded_chapters("manga1")
        result2 = tracker_with_temp_file.get_downloaded_chapters("manga2")

        assert len(result1) == 1
        assert len(result2) == 1
        assert result1["1"]["file_path"] == "/path/a1.pdf"
        assert result2["1"]["file_path"] == "/path/b1.pdf"


class TestDownloadedChaptersTrackerPersistence:
    """Test persistence to/from JSON file."""

    def test_persistence_save_load(self, tracker_with_temp_file):
        """Data should persist between instances."""
        # Create first tracker and add data
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
        )

        # Create new tracker instance (simulating new program run)
        # It should load the same data
        assert tracker_with_temp_file.is_downloaded("manga123", "1")

    def test_json_file_structure(self, tracker_with_temp_file, temp_downloads_file):
        """JSON file should have correct structure."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
            source="mangadex",
        )

        # Read and verify JSON structure
        with open(temp_downloads_file, "r") as f:
            data = json.load(f)

        assert "manga123" in data
        assert data["manga123"]["manga_title"] == "Test Manga"
        assert data["manga123"]["source"] == "mangadex"
        assert "1" in data["manga123"]["downloaded_chapters"]
        assert "file_path" in data["manga123"]["downloaded_chapters"]["1"]
        assert "file_size_mb" in data["manga123"]["downloaded_chapters"]["1"]
        assert "downloaded_at" in data["manga123"]["downloaded_chapters"]["1"]


class TestDownloadedChaptersTrackerCleanup:
    """Test cleanup functionality."""

    def test_cleanup_download(self, tracker_with_temp_file):
        """Cleanup should remove chapter from tracking."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
        )

        assert tracker_with_temp_file.is_downloaded("manga123", "1")

        tracker_with_temp_file.cleanup_download("manga123", "1")

        assert not tracker_with_temp_file.is_downloaded("manga123", "1")

    def test_cleanup_nonexistent_chapter(self, tracker_with_temp_file):
        """Cleanup of non-existent chapter should not error."""
        # Should not raise error
        tracker_with_temp_file.cleanup_download("manga123", "1")
        assert not tracker_with_temp_file.is_downloaded("manga123", "1")

    def test_cleanup_partial(self, tracker_with_temp_file):
        """Cleanup should only remove specified chapter."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
        )
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="2",
            file_path="/path/2.pdf",
            file_size_mb=2.5,
        )

        tracker_with_temp_file.cleanup_download("manga123", "1")

        assert not tracker_with_temp_file.is_downloaded("manga123", "1")
        assert tracker_with_temp_file.is_downloaded("manga123", "2")


class TestDownloadedChaptersTrackerMetadata:
    """Test metadata handling."""

    def test_file_size_tracking(self, tracker_with_temp_file):
        """File size should be correctly tracked."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=5.5,
        )

        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert result["1"]["file_size_mb"] == 5.5

    def test_timestamp_included(self, tracker_with_temp_file):
        """Downloaded chapter should include timestamp."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
        )

        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert "downloaded_at" in result["1"]
        assert result["1"]["downloaded_at"] != ""

    def test_source_tracking(self, tracker_with_temp_file):
        """Source should be tracked for each manga."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=2.0,
            source="mangadex",
        )

        data = tracker_with_temp_file._load_raw()
        assert data["manga123"]["source"] == "mangadex"

    def test_different_source_per_manga(self, tracker_with_temp_file):
        """Different sources can be tracked for different manga."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga1",
            manga_title="Manga A",
            chapter_number="1",
            file_path="/path/a1.pdf",
            file_size_mb=2.0,
            source="mangadex",
        )
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga2",
            manga_title="Manga B",
            chapter_number="1",
            file_path="/path/b1.pdf",
            file_size_mb=2.0,
            source="mugiwaras",
        )

        data = tracker_with_temp_file._load_raw()
        assert data["manga1"]["source"] == "mangadex"
        assert data["manga2"]["source"] == "mugiwaras"


class TestDownloadedChaptersTrackerEdgeCases:
    """Test edge cases and special scenarios."""

    def test_decimal_chapter_numbers(self, tracker_with_temp_file):
        """Handle decimal chapter numbers (e.g., 42.5)."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="42.5",
            file_path="/path/42.5.pdf",
            file_size_mb=2.0,
        )

        assert tracker_with_temp_file.is_downloaded("manga123", "42.5")

    def test_large_file_sizes(self, tracker_with_temp_file):
        """Handle large file sizes."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1.pdf",
            file_size_mb=150.5,
        )

        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert result["1"]["file_size_mb"] == 150.5

    def test_special_characters_in_path(self, tracker_with_temp_file):
        """Handle special characters in file paths."""
        special_path = "/path/with spaces/日本語/chapter-1.pdf"
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path=special_path,
            file_size_mb=2.0,
        )

        path = tracker_with_temp_file.get_download_path("manga123", "1")
        assert path == special_path

    def test_redownload_overwrites(self, tracker_with_temp_file):
        """Redownloading a chapter should update metadata."""
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1-old.pdf",
            file_size_mb=2.0,
        )

        # Re-download with new metadata
        tracker_with_temp_file.mark_downloaded(
            manga_id="manga123",
            manga_title="Test Manga",
            chapter_number="1",
            file_path="/path/1-new.pdf",
            file_size_mb=3.5,
        )

        result = tracker_with_temp_file.get_downloaded_chapters("manga123")
        assert result["1"]["file_path"] == "/path/1-new.pdf"
        assert result["1"]["file_size_mb"] == 3.5

    def test_many_chapters(self, tracker_with_temp_file):
        """Handle manga with many chapters."""
        for i in range(1, 201):  # 200 chapters
            tracker_with_temp_file.mark_downloaded(
                manga_id="manga_long",
                manga_title="Long Manga",
                chapter_number=str(i),
                file_path=f"/path/{i}.pdf",
                file_size_mb=2.0,
            )

        result = tracker_with_temp_file.get_downloaded_chapters("manga_long")
        assert len(result) == 200
        assert tracker_with_temp_file.is_downloaded("manga_long", "1")
        assert tracker_with_temp_file.is_downloaded("manga_long", "200")
        assert not tracker_with_temp_file.is_downloaded("manga_long", "201")


class TestDownloadedChaptersTrackerIntegration:
    """Integration tests simulating realistic workflows."""

    def test_typical_workflow(self, tracker_with_temp_file):
        """Simulate typical download workflow."""
        manga_id = "dandadan"
        manga_title = "Dandadan"

        # Download first batch of chapters
        for i in range(1, 6):
            tracker_with_temp_file.mark_downloaded(
                manga_id=manga_id,
                manga_title=manga_title,
                chapter_number=str(i),
                file_path=f"/manga/{i}.pdf",
                file_size_mb=2.0 + i * 0.1,
            )

        # Check downloads
        result = tracker_with_temp_file.get_downloaded_chapters(manga_id)
        assert len(result) == 5

        # Download more chapters
        for i in range(6, 11):
            tracker_with_temp_file.mark_downloaded(
                manga_id=manga_id,
                manga_title=manga_title,
                chapter_number=str(i),
                file_path=f"/manga/{i}.pdf",
                file_size_mb=2.0 + i * 0.1,
            )

        # Check updated downloads
        result = tracker_with_temp_file.get_downloaded_chapters(manga_id)
        assert len(result) == 10

        # Delete some old chapters
        for i in range(1, 4):
            tracker_with_temp_file.cleanup_download(manga_id, str(i))

        # Check remaining
        result = tracker_with_temp_file.get_downloaded_chapters(manga_id)
        assert len(result) == 7
        assert not tracker_with_temp_file.is_downloaded(manga_id, "1")
        assert tracker_with_temp_file.is_downloaded(manga_id, "4")
        assert tracker_with_temp_file.is_downloaded(manga_id, "10")
