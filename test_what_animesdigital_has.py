#!/usr/bin/env python3
"""
Check what AnimesDigital actually has for each query.
"""

from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import rep

queries = [
    "jujutsu",
    "jujutsu kaisen",
    "dandadan",
    "chainsaw"
]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Query: '{query}'")
    print('='*60)

    rep.clear_search_results()
    AnimesDigital.search_anime(query)

    ad_titles = [t for t in rep.anime_to_urls.keys() if any(
        s == "animesdigital" for _, s, _ in rep.anime_to_urls[t]
    )]

    print(f"AnimesDigital results: {len(ad_titles)}")
    if ad_titles:
        for title in ad_titles:
            print(f"  - {title}")
    else:
        print("  (none)")
