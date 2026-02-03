"""Browser pool for managing Selenium WebDriver instances.

Provides thread-safe reuse of Chrome and Firefox browsers across scrapers:
- Singleton pattern for application-wide pooling
- Separate pools for Chrome and Firefox
- Semaphore-based allocation (prevents oversubscription)
- Health checks with automatic recycling
- Context manager for safe lifecycle management
"""

import logging
import threading
import time
from contextlib import contextmanager
from queue import Queue
from typing import Iterator, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from models.config import settings

logger = logging.getLogger(__name__)


class BrowserPoolExhausted(Exception):
    """Raised when browser pool has no available browsers and timeout expired."""

    pass


class BrowserPool:
    """Thread-safe pool of reusable Selenium WebDriver instances.

    Manages Chrome and Firefox browsers separately:
    - Allocates from idle queue if available
    - Creates new instances if under pool size limit
    - Waits on semaphore if at capacity (respects timeout)
    - Recycles browsers after max_age or use count
    - Automatic cleanup of stale/crashed browsers

    Usage:
        with browser_pool.get_chrome(timeout=10) as driver:
            driver.get("https://example.com")
            # Auto-cleanup on context exit
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure one pool per application."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize browser pool with separate Chrome and Firefox queues."""
        if hasattr(self, "_initialized"):
            return

        self.chrome_idle: Queue = Queue()
        self.firefox_idle: Queue = Queue()
        self.chrome_active: set = set()
        self.firefox_active: set = set()

        # Semaphores prevent oversubscription
        pool_size = settings.performance.browser_pool_size
        self.chrome_semaphore = threading.Semaphore(pool_size)
        self.firefox_semaphore = threading.Semaphore(pool_size)

        # Track browser creation times for max_age recycling
        self._browser_creation_times: dict = {}
        self._browser_use_count: dict = {}
        self._pool_lock = threading.Lock()

        self._initialized = True

        logger.debug(
            f"Browser pool initialized: size={pool_size}, "
            f"max_age={settings.performance.browser_max_age}s"
        )

    @contextmanager
    def get_chrome(self, timeout: Optional[int] = None) -> Iterator[WebDriver]:
        """Allocate Chrome browser from pool.

        Acquires from idle queue if available, else creates new (if under limit).
        Automatically returns browser to pool and cleans up on context exit.

        Args:
            timeout: Max seconds to wait for available browser.
                    Defaults to config browser_health_check_timeout.

        Yields:
            selenium.webdriver.Chrome: Allocated WebDriver instance

        Raises:
            BrowserPoolExhausted: If no browser available after timeout

        Example:
            try:
                with browser_pool.get_chrome(timeout=10) as driver:
                    driver.get("https://example.com")
            except BrowserPoolExhausted:
                logger.warning("Chrome pool exhausted, skipping scraper")
        """
        timeout = timeout or settings.performance.browser_health_check_timeout
        driver = None

        # Acquire semaphore slot (waits if at capacity)
        acquired = self.chrome_semaphore.acquire(timeout=timeout)
        if not acquired:
            raise BrowserPoolExhausted(
                f"Chrome pool exhausted after {timeout}s "
                f"(max {settings.performance.browser_pool_size})"
            )

        try:
            # Try to get from idle queue
            try:
                driver = self.chrome_idle.get_nowait()
                logger.debug("Allocated Chrome from idle pool")
            except:
                # No idle browser, create new one
                driver = self._create_chrome()
                logger.debug("Created new Chrome instance")

            # Health check: verify browser is responsive
            if not self._health_check(driver):
                logger.debug("Chrome health check failed, creating new instance")
                try:
                    driver.quit()
                except:
                    pass
                driver = self._create_chrome()

            # Mark as active
            with self._pool_lock:
                self.chrome_active.add(id(driver))

            yield driver

        except BrowserPoolExhausted:
            raise
        except Exception as e:
            logger.error(f"Error in get_chrome context: {e}")
            raise
        finally:
            # Return browser to pool or cleanup
            if driver:
                try:
                    self._return_browser(driver, "chrome")
                except Exception as e:
                    logger.error(f"Error returning Chrome to pool: {e}")

            # Release semaphore slot
            self.chrome_semaphore.release()

    @contextmanager
    def get_firefox(self, timeout: Optional[int] = None) -> Iterator[WebDriver]:
        """Allocate Firefox browser from pool.

        Same behavior as get_chrome() but for Firefox instances.

        Args:
            timeout: Max seconds to wait for available browser.
                    Defaults to config browser_health_check_timeout.

        Yields:
            selenium.webdriver.Firefox: Allocated WebDriver instance

        Raises:
            BrowserPoolExhausted: If no browser available after timeout

        Example:
            with browser_pool.get_firefox(timeout=10) as driver:
                driver.get("https://example.com")
        """
        timeout = timeout or settings.performance.browser_health_check_timeout
        driver = None

        # Acquire semaphore slot
        acquired = self.firefox_semaphore.acquire(timeout=timeout)
        if not acquired:
            raise BrowserPoolExhausted(
                f"Firefox pool exhausted after {timeout}s "
                f"(max {settings.performance.browser_pool_size})"
            )

        try:
            # Try to get from idle queue
            try:
                driver = self.firefox_idle.get_nowait()
                logger.debug("Allocated Firefox from idle pool")
            except:
                # No idle browser, create new one
                driver = self._create_firefox()
                logger.debug("Created new Firefox instance")

            # Health check
            if not self._health_check(driver):
                logger.debug("Firefox health check failed, creating new instance")
                try:
                    driver.quit()
                except:
                    pass
                driver = self._create_firefox()

            # Mark as active
            with self._pool_lock:
                self.firefox_active.add(id(driver))

            yield driver

        except BrowserPoolExhausted:
            raise
        except Exception as e:
            logger.error(f"Error in get_firefox context: {e}")
            raise
        finally:
            # Return browser to pool or cleanup
            if driver:
                try:
                    self._return_browser(driver, "firefox")
                except Exception as e:
                    logger.error(f"Error returning Firefox to pool: {e}")

            # Release semaphore slot
            self.firefox_semaphore.release()

    def _create_chrome(self) -> WebDriver:
        """Create and configure Chrome WebDriver instance."""
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        driver = webdriver.Chrome(options=options)

        # Track creation time and use count
        with self._pool_lock:
            driver_id = id(driver)
            self._browser_creation_times[driver_id] = time.time()
            self._browser_use_count[driver_id] = 0

        return driver

    def _create_firefox(self) -> WebDriver:
        """Create and configure Firefox WebDriver instance."""
        options = FirefoxOptions()
        options.add_argument("--headless")

        driver = webdriver.Firefox(options=options)

        # Track creation time and use count
        with self._pool_lock:
            driver_id = id(driver)
            self._browser_creation_times[driver_id] = time.time()
            self._browser_use_count[driver_id] = 0

        return driver

    def _health_check(self, driver: WebDriver) -> bool:
        """Verify browser is responsive and healthy.

        Attempts a simple JavaScript execution to confirm browser is alive.

        Args:
            driver: WebDriver instance to check

        Returns:
            bool: True if browser is responsive, False otherwise
        """
        try:
            driver.execute_script("return true;")
            return True
        except Exception as e:
            logger.debug(f"Browser health check failed: {e}")
            return False

    def _return_browser(self, driver: WebDriver, browser_type: str) -> None:
        """Return browser to idle pool or cleanup if stale.

        Args:
            driver: WebDriver instance to return
            browser_type: "chrome" or "firefox"
        """
        driver_id = id(driver)
        max_age = settings.performance.browser_max_age

        with self._pool_lock:
            # Check if browser has exceeded max age
            created_at = self._browser_creation_times.get(driver_id, time.time())
            age = time.time() - created_at

            # Mark as inactive
            if browser_type == "chrome":
                self.chrome_active.discard(driver_id)
            else:
                self.firefox_active.discard(driver_id)

            # Recycle if over max age
            if age > max_age:
                logger.debug(
                    f"{browser_type} browser exceeded max age ({age:.0f}s > {max_age}s), recycling"
                )
                try:
                    driver.quit()
                except:
                    pass
                # Clean up tracking
                self._browser_creation_times.pop(driver_id, None)
                self._browser_use_count.pop(driver_id, None)
                return

        # Otherwise, return to idle queue
        if browser_type == "chrome":
            self.chrome_idle.put(driver)
            logger.debug(f"Returned Chrome to idle pool (size: {self.chrome_idle.qsize()})")
        else:
            self.firefox_idle.put(driver)
            logger.debug(f"Returned Firefox to idle pool (size: {self.firefox_idle.qsize()})")

    def close_all(self) -> None:
        """Cleanup all browsers in pool (active and idle).

        Called on application shutdown.
        """
        logger.info("Closing all browser pool instances")

        # Close idle browsers
        while True:
            try:
                driver = self.chrome_idle.get_nowait()
                try:
                    driver.quit()
                except:
                    pass
            except:
                break

        while True:
            try:
                driver = self.firefox_idle.get_nowait()
                try:
                    driver.quit()
                except:
                    pass
            except:
                break

        # Close active browsers (emergency cleanup)
        for browser_id in list(self.chrome_active):
            with self._pool_lock:
                self.chrome_active.discard(browser_id)

        for browser_id in list(self.firefox_active):
            with self._pool_lock:
                self.firefox_active.discard(browser_id)

        logger.info("Browser pool cleanup complete")

    def get_stats(self) -> dict:
        """Return pool statistics for monitoring.

        Returns:
            dict: Stats including active/idle counts, pool size limits
        """
        return {
            "chrome_idle": self.chrome_idle.qsize(),
            "chrome_active": len(self.chrome_active),
            "firefox_idle": self.firefox_idle.qsize(),
            "firefox_active": len(self.firefox_active),
            "pool_size": settings.performance.browser_pool_size,
            "max_age_seconds": settings.performance.browser_max_age,
        }


# Global singleton instance for easy import
browser_pool = BrowserPool()
