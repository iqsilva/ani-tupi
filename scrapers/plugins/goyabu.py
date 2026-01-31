"""Goyabu anime scraper plugin for https://goyabu.io

Goyabu is a Brazilian Portuguese anime streaming site with HD video support.
This plugin implements search, episode extraction, and HD video source discovery.

Site Structure:
- Search: WordPress standard search via ?s=query parameter
- Episodes: JavaScript inline array (const allEpisodes = [...]) in HTML
- Player: JWPlayer 8 with Blogger video CDN
- Video Sources: Fetched via AJAX POST to decode_blogger_video endpoint

HD Quality Strategy:
- AJAX response provides array of quality options (720p HD, 360p SD, etc.)
- Selects highest priority quality: 1080p > 720p > 480p > 360p
- Video URLs expire within minutes (contain timestamp parameters)
"""

import json
import re
from selectolax.parser import HTMLParser
from urllib.parse import urljoin

from scrapers.core.browser_pool import get_browser_pool
from scrapers.plugins.utils import get_with_retry
from services.repository import rep

REQUEST_TIMEOUT = 30  # seconds


class Goyabu:
    """Goyabu.io anime scraper plugin."""

    languages = ["pt-br"]
    name = "goyabu"
    base_url = "https://goyabu.io"

    def search_anime(self, query: str) -> None:
        """Search for anime on Goyabu using WordPress search.

        Constructs search URL with query parameter and extracts anime titles,
        URLs, cover images, and ratings from search result cards.

        Args:
            query: Anime title to search for (e.g., "jujutsu kaisen")
        """
        try:
            # Use WordPress search parameter
            search_url = f"{self.base_url}/?s={'+'.join(query.split())}"
            response = get_with_retry(search_url, timeout=REQUEST_TIMEOUT)
            tree = HTMLParser(response.text)

            # Extract anime card links from search results
            # Search results display anime cards in grid layout
            anime_links = tree.css("a[href*='/anime/']")

            for link in anime_links:
                href = link.attributes.get("href")

                # Title is in the img alt/title attribute, not in spans
                img = link.css_first("img")
                title = None
                if img:
                    # Try alt first, fallback to title attribute
                    title = img.attributes.get("alt") or img.attributes.get("title")

                if href and title:
                    # Clean up title
                    title = " ".join(title.split())
                    rep.add_anime(title, href, self.name)

        except Exception:
            # Graceful degradation: return without adding anime
            # This allows other plugins to provide results
            pass

    def search_episodes(self, anime: str, url: str, params: dict | None) -> None:
        """Fetch episode list from anime detail page.

        Episodes are stored as JSON in const allEpisodes = [...] in the HTML.
        Extracts the JSON array using regex pattern matching.

        Args:
            anime: Anime title
            url: Anime detail page URL
            params: Optional parameters (e.g., dubbed status from search)
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.wait import WebDriverWait

            with get_browser_pool().get_browser() as driver:
                driver.get(url)

                # Wait for page to load
                WebDriverWait(driver, REQUEST_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, "//*"))
                )

                # Get page source and extract allEpisodes JSON
                page_source = driver.page_source

                # Pattern: const allEpisodes = [...]
                match = re.search(
                    r"const allEpisodes\s*=\s*(\[[^\]]*(?:\{[^}]*\}[^\]]*)*\])", page_source
                )

                if not match:
                    return

                try:
                    # Extract and parse JSON
                    json_str = match.group(1)
                    episodes_data = json.loads(json_str)
                except (json.JSONDecodeError, ValueError):
                    return

                if not episodes_data:
                    return

                episode_titles = []
                episode_urls = []

                for ep in episodes_data:
                    ep_num = ep.get("episodio", "")
                    ep_title = ep.get("episode_name", "") or f"Episódio {ep_num}"
                    ep_link = ep.get("link", "")

                    if ep_link:
                        # Convert relative URL to absolute
                        ep_url = urljoin(self.base_url, ep_link)
                        episode_titles.append(ep_title)
                        episode_urls.append(ep_url)

                # Add episodes to repository
                if episode_urls:
                    rep.add_episode_list(anime, episode_titles, episode_urls, self.name)

        except Exception:
            # Graceful degradation: return without adding episodes
            pass

    def search_player_src(self, url: str, container: list, event) -> None:
        """Extract HD video source from episode player.

        Goyabu uses JWPlayer 8 with Blogger video CDN. Video sources are fetched
        via AJAX POST to wp-admin/admin-ajax.php?action=decode_blogger_video.

        The AJAX response contains an array of quality options with labels and URLs.
        This method selects the highest quality available (1080p > 720p > 480p > 360p).

        Args:
            url: Episode player page URL
            container: List to append video URL to (thread-safe container)
            event: Threading event to signal completion
        """
        try:
            from playwright.sync_api import sync_playwright

            video_url = None

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Listen for AJAX responses containing video sources
                def handle_response(response):
                    nonlocal video_url
                    if "decode_blogger_video" in response.url:
                        try:
                            data = response.json()
                            # AJAX response is an array of quality objects
                            if isinstance(data, list):
                                video_url = self._select_best_quality(data)
                        except Exception:
                            pass

                page.on("response", handle_response)

                # Navigate to episode page
                page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)

                # If AJAX response was captured, we have the video URL
                if video_url:
                    if not event.is_set():
                        container.append(video_url)
                        event.set()
                    browser.close()
                    return

                # Fallback: try to extract video URL from player context
                try:
                    video_url = page.evaluate("""
                        () => {
                            // Try to get from JWPlayer instance
                            if (window.jwplayer && window.jwplayer().getPlaylist) {
                                const playlist = window.jwplayer().getPlaylist();
                                if (playlist && playlist[0] && playlist[0].sources) {
                                    const best = playlist[0].sources.reduce((prev, current) => {
                                        const prevQuality = parseInt(prev.label) || 0;
                                        const currQuality = parseInt(current.label) || 0;
                                        return currQuality > prevQuality ? current : prev;
                                    });
                                    return best.file;
                                }
                            }
                            return '';
                        }
                    """)

                    if video_url and not event.is_set():
                        container.append(video_url)
                        event.set()

                except Exception:
                    pass

                browser.close()

                if not event.is_set():
                    raise Exception("Failed to extract video source from Goyabu player")

        except Exception as e:
            raise Exception(f"Failed to extract video from Goyabu: {str(e)}")

    def _select_best_quality(self, sources: list[dict]) -> str:
        """Select highest quality video URL from AJAX response.

        Args:
            sources: Array of video source objects with 'label' and 'file' keys

        Returns:
            Video URL of highest priority quality, or first source URL as fallback
        """
        quality_priority = ["1080p", "720p", "480p", "360p"]
        original_url = None

        for source in sources:
            source_label = source.get("label", "").lower()
            source_file = source.get("file")

            # Store original (first) URL with valid file as ultimate fallback
            if original_url is None and source_file:
                original_url = source_file

            # Try to match priority order
            for priority_quality in quality_priority:
                if priority_quality in source_label and source_file:
                    return source_file

        # Fallback: return first/original URL if no priority match
        return original_url if original_url else ""


def load(languages_dict) -> None:
    """Load plugin if language is supported.

    Called by plugin loader to register this plugin for supported languages.
    Currently supports Portuguese (Brazil) only.

    Args:
        languages_dict: Dictionary of supported languages for current session
    """
    can_load = False
    for language in Goyabu.languages:
        if language in languages_dict:
            can_load = True
            break
    if not can_load:
        return
    rep.register(Goyabu())
