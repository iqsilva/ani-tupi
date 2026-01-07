#!/usr/bin/env python3
"""
Debug AnimesDigital search.
"""

import requests
from selectolax.parser import HTMLParser

query = "jujutsu kaisen"
url = f"https://animesdigital.org/search/{query.replace(' ', '+')}"

print(f"URL: {url}")
print(f"Fetching...")

try:
    response = requests.get(url, timeout=20)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)}")

    if response.status_code == 200:
        tree = HTMLParser(response.text)

        # Find all links
        links = tree.css("a")
        print(f"Total links: {len(links)}")

        # Find anime links
        anime_links = tree.css("a[href*='/anime/']")
        print(f"Anime links: {len(anime_links)}")

        if anime_links:
            print("\nFirst 3 anime found:")
            for link in anime_links[:3]:
                href = link.attributes.get("href")
                text = link.text()
                print(f"  - {text[:50]}")
                print(f"    {href}")
        else:
            print("\nNo anime links found!")
            print("\nAll links on page:")
            for i, link in enumerate(links[:10]):
                href = link.attributes.get("href", "")
                text = link.text()[:50]
                print(f"  [{i}] {text} -> {href[:80]}")
    else:
        print(f"Error status: {response.status_code}")
        print(f"Response text: {response.text[:500]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
