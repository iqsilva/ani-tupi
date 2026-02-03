from scrapling import Fetcher, DynamicFetcher
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

from services.repository import rep

# Request timeout for all AnimesDigital API calls (seconds)
# Increased to 30s to handle slow network conditions
REQUEST_TIMEOUT = 30


class AnimesDigital:
    languages = ["pt-br"]
    name = "animesdigital"

    def _search_with_selenium(self, query: str, url: str) -> list[tuple[str, str]]:
        """Search anime using Selenium with #termo_busca input.

        Uses dynamic page interaction to search both dubbed and subtitled versions.
        Returns list of (title, url) tuples.
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        driver = None
        results = []

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)

            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
            )

            time.sleep(1)

            # Find search input #termo_busca
            try:
                search_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "termo_busca"))
                )
            except Exception as e:
                raise Exception(f"Could not find #termo_busca on {url}: {e}")

            # Type query and trigger input/change events
            search_input.clear()
            search_input.send_keys(query)
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_input
            )
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", search_input
            )

            # Wait for results to load
            time.sleep(2)

            # Parse page content
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Extract anime from div[class*='item'] containers
            anime_items = soup.select("div[class*='item']")

            for item in anime_items:
                link = item.find("a", href=True)
                if not link:
                    continue

                href = link.get("href")
                title = link.get_text(strip=True)

                if href and title and "/anime/" in href:
                    # Avoid duplicates
                    if not any(t[0] == title for t in results):
                        results.append((title, href))

        except Exception as e:
            import sys

            print(f"Warning: Selenium search on {url} for '{query}': {e}", file=sys.stderr)

        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        return results

    def search_anime(self, query) -> None:
        """Search for anime on AnimesDigital.

        Searches both dubbed (dublado) and subtitled (legendado) versions.
        Uses dynamic Selenium-based search with #termo_busca input.
        Returns all versions found (legendado and dublado are different links).
        """
        search_urls = [
            "https://animesdigital.org/animes-legendados-online",
            "https://animesdigital.org/animes-dublado/",
        ]

        titled_urls = []

        for search_url in search_urls:
            results = self._search_with_selenium(query, search_url)

            for title, url in results:
                # Add all versions (legendado and dublado are different URLs)
                titled_urls.append((title, url))

        # Add anime to repository
        for title, url in titled_urls:
            rep.add_anime(title, url, AnimesDigital.name)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list from anime page.

        Ensures all episodes are displayed by adding ?odr=1 parameter.
        Extracts episodes from the detail page using div.item_ep selector.
        Filters out special episodes (fractionated like 13.5) to avoid duplicates.
        """
        import re

        # Ensure ?odr=1 parameter is present to show all episodes
        if "?" in url:
            if "odr=" not in url:
                url = url + "&odr=1"
        else:
            url = url + "?odr=1"

        fetcher = Fetcher()
        tree = fetcher.get(url, timeout=REQUEST_TIMEOUT)

        # Find all episode containers
        episode_divs = tree.css("div.item_ep")

        episode_titles = []
        episode_urls = []

        for ep_div in episode_divs:
            # Find the link inside the episode div for the URL
            link = ep_div.css_first("a")
            href = None
            if link:
                href = link.attrib.get("href")

            # Get episode title from .title_anime class (avoids metadata like "9 meses atrás")
            title_elem = ep_div.css_first(".title_anime")
            if title_elem and href:
                title = str(title_elem.text).strip()
                # Clean up extra whitespace
                title = " ".join(title.split())
                if title:
                    # Filter out special episodes (fractionated like 13.5, 0.5, etc)
                    # These are OVAs/specials that shouldn't be counted as main episodes
                    if re.search(r"Episódio\s+\d+\.\d+", title):
                        continue  # Skip special episodes
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Add episodes to repository
        rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract video URL from episode player.

        AnimesDigital loads iframes dynamically via JavaScript.
        Uses DynamicFetcher to render the page and extract iframe sources.
        Prioritizes api.anivideo.net iframes which are most reliable.
        """
        try:
            # Use Firefox for better library compatibility
            page = DynamicFetcher.fetch(url, timeout=15000, browser="firefox")

            # Extract all iframes
            iframes = page.css("iframe")

            if not iframes:
                raise Exception("No iframe found in AnimesDigital episode page.")

            # Priority 1: Look for api.anivideo.net iframes (most reliable)
            for iframe in iframes:
                src = iframe.attrib.get("src")
                if src and "api.anivideo.net" in src:
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Priority 2: Look for m3u8 or mp4 iframes
            for iframe in iframes:
                src = iframe.attrib.get("src")
                if src and ("m3u8" in src or "mp4" in src):
                    if not event.is_set():
                        container.append(src)
                        event.set()
                    return

            # Priority 3: Use the first iframe as fallback
            src = iframes[0].attrib.get("src")
            if src and not event.is_set():
                container.append(src)
                event.set()

        except Exception as e:
            msg = f"Could not extract video from AnimesDigital: {e}"
            raise Exception(msg) from e


def load(languages_dict) -> None:
    """Load plugin if language is supported."""
    can_load = False
    for language in AnimesDigital.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(AnimesDigital())
