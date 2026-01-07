#!/usr/bin/env python3
"""
Debug repository search behavior with verbose output.
"""

from scrapers.loader import load_plugins
from services.repository import Repository

# Fresh repo
Repository.reset_singleton()
repo = Repository()
load_plugins({'pt-br'})
print(f"Loaded sources: {repo.get_active_sources()}\n")

queries = ["jujutsu", "jujutsu kaisen"]

for query in queries:
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print('='*70)

    # Clear
    repo.clear_search_results()

    # Search with verbose
    print(f"Calling repo.search_anime('{query}', verbose=True)...")
    repo.search_anime(query, verbose=True)

    # Show results
    print(f"\nResults:")
    titles = list(repo.anime_to_urls.keys())
    print(f"  Total titles: {len(titles)}")

    # Count by source
    sources_count = {}
    for title in titles:
        for url, source, params in repo.anime_to_urls[title]:
            sources_count[source] = sources_count.get(source, 0) + 1

    print(f"  By source:")
    for source in ['animesdigital', 'animefire', 'animesonlinecc']:
        count = sources_count.get(source, 0)
        print(f"    {source}: {count}")

    # Check metadata
    metadata = repo.get_search_metadata()
    print(f"\nSearch metadata:")
    print(f"  original_query: {metadata.original_query}")
    print(f"  used_query: {metadata.used_query}")
    print(f"  used_words: {metadata.used_words}")
