#!/usr/bin/env python3
"""
Extract video URLs from topanimes.net using Playwright

This script demonstrates how to extract actual video URLs from JavaScript-heavy
streaming sites using browser automation and network interception.

Usage:
    uv run --with playwright scripts/extract_topanimes_video.py <episode_url>

Example:
    uv run --with playwright scripts/extract_topanimes_video.py \
        "https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/"

Requirements:
    - playwright
    - chromium browser (install with: playwright install chromium)
"""

import asyncio
import sys
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright  # type: ignore[import-untyped]


class TopanimesExtractor:
    """Extract video URLs from topanimes.net episodes"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.video_urls: list = []

    async def extract(self, episode_url: str) -> dict:
        """
        Extract video information from a topanimes.net episode URL

        Args:
            episode_url: Full URL to the episode page

        Returns:
            Dictionary containing:
                - video_urls: List of extracted video URLs with metadata
                - episode_info: Extracted episode information
                - status: Success/failure status
        """
        self.video_urls = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            # Intercept all network requests
            await page.route("**/*", self._handle_route)

            try:
                print(f"Loading page: {episode_url}")
                await page.goto(episode_url, wait_until="networkidle", timeout=30000)

                # Wait for player to fully load
                await page.wait_for_timeout(3000)

                # Try to extract episode info from page
                title = await self._extract_title(page)
                episode_num = self._extract_episode_number(episode_url)

                await browser.close()

                return {
                    "status": "success",
                    "episode_url": episode_url,
                    "title": title,
                    "episode_number": episode_num,
                    "video_urls": self.video_urls,
                    "video_count": len(self.video_urls),
                }

            except Exception as e:
                await browser.close()
                return {
                    "status": "error",
                    "episode_url": episode_url,
                    "error": str(e),
                    "video_urls": self.video_urls,
                }

    async def _handle_route(self, route):
        """Intercept network requests and extract video URLs"""
        request = route.request
        url = request.url

        # Look for video file extensions
        if any(ext in url.lower() for ext in [".mp4", ".m3u8", ".mkv", ".webm"]):
            # Avoid duplicates
            if not any(v["url"] == url for v in self.video_urls):
                video_info = {
                    "url": url,
                    "format": self._detect_format(url),
                    "source": self._detect_source(url),
                }
                self.video_urls.append(video_info)
                print(f"  ✓ Found: {video_info['format'].upper()} from {video_info['source']}")

        return await route.continue_()

    async def _extract_title(self, page) -> str:
        """Extract episode title from page"""
        try:
            title = await page.title()
            return title
        except:
            return "Unknown"

    @staticmethod
    def _extract_episode_number(url: str) -> Optional[int]:
        """Extract episode number from URL"""
        import re

        match = re.search(r"episodio[io]?-(\d+)", url.lower())
        return int(match.group(1)) if match else None

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
            parsed = urlparse(url)
            return parsed.netloc or "Unknown"


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python extract_topanimes_video.py <episode_url>")
        print()
        print("Example:")
        print("  python extract_topanimes_video.py \\")
        print('    "https://topanimes.net/episodio/anime-name-episodio-10/"')
        sys.exit(1)

    episode_url = sys.argv[1]

    print("\n" + "=" * 60)
    print("TopAnimes Video Extractor")
    print("=" * 60 + "\n")

    extractor = TopanimesExtractor(headless=True)
    result = await extractor.extract(episode_url)

    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60 + "\n")

    if result["status"] == "success":
        print("✅ Status: Success")
        print(f"   Episode: {result['episode_number']}")
        print(f"   Title: {result['title']}")
        print(f"   Videos Found: {result['video_count']}\n")

        if result["video_urls"]:
            print("Video Sources:")
            for i, video in enumerate(result["video_urls"], 1):
                print(f"\n  {i}. {video['format'].upper()} ({video['source']})")
                print(f"     URL: {video['url'][:80]}...")

            print("\n" + "=" * 60)
            print("Best Source for Playback:")
            print("=" * 60)

            # Find best source (prefer direct MP4 over redirects)
            mp4_videos = [v for v in result["video_urls"] if v["format"] == "mp4"]
            if mp4_videos:
                best = mp4_videos[0]
                print(f"\n✓ Recommended: {best['source']} ({best['format'].upper()})")
                print("\nPlay with mpv:")
                print(f"  mpv '{best['url']}'")
                print("\nPlay with vlc:")
                print(f"  vlc '{best['url']}'")
        else:
            print("❌ No video sources found!")
    else:
        print(f"❌ Error: {result['error']}")

    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
