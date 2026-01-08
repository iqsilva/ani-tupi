#!/usr/bin/env python3
"""
Simular busca direta como main.py --query faz.
"""

from scrapers.loader import load_plugins
from services.repository import rep

print("Loading plugins...")
load_plugins({'pt-br'})

queries = ["jujutsu", "jujutsu kaisen", "dandadan"]

for query in queries:
    print("\n" + "="*70)
    print(f"Query: '{query}'")
    print("="*70)

    # Clear previous results
    rep.clear_search_results()

    # Search
    print("Buscando...")
    rep.search_anime(query, verbose=False)

    # Get results
    titles = rep.get_anime_titles_with_sources(original_query=query)

    print(f"Total: {len(titles)} resultados\n")

    # Show first 10
    for i, title in enumerate(titles[:10]):
        print(f"  {i+1:2d}. {title}")

    # Count by source
    if rep.anime_to_urls:
        sources_count = {}
        for title in rep.anime_to_urls.keys():
            for url, source, params in rep.anime_to_urls[title]:
                sources_count[source] = sources_count.get(source, 0) + 1

        print("\nPor fonte:")
        for source, count in sorted(sources_count.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")
