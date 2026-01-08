#!/usr/bin/env python3
"""
End-to-end test: AnimesDigital plugin with ani-tupi pipeline.

Simulates full workflow:
1. Search for anime
2. Select anime
3. Select episode
4. Play video

Run with:
  uv run test_animesdigital_e2e.py
"""

from services.repository import rep
from scrapers.loader import load_plugins

print("=" * 70)
print("AnimesDigital E2E Test (Full Pipeline)")
print("=" * 70)

# Step 1: Load plugins (this happens in ani-tupi initialization)
print("\n[1/4] Loading plugins...")
load_plugins({'pt-br'})
sources = rep.get_active_sources()
print(f"✓ Loaded {len(sources)} sources: {', '.join(sources)}")

# Step 2: Search for anime (this happens when user searches)
print("\n[2/4] Searching for 'isekai de'...")
rep.search_anime("isekai de", verbose=False)
anime_titles = rep.get_anime_titles()
print(f"✓ Found {len(anime_titles)} anime")

# Show AnimesDigital results
ad_animes = []
for title in anime_titles:
    urls_and_sources = rep.anime_to_urls[title]
    sources_list = [source for _, source, _ in urls_and_sources]
    if "animesdigital" in sources_list:
        ad_animes.append(title)

print(f"✓ AnimesDigital has {len(ad_animes)} anime")
if ad_animes:
    for anime in ad_animes[:3]:
        print(f"  - {anime}")

# Step 3: Select anime and load episodes
if ad_animes:
    test_anime = ad_animes[0]
    print(f"\n[3/4] Loading episodes for: {test_anime}")
    rep.search_episodes(test_anime, source_filter="animesdigital")
    episodes = rep.get_episode_list(test_anime)
    print(f"✓ Found {len(episodes)} episodes")
    for i, ep in enumerate(episodes[:3]):
        print(f"  [{i+1}] {ep}")

    # Step 4: Get video URL
    print("\n[4/4] Extracting video URL...")
    result = rep.get_episode_url_and_source(test_anime, 1)
    if result:
        video_url, source = result
        print(f"✓ Video URL extracted from: {source}")
        print(f"  {video_url[:80]}...")

        print("\n" + "=" * 70)
        print("SUCCESS: Full pipeline working!")
        print("=" * 70)
        print("""
Summary:
✓ Plugin auto-loaded
✓ Search working
✓ Episodes extracted
✓ Video URL obtained

Ready to play in MPV! 🎬
""")
    else:
        print("✗ Could not get video URL")
else:
    print("✗ No AnimesDigital anime found in search results")
