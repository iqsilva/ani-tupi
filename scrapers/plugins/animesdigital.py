"""AnimesDigital scraper plugin.

CRITICAL REQUIREMENT: When fetching episode lists from AnimesDigital series pages,
the ?odr=1 parameter MUST be present in the URL. Without this parameter,
episodes will not be displayed on the page and cannot be fetched.

The parameter enables proper episode ordering from 1 to end.
"""

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
            "limit": "90",  # Fetch up to 90 episodes in one request (default API returns only 10)
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
        via JavaScript rendering. This is the most reliable approach because:
        1. We scrape the exact series URL, avoiding generic API search issues
        2. API search can return episodes from multiple series (e.g., "Sakamoto Days"
           returns both original + "Part 2", causing duplicates)
        3. DynamicFetcher with ?odr=1 is reliable and consistently finds all episodes

        Strategy:
        1. Use DynamicFetcher to scrape the series page directly (primary method)
        2. If scraping fails or finds few episodes, try API as fallback
        3. Supplement with homepage search for newly-published episodes
        """
        import re

        try:
            # Primary: Scrape the series page directly (most accurate)
            # CRITICAL: ?odr=1 parameter MUST be present to display all episodes
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

            # If we got episodes from scraping, we're done with primary method
            if episode_count > 0:
                # Supplement with homepage search for newly-published episodes
                try:
                    homepage_episodes = self.search_homepage_incremental(anime)
                    if homepage_episodes:
                        self._merge_homepage_episodes(anime, animesdigital_urls, homepage_episodes)
                except Exception as e:
                    logger.debug(f"Homepage search failed for '{anime}': {e}")
                return

            # If scraping found nothing, fallback to API search
            logger.debug(
                f"Series page scraping found no episodes for '{anime}'. Trying API fallback..."
            )

        except Exception as e:
            logger.debug(f"Series page scraping failed: {e}")

        # Fallback: Use API search (but be careful of duplicates)
        try:
            anime_slug_match = re.search(r"/anime/a/([^/?]+)", url)
            if not anime_slug_match:
                logger.error(f"Could not extract anime slug from URL: {url}")
                return

            anime_slug = anime_slug_match.group(1)
            anime_slug_clean = re.sub(r"-(dublado|legendado)$", "", anime_slug)
            search_words = anime_slug_clean.split("-")[:4]
            search_query = " ".join(search_words)

            from models.config import settings

            all_results = []
            preferred = settings.search.preferred_audio

            # Try preferred audio type first
            preferred_results = self._search_episodes_with_audio(search_query, preferred)
            if preferred_results:
                all_results = preferred_results
                logger.debug(
                    f"API search found {len(preferred_results)} {preferred} episodes for '{search_query}'"
                )

            # If few episodes, supplement with the other audio type
            if len(all_results) < 5:
                other_audio = "legendado" if preferred == "dublado" else "dublado"
                other_results = self._search_episodes_with_audio(search_query, other_audio)
                if other_results:
                    preferred_urls = {r["url"] for r in all_results}
                    new_episodes = [r for r in other_results if r["url"] not in preferred_urls]
                    if new_episodes:
                        all_results.extend(new_episodes)
                        logger.debug(
                            f"Supplemented with {len(new_episodes)} {other_audio} episodes (total: {len(all_results)})"
                        )

            if all_results:
                episode_titles = [ep["title"] for ep in all_results]
                episode_urls = [ep["url"] for ep in all_results]
                rep.add_episode_list(anime, episode_titles, episode_urls, AnimesDigital.name)

        except Exception as e:
            logger.error(f"AnimesDigital: both scraping and API search failed for '{anime}': {e}")
            return

        # Supplement with homepage search for newly-published episodes
        try:
            animesdigital_urls = []
            for urls_list, source in rep.anime_episodes_urls.get(anime, []):
                if source == AnimesDigital.name:
                    animesdigital_urls = list(urls_list)
                    break

            homepage_episodes = self.search_homepage_incremental(anime)
            if homepage_episodes and animesdigital_urls:
                self._merge_homepage_episodes(anime, animesdigital_urls, homepage_episodes)

        except Exception as e:
            logger.debug(f"Homepage search failed for '{anime}': {e}")

    def _merge_homepage_episodes(
        self, anime: str, current_urls: list[str], homepage_episodes: list[dict]
    ) -> None:
        """Merge homepage episodes with existing episodes, avoiding duplicates.

        Args:
            anime: Anime title
            current_urls: List of URLs already found
            homepage_episodes: Episodes from homepage search
        """
        try:
            # Create a set of all current URLs for deduplication
            current_urls_set = set(current_urls)

            # Find new episodes from homepage that aren't already indexed
            new_episodes = []
            for ep in homepage_episodes:
                if ep["episode_url"] not in current_urls_set:
                    new_episodes.append(ep)

            if new_episodes:
                logger.debug(f"Found {len(new_episodes)} new episodes from homepage for '{anime}'")

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

        except Exception as e:
            logger.debug(f"Error merging homepage episodes: {e}")

    def _parse_episode_results(self, html_fragments: list[str]) -> list[dict]:
        """Parse episode links from API HTML fragments.

        Args:
            html_fragments: List of HTML strings from API

        Returns:
            List of dicts with 'title' and 'url' keys, sorted by episode number
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

        Uses DynamicFetcher to render JavaScript and extract episodes.
        This is slower but works if the API fails.

        CRITICAL: The ?odr=1 parameter is REQUIRED. Without it, episodes
        disappear from the AnimesDigital series page and cannot be fetched.
        This parameter enables episode ordering from 1 to end.

        Args:
            anime: Anime title (needed to add episodes to repository)
            url: Series URL
        """
        import re
        from concurrent.futures import ThreadPoolExecutor
        import asyncio

        # REQUIRED: ?odr=1 parameter MUST be present to show all episodes
        # Without this parameter, the series page will NOT display episodes
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
        seen_urls = set()  # Track to avoid duplicates

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

                    # Skip duplicate URLs (in case DynamicFetcher finds duplicates)
                    if href in seen_urls:
                        continue

                    seen_urls.add(href)
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
                    matched_episodes.append(ep)

            # Sort by episode number to ensure correct order (1, 2, 3, ...)
            matched_episodes.sort(key=lambda ep: ep["episode_number"])

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
