#!/usr/bin/env python3
"""Debug script for topanimes video extraction."""

import sys
import re
from pathlib import Path
from urllib.parse import unquote

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.core.selenium_driver import SeleniumWebDriver


def extract_video_url_debug(episode_url: str):
    """Debug video extraction from topanimes episode page."""
    print(f"\n🔍 Debugging video extraction from: {episode_url}\n")

    try:
        with SeleniumWebDriver() as driver:
            print("📄 Fetching page with Selenium...")
            page = driver.fetch(episode_url)

        page_text = str(page)
        print(f"✓ Page fetched. Size: {len(page_text)} characters\n")

        # Look for all URLs in the page
        print("🔎 Searching for video URLs...\n")

        all_urls = re.findall(r'https?://[^\s"\'<>]+', page_text)
        video_urls = [
            url
            for url in all_urls
            if any(ext in url.lower() for ext in [".mp4", ".m3u8", ".mkv", "/stream", "video"])
        ]

        if video_urls:
            print(f"Found {len(video_urls)} potential video URLs:")
            for i, url in enumerate(set(video_urls), 1):
                print(f"  {i}. {url[:100]}...")
        else:
            print("❌ No video URLs found in page text!")

        print("\n" + "=" * 80)
        print("📝 Searching in <script> tags specifically...\n")

        scripts = page.select("script")
        print(f"Found {len(scripts)} script tags\n")

        script_video_urls = []
        for i, script in enumerate(scripts, 1):
            if not script.string:
                continue

            script_text = script.string
            # Look for video URLs
            matches = re.findall(r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*', script_text)

            if matches:
                print(f"Script #{i} has {len(matches)} video URL(s):")
                for url in matches:
                    print(f"  - {url[:120]}...")
                    script_video_urls.extend(matches)

        if not script_video_urls:
            print("❌ No video URLs found in script tags!")

        print("\n" + "=" * 80)
        print("🎬 Checking for iframes and data attributes...\n")

        iframes = page.select("iframe")
        print(f"Found {len(iframes)} iframes:")
        for iframe in iframes:
            src = iframe.get("src")
            if src:
                print(f"  - {src[:120]}...")

                # Try to decode URLs embedded in iframe src
                if "url=" in src:
                    # Extract and decode the embedded URL
                    match = re.search(r"url=([^&]+)", src)
                    if match:
                        encoded_url = match.group(1)
                        try:
                            decoded_url = unquote(encoded_url)
                            print(f"    📌 Decoded URL: {decoded_url[:120]}...")
                        except:
                            pass

        data_src_elems = page.select("[data-src]")
        print(f"\nFound {len(data_src_elems)} elements with data-src:")
        for elem in data_src_elems:
            src = elem.get("data-src")
            if src:
                print(f"  - {src[:120]}...")

        data_url_elems = page.select("[data-url]")
        print(f"\nFound {len(data_url_elems)} elements with data-url:")
        for elem in data_url_elems:
            src = elem.get("data-url")
            if src:
                print(f"  - {src[:120]}...")

        print("\n" + "=" * 80)
        print("🔍 Checking video/source tags...\n")

        videos = page.select("video")
        print(f"Found {len(videos)} <video> tags:")
        for video in videos:
            src = video.get("src")
            if src:
                print(f"  video src: {src[:120]}...")

            sources = video.select("source")
            for source in sources:
                src = source.get("src")
                if src:
                    print(f"  source src: {src[:120]}...")

        print("\n" + "=" * 80)
        print("\n📋 Page snippet (first 2000 chars of HTML):\n")
        print(page_text[:2000])

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Test with actual episode URL
    episode_url = "https://topanimes.net/episodio/bocchi-the-rock-dublado-episodio-12/"

    if len(sys.argv) > 1:
        episode_url = sys.argv[1]

    extract_video_url_debug(episode_url)
