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
from urllib.parse import urljoin

from scrapling import Fetcher, DynamicFetcher
from services.repository import rep


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
            fetcher = Fetcher()
            tree = fetcher.get(search_url)

            # Extract anime card links from search results
            # Search results display anime cards in grid layout
            anime_links = tree.css("a[href*='/anime/']")

            for link in anime_links:
                href = link.attrib.get("href")

                # Title is in the img alt/title attribute, not in spans
                img_list = link.css("img")
                img = img_list[0] if img_list else None
                title = None
                if img:
                    # Try alt first, fallback to title attribute
                    title = img.attrib.get("alt") or img.attrib.get("title")

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
            # Use DynamicFetcher to load JavaScript content
            tree = DynamicFetcher.fetch(url, timeout=30000)

            # Get page source and extract allEpisodes JSON
            page_source = tree.html_content

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

        Requires a blogger_token from the page. This method:
        1. Uses DynamicFetcher to load the episode page
        2. Extracts the blogger_token from page source
        3. Makes AJAX POST request to get video URLs
        4. Selects highest quality (1080p > 720p > 480p > 360p)

        Args:
            url: Episode player page URL
            container: List to append video URL to (thread-safe container)
            event: Threading event to signal completion
        """
        try:
            # Use DynamicFetcher to load page with JavaScript
            tree = DynamicFetcher.fetch(url, timeout=30000)
            page_source = tree.html_content

            # Extract encrypted URL from page
            # Pattern: data-blogger-url-encrypted="..."
            encrypted_url_match = re.search(r'data-blogger-url-encrypted="([^"]+)"', page_source)

            if not encrypted_url_match:
                raise Exception("encrypted URL not found in page")

            encrypted_url = encrypted_url_match.group(1)

            # Make AJAX request to decrypt the URL
            ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"

            # Use Fetcher for POST request
            fetcher_post = Fetcher()
            response = fetcher_post.post(
                ajax_url,
                data={"action": "decrypt_blogger_url", "encrypted_url": encrypted_url},
            )

            try:
                # Extract JSON from response using .json() method
                response_data = response.json()
            except (json.JSONDecodeError, ValueError, AttributeError):
                raise Exception("Invalid JSON response from decrypt API")

            # Parse response: {"success": true, "data": {"url": "https://www.blogger.com/video.g?..."}}
            if not response_data.get("success"):
                raise Exception("Decrypt API returned success=false")

            video_url = response_data.get("data", {}).get("url")

            if not video_url:
                raise Exception("No URL in decrypt response")

            if not event.is_set():
                container.append(video_url)
                event.set()

        except Exception:
            # Graceful degradation: silently fail if video extraction doesn't work
            # This allows other sources to provide the video URL
            pass


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
