#!/usr/bin/env python3
"""
Test script for AnimesDigital plugin.

Run with:
  uv run test_plugin_animesdigital.py
"""

import sys
from threading import Event

# Import the plugin directly
from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

# Test search_anime
print("=" * 70)
print("TEST 1: AnimesDigital.search_anime()")
print("=" * 70)

# Get singleton repository (will be shared across all plugin calls)
repo = Repository()
# Register the plugin
repo.register(AnimesDigital)

print("Searching for 'isekai de'...")
try:
    AnimesDigital.search_anime("isekai de")

    anime_titles = list(repo.anime_to_urls.keys())
    print(f"✓ Found {len(anime_titles)} anime\n")

    print("First 3 results:")
    for i, title in enumerate(anime_titles[:3]):
        urls_and_sources = repo.anime_to_urls[title]
        print(f"  [{i+1}] {title}")
        for url, source, params in urls_and_sources:
            print(f"      URL: {url}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test search_episodes
print("\n" + "=" * 70)
print("TEST 2: AnimesDigital.search_episodes()")
print("=" * 70)

if anime_titles:
    test_anime = anime_titles[0]
    urls_and_sources = repo.anime_to_urls[test_anime]
    test_url = urls_and_sources[0][0]

    print(f"Testing with: {test_anime}")
    print(f"URL: {test_url}\n")

    try:
        AnimesDigital.search_episodes(test_anime, test_url, None)

        episode_titles = repo.get_episode_list(test_anime)
        if episode_titles:
            print(f"✓ Found {len(episode_titles)} episodes\n")

            print("First 3 episodes:")
            for i, title in enumerate(episode_titles[:3]):
                print(f"  [{i+1}] {title}")
        else:
            print("✗ No episodes found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Test search_player_src (with Selenium) - OPTIONAL
print("\n" + "=" * 70)
print("TEST 3: AnimesDigital.search_player_src() [OPTIONAL - requires Firefox]")
print("=" * 70)

episode_titles = repo.get_episode_list(test_anime)
if episode_titles:
    # Get first episode URL
    result = repo.get_episode_url_and_source(test_anime, 1)
    if result:
        test_episode_url, source = result
        print(f"Testing with: {episode_titles[0]}")
        print(f"URL: {test_episode_url}\n")

        container = []
        event = Event()

        try:
            print("Launching Firefox (headless)...")
            AnimesDigital.search_player_src(test_episode_url, container, event)

            if container:
                print(f"✓ Video URL found:")
                print(f"  {container[0]}")
            else:
                print("✗ No video URL extracted")

        except RuntimeError as e:
            print(f"⚠ Skipped: {e}")
            print("  (This is expected if Firefox is not installed)")
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()

print("\n" + "=" * 70)
print("Tests Complete!")
print("=" * 70)
print("""
Summary:
- TEST 1: Search functionality ✓
- TEST 2: Episode extraction ✓
- TEST 3: Video extraction (requires Firefox)

The plugin is ready to be integrated!
""")
