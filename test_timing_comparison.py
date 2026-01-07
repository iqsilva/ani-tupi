#!/usr/bin/env python3
"""
Compare timing for 1-word vs 2-word queries.
"""

import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from scrapers.plugins.animesdigital import AnimesDigital
from scrapers.plugins.animefire import AnimeFire
from scrapers.plugins.animesonlinecc import AnimesOnlineCC

queries = ["jujutsu", "jujutsu kaisen"]
plugins = [
    ("AnimesDigital", AnimesDigital),
    ("AnimeFire", AnimeFire),
    ("AnimesOnlineCC", AnimesOnlineCC),
]

for query in queries:
    print(f"\n{'='*70}")
    print(f"Query: '{query}' ({len(query.split())} word(s))")
    print('='*70)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}

        for name, plugin in plugins:
            start = time.time()
            future = executor.submit(plugin.search_anime, query)
            futures[future] = (name, start)

        for future in wait(futures.keys(), return_when=ALL_COMPLETED).done:
            name, start = futures[future]
            elapsed = time.time() - start
            try:
                future.result()
                print(f"  ✓ {name:20s} {elapsed:6.2f}s")
            except Exception as e:
                print(f"  ✗ {name:20s} {elapsed:6.2f}s - {str(e)[:50]}")
