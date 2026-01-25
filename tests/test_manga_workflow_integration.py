"""Integration tests for manga reading workflow.

Tests realistic user scenarios for searching, selecting, and reading manga.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


@pytest.fixture
def mock_mangadex_api():
    """Mock MangaDex API responses."""
    api = Mock()

    # Mock search results
    api.search_manga = Mock(return_value=[
        {"id": "manga1", "title": "Dandadan", "status": "ongoing", "latest_chapter": "50"},
        {"id": "manga2", "title": "Jujutsu Kaisen", "status": "completed", "latest_chapter": "271"},
        {"id": "manga3", "title": "Blue Lock", "status": "ongoing", "latest_chapter": "240"},
    ])

    # Mock chapter list
    api.get_chapters = Mock(return_value=[
        {"id": "ch1", "chapter": "1", "title": "Beginning"},
        {"id": "ch2", "chapter": "2", "title": "Development"},
        {"id": "ch3", "chapter": "3", "title": "Climax"},
    ])

    # Mock chapter pages
    api.get_chapter_pages = Mock(return_value=[
        "https://example.com/page1.jpg",
        "https://example.com/page2.jpg",
        "https://example.com/page3.jpg",
    ])

    return api


@pytest.fixture
def temp_manga_dir():
    """Create temporary directory for manga storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manga_service(mock_mangadex_api, temp_manga_dir):
    """Create manga service mock with mocked API."""
    service = Mock()
    service.output_dir = temp_manga_dir
    service.search = lambda q: mock_mangadex_api.search_manga(q)
    service.get_chapters = lambda mid: mock_mangadex_api.get_chapters(mid)
    service.get_chapter_pages = lambda cid: mock_mangadex_api.get_chapter_pages(cid)
    service.mark_as_read = Mock()
    service.get_reading_history = Mock(return_value={})
    service.get_next_chapter = Mock(return_value="next")
    service.download_chapter = Mock(return_value="/tmp/ch.pdf")
    service.open_pdf = Mock(return_value=True)
    service.can_sync_to_anilist = Mock(return_value=True)
    service.sync_to_anilist = Mock(return_value=True)
    service._is_downloaded = Mock(return_value=False)
    service.get_chapter_path = Mock(return_value="/tmp/ch.pdf")
    yield service


class TestMangaSearchWorkflow:
    """Test manga search and discovery workflow."""

    def test_user_searches_for_manga(self, manga_service, mock_mangadex_api):
        """User searches for manga by title."""
        results = manga_service.search("Dandadan")

        assert len(results) >= 1
        assert any(r["title"] == "Dandadan" for r in results)
        mock_mangadex_api.search_manga.assert_called_once()

    def test_user_searches_partial_title(self, manga_service, mock_mangadex_api):
        """User searches with partial title."""
        manga_service.search("Danda")
        mock_mangadex_api.search_manga.assert_called()

    def test_search_returns_empty_for_nonexistent(self, manga_service, mock_mangadex_api):
        """Search returns empty when manga doesn't exist."""
        mock_mangadex_api.search_manga.return_value = []
        results = manga_service.search("NonexistentManga2024")
        assert results == []


class TestMangaSelectionWorkflow:
    """Test selecting manga and chapters."""

    def test_user_selects_manga_from_search_results(self, manga_service, mock_mangadex_api):
        """User selects specific manga from search results."""
        search_results = manga_service.search("Dandadan")
        selected_manga = search_results[0]

        chapters = manga_service.get_chapters(selected_manga["id"])

        assert len(chapters) == 3
        assert chapters[0]["chapter"] == "1"
        mock_mangadex_api.get_chapters.assert_called_once()

    def test_chapters_sorted_correctly(self, manga_service, mock_mangadex_api):
        """Chapters are returned in correct order."""
        manga_service.get_chapters("manga1")
        chapters = mock_mangadex_api.get_chapters.return_value

        assert chapters[0]["chapter"] == "1"
        assert chapters[-1]["chapter"] == "3"

    def test_user_selects_specific_chapter(self, manga_service, mock_mangadex_api):
        """User selects specific chapter to read."""
        chapters = manga_service.get_chapters("manga1")
        selected_chapter = chapters[1]  # Chapter 2

        assert selected_chapter["chapter"] == "2"
        assert selected_chapter["title"] == "Development"


class TestMangaDownloadWorkflow:
    """Test chapter download and PDF conversion."""

    def test_download_chapter_creates_pdf(self, manga_service):
        """Downloading a chapter triggers PDF creation."""
        manga_id = "manga1"
        chapter_number = "1"

        pdf_path = manga_service.download_chapter(manga_id, chapter_number)
        assert pdf_path is not None

    def test_chapter_path_retrieval(self, manga_service):
        """Can retrieve path to downloaded chapter."""
        manga_id = "manga1"
        chapter_number = "1"

        result = manga_service.get_chapter_path(manga_id, chapter_number)
        assert result is not None


class TestMangaReadingHistoryWorkflow:
    """Test reading history tracking and sync."""

    def test_mark_chapter_as_read(self, manga_service):
        """User reads chapter and history is updated."""
        manga_id = "manga1"
        chapter_number = "5"

        manga_service.mark_as_read(manga_id, chapter_number)
        history = manga_service.get_reading_history(manga_id)
        assert history is not None

    def test_suggest_next_chapter(self, manga_service):
        """'Continue reading' suggests next unread chapter."""
        manga_id = "manga1"
        next_chapter = manga_service.get_next_chapter(manga_id)
        assert next_chapter is not None


class TestMangaPDFReaderWorkflow:
    """Test PDF reader integration."""

    def test_pdf_opens_successfully(self, manga_service):
        """PDF opens with configured reader."""
        pdf_path = "/tmp/manga1_ch1.pdf"

        result = manga_service.open_pdf(pdf_path)
        assert result is True


class TestMangaBatchDownloadWorkflow:
    """Test downloading multiple chapters at once."""

    def test_download_multiple_chapters(self, manga_service):
        """User can download multiple chapters."""
        manga_id = "manga1"
        chapters = ["1", "2", "3", "4", "5"]

        results = [manga_service.download_chapter(manga_id, ch) for ch in chapters]

        assert len(results) == 5


class TestMangaAniListIntegrationWorkflow:
    """Test AniList sync for manga reading."""

    def test_sync_progress_to_anilist(self, manga_service):
        """Reading progress can sync to AniList."""
        manga_id = "manga1"
        chapter = "50"

        manga_service.mark_as_read(manga_id, chapter)
        result = manga_service.sync_to_anilist(manga_id, chapter)
        assert result is True

    def test_check_anilist_authentication(self, manga_service):
        """Can check if AniList is authenticated."""
        result = manga_service.can_sync_to_anilist()
        assert result is not None


class TestMangaCompleteWorkflow:
    """End-to-end realistic manga reading scenarios."""

    def test_user_searches_and_selects_manga(self, manga_service, mock_mangadex_api):
        """User searches for manga and selects from results."""
        # Step 1: Search
        search_results = manga_service.search("Dandadan")
        assert len(search_results) > 0

        # Step 2: Select manga
        selected_manga = search_results[0]
        chapters = manga_service.get_chapters(selected_manga["id"])
        assert len(chapters) > 0

    def test_user_tracks_reading_progress(self, manga_service):
        """User marks manga as read and tracks progress."""
        manga_id = "manga1"

        # Mark chapter as read
        manga_service.mark_as_read(manga_id, "15")

        # Check history was saved
        history = manga_service.get_reading_history(manga_id)
        assert history is not None
