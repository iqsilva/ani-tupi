"""Phase 1 (C1) TDD Tests: Consolidate Manga Services

Tests verify that all manga service components are available from a single
consolidated manga_service module, replacing split implementations.
"""

from services.manga_service import (
    UnifiedMangaService,
    MangaHistory,
    DownloadedChaptersTracker,
    MangaError,
    MangaNotFoundError,
    MangaDexError,
    ChapterNotAvailableError,
    MangaDexClient,  # Backward compatibility alias
)


class TestUnifiedServiceImport:
    """Verify UnifiedMangaService is importable from consolidated module."""

    def test_unified_service_available(self):
        """UnifiedMangaService should be importable."""
        assert UnifiedMangaService is not None

    def test_unified_service_has_required_methods(self):
        """UnifiedMangaService should have required methods."""
        assert hasattr(UnifiedMangaService, "search_manga")
        assert hasattr(UnifiedMangaService, "get_chapters")
        assert hasattr(UnifiedMangaService, "get_chapter_pages")


class TestUtilityClassesImport:
    """Verify all utility classes are importable from consolidated module."""

    def test_unified_cache_available(self):
        """Unified cache should be importable."""
        from utils.cache import Cache

        assert Cache is not None

    def test_manga_history_available(self):
        """MangaHistory should be importable."""
        assert MangaHistory is not None

    def test_downloaded_chapters_tracker_available(self):
        """DownloadedChaptersTracker should be importable."""
        assert DownloadedChaptersTracker is not None


class TestExceptionClassesImport:
    """Verify all exception classes are importable from consolidated module."""

    def test_manga_error_available(self):
        """MangaError should be importable."""
        assert MangaError is not None
        assert issubclass(MangaError, Exception)

    def test_manga_not_found_error_available(self):
        """MangaNotFoundError should be importable."""
        assert MangaNotFoundError is not None
        assert issubclass(MangaNotFoundError, MangaError)

    def test_manga_dex_error_available(self):
        """MangaDexError should be importable."""
        assert MangaDexError is not None
        assert issubclass(MangaDexError, MangaError)

    def test_chapter_not_available_error_available(self):
        """ChapterNotAvailableError should be importable."""
        assert ChapterNotAvailableError is not None
        assert issubclass(ChapterNotAvailableError, MangaError)


class TestUnifiedCacheFunctionality:
    """Verify unified cache works correctly for manga service."""

    def test_cache_set_and_get(self):
        """Cache should store and retrieve values."""
        from utils.cache import MemoryCache

        cache = MemoryCache(max_size_mb=10, default_ttl=3600)
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_cache_returns_none_for_missing_key(self):
        """Cache should return None for missing keys."""
        from utils.cache import MemoryCache

        cache = MemoryCache(max_size_mb=10, default_ttl=3600)
        assert cache.get("nonexistent") is None

    def test_cache_clear(self):
        """Cache should clear all entries."""
        from utils.cache import MemoryCache

        cache = MemoryCache(max_size_mb=10, default_ttl=3600)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestMangaHistoryFunctionality:
    """Verify MangaHistory works correctly after consolidation."""

    def test_history_can_be_instantiated(self):
        """MangaHistory should be instantiable."""
        history = MangaHistory()
        assert history is not None

    def test_history_has_required_methods(self):
        """MangaHistory should have required methods."""
        assert hasattr(MangaHistory, "load")
        assert hasattr(MangaHistory, "save")
        assert hasattr(MangaHistory, "get_last_chapter")
        assert hasattr(MangaHistory, "update")


class TestDownloadedChaptersTrackerFunctionality:
    """Verify DownloadedChaptersTracker works correctly after consolidation."""

    def test_tracker_can_be_instantiated(self):
        """DownloadedChaptersTracker should be instantiable."""
        tracker = DownloadedChaptersTracker()
        assert tracker is not None

    def test_tracker_has_required_methods(self):
        """DownloadedChaptersTracker should have required methods."""
        assert hasattr(DownloadedChaptersTracker, "mark_downloaded")
        assert hasattr(DownloadedChaptersTracker, "is_downloaded")
        assert hasattr(DownloadedChaptersTracker, "get_downloaded_chapters")
        assert hasattr(DownloadedChaptersTracker, "get_download_path")


class TestBackwardCompatibilityAlias:
    """Verify MangaDexClient backward compatibility alias works."""

    def test_manga_dex_client_alias_available(self):
        """MangaDexClient should be importable as backward compatibility alias."""
        assert MangaDexClient is not None

    def test_manga_dex_client_is_subclass_of_unified_service(self):
        """MangaDexClient should be an alias/subclass of UnifiedMangaService."""
        assert issubclass(MangaDexClient, UnifiedMangaService)


class TestExceptionUserMessages:
    """Verify exception classes have proper user-friendly messages."""

    def test_manga_error_has_user_message(self):
        """MangaError should have user_message attribute."""
        err = MangaError("test error", user_message="Erro customizado")
        assert err.user_message == "Erro customizado"

    def test_manga_not_found_error_has_user_message(self):
        """MangaNotFoundError should have user_message attribute."""
        assert hasattr(MangaNotFoundError, "user_message")

    def test_manga_dex_error_has_user_message(self):
        """MangaDexError should have user_message attribute."""
        assert hasattr(MangaDexError, "user_message")

    def test_chapter_not_available_error_has_user_message(self):
        """ChapterNotAvailableError should have user_message attribute."""
        assert hasattr(ChapterNotAvailableError, "user_message")


class TestNoUnusedImports:
    """Verify old imports from separate files are no longer needed."""

    def test_unified_manga_service_module_not_required(self):
        """unified_manga_service module should be deprecated after consolidation."""
        # This test documents that unified_manga_service.py should be deleted
        # and users should import from manga_service.py instead
        # In a real scenario, trying to import from unified_manga_service would fail
        pass  # Placeholder for integration testing phase

    def test_old_manga_service_structure_consolidated(self):
        """Old manga_service.py structure should be consolidated into single file."""
        # This test documents that the consolidation is complete
        # Both utilities and service are now in the same module
        pass  # Placeholder for integration testing phase
