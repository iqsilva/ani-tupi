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

        Uses the WP JSON API endpoint (/wp-json/dooplay/search/) to fetch
        search results as JSON. This is more reliable than HTML parsing.
        Extracts anime titles and links from the API response.
        """
        # TopAnimes uses WP-JSON API for search
        url = "https://topanimes.net/wp-json/dooplay/search/"
        params = {"s": query}

        try:
            response = get_with_retry(url, params=params, timeout=REQUEST_TIMEOUT)
            data = response.json()

            # API returns a list of anime results
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("name", "").strip()
                        link = item.get("url") or item.get("link", "").strip()

                        if title and link:
                            # Clean up title
                            title = " ".join(title.split())
                            rep.add_anime(title, link, TopAnimes.name)

            elif isinstance(data, dict):
                # If API returns a dict with results key
                results = data.get("results", [])
                for item in results:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("name", "").strip()
                        link = item.get("url") or item.get("link", "").strip()

                        if title and link:
                            title = " ".join(title.split())
                            rep.add_anime(title, link, TopAnimes.name)

        except Exception:
            # Fallback to HTML parsing if API fails
            self._search_anime_html(query)

    def _search_anime_html(self, query: str) -> None:
        """Fallback HTML parsing for anime search.

        If API is unavailable, falls back to parsing HTML from search page.
        """
        url = "https://topanimes.net/?s=" + "+".join(query.split())
        response = get_with_retry(url, timeout=REQUEST_TIMEOUT)
        tree = HTMLParser(response.text)

        # TopAnimes uses .module .content .items .item structure
        anime_items = tree.css(".module .content .items .item")

        for item in anime_items:
            # Get title from h3 or h2
            title_elem = item.css_first("h3") or item.css_first("h2")
            if not title_elem:
                continue

            title = title_elem.text().strip()

            # Get URL from the link
            link = item.css_first("a")
            href = None
            if link:
                href = link.attributes.get("href")

            if href and title:
                title = " ".join(title.split())
                rep.add_anime(title, href, TopAnimes.name)

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
