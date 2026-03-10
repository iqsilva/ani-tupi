"""
TopAnimes.net Scraper Plugin

Brazilian Portuguese anime streaming site using DooPlayer.
Supports search, episode extraction, and video URL discovery.

This plugin implements the ani-tupi scraper interface with three methods:
- search_anime(query): Find anime and register with repository
- search_episodes(anime, url, params): Extract episodes
- search_player_src(url, container, event): Extract video URLs
"""

import asyncio
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright  # type: ignore[import-untyped]
from services.repository import rep


class TopanimesScraper:
    """TopAnimes.net anime scraper with video extraction"""

    BASE_URL = "https://topanimes.net"
    name = "topanimes"
    languages = ["pt-br"]  # Brazilian Portuguese

    def search_anime(self, query: str) -> None:
        """
        Search for anime on topanimes.net and register results with repository

        Args:
            query: Anime name or partial title (e.g., "jujutsu kaisen")
        """
        try:
            search_url = f"{self.BASE_URL}/?s={query.replace(' ', '+')}"

            # Fetch HTML directly (no Playwright needed for search)
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            anime_links = soup.select('a[href*="/animes/"]')

            seen_urls = set()

            for link in anime_links:
                href = link.get("href")
                title = link.get_text(strip=True)

                # Filter valid anime links and skip duplicates
                if not href or "/animes/" not in href:
                    continue
                if href in seen_urls:
                    continue

                title = title.strip() if title else "Unknown"

                # Skip navigation items
                if title in ["TV", "Filme", "OVA", "Especial"] or title.isdigit():
                    continue

                seen_urls.add(href)

                # Register anime with repository
                rep.add_anime(title, href, self.name)

                # Limit results to 10
                if len(seen_urls) >= 10:
                    break

        except Exception as e:
            print(f"Error searching TopAnimes: {e}")

    def search_episodes(self, anime: str, url: str, params: dict | None = None) -> None:
        """
        Extract episodes from anime page and register with repository

        Args:
            anime: Anime title
            url: URL to anime page
            params: Optional parameters (ignored)
        """
        try:
            asyncio.run(self._async_search_episodes(anime, url))
        except Exception as e:
            print(f"Error getting episodes from TopAnimes: {e}")

    async def _async_search_episodes(self, anime: str, url: str) -> None:
        """Async implementation of search_episodes"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1000)

                # Get all episode links
                episode_links = await page.query_selector_all('a[href*="/episodio/"]')

                episode_titles = []
                episode_urls = []

                for link in episode_links:
                    ep_href = await link.get_attribute("href")

                    if not ep_href or "/episodio/" not in ep_href:
                        continue

                    # Extract episode number
                    ep_num = self._extract_episode_number(ep_href)
                    if ep_num is None:
                        continue

                    episode_titles.append(f"Episódio {ep_num}")
                    episode_urls.append(ep_href)

                # Register episodes with repository
                if episode_titles and episode_urls:
                    rep.add_episode_list(anime, episode_titles, episode_urls, self.name)

            finally:
                await browser.close()

    def search_player_src(self, url: str, container: list, event) -> None:
        """
        Extract video URLs from episode page

        Args:
            url: Episode URL
            container: List to append video URLs to
            event: Event object (not used)
        """
        try:
            video_url = asyncio.run(self._async_extract_video_url(url))
            if video_url:
                container.append(video_url)
        except Exception as e:
            print(f"Error extracting video from TopAnimes: {e}")

    async def _async_extract_video_url(self, episode_url: str) -> Optional[str]:
        """
        Extract actual video URL from episode page using network interception

        Args:
            episode_url: URL to the episode page

        Returns:
            Direct video URL (usually from Discord CDN) or None if not found
        """
        video_urls = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            def handle_route(route):
                request = route.request
                url = request.url
                resource_type = request.resource_type

                # Only capture media requests with video extensions
                # Skip API calls, tracking pixels, etc.
                if resource_type in ["media", "fetch"]:
                    # Check if URL ends with video extension (not just contains it)
                    url_lower = url.lower()
                    if any(
                        url_lower.endswith(ext) or f"{ext}?" in url_lower
                        for ext in [".mp4", ".m3u8", ".mkv"]
                    ):
                        video_urls.append(
                            {
                                "url": url,
                                "source": self._detect_source(url),
                                "format": self._detect_format(url),
                            }
                        )

                return route.continue_()

            await page.route("**/*", handle_route)

            try:
                await page.goto(episode_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                # Prefer Discord CDN (direct playable), then any MP4, then others
                for source_name in ["Discord CDN", "TopAnimes", "OdaCDN"]:
                    for video in video_urls:
                        if video["source"] == source_name and video["format"] == "mp4":
                            return video["url"]

                # Fallback: return first MP4
                for video in video_urls:
                    if video["format"] == "mp4":
                        return video["url"]

                # Fallback: return any video URL
                if video_urls:
                    return video_urls[0]["url"]

                return None

            finally:
                await browser.close()

    @staticmethod
    def _extract_episode_number(url: str) -> Optional[int]:
        """Extract episode number from URL"""
        match = re.search(r"episodio[io]?-(\d+)", url.lower())
        return int(match.group(1)) if match else None

    @staticmethod
    def _detect_source(url: str) -> str:
        """Detect hosting source from URL"""
        if "discord" in url.lower() or "discordapp" in url.lower():
            return "Discord CDN"
        elif "odacdn" in url.lower():
            return "OdaCDN"
        elif "ruplay" in url.lower():
            return "Ruplay"
        elif "aniplay" in url.lower():
            return "AniPlay"
        elif "zuplay" in url.lower():
            return "Zuplay"
        elif "topanimes" in url.lower():
            return "TopAnimes"
        else:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc or "Unknown"

    @staticmethod
    def _detect_format(url: str) -> str:
        """Detect video format from URL"""
        if ".mp4" in url.lower():
            return "mp4"
        elif ".m3u8" in url.lower():
            return "hls"
        elif ".mkv" in url.lower():
            return "mkv"
        elif ".webm" in url.lower():
            return "webm"
        return "unknown"


# Plugin loader interface
def load(languages_dict) -> None:
    """Load the TopAnimes plugin if the requested language is supported"""
    can_load = False
    for language in TopanimesScraper.languages:
        if language in languages_dict:
            can_load = True
            break

    if not can_load:
        return

    rep.register(TopanimesScraper())
