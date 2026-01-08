#!/usr/bin/env python3
"""
Debug full search workflow.
"""

from scrapers.loader import load_plugins
from services.repository import Repository

# Load plugins
repo = Repository()
load_plugins({'pt-br'})

print("Full Search Test")
print("="*60)

query = "jujutsu kaisen"
print(f"Searching for: '{query}'")

# Call search_anime directly on plugin
from scrapers.plugins.animesdigital import AnimesDigital
print("\n1. Direct plugin call:")
repo.clear_search_results()
AnimesDigital.search_anime(query)
results = list(repo.anime_to_urls.keys())
print(f"   Found: {len(results)} anime")
for r in results[:3]:
    print(f"   - {r}")

# Check anime_to_urls structure
print("\n2. Repository data:")
print(f"   anime_to_urls keys: {len(repo.anime_to_urls)}")
for title, urls_and_sources in list(repo.anime_to_urls.items())[:3]:
    print(f"   - {title}")
    for url, source, params in urls_and_sources:
        print(f"     source: {source}")

# Check normalized titles
print("\n3. Normalized titles:")
for title, norm in list(repo.norm_titles.items())[:3]:
    print(f"   '{title}' -> '{norm}'")
