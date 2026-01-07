#!/usr/bin/env python3
"""
Debug timeouts with AnimesDigital search.
"""

import time
from scrapers.plugins.animesdigital import AnimesDigital

queries = ["jujutsu", "jujutsu kaisen"]

for query in queries:
    print(f"\n{'='*60}")
    print(f"Testing query: '{query}'")
    print('='*60)

    start = time.time()
    try:
        AnimesDigital.search_anime(query)
        elapsed = time.time() - start
        print(f"✓ Success in {elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ Error in {elapsed:.2f}s")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
