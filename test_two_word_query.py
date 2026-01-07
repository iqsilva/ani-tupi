#!/usr/bin/env python3
"""
Debug why AnimesDigital fails with 2-word queries.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.plugins.animesdigital import AnimesDigital
from services.repository import rep

query = "jujutsu kaisen"
print(f"Testing query: '{query}'\n")

# Test 1: Direct call
print("TEST 1: Direct AnimesDigital.search_anime()")
print("-" * 60)
rep.clear_search_results()

start = time.time()
try:
    AnimesDigital.search_anime(query)
    elapsed = time.time() - start
    results = len(rep.anime_to_urls)
    print(f"✓ Success in {elapsed:.2f}s")
    print(f"  Results added: {results}")
    for title in list(rep.anime_to_urls.keys())[:3]:
        print(f"    - {title}")
except Exception as e:
    elapsed = time.time() - start
    print(f"✗ Failed in {elapsed:.2f}s")
    print(f"  Error: {e}")

# Test 2: Check if timeout is the issue
print("\n" + "="*60)
print("TEST 2: Check response time")
print("-" * 60)

import requests
from selectolax.parser import HTMLParser

url = f"https://animesdigital.org/search/{query.replace(' ', '+')}"
print(f"URL: {url}")

start = time.time()
try:
    response = requests.get(url, timeout=20)
    elapsed = time.time() - start
    print(f"✓ Response in {elapsed:.2f}s")
    print(f"  Status: {response.status_code}")
    print(f"  Content length: {len(response.text)}")

    tree = HTMLParser(response.text)
    anime_links = tree.css("a[href*='/anime/']")
    print(f"  Anime links found: {len(anime_links)}")

except Exception as e:
    elapsed = time.time() - start
    print(f"✗ Failed in {elapsed:.2f}s")
    print(f"  Error: {e}")

# Test 3: Parallel execution with other plugins
print("\n" + "="*60)
print("TEST 3: Parallel execution (like Repository does)")
print("-" * 60)

from scrapers.plugins.animefire import AnimeFire
from scrapers.plugins.animesonlinecc import AnimesOnlineCC

plugins = [
    ("AnimesDigital", AnimesDigital),
    ("AnimeFire", AnimeFire),
    ("AnimesOnlineCC", AnimesOnlineCC),
]

rep.clear_search_results()

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {}

    for name, plugin in plugins:
        future = executor.submit(plugin.search_anime, query)
        futures[future] = name

    for future in as_completed(futures):
        name = futures[future]
        try:
            future.result()
            # Count results for this plugin
            ad_count = sum(1 for title in rep.anime_to_urls.keys()
                          if any(s == name.lower().replace("online", "").strip()
                                for _, s, _ in rep.anime_to_urls[title]))
            print(f"✓ {name:20s} (estimated results: {ad_count})")
        except Exception as e:
            print(f"✗ {name:20s} - {e}")

# Final check
print("\n" + "="*60)
print("Final repository state:")
sources_count = {}
for title in rep.anime_to_urls.keys():
    for url, source, params in rep.anime_to_urls[title]:
        sources_count[source] = sources_count.get(source, 0) + 1

for source in sorted(sources_count.keys()):
    print(f"  {source}: {sources_count[source]}")
