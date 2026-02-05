import json
import logging
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from scrapling import DynamicFetcher

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
        self, query: str, page: int = 1, limit: int = 90, audio_type: str = "legendado"
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
            "legendado",
            "dublado",
        ]

        all_anime = []

        try:
            for audio_type in search_configs:
                results, _ = self._search_api(query, audio_type=audio_type)

                if not results:
                    continue

                all_anime.extend(results)

        except Exception as e:
            logger.error(f"❌ AnimesDigital search failed for '{query}': {e}")
            return

        # Add anime to repository
        for anime in all_anime:
            rep.add_anime(anime["title"], anime["url"], AnimesDigital.name)

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list using the API.

        AnimesDigital's series page (via DynamicFetcher) doesn't load all episodes.
        The /func/listanime API reliably returns all episodes for an anime.

        Strategy:
        1. Extract anime name from the series URL slug
        2. Query API with anime name (minimal params for best results)
        3. Parse results and extract episode URLs

        This avoids the dynamic loading issue while being faster and more reliable
        than trying to scrape the series page with JavaScript rendering.
        """
        import re

        # Extract anime slug from URL (e.g., /anime/a/yuusha-kei-ni-shosu-dublado)
        # Then convert back to searchable format
        anime_slug_match = re.search(r"/anime/a/([^/?]+)", url)
        if not anime_slug_match:
            # Fall back to scraping if we can't extract the slug
            self._scrape_series_page(anime, url)
            return

        anime_slug = anime_slug_match.group(1)
        # Remove audio type suffix (dublado/legendado) if present
        # e.g., "yuusha-kei-ni-shosu-dublado" -> "yuusha-kei-ni-shosu"
        anime_slug_clean = re.sub(r"-(dublado|legendado)$", "", anime_slug)

        # Convert slug to search term: replace hyphens with spaces
        # Keep season/number information (e.g., "jujutsu-kaisen-3" -> "jujutsu kaisen 3")
        search_words = anime_slug_clean.split("-")[:4]
        search_query = " ".join(search_words)

        try:
            # Search for episodes using API
            # API returns what it finds (usually dubbed versions are more complete)
            payload = {
                "token": API_TOKEN,
                "search": search_query,
                "type": "lista",
            }

            response = requests.post(
                API_URL, data=payload, headers=API_HEADERS, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            # Parse HTML fragments from results
            results = self._parse_episode_results(data.get("results", []))

            if not results:
                logger.debug(
                    f"No episodes found via API for '{search_query}'. Falling back to scraping series page."
                )
                # Fallback: try scraping the series page
                try:
                    self._scrape_series_page(anime, url)
                except Exception as e:
                    logger.debug(f"Series page scraping failed: {e}")
                # Don't return here - continue to homepage search for newly-published episodes

            episode_titles = [ep["title"] for ep in results]
            episode_urls = [ep["url"] for ep in results]

            # Add episodes to repository
            rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

        except Exception as e:
            logger.debug(f"AnimesDigital API search failed for '{search_query}': {e}")
            # Fallback to scraping
            try:
                self._scrape_series_page(anime, url)
            except Exception as scrape_error:
                logger.error(
                    f"AnimesDigital: both API and scraping failed for '{anime}': {scrape_error}"
                )
                return

        # After finding episodes via API or series page, supplement with homepage search
        # for newly-published episodes that may not yet be indexed on the series page
        try:
            homepage_episodes = self.search_homepage_incremental(anime)
            if homepage_episodes:
                # Get current AnimesDigital episodes (not from other sources!)
                animesdigital_urls = []
                for urls_list, source in rep.anime_episodes_urls.get(anime, []):
                    if source == AnimesDigital.name:
                        animesdigital_urls = list(urls_list)
                        break

                print(
                    f"[DEBUG homepage merge] AnimesDigital has {len(animesdigital_urls)} episodes"
                )

                # Extract all URLs currently in repository for this anime (all sources)
                current_urls = set()
                for urls_list, source in rep.anime_episodes_urls.get(anime, []):
                    current_urls.update(urls_list)

                # Add new episodes from homepage if not already present
                new_episodes = []
                for ep in homepage_episodes:
                    if ep["episode_url"] not in current_urls:
                        new_episodes.append(ep)

                if new_episodes:
                    logger.debug(
                        f"Found {len(new_episodes)} new episodes from homepage for '{anime}'"
                    )
                    # Build episode titles and URLs from homepage results
                    titles = []
                    urls = []
                    for ep in new_episodes:
                        # Get full title from homepage result
                        if ep.get("anime_title"):
                            title = f"{ep['anime_title']} Episódio {ep['episode_number']}"
                        else:
                            title = f"Episódio {ep['episode_number']}"
                        titles.append(title)
                        urls.append(ep["episode_url"])

                    if animesdigital_urls:
                        print(
                            f"[DEBUG homepage merge] Merging {len(titles)} new episodes with {len(animesdigital_urls)} existing"
                        )
                        # Merge: Generate titles for all AnimesDigital episodes (existing + new)
                        all_titles = []
                        for i in range(len(animesdigital_urls)):
                            all_titles.append(f"{anime} Episódio {i + 1}")
                        # Add new titles from homepage
                        all_titles.extend(titles)

                        # Combine URLs: existing AnimesDigital + new from homepage
                        all_urls = animesdigital_urls + urls

                        print(f"[DEBUG homepage merge] Adding {len(all_titles)} total episodes")
                        rep.add_episode_list(anime, all_titles, all_urls, AnimesDigital.name)
                    else:
                        # No existing AnimesDigital episodes, just add the homepage episodes
                        print(
                            f"[DEBUG homepage merge] No existing episodes, adding {len(titles)} from homepage"
                        )
                        rep.add_episode_list(anime, titles, urls, AnimesDigital.name)

        except Exception as e:
            logger.debug(f"Homepage search failed for '{anime}': {e}")

    def _parse_episode_results(self, html_fragments: list[str]) -> list[dict]:
        """Parse episode links from API HTML fragments.

        Args:
            html_fragments: List of HTML strings from API

        Returns:
            List of dicts with 'title' and 'url' keys
        """
        import re

        results = []
        seen_urls = set()  # Track to avoid duplicates

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

                if title and url and url not in seen_urls:
                    # Filter out special episodes (fractionated like 13.5, 0.5, etc)
                    if not re.search(r"Episódio\s+\d+\.\d+", title):
                        results.append({"title": title, "url": url})
                        seen_urls.add(url)

            except Exception as e:
                logger.debug(f"Failed to parse episode HTML fragment: {e}")
                continue

        return results

    def _scrape_series_page(self, anime: str, url: str) -> None:
        """Fallback method to scrape anime series page directly.

        Uses DynamicFetcher to render JavaScript and extract episodes.
        This is slower but works if the API fails.

        Args:
            anime: Anime title (needed to add episodes to repository)
            url: Series URL
        """
        import re
        from concurrent.futures import ThreadPoolExecutor
        import asyncio

        # Ensure ?odr=1 parameter is present to show all episodes
        if "?" in url:
            if "odr=" not in url:
                url = url + "&odr=1"
        else:
            url = url + "?odr=1"

        # Run DynamicFetcher in a thread pool to avoid asyncio loop conflicts
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context, use executor
            with ThreadPoolExecutor(max_workers=1) as executor:
                tree = loop.run_until_complete(
                    loop.run_in_executor(
                        executor,
                        lambda: DynamicFetcher.fetch(url, timeout=15000, browser="firefox"),
                    )
                )
        except RuntimeError:
            # No event loop running, call directly
            tree = DynamicFetcher.fetch(url, timeout=15000, browser="firefox")

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
                    if re.search(r"Episódio\s+\d+\.\d+", title):
                        continue  # Skip special episodes
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Add episodes to repository if found
        if episode_titles:
            rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)
        else:
            logger.warning(f"No episodes found for '{anime}' even with DynamicFetcher scraping")

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

    def search_homepage_incremental(self, title: str) -> list[dict]:
        """Search AnimesDigital homepage "últimos episódios" with incremental search.

        Fetches the homepage and searches the recent episodes section using an
        incremental search pattern: start with first word, add words until
        results <= 5 or all words exhausted.

        Args:
            title: Anime title to search (e.g., "Jujutsu Kaisen Season 2")

        Returns:
            List of dicts with keys: anime_title, episode_number, episode_url
            Empty list if no matches found or on error
        """
        import re
        from fuzzywuzzy import fuzz

        try:
            # Fetch homepage with requests first to get raw HTML
            # Use normal browser headers (not API headers) to get full HTML
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
            }
            response = requests.get(
                "https://animesdigital.org/home", headers=browser_headers, timeout=10
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find all episode links in homepage
            episode_links = soup.find_all("a", href=re.compile(r"/video/a/"))
            if not episode_links:
                logger.debug("No episode links found on AnimesDigital homepage")
                return []

            # Parse all episodes: extract title and URL
            all_episodes = []
            for link in episode_links:
                try:
                    url = link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://animesdigital.org{url}"

                    # Get title from img title attribute (contains "Anime Name Episódio XX")
                    img = link.find("img")
                    if not img:
                        continue

                    full_title = img.get("title", "")
                    if not full_title:
                        continue

                    # Parse: "Anime Name Episódio XX" -> extract episode number
                    match = re.search(r"Episódio\s+(\d+)", full_title)
                    if not match:
                        continue

                    episode_number = int(match.group(1))
                    # Extract anime name (everything before "Episódio")
                    anime_name = re.sub(r"\s*Episódio\s+\d+.*", "", full_title).strip()
                    # Remove "Assistir" prefix if present
                    anime_name = re.sub(r"^Assistir\s+", "", anime_name).strip()

                    if anime_name and episode_number > 0:
                        all_episodes.append(
                            {
                                "anime_title": anime_name,
                                "episode_number": episode_number,
                                "episode_url": url,
                            }
                        )

                except Exception as e:
                    logger.debug(f"Error parsing episode link: {e}")
                    continue

            if not all_episodes:
                logger.debug("No parseable episodes found on homepage")
                return []

            # Incremental search: normalize and match titles
            query_words = title.lower().split()
            matched_episodes = []

            for word_count in range(1, len(query_words) + 1):
                search_query = " ".join(query_words[:word_count])

                # Fuzzy match against all episodes
                for ep in all_episodes:
                    anime_title_normalized = ep["anime_title"].lower()

                    # Use partial_ratio for better partial matching
                    score = fuzz.partial_ratio(search_query, anime_title_normalized)

                    # Keep if score >= 70% (reasonable matching)
                    if score >= 70 and ep not in matched_episodes:
                        matched_episodes.append(ep)

                # If we have results <= 5, stop iterating words
                if len(matched_episodes) <= 5:
                    break

            # Filter to top 5 results by score
            if len(matched_episodes) > 5:
                # Re-score and sort by best match
                final_query = " ".join(query_words)
                scored = [
                    (
                        fuzz.partial_ratio(final_query, ep["anime_title"].lower()),
                        ep,
                    )
                    for ep in matched_episodes
                ]
                scored.sort(key=lambda x: x[0], reverse=True)
                matched_episodes = [ep for _, ep in scored[:5]]

            logger.debug(
                f"AnimesDigital homepage search for '{title}': found {len(matched_episodes)} episodes"
            )
            return matched_episodes

        except requests.exceptions.Timeout:
            logger.warning("AnimesDigital homepage fetch timed out")
            return []
        except Exception as e:
            logger.warning(f"Error searching AnimesDigital homepage: {e}")
            return []


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
