#!/usr/bin/env python3
"""
Check what's actually in the repository after search.
"""

from scrapers.loader import load_plugins
from services.repository import rep

load_plugins({'pt-br'})
print(f"Loaded plugins: {rep.get_active_sources()}\n")

query = "jujutsu kaisen"
print(f"Searching for: '{query}'\n")

rep.search_anime(query, verbose=False)

print(f"Total titles in repository: {len(rep.anime_to_urls)}\n")

print("All titles and their sources:")
for i, (title, urls_and_sources) in enumerate(rep.anime_to_urls.items(), 1):
    sources = [source for url, source, params in urls_and_sources]
    sources_str = ", ".join(sorted(sources))
    print(f"  {i:2d}. {title}")
    print(f"      Sources: {sources_str}")

# Count by source
print("\n" + "="*60)
sources_count = {}
for title in rep.anime_to_urls.keys():
    for url, source, params in rep.anime_to_urls[title]:
        sources_count[source] = sources_count.get(source, 0) + 1

print("Totals by source:")
for source in sorted(sources_count.keys()):
    print(f"  {source}: {sources_count[source]}")

# Check if AnimesDigital titles are there
print("\n" + "="*60)
ad_results = []
for title in rep.anime_to_urls.keys():
    for url, source, params in rep.anime_to_urls[title]:
        if source == "animesdigital":
            ad_results.append(title)
            break

print(f"\nAnimesDigital titles found:")
if ad_results:
    for title in ad_results:
        print(f"  - {title}")
else:
    print(f"  (None found!)")

# Compare with direct plugin search
print("\n" + "="*60)
print("Direct AnimesDigital.search_anime() test:")
# Note: can't reset here because it's a singleton already loaded

from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository as RepClass

test_repo = RepClass()
test_repo.clear_search_results()
AnimesDigital.search_anime(query)

ad_direct = [t for t in test_repo.anime_to_urls.keys() if any(
    s == "animesdigital" for _, s, _ in test_repo.anime_to_urls[t]
)]

print(f"AnimesDigital direct search found {len(ad_direct)} titles:")
for title in ad_direct[:5]:
    print(f"  - {title}")
