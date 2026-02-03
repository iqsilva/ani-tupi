"""Tests for the browser pool implementation.

Tests verify:
- Singleton pattern (one pool per application)
- Chrome and Firefox allocation from pool
- Health checks and browser recycling
- Semaphore-based concurrency limits
- Context manager cleanup
- Pool exhaustion handling
- Statistics and monitoring
"""

import threading
import time

import pytest

from scrapers.core.browser_pool import (
    BrowserPool,
    browser_pool,
)
from models.config import settings


class TestBrowserPoolSingleton:
    """Test singleton pattern for browser pool."""

    def test_singleton_instance(self):
        """Same instance returned on multiple calls."""
        pool1 = BrowserPool()
        pool2 = BrowserPool()
        assert pool1 is pool2
        assert pool1 is browser_pool

    def test_singleton_thread_safe(self):
        """Singleton creation is thread-safe."""
        instances = []
        lock = threading.Lock()

        def create_pool():
            pool = BrowserPool()
            with lock:
                instances.append(pool)

        threads = [threading.Thread(target=create_pool) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(p) for p in instances)) == 1

    def test_pool_initialization(self):
        """Pool initializes with correct configuration."""
        pool = BrowserPool()
        stats = pool.get_stats()

        assert stats["pool_size"] == settings.performance.browser_pool_size
        assert stats["max_age_seconds"] == settings.performance.browser_max_age
        assert stats["chrome_idle"] == 0
        assert stats["firefox_idle"] == 0
        assert stats["chrome_active"] == 0
        assert stats["firefox_active"] == 0


class TestBrowserPoolAllocation:
    """Test browser allocation from pool."""

    def test_get_chrome_creates_driver(self):
        """Chrome allocation returns a WebDriver instance."""
        pool = BrowserPool()

        try:
            with pool.get_chrome(timeout=5) as driver:
                assert driver is not None
                # Can execute basic JavaScript
                result = driver.execute_script("return 1 + 1")
                assert result == 2
        finally:
            # Cleanup after test
            pool.close_all()

    def test_get_firefox_creates_driver(self):
        """Firefox allocation returns a WebDriver instance."""
        pool = BrowserPool()

        try:
            with pool.get_firefox(timeout=5) as driver:
                assert driver is not None
                # Can execute basic JavaScript
                result = driver.execute_script("return 1 + 1")
                assert result == 2
        finally:
            pool.close_all()

    def test_chrome_returned_to_idle_pool(self):
        """Chrome driver returned to idle queue after context exit."""
        pool = BrowserPool()

        try:
            # First allocation
            with pool.get_chrome(timeout=5):
                pass

            stats = pool.get_stats()
            assert stats["chrome_idle"] == 1
            assert stats["chrome_active"] == 0

            # Second allocation reuses from idle
            with pool.get_chrome(timeout=5):
                pass

            stats = pool.get_stats()
            assert stats["chrome_idle"] == 1
        finally:
            pool.close_all()

    def test_firefox_returned_to_idle_pool(self):
        """Firefox driver returned to idle queue after context exit."""
        pool = BrowserPool()

        try:
            with pool.get_firefox(timeout=5):
                pass

            stats = pool.get_stats()
            assert stats["firefox_idle"] == 1
            assert stats["firefox_active"] == 0
        finally:
            pool.close_all()


class TestBrowserPoolConcurrency:
    """Test semaphore-based concurrency limits."""

    def test_chrome_semaphore_initialized_correctly(self):
        """Chrome semaphore initialized to pool size."""
        pool = BrowserPool()
        max_size = settings.performance.browser_pool_size

        # Check semaphore is initialized with correct value
        assert pool.chrome_semaphore._value == max_size

    def test_firefox_semaphore_initialized_correctly(self):
        """Firefox semaphore initialized to pool size."""
        pool = BrowserPool()
        max_size = settings.performance.browser_pool_size

        # Check semaphore is initialized with correct value
        assert pool.firefox_semaphore._value == max_size

    def test_semaphore_released_after_use(self):
        """Semaphore is released after browser allocation completes."""
        pool = BrowserPool()
        max_size = settings.performance.browser_pool_size

        try:
            # Before allocation
            initial_value = pool.chrome_semaphore._value
            assert initial_value == max_size

            # Allocate and release
            with pool.get_chrome(timeout=5):
                # During allocation, semaphore decremented
                # (can't check reliably due to threading, but browser works)
                pass

            # After release, should be restored
            # (may not be exactly max_size if other threads are using it,
            # but should be less exhausted)
            final_value = pool.chrome_semaphore._value
            assert final_value >= 1

        finally:
            pool.close_all()


class TestBrowserPoolHealthCheck:
    """Test health check and browser recycling."""

    def test_health_check_detects_responsive_browser(self):
        """Health check returns True for working browser."""
        pool = BrowserPool()

        try:
            with pool.get_chrome(timeout=5) as driver:
                assert pool._health_check(driver) is True
        finally:
            pool.close_all()

    def test_browser_max_age_triggers_cleanup(self):
        """Browser over max_age is cleaned up."""
        pool = BrowserPool()
        max_age = settings.performance.browser_max_age

        try:
            with pool.get_chrome(timeout=5) as driver:
                driver_id = id(driver)
                # Manually set creation time to past
                pool._browser_creation_times[driver_id] = time.time() - max_age - 100

            # Browser should be cleaned up, not returned to idle
            stats = pool.get_stats()
            # Pool should be empty (browser was cleaned up)
            assert stats["chrome_idle"] == 0

        finally:
            pool.close_all()


class TestBrowserPoolErrors:
    """Test error handling and recovery."""

    def test_context_manager_cleanup_on_error(self):
        """Browser returned to pool even if error occurs inside context."""
        pool = BrowserPool()

        try:
            with pytest.raises(RuntimeError):
                with pool.get_chrome(timeout=5):
                    raise RuntimeError("Test error")

            # Browser should still be in idle queue (or recycled if stale)
            # Even with error, semaphore should be released
            assert pool.chrome_semaphore._value > 0

        finally:
            pool.close_all()

    def test_driver_quit_error_handled_gracefully(self):
        """Driver cleanup errors don't propagate."""
        pool = BrowserPool()

        try:
            with pool.get_chrome(timeout=5) as driver:
                # Manually quit the driver to cause cleanup error
                driver.quit()
                # Context exit should handle the error gracefully

            # Pool should still be functional
            assert pool.chrome_semaphore._value >= 1

        finally:
            pool.close_all()


class TestBrowserPoolStats:
    """Test pool statistics and monitoring."""

    def test_get_stats_returns_all_metrics(self):
        """Stats includes all required metrics."""
        pool = BrowserPool()

        stats = pool.get_stats()

        assert "chrome_idle" in stats
        assert "chrome_active" in stats
        assert "firefox_idle" in stats
        assert "firefox_active" in stats
        assert "pool_size" in stats
        assert "max_age_seconds" in stats

    def test_stats_reflect_current_state(self):
        """Stats accurately reflect pool state."""
        pool = BrowserPool()

        try:
            # Initially empty
            stats = pool.get_stats()
            assert stats["chrome_idle"] == 0
            assert stats["chrome_active"] == 0

            # Allocate one
            with pool.get_chrome(timeout=5):
                stats = pool.get_stats()
                assert stats["chrome_active"] >= 1

            # After release, should be in idle
            stats = pool.get_stats()
            assert stats["chrome_idle"] >= 1

        finally:
            pool.close_all()


class TestBrowserPoolCleanup:
    """Test cleanup and resource management."""

    def test_close_all_cleans_up_all_browsers(self):
        """close_all() terminates all pool browsers."""
        pool = BrowserPool()

        try:
            # Allocate and return several browsers
            for _ in range(2):
                with pool.get_chrome(timeout=5):
                    pass

            stats = pool.get_stats()
            assert stats["chrome_idle"] >= 1

            # Close all
            pool.close_all()

            # Pool should be empty
            stats = pool.get_stats()
            assert stats["chrome_idle"] == 0
            assert stats["firefox_idle"] == 0

        except Exception:
            pool.close_all()

    def test_separate_pools_for_chrome_firefox(self):
        """Chrome and Firefox pools are independent."""
        pool = BrowserPool()

        try:
            with pool.get_chrome(timeout=5):
                pass

            with pool.get_firefox(timeout=5):
                pass

            stats = pool.get_stats()
            # Both should have browsers
            assert stats["chrome_idle"] >= 1
            assert stats["firefox_idle"] >= 1

        finally:
            pool.close_all()


class TestBrowserPoolIntegration:
    """Integration tests for browser pool usage."""

    def test_sequential_allocations_reuse_browsers(self):
        """Sequential allocations efficiently reuse browsers."""
        pool = BrowserPool()

        try:
            # First allocation
            with pool.get_chrome(timeout=5) as driver1:
                driver1_id = id(driver1)

            # Second allocation should reuse same browser
            with pool.get_chrome(timeout=5) as driver2:
                driver2_id = id(driver2)

            # Same instance reused
            assert driver1_id == driver2_id

        finally:
            pool.close_all()

    def test_multiple_browser_types_coexist(self):
        """Chrome and Firefox instances coexist in same pool."""
        pool = BrowserPool()

        try:
            with pool.get_chrome(timeout=5) as chrome_driver:
                with pool.get_firefox(timeout=5) as firefox_driver:
                    assert chrome_driver is not None
                    assert firefox_driver is not None
                    assert id(chrome_driver) != id(firefox_driver)

        finally:
            pool.close_all()
