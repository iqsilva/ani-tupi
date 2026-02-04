import json
import logging
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from scrapling import DynamicFetcher, Fetcher

from services.repository import rep

logger = logging.getLogger(__name__)

# Request timeout for all AnimesDigital API calls (seconds)
REQUEST_TIMEOUT = 30

# API endpoint for searching
API_URL = "https://animesdigital.org/func/listanime"

# API token - may need to be updated if it expires
API_TOKEN = "c1deb78cd4"

# Headers for API requests
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://animesdigital.org",
    "Connection": "keep-alive",
    "Referer": "https://animesdigital.org/animes-legendados-online",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


class AnimeResult(TypedDict):
    title: str
    url: str
    image: str


class AnimesDigital:
    languages = ["pt-br"]
    name = "animesdigital"

    def _search_api(
        self, query: str, page: int = 1, limit: int = 30, audio_type: str = "legendado"
    ) -> tuple[list[AnimeResult], dict]:
        """Search anime using the JSON API.

        Args:
            query: Search term
            page: Page number (1-indexed)
            limit: Results per page
            audio_type: "legendado" or "dublado"

        Returns:
            Tuple of (results list, metadata dict)
        """
        filters = {
            "filter_data": f"filter_letter=0&type_url=animes&filter_audio={audio_type}&filter_order=name",
            "filter_genre_add": [],
            "filter_genre_del": [],
        }

        payload = {
            "token": API_TOKEN,
            "pagina": str(page),
            "search": query,
            "limit": str(limit),
            "type": "lista",
            "filters": json.dumps(filters),
        }

        try:
            response = requests.post(
                API_URL, data=payload, headers=API_HEADERS, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # Parse HTML fragments from results
            results = self._parse_html_results(data.get("results", []))

            # Extract metadata
            metadata = {
                "page": data.get("page"),
                "total_results": data.get("total_results"),
                "total_page": data.get("total_page"),
            }

            return results, metadata

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ AnimesDigital API request failed for '{query}': {e}")
            return [], {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ AnimesDigital failed to parse API response for '{query}': {e}")
            return [], {}

    def _parse_html_results(self, html_fragments: list[str]) -> list[AnimeResult]:
        """Parse HTML fragments from API response.

        Each fragment is a <div class="itemA"> containing anime link and image.

        Args:
            html_fragments: List of HTML strings from API

        Returns:
            List of parsed anime results
        """
        results = []

        for html in html_fragments:
            try:
                soup = BeautifulSoup(html, "html.parser")

                # Find the link element
                link = soup.find("a", href=True)
                if not link:
                    continue

                url = link.get("href")
                title_elem = link.find("span", class_="title_anime")
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Find the image
                img = link.find("img")
                image = img.get("src") if img else ""

                if title and url:
                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "image": image,
                        }
                    )

            except Exception as e:
                logger.debug(f"Failed to parse HTML fragment: {e}")
                continue

        return results

    def search_anime(self, query: str) -> None:
        """Search for anime on AnimesDigital using the JSON API.

        Searches both dubbed and subtitled versions using the efficient
        /func/listanime endpoint. Much faster than browser automation.
        """
        search_configs = [
            ("legendado", "subtitled"),
            ("dublado", "dubbed"),
        ]

        all_anime = []

        try:
            for audio_type, audio_name in search_configs:
                logger.info(f"🔍 Searching {audio_name} anime for '{query}'")

                results, metadata = self._search_api(query, audio_type=audio_type)

                if not results:
                    logger.debug(f"No {audio_name} results found for '{query}'")
                    continue

                logger.info(
                    f"✅ Found {len(results)} {audio_name} results for '{query}' "
                    f"({metadata.get('total_results')} total)"
                )

                all_anime.extend(results)

        except Exception as e:
            logger.error(f"❌ AnimesDigital search failed for '{query}': {e}")
            return

        # Add anime to repository
        for anime in all_anime:
            rep.add_anime(anime["title"], anime["url"], AnimesDigital.name)

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

        episode_titles: list[str] = []
        episode_urls: list[str] = []

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
