from selectolax.parser import HTMLParser

from scrapers.core.browser_pool import get_browser_pool
from scrapers.plugins.utils import get_with_retry
from services.repository import rep

REQUEST_TIMEOUT = 30


class TopAnimes:
    languages = ["pt-br"]
    name = "topanimes"

    def search_anime(self, query: str) -> None:
        """Search for anime on TopAnimes.

        Uses Playwright to load search results and extract anime links.
        """
        from playwright.sync_api import sync_playwright

        url = "https://topanimes.net/?s=" + "+".join(query.split())

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)
                    tree = HTMLParser(page.content())
                finally:
                    browser.close()

                # Extract anime links from search results
                # TopAnimes has links to /animes/ and /filmes/
                links = tree.css("a[href*='/animes/']")
                links.extend(tree.css("a[href*='/filmes/']"))

                seen = set()  # Track seen URLs to avoid duplicates
                for link in links:
                    href = link.attributes.get("href")
                    title = link.text().strip()

                    if not href or not title or href in seen:
                        continue

                    # Clean up title
                    title = " ".join(title.split())

                    # Filter out generic titles like "TV", "Movie", etc.
                    if title.lower() in ("tv", "movie", "filme", "ep.", "legend", "dub"):
                        continue

                    if not href.startswith("http"):
                        href = "https://topanimes.net" + href

                    seen.add(href)
                    rep.add_anime(title, href, TopAnimes.name)

        except Exception:
            return  # Silently fail if Playwright isn't available

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list from anime page.

        Extracts episodes from the anime detail page using CSS selectors.
        Episodes are typically found in #seasons .se-c .se-a ul.episodios li structure.
        """
        response = get_with_retry(url, timeout=REQUEST_TIMEOUT)
        tree = HTMLParser(response.text)

        episode_titles = []
        episode_urls = []

        # TopAnimes uses #seasons structure for episode listing
        # Look for episodes in: #seasons .se-c .se-a ul.episodios li
        episode_items = tree.css("#seasons .se-c .se-a ul.episodios li")

        if not episode_items:
            # Fallback: try different selectors
            episode_items = tree.css("ul.episodios li")

        if not episode_items:
            # Another fallback: look for any episode links
            episode_items = tree.css(".episodio")

        for item in episode_items:
            # Get title from .episodiotitle or the text content
            title_elem = item.css_first(".episodiotitle a")
            if not title_elem:
                title_elem = item.css_first("a")

            if not title_elem:
                continue

            title = title_elem.text().strip()
            href = title_elem.attributes.get("href")

            if href and title:
                # Clean up title
                title = " ".join(title.split())
                episode_urls.append(href)
                episode_titles.append(title)

        # Add episodes to repository
        if episode_titles and episode_urls:
            rep.add_episode_list(anime, episode_titles, episode_urls, TopAnimes.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video URL from episode player.

        TopAnimes typically uses iframes for video playback.
        Uses Selenium browser pool to wait for iframe and extract src.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.wait import WebDriverWait

            with get_browser_pool().get_browser() as driver:
                driver.get(url)

                # Wait for iframe to be present
                try:
                    params = (By.TAG_NAME, "iframe")
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located(params))
                except Exception:
                    raise Exception("No iframe found on TopAnimes episode page.")

                iframes = driver.find_elements(By.TAG_NAME, "iframe")

                if not iframes:
                    raise Exception("No iframe found on TopAnimes episode page.")

                # Try to get src from iframes, prioritizing certain providers
                # TopAnimes uses various iframe providers
                for iframe in iframes:
                    src = iframe.get_attribute("src")
                    if src and src.startswith("http"):
                        # Prioritize certain providers if needed
                        if not event.is_set():
                            container.append(src)
                            event.set()
                        return

                # If no valid iframe found, raise error
                raise Exception("No valid iframe source found on TopAnimes episode page.")

        except Exception as e:
            msg = f"Could not extract video from TopAnimes: {e}"
            raise Exception(msg) from e


def load(languages_dict) -> None:
    """Load plugin if language is supported."""
    can_load = False
    for language in TopAnimes.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(TopAnimes())
