#!/usr/bin/env python3
"""
Test AnimesDigital search for specific anime.
"""

from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

# Get repository singleton
repo = Repository()
repo.register(AnimesDigital)

queries = ["jujutsu kaisen", "dandadan", "chainsaw man"]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Buscando: {query}")
    print('='*60)

    # Clear previous results
    repo.clear_search_results()

    # Search
    AnimesDigital.search_anime(query)

    # Get results
    results = list(repo.anime_to_urls.keys())
    print(f"Resultados: {len(results)}")

    if results:
        print("\nAnime encontrado:")
        for anime in results[:5]:
            print(f"  • {anime}")
    else:
        print("  ⚠ Nenhum resultado encontrado")
