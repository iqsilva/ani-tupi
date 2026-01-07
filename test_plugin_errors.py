#!/usr/bin/env python3
"""
Check if AnimesDigital is throwing errors during search.
"""

import sys
import traceback
from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import Repository

# Fresh repo
repo = Repository()

query = "jujutsu kaisen"
print(f"Testing AnimesDigital.search_anime('{query}')\n")

try:
    # Call plugin directly
    print("Calling AnimesDigital.search_anime()...")
    AnimesDigital.search_anime(query)
    print("✓ No exception thrown")

    # Check what was added
    titles = [t for t in repo.anime_to_urls.keys() if any(
        s == "animesdigital" for _, s, _ in repo.anime_to_urls[t]
    )]

    print(f"\nResults added to repository:")
    print(f"  Count: {len(titles)}")
    for title in titles:
        print(f"  - {title}")

except Exception as e:
    print(f"✗ Exception thrown!")
    print(f"\nError: {e}")
    traceback.print_exc()
