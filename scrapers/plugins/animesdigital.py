"""AnimesDigital scraper plugin.

CRITICAL REQUIREMENT: When fetching episode lists from AnimesDigital series pages,
the ?odr=1 parameter MUST be present in the URL. Without this parameter,
episodes will not be displayed on the page and cannot be fetched.

The parameter enables proper episode ordering from 1 to end.
"""

import json
import logging
import re
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

from scrapers.core.selenium_driver import SeleniumWebDriver
from scrapers.plugins.utils import load_plugin, store_player_source
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
        self, query: str, page: int = 1, limit: int = 200, audio_type: str = "legendado"
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

    def _normalize_title_for_slug(self, title: str) -> str:
        """Normalize title for slug generation.

        - Replace "2nd Season", "3rd Season", etc. → "2", "3"
        - Keep only letters and numbers
        - Replace spaces with hyphens
        - Lowercase

        Examples:
            "Jujutsu Kaisen 2nd Season" → "jujutsu-kaisen-2"
            "Attack on Titan Season 3" → "attack-on-titan-season-3"
            "Spy × Family" → "spy-family"
        """

        # Replace "Xnd Season", "Xst Season", "Xth Season", "Xrd Season" → " X"
        normalized = re.sub(
            r"\s+(\d+)(?:nd|st|th|rd)\s+season\b", r" \1", title, flags=re.IGNORECASE
        )

        # Also handle "Season X" format → " X"
        normalized = re.sub(r"\bseason\s+(\d+)\b", r"\1", normalized, flags=re.IGNORECASE)

        # Keep only letters, numbers, and spaces
        normalized = re.sub(r"[^a-zA-Z0-9\s]", "", normalized)

        # Clean up extra spaces
        normalized = " ".join(normalized.split())

        # Replace spaces with hyphens and lowercase
        slug = normalized.lower().replace(" ", "-")

        return slug

    def _extract_series_url(self, episode_url: str) -> str | None:
        """Extract the anime series URL from an episode page.

        Episode pages contain a navigation link back to the series page.
        Looks for: div.epsL a[href*='/anime/a/']

        Args:
            episode_url: URL like https://animesdigital.org/video/a/133808/

        Returns:
            Series URL like https://animesdigital.org/anime/a/ikoku-nikki, or None
        """
        BROWSER_HEADERS = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://animesdigital.org",
        }
        try:
            resp = requests.get(episode_url, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for back-link in div.epsL navigation
            link = soup.select_one("div.epsL a[href*='/anime/a/']")
            if link:
                href = link.get("href")
                # Ensure it's a full URL
                if href and not href.startswith("http"):
                    href = f"https://animesdigital.org{href}"
                return href
        except Exception as e:
            logger.debug(f"Failed to extract series URL from {episode_url}: {e}")
        return None

    def search_anime(self, query: str) -> None:
        """Search for anime on AnimesDigital using incremental search.

        Search order:
        1. API incremental (1 word → 2 words → ... → all words) for both audio types
        2. Homepage incremental (same pattern) for both audio types
        3. Slug search (complete query) for both audio types

        When multiple versions (legendado/dublado) are found, adds both to repository
        as separate entries so user can choose which version to watch.
        """
        all_anime: dict[str, dict] = {}  # Map: normalized_title -> {legendado, dublado URLs}

        # Step 1: Incremental API search
        logger.debug(f"Starting incremental API search for '{query}'...")
        query_words = query.lower().split()

        for word_count in range(1, len(query_words) + 1):
            incremental_query = " ".join(query_words[:word_count])
            logger.debug(f"API incremental search ({word_count} words): '{incremental_query}'")

            try:
                for audio_type in ["legendado", "dublado"]:
                    results, _ = self._search_api(incremental_query, audio_type=audio_type)
                    if not results:
                        continue

                    for result in results:
                        title = result["title"]
                        url = result["url"]
                        image = result.get("image", "")

                        # Normalize title for grouping (remove audio markers)
                        normalized = title.replace(" Dublado", "").replace(" dublado", "").strip()

                        if normalized not in all_anime:
                            all_anime[normalized] = {
                                "base_title": normalized,
                                "legendado": None,
                                "dublado": None,
                                "image": image,
                            }

                        if audio_type == "dublado":
                            all_anime[normalized]["dublado"] = url
                        else:
                            all_anime[normalized]["legendado"] = url

            except Exception as e:
                logger.error(f"❌ AnimesDigital API search failed for '{incremental_query}': {e}")
                continue

        # Step 2: Incremental homepage search
        logger.debug(f"Starting incremental homepage search for '{query}'...")

        for word_count in range(1, len(query_words) + 1):
            incremental_query = " ".join(query_words[:word_count])
            logger.debug(f"Homepage incremental search ({word_count} words): '{incremental_query}'")

            # Try both legendado and dublado on homepage
            for audio_type in ["legendado", "dublado"]:
                homepage_results = self.search_homepage_incremental(
                    incremental_query, audio_type=audio_type
                )

                if homepage_results:
                    # Group by anime_title (one entry per anime)
                    seen_titles: set[str] = set()
                    for ep in homepage_results:
                        title = ep.get("anime_title", "")
                        episode_url = ep.get("episode_url", "")
                        if not title or not episode_url or title in seen_titles:
                            continue
                        seen_titles.add(title)

                        series_url = self._extract_series_url(episode_url)
                        if series_url:
                            logger.debug(f"Homepage search found: '{title}' -> {series_url}")

                            # Normalize title for grouping
                            normalized = (
                                title.replace(" Dublado", "").replace(" dublado", "").strip()
                            )

                            if normalized not in all_anime:
                                all_anime[normalized] = {
                                    "base_title": normalized,
                                    "legendado": None,
                                    "dublado": None,
                                    "image": "",
                                }

                            if audio_type == "dublado":
                                all_anime[normalized]["dublado"] = series_url
                            else:
                                all_anime[normalized]["legendado"] = series_url
                        else:
                            logger.debug(
                                f"Could not extract series URL for '{title}' from {episode_url}"
                            )

        # Step 3: Complete slug search (using FULL query, not partial)
        if not all_anime:
            logger.debug("No results from API/homepage, trying complete slug search...")

            # Normalize complete query to slug
            complete_slug = self._normalize_title_for_slug(query)
            logger.debug(f"Complete slug from '{query}': {complete_slug}")

            for audio_type in ["legendado", "dublado"]:
                slug = complete_slug if audio_type == "legendado" else f"{complete_slug}-dublado"
                url = f"https://animesdigital.org/anime/a/{slug}"

                try:
                    logger.debug(f"Trying complete slug: {url}")
                    from concurrent.futures import ThreadPoolExecutor
                    import asyncio

                    if "?" in url:
                        if "odr=" not in url:
                            url = url + "&odr=1"
                    else:
                        url = url + "?odr=1"

                    try:
                        loop = asyncio.get_running_loop()
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            tree = loop.run_until_complete(
                                loop.run_in_executor(
                                    executor,
                                    lambda: SeleniumWebDriver().fetch(url),
                                )
                            )
                    except RuntimeError:
                        tree = SeleniumWebDriver().fetch(
                            url.replace("?odr=1", "").replace("&odr=1", "")
                        )

                    # Check if page has episodes (if it exists)
                    episode_divs = tree.select("div.item_ep")
                    if episode_divs:
                        logger.debug(f"Complete slug found episodes: {url}")

                        if query not in all_anime:
                            all_anime[query] = {
                                "base_title": query,
                                "legendado": None,
                                "dublado": None,
                                "image": "",
                            }

                        if audio_type == "dublado":
                            all_anime[query]["dublado"] = url
                        else:
                            all_anime[query]["legendado"] = url

                except Exception as e:
                    logger.debug(f"Complete slug failed for '{slug}': {e}")
                    continue

        # Deduplicate by URL before adding to repository
        # Some anime might be found from multiple sources (API + homepage) with same URL
        seen_urls: set[str] = set()
        deduplicated_anime: dict[str, dict] = {}

        for normalized_title, data in all_anime.items():
            legendado_url = data["legendado"]
            dublado_url = data["dublado"]

            # Only keep URLs we haven't seen before
            should_keep_legendado = legendado_url and legendado_url not in seen_urls
            should_keep_dublado = dublado_url and dublado_url not in seen_urls

            if should_keep_legendado:
                seen_urls.add(legendado_url)

            if should_keep_dublado:
                seen_urls.add(dublado_url)

            # Only add to deduplicated if at least one version is unique
            if should_keep_legendado or should_keep_dublado:
                deduplicated_anime[normalized_title] = {
                    "base_title": data["base_title"],
                    "image": data["image"],
                    "legendado": legendado_url if should_keep_legendado else None,
                    "dublado": dublado_url if should_keep_dublado else None,
                }

        # Add all deduplicated anime to repository
        for normalized_title, data in deduplicated_anime.items():
            # Add legendado version if found
            if data["legendado"]:
                title = data["base_title"]
                rep.add_anime(title, data["legendado"], AnimesDigital.name)
                logger.debug(f"Added legendado: '{title}' -> {data['legendado']}")

            # Add dublado version if found (with " Dublado" suffix)
            if data["dublado"]:
                title = f"{data['base_title']} Dublado"
                rep.add_anime(title, data["dublado"], AnimesDigital.name)
                logger.debug(f"Added dublado: '{title}' -> {data['dublado']}")

    def _search_episodes_with_audio(
        self, search_query: str, audio_type: str = "dublado"
    ) -> list[dict]:
        """Search for episodes with a specific audio type.

        Args:
            search_query: Anime search term
            audio_type: "dublado" or "legendado"

        Returns:
            List of dicts with 'title' and 'url' keys
        """
        payload = {
            "token": API_TOKEN,
            "search": search_query,
            "type": "lista",
            "filter_audio": audio_type,
            "limit": "200",  # Fetch up to 200 episodes in one request (default API returns only 10)
        }

        try:
            response = requests.post(
                API_URL, data=payload, headers=API_HEADERS, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            results = self._parse_episode_results(data.get("results", []))
            return results
        except Exception as e:
            logger.debug(f"Search failed for audio_type={audio_type}: {e}")
            return []

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list by scraping the series page directly.

        AnimesDigital's series page (with ?odr=1 parameter) loads all episodes
        via JavaScript rendering. This is the most reliable approach.

        Attempts to fetch episodes from the provided URL, then supplements with
        homepage search to catch newly-published episodes.

        CRITICAL: ?odr=1 parameter MUST be present to display all episodes
        """
        try:
            logger.debug(f"Scraping AnimesDigital series page for '{anime}'...")
            self._scrape_series_page(anime, url)

            # Check how many episodes were found
            animesdigital_urls = []
            for urls_list, source in rep.anime_episodes_urls.get(anime, []):
                if source == AnimesDigital.name:
                    animesdigital_urls = list(urls_list)
                    break

            episode_count = len(animesdigital_urls)
            logger.debug(f"Series page scraping found {episode_count} episodes for '{anime}'")

            if episode_count == 0:
                logger.debug(f"No episodes found for '{anime}' in series page scraping")

            # Step 2: Supplement with homepage search for newly-published episodes
            # Homepage "Últimos Episódios" may have episodes not yet on the series page
            logger.debug(f"Searching AnimesDigital homepage for new episodes of '{anime}'...")
            # Detect audio type based on anime title
            audio_type = "dublado" if "dublado" in anime.lower() else "legendado"
            homepage_episodes = self.search_homepage_incremental(anime, audio_type=audio_type)

            if homepage_episodes:
                logger.debug(f"Found {len(homepage_episodes)} episodes on homepage for '{anime}'")
                # Max episode on page is the count (episodes are numbered 1 to N sequentially)
                max_episode_on_page = len(animesdigital_urls)
                self._merge_homepage_episodes(
                    anime, animesdigital_urls, homepage_episodes, max_episode_on_page
                )
            else:
                logger.debug(f"No new episodes found on homepage for '{anime}'")

        except Exception as e:
            logger.debug(f"AnimesDigital series page scraping failed for '{anime}': {e}")

    def _merge_homepage_episodes(
        self,
        anime: str,
        current_urls: list[str],
        homepage_episodes: list[dict],
        max_episode_on_page: int = 0,
    ) -> None:
        """Merge homepage episodes with existing episodes, avoiding duplicates.

        Only includes homepage episodes with episode_number > max_episode_on_page
        to ensure homepage supplements with newer episodes only.

        Args:
            anime: Anime title
            current_urls: List of URLs already found
            homepage_episodes: Episodes from homepage search
            max_episode_on_page: Maximum episode number found on series page
        """
        try:
            # Create a set of all current URLs for deduplication
            current_urls_set = set(current_urls)

            # Find new episodes from homepage that:
            # 1. Aren't already indexed (URL check)
            # 2. Have episode number > max on series page (newer episodes only)
            new_episodes = []
            for ep in homepage_episodes:
                if (
                    ep["episode_url"] not in current_urls_set
                    and ep["episode_number"] > max_episode_on_page
                ):
                    new_episodes.append(ep)

            if new_episodes:
                logger.debug(
                    f"Found {len(new_episodes)} new episodes from homepage for '{anime}' "
                    f"(episode number > {max_episode_on_page})"
                )

                # Build episode titles and URLs from new homepage results
                new_titles = []
                new_urls = []
                for ep in new_episodes:
                    if ep.get("anime_title"):
                        title = f"{ep['anime_title']} Episódio {ep['episode_number']}"
                    else:
                        title = f"Episódio {ep['episode_number']}"
                    new_titles.append(title)
                    new_urls.append(ep["episode_url"])

                # Merge: Keep all existing episodes + add new ones from homepage
                all_titles = []
                for i in range(len(current_urls)):
                    all_titles.append(f"{anime} Episódio {i + 1}")
                all_titles.extend(new_titles)

                all_urls = current_urls + new_urls
                rep.add_episode_list(anime, all_titles, all_urls, AnimesDigital.name)
            else:
                logger.debug(
                    f"No new episodes from homepage for '{anime}' "
                    f"(all homepage episodes <= {max_episode_on_page})"
                )

        except Exception as e:
            logger.debug(f"Error merging homepage episodes: {e}")

    def _parse_episode_results(self, html_fragments: list[str]) -> list[dict]:
        """Parse episode links from API HTML fragments.

        Args:
            html_fragments: List of HTML strings from API

        Returns:
            List of dicts with 'title' and 'url' keys, sorted by episode number
        """

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
                        # Extract episode number for sorting
                        ep_match = re.search(r"Episódio\s+(\d+)", title)
                        ep_number = int(ep_match.group(1)) if ep_match else float("inf")
                        results.append({"title": title, "url": url, "_ep_number": ep_number})
                        seen_urls.add(url)

            except Exception as e:
                logger.debug(f"Failed to parse episode HTML fragment: {e}")
                continue

        # Sort by episode number to ensure correct order (1, 2, 3, ...)
        results.sort(key=lambda x: x["_ep_number"])
        # Remove temporary sort key
        for r in results:
            del r["_ep_number"]

        return results

    def _scrape_series_page(self, anime: str, url: str) -> None:
        """Fallback method to scrape anime series page directly.

        Uses static HTML parsing to extract episodes from the series page.

        CRITICAL: The ?odr=1 parameter is REQUIRED. Without it, episodes
        disappear from the AnimesDigital series page and cannot be fetched.
        This parameter enables episode ordering from 1 to end.

        Args:
            anime: Anime title (needed to add episodes to repository)
            url: Series URL
        """
        # REQUIRED: ?odr=1 parameter MUST be present to show all episodes
        # Without this parameter, the series page will NOT display episodes
        if "?" in url:
            if "odr=" not in url:
                url = url + "&odr=1"
        else:
            url = url + "?odr=1"

        browser_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Referer": "https://animesdigital.org",
        }
        response = requests.get(url, headers=browser_headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        tree = BeautifulSoup(response.text, "html.parser")

        # Find all episode containers
        episode_divs = tree.select("div.item_ep")

        episode_titles: list[str] = []
        episode_urls: list[str] = []
        seen_urls = set()  # Track to avoid duplicates

        for ep_div in episode_divs:
            # Find the link inside the episode div for the URL
            link = ep_div.select_one("a")
            if not link:
                continue
            href = link.get("href")

            # Get episode title from .title_anime class (avoids metadata like "9 meses atrás")
            title_elem = ep_div.select_one(".title_anime")
            if title_elem and href:
                title = str(title_elem.text).strip()
                # Clean up extra whitespace
                title = " ".join(title.split())
                if title:
                    # Filter out special episodes (fractionated like 13.5, 0.5, etc)
                    if re.search(r"Episódio\s+\d+\.\d+", title):
                        continue  # Skip special episodes

                    # Skip duplicate URLs in case the page repeats entries.
                    if href in seen_urls:
                        continue

                    seen_urls.add(href)
                    episode_urls.append(href)
                    episode_titles.append(title)

        # Add episodes to repository if found
        if episode_titles:
            rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)
        else:
            logger.debug(f"No episodes found for '{anime}' in series page scraping")

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract actual video source URLs from AnimesDigital episode page.

        Extracts direct video sources (HLS m3u8, MP4) instead of just iframes.
        Uses regex to find video URLs and returns the best available source.

        Priority order:
        1. HLS streams (api.anivideo.net) - adaptive bitrate, best quality
        2. Decoded MP4 sources - direct playback fallback
        3. Encoded MP4 sources - obfuscated playback fallback
        """
        import html

        try:
            # Fetch HTML content with requests to get raw HTML for regex extraction
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
            }
            response = requests.get(url, headers=browser_headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            html_content = response.text

            video_sources = {
                "hls": None,
                "mp4_decoded": None,
                "mp4_encoded": None,
            }

            # Extract HLS stream (Player FHD - api.anivideo.net)
            # The proxy URL contains the real video URL: https://api.anivideo.net/videohls.php?d=REAL_URL
            # Extract REAL_URL from the d= parameter instead of using the proxy URL
            hls_match = re.search(
                r'https://api\.anivideo\.net/videohls\.php\?d=([^"<>&\s]+)', html_content
            )
            if hls_match:
                # Extract the actual video URL from the d= parameter (group 1)
                real_video_url = hls_match.group(1)
                # Unescape HTML entities (&amp; → &, etc)
                real_video_url = html.unescape(real_video_url)
                video_sources["hls"] = real_video_url

            # Extract MP4 sources
            mp4_matches = re.findall(r'https://[^"<>\s]+\.mp4(?:[^\s"<>]*)?', html_content)

            for mp4_url in mp4_matches:
                # Check if encoded (animesdigital.org with base64)
                if "animesdigital.org/" in mp4_url and "aHR0cHM6Ly9" in mp4_url:
                    video_sources["mp4_encoded"] = mp4_url

                    # Try to decode base64 part
                    match = re.search(r"animesdigital\.org/([A-Za-z0-9+/]+={0,2})/", mp4_url)
                    if match:
                        try:
                            import base64

                            encoded = match.group(1)
                            decoded = base64.b64decode(encoded).decode("utf-8")
                            video_sources["mp4_decoded"] = decoded
                        except Exception:
                            pass  # Keep encoded version as fallback
                    break

            # Select best source and add to container
            selected_url = None
            if video_sources["hls"]:
                selected_url = video_sources["hls"]
            elif video_sources["mp4_decoded"]:
                selected_url = video_sources["mp4_decoded"]
            elif video_sources["mp4_encoded"]:
                selected_url = video_sources["mp4_encoded"]

            if selected_url:
                if store_player_source(container, event, selected_url):
                    return

            # Fallback: Try iframe method if no direct sources found
            logger.debug("No direct video sources found, falling back to iframe method")
            self._extract_iframe_src(html_content, container, event)

        except Exception as e:
            msg = f"Could not extract video from AnimesDigital: {e}"
            raise Exception(msg) from e

    def _extract_iframe_src(self, html_content: str, container: list, event) -> None:
        """Fallback method to extract iframe src when direct sources not available.

        Args:
            html_content: Page HTML content
            container: List to append video URL to
            event: Threading event to signal completion
        """

        try:
            # Look for iframe src patterns
            iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_content)

            for src in iframe_matches:
                # Prioritize api.anivideo
                if "api.anivideo" in src:
                    if store_player_source(container, event, src):
                        return

            # Use any iframe as fallback
            if iframe_matches:
                store_player_source(container, event, iframe_matches[0])

        except Exception as e:
            logger.debug(f"Could not extract iframe src: {e}")

    def search_homepage_incremental(self, title: str, audio_type: str = "legendado") -> list[dict]:
        """Search AnimesDigital homepage "últimos episódios" with incremental search.

        Fetches the homepage and searches the recent episodes section using an
        incremental search pattern: start with first word, add words until
        results <= 5 or all words exhausted.

        Args:
            title: Anime title to search (e.g., "Jujutsu Kaisen Season 2")
            audio_type: Audio type to filter ("dublado" or "legendado")

        Returns:
            List of dicts with keys: anime_title, episode_number, episode_url
            Filtered to include only episodes matching the specified audio_type
            Empty list if no matches found or on error
        """
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
            seen_urls = set()  # Track URLs to avoid duplicates
            for link in episode_links:
                try:
                    url = link.get("href", "")
                    if not url.startswith("http"):
                        url = f"https://animesdigital.org{url}"

                    # Skip if we've already seen this URL
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

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
            # Strategy: keep adding words until we find exact/near-exact matches
            query_words = title.lower().split()
            matched_episodes = []
            best_matches = []  # Track the highest-scoring matches

            for word_count in range(1, len(query_words) + 1):
                search_query = " ".join(query_words[:word_count])
                current_matches = []

                # Score all episodes against current search query
                for ep in all_episodes:
                    anime_title_normalized = ep["anime_title"].lower()

                    # Use different matching strategies based on search length:
                    # - Single word: use partial_ratio (matches "jujutsu" in "Jujutsu Kaisen...")
                    # - Multiple words: use ratio which handles partial sequences better
                    if word_count == 1:
                        # Single word: be lenient to catch keywords
                        score = fuzz.partial_ratio(search_query, anime_title_normalized)
                        threshold = 70
                    else:
                        # Multiple words: use ratio for partial title matching
                        # Also try partial_ratio and keep the best score
                        ratio_score = fuzz.ratio(search_query, anime_title_normalized)
                        partial_score = fuzz.partial_ratio(search_query, anime_title_normalized)
                        score = max(ratio_score, partial_score)
                        threshold = 65  # Slightly lower to catch good partial matches

                    if score >= threshold:
                        current_matches.append((score, ep))

                if current_matches:
                    # Sort by score (best matches first)
                    current_matches.sort(key=lambda x: x[0], reverse=True)
                    # Update best matches - keep replacing until we stabilize
                    best_matches = current_matches

                    # If top match has very high confidence or we've used all words, stop
                    # Single word: need >90%, Multiple words: need >95%
                    top_score = best_matches[0][0]
                    stop_threshold = 90 if word_count == 1 else 95
                    if top_score > stop_threshold or word_count == len(query_words):
                        break

            # Extract top 5 episodes from best matches
            # But also filter out weak matches: require final full-title match >= 75%
            matched_episodes = []
            final_query = " ".join(query_words).lower()

            for _, ep in best_matches[:5]:
                # Re-score with full query to avoid weak partial matches
                final_score = max(
                    fuzz.ratio(final_query, ep["anime_title"].lower()),
                    fuzz.partial_ratio(final_query, ep["anime_title"].lower()),
                )
                # Only keep if final score is acceptable (75%+)
                if final_score >= 75:
                    matched_episodes.append((final_score, ep["anime_title"], ep))

            # FIRST: Filter by audio type (dublado vs legendado)
            # This must happen BEFORE selecting best_anime to ensure we compare
            # only episodes of the requested audio type
            #
            # Important: In practice, "Legendado" is the default (no marker needed).
            # - Dublado episodes ALWAYS have "Dublado" in the title
            # - Legendado episodes usually DON'T have "Legendado" in the title
            if matched_episodes:
                filtered = []
                for score, anime_title, ep in matched_episodes:
                    episode_title_lower = ep["anime_title"].lower()

                    if audio_type == "dublado":
                        # For Dublado: ONLY accept episodes with "Dublado" explicitly
                        if "dublado" in episode_title_lower:
                            filtered.append((score, anime_title, ep))
                    else:  # legendado (default)
                        # For Legendado: Accept episodes WITHOUT "Dublado"
                        # This includes:
                        # - Episodes with "Legendado" explicit marker
                        # - Episodes without any marker (default = legendado)
                        if "dublado" not in episode_title_lower:
                            filtered.append((score, anime_title, ep))

                matched_episodes = filtered

            # SECOND: Select best_anime from the filtered results
            # Track best score for each unique anime (after audio filtering)
            if matched_episodes:
                anime_scores = {}
                for score, anime_title, ep in matched_episodes:
                    if anime_title not in anime_scores or score > anime_scores[anime_title]:
                        anime_scores[anime_title] = score

                # Find the anime with the highest score
                best_anime = max(anime_scores.items(), key=lambda x: x[1])[0]
                # Keep only episodes from the best-matching anime
                matched_episodes = [ep for _, anime, ep in matched_episodes if anime == best_anime]
            else:
                # Convert to plain episode list if empty
                matched_episodes = []

            # Sort by episode number to ensure correct order (1, 2, 3, ...)
            matched_episodes.sort(key=lambda ep: ep["episode_number"])

            logger.debug(
                f"AnimesDigital homepage search for '{title}': found {len(matched_episodes)} episodes"
            )
            return matched_episodes

        except requests.exceptions.Timeout:
            logger.debug("AnimesDigital homepage fetch timed out")
            return []
        except Exception as e:
            logger.debug(f"Error searching AnimesDigital homepage: {e}")
            return []


def load() -> None:
    """Load plugin."""
    load_plugin(AnimesDigital, rep.register)
