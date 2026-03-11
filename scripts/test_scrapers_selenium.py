"""Test script for validating scraper functionality with Selenium.

Usage:
    python scripts/test_scrapers_selenium.py --scraper animefire --test search
    python scripts/test_scrapers_selenium.py --scraper animefire --all
    python scripts/test_scrapers_selenium.py --all

Tests all scrapers:
    - search_anime: Validates search result structure
    - search_episodes: Validates episode list structure
    - search_player_src: Validates video URL extraction
"""

import argparse
import importlib
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.loader import get_resource_path
from os.path import isfile, join
from os import listdir


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_scraper_instances():
    """Load and return all available scraper instances."""
    scrapers = []
    path = get_resource_path("plugins/")
    system = {"__init__.py", "utils.py"}

    # Get all available plugin files
    all_plugin_files = [
        file[:-3]
        for file in listdir(path)
        if isfile(join(path, file)) and file.endswith(".py") and file not in system
    ]

    # Load each plugin and instantiate
    for plugin_name in all_plugin_files:
        try:
            plugin_module = importlib.import_module("scrapers.plugins." + plugin_name)
            # Find the scraper class in the module (usually the main class)
            for attr_name in dir(plugin_module):
                attr = getattr(plugin_module, attr_name)
                if isinstance(attr, type) and hasattr(attr, "search_anime"):
                    scrapers.append(attr())
                    break
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")

    return scrapers


def test_search_anime(scraper, query: str = "naruto") -> bool:
    """Test search_anime() function.

    Args:
        scraper: Scraper instance
        query: Anime to search for (default: "naruto")

    Returns:
        bool: True if test passes
    """
    try:
        logger.info(f"Testing {scraper.__class__.__name__}.search_anime('{query}')")
        results = scraper.search_anime(query)

        if not results:
            logger.error("  ✗ No results returned")
            return False

        # Validate first result structure
        first = results[0]
        required_fields = ["title", "url"]
        for field in required_fields:
            if not hasattr(first, field):
                logger.error(f"  ✗ Missing field: {field}")
                return False

        logger.info(f"  ✓ Found {len(results)} results, first: {first.title}")
        return True

    except Exception as e:
        logger.error(f"  ✗ Error: {e}", exc_info=True)
        return False


def test_search_episodes(scraper) -> bool:
    """Test search_episodes() function.

    Args:
        scraper: Scraper instance

    Returns:
        bool: True if test passes
    """
    try:
        # First search for an anime
        logger.info(f"Testing {scraper.__class__.__name__}.search_episodes()")
        results = scraper.search_anime("naruto")

        if not results:
            logger.error("  ✗ Could not find anime to test episodes")
            return False

        url = results[0].url
        logger.info(f"  Using URL: {url}")

        # Search episodes
        episodes = scraper.search_episodes(url)

        if not episodes:
            logger.error("  ✗ No episodes returned")
            return False

        # Validate first episode structure
        first = episodes[0]
        required_fields = ["number", "title"]
        for field in required_fields:
            if not hasattr(first, field):
                logger.error(f"  ✗ Missing field: {field}")
                return False

        logger.info(f"  ✓ Found {len(episodes)} episodes, first: Ep {first.number}")
        return True

    except Exception as e:
        logger.error(f"  ✗ Error: {e}", exc_info=True)
        return False


def test_search_player_src(scraper) -> bool:
    """Test search_player_src() function.

    Args:
        scraper: Scraper instance

    Returns:
        bool: True if test passes
    """
    try:
        logger.info(f"Testing {scraper.__class__.__name__}.search_player_src()")

        # First search for an anime
        results = scraper.search_anime("naruto")
        if not results:
            logger.error("  ✗ Could not find anime to test player src")
            return False

        # Search episodes
        episodes = scraper.search_episodes(results[0].url)
        if not episodes:
            logger.error("  ✗ Could not find episodes to test player src")
            return False

        # Search player src
        url = episodes[0].url
        logger.info(f"  Using episode URL: {url}")
        src = scraper.search_player_src(url)

        if not src:
            logger.error("  ✗ No player src returned")
            return False

        logger.info(f"  ✓ Got player src: {src[:60]}...")
        return True

    except Exception as e:
        logger.error(f"  ✗ Error: {e}", exc_info=True)
        return False


def test_scraper(scraper_name: str, test_type: str) -> bool:
    """Test a specific scraper.

    Args:
        scraper_name: Name of scraper to test
        test_type: Type of test ("search", "episodes", "player", or "all")

    Returns:
        bool: True if all tests pass
    """
    scrapers = get_scraper_instances()
    scraper = next(
        (s for s in scrapers if s.__class__.__name__.lower() == scraper_name.lower()),
        None,
    )

    if not scraper:
        logger.error(f"Scraper '{scraper_name}' not found")
        logger.info(f"Available scrapers: {[s.__class__.__name__ for s in scrapers]}")
        return False

    results = []

    if test_type in ("search", "all"):
        results.append(("search_anime", test_search_anime(scraper)))

    if test_type in ("episodes", "all"):
        results.append(("search_episodes", test_search_episodes(scraper)))

    if test_type in ("player", "all"):
        results.append(("search_player_src", test_search_player_src(scraper)))

    # Print summary
    logger.info("")
    logger.info(f"Results for {scraper_name}:")
    for test_name, passed in results:
        status = "✓" if passed else "✗"
        logger.info(f"  {status} {test_name}")

    return all(passed for _, passed in results)


def test_all_scrapers() -> bool:
    """Test all available scrapers.

    Returns:
        bool: True if all scrapers pass all tests
    """
    scrapers = get_scraper_instances()
    results = {}

    for scraper in scrapers:
        scraper_name = scraper.__class__.__name__
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing {scraper_name}")
        logger.info(f"{'=' * 60}")

        passed = test_scraper(scraper_name, "all")
        results[scraper_name] = passed

    # Print final summary
    logger.info(f"\n{'=' * 60}")
    logger.info("FINAL SUMMARY")
    logger.info(f"{'=' * 60}")
    for scraper_name, passed in results.items():
        status = "✓" if passed else "✗"
        logger.info(f"{status} {scraper_name}")

    total_passed = sum(1 for p in results.values() if p)
    logger.info(f"\nPassed: {total_passed}/{len(results)}")

    return all(results.values())


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Test scrapers with Selenium WebDriver")
    parser.add_argument(
        "--scraper",
        type=str,
        help="Specific scraper to test (e.g., 'animefire')",
    )
    parser.add_argument(
        "--test",
        type=str,
        choices=["search", "episodes", "player"],
        help="Specific test to run (default: all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all scrapers (overrides --scraper)",
    )

    args = parser.parse_args()

    if args.all or (not args.scraper):
        success = test_all_scrapers()
    else:
        test_type = args.test or "all"
        success = test_scraper(args.scraper, test_type)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
