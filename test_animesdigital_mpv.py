#!/usr/bin/env python3
"""
Test AnimesDigital plugin with actual MPV playback.

Run with:
  uv run test_animesdigital_mpv.py
"""

import subprocess
import sys
from threading import Event

from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

# Get singleton repository
repo = Repository()
repo.register(AnimesDigital)

print("=" * 70)
print("AnimesDigital Full Integration Test")
print("=" * 70)

# Step 1: Search
print("\n[1/4] Searching for anime...")
AnimesDigital.search_anime("isekai de")
anime_titles = list(repo.anime_to_urls.keys())
test_anime = anime_titles[0]
print(f"✓ Found: {test_anime}")

# Step 2: Get episodes
print("\n[2/4] Fetching episodes...")
urls_and_sources = repo.anime_to_urls[test_anime]
test_url = urls_and_sources[0][0]
AnimesDigital.search_episodes(test_anime, test_url, None)
episode_titles = repo.get_episode_list(test_anime)
print(f"✓ Found {len(episode_titles)} episodes")

# Step 3: Get video URL
print("\n[3/4] Extracting video URL...")
result = repo.get_episode_url_and_source(test_anime, 1)
if result:
    test_episode_url, source = result
    print(f"Episode: {episode_titles[0]}")

    container = []
    event = Event()

    try:
        AnimesDigital.search_player_src(test_episode_url, container, event)

        if container:
            video_url = container[0]
            print(f"✓ Video URL: {video_url[:80]}...")

            # Step 4: Play in MPV
            print("\n[4/4] Opening in MPV...")
            print("\nPress 'q' to quit MPV\n")

            try:
                subprocess.run(
                    ["mpv", "--force-window=immediate", video_url],
                    check=False,
                    timeout=600,
                )
                print("\n✓ MPV playback test complete!")
            except FileNotFoundError:
                print("⚠ MPV not found. Video URL is valid:")
                print(f"  {video_url}")
                print("\nYou can copy this URL and play it manually.")
            except subprocess.TimeoutExpired:
                print("\n✓ MPV timeout (playback took longer than expected)")

        else:
            print("✗ No video URL extracted")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
else:
    print("✗ No episode found")
    sys.exit(1)
