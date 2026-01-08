#!/usr/bin/env python3
"""
Check if cache is preventing AnimesDigital from appearing.
"""

from utils.cache_manager import get_cache
from scrapers.loader import load_plugins
from services.repository import Repository

# Check cache first
print("="*60)
print("Checking cache...")
print("="*60)

dc = get_cache()
cache_key = "search:jujutsu kaisen"
cached = dc.get(cache_key)

if cached:
    print(f"✓ Cache HIT for '{cache_key}'")
    print(f"  Cached anime count: {len(cached)}")
    print("  Cached anime (first 5):")
    for title in list(cached.keys())[:5]:
        sources = [s for _, s, _ in cached[title]]
        print(f"    - {title} ({','.join(sources)})")

    print("\n  Does cache have AnimesDigital? ", end="")
    has_ad = any(any(s == "animesdigital" for _, s, _ in sources_list)
                  for sources_list in cached.values())
    print("YES ✓" if has_ad else "NO ✗")
else:
    print(f"✗ Cache MISS for '{cache_key}'")

# Clear cache and re-search
print("\n" + "="*60)
print("Clearing cache and re-searching...")
print("="*60)

dc.delete(cache_key)
print(f"✓ Deleted cache key: {cache_key}")

# Now search
Repository.reset_singleton()
repo = Repository()
load_plugins({'pt-br'})

print(f"\nLoaded plugins: {repo.get_active_sources()}")
print("Searching for 'jujutsu kaisen'...")

repo.search_anime("jujutsu kaisen", verbose=False)

titles = repo.get_anime_titles()
sources_count = {}
for title in titles:
    for url, source, params in repo.anime_to_urls[title]:
        sources_count[source] = sources_count.get(source, 0) + 1

print("\nResults:")
print(f"  Total: {len(titles)} anime")
print("  By source:")
for source in sorted(sources_count.keys()):
    print(f"    {source}: {sources_count[source]}")
