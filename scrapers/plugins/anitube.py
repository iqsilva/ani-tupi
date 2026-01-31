from selectolax.parser import HTMLParser

from scrapers.core.browser_pool import get_browser_pool
from scrapers.plugins.utils import get_with_retry
from services.repository import rep

REQUEST_TIMEOUT = 30


class AniTube:
    languages = ["pt-br"]
    name = "anitube"

    def search_anime(self, query: str) -> None:
        """Search for anime on AniTube.

        Uses Playwright to bypass anti-bot protection.
        Extracts anime titles and links from the search results page.
        """
        from playwright.sync_api import sync_playwright

        url = "https://www.anitube.news/?s=" + "+".join(query.split())

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)
                    tree = HTMLParser(page.content())
                finally:
                    browser.close()
        except Exception:
            return  # Silently fail if Playwright isn't available

        # Extract anime links directly
        # AniTube search results have links with /video/ in href
        links = tree.css("a[href*='/video/']")

        for link in links:
            href = link.attributes.get("href")
            title = link.text().strip()

            if not href or not title:
                continue

            # Clean up title (remove extra whitespace)
            title = " ".join(title.split())

            if title:
                if not href.startswith("http"):
                    href = "https://www.anitube.news" + href
                rep.add_anime(title, href, AniTube.name)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list from anime page.

        Extracts episodes from the anime detail page.
        Episodes are typically listed in a dedicated section.
        """
        response = get_with_retry(url, timeout=REQUEST_TIMEOUT)
        tree = HTMLParser(response.text)

        episode_titles = []
        episode_urls = []

        # Look for episode links in various possible structures
        # AniTube typically uses anchor tags with episode info
        episode_links = tree.css("a[href*='/video/']")

        # Filter to only include links that are actually episodes (not the main anime link)
        for link in episode_links:
            href = link.attributes.get("href")
            text = link.text().strip()

            if not href or not text:
                continue

            # Skip if it's just the main anime page link
            if href == url:
                continue

            # Extract episode number from text if available
            text = " ".join(text.split())

            episode_urls.append(href)
            episode_titles.append(text)

        # Add episodes to repository
        if episode_titles and episode_urls:
            rep.add_episode_list(anime, episode_titles, episode_urls, AniTube.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video URL from episode player.

        AniTube loads videos through iframes that are dynamically rendered.
        Uses Selenium browser pool to wait for iframe to load and extract src.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.wait import WebDriverWait

            with get_browser_pool().get_browser() as driver:
                driver.get(url)

                # Wait for iframe to be visible
                try:
                    params = (By.TAG_NAME, "iframe")
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located(params))
                except Exception:
                    raise Exception("No iframe found on AniTube episode page.")

                iframes = driver.find_elements(By.TAG_NAME, "iframe")

                if not iframes:
                    raise Exception("No iframe found on AniTube episode page.")

                # Try to get src from the first iframe
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and src.startswith("http"):
                        if not event.is_set():
                            container.append(src)
                            event.set()
                        return

                # If no valid iframe found, raise error
                raise Exception("No valid iframe source found on AniTube episode page.")

        except Exception as e:
            msg = f"Could not extract video from AniTube: {e}"
            raise Exception(msg) from e


def load(languages_dict) -> None:
    """Load plugin if language is supported."""
    can_load = False
    for language in AniTube.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AniTube())
