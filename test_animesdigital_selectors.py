#!/usr/bin/env python3
"""
Test script to explore AnimesDigital selectors before implementing the plugin.

Run with:
  uv run test_animesdigital_selectors.py
"""

import requests
from selectolax.parser import HTMLParser

# Test search page
print("=" * 60)
print("Testing AnimesDigital Search Page")
print("=" * 60)

search_query = "isekai"
search_url = f"https://animesdigital.org/search/{search_query}"

print(f"\nFetching: {search_url}")
try:
    response = requests.get(search_url, timeout=10)
    print(f"Status: {response.status_code}")

    tree = HTMLParser(response.text)

    # Try different selectors for anime cards
    print("\n" + "=" * 60)
    print("Testing anime card selectors:")
    print("=" * 60)

    # Test 1: Generic divs with anime data
    print("\n[1] Looking for divs with class 'anime' or 'card':")
    for selector in ["div.anime", "div.card", "div.anime-card", "article.anime"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            # Show first element structure
            if elements:
                first = elements[0]
                print(f"    First element: {str(first)[:200]}...")

    # Test 2: Links to anime pages
    print("\n[2] Looking for anime links:")
    for selector in ["a[href*='/anime/']", "a.anime-link", "h2 a", "h3 a", ".anime-title a"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements:
                first = elements[0]
                href = first.attributes.get("href", "")
                text = first.text()
                print(f"    First: href='{href}', text='{text}'")

    # Test 3: Anime titles
    print("\n[3] Looking for anime titles:")
    for selector in ["h2.anime-title", "h3.anime-title", ".anime-title", "h2 a", "h3 a"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements:
                print(f"    First: '{elements[0].text()}'")

    # Test 4: All divs to understand structure
    print("\n[4] All divs on page (first 10 with class attributes):")
    divs = tree.css("div[class]")
    unique_classes = {}
    for div in divs[:50]:
        classes = div.attributes.get("class", "")
        if classes:
            if classes not in unique_classes:
                unique_classes[classes] = 0
            unique_classes[classes] += 1

    for classes, count in sorted(unique_classes.items(), key=lambda x: -x[1])[:10]:
        print(f"  - '{classes}': {count} occurrences")

    # Test 5: Try to find the container with all results
    print("\n[5] Looking for result container selectors:")
    for selector in ["div.results", "div.container", "div.search-results", "main", ".grid", ".search-grid"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")

except Exception as e:
    print(f"Error fetching search page: {e}")

# Test anime detail page
print("\n\n" + "=" * 60)
print("Testing AnimesDigital Anime Detail Page")
print("=" * 60)

detail_url = "https://animesdigital.org/anime/isekai-no-smartphone"
print(f"\nFetching: {detail_url}")
try:
    response = requests.get(detail_url, timeout=10)
    print(f"Status: {response.status_code}")

    tree = HTMLParser(response.text)

    # Test 1: Episode list selectors
    print("\n[1] Looking for episode list selectors:")
    for selector in ["ul.episodes", "div.episode", "a.episode", "div.ep-item", ".episode-list"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements and selector.startswith("a"):
                first = elements[0]
                href = first.attributes.get("href", "")
                text = first.text()
                print(f"    First: href='{href}', text='{text}'")

    # Test 2: Episode links
    print("\n[2] Looking for episode links:")
    for selector in ["a[href*='/episodio/']", "a[href*='/ep/']", "a[href*='/episode/']"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements:
                for elem in elements[:3]:
                    href = elem.attributes.get("href", "")
                    text = elem.text()
                    print(f"    - href='{href}', text='{text}'")

    # Test 3: Anime title
    print("\n[3] Looking for anime title:")
    for selector in ["h1", "h1.title", ".anime-title", "span.title"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements:
                print(f"    First: '{elements[0].text()}'")

    # Test 4: All links to understand structure
    print("\n[4] Links containing 'ep' or 'episodio' (first 5):")
    all_links = tree.css("a")
    ep_links = [l for l in all_links if "ep" in l.attributes.get("href", "").lower() or "episodio" in l.attributes.get("href", "").lower()]
    for link in ep_links[:5]:
        href = link.attributes.get("href", "")
        text = link.text()
        print(f"  - href='{href}', text='{text}'")

except Exception as e:
    print(f"Error fetching detail page: {e}")

# Test episode player page
print("\n\n" + "=" * 60)
print("Testing AnimesDigital Episode Player Page")
print("=" * 60)

episode_url = "https://animesdigital.org/episodio/isekai-no-smartphone-1"
print(f"\nFetching: {episode_url}")
try:
    response = requests.get(episode_url, timeout=10)
    print(f"Status: {response.status_code}")

    tree = HTMLParser(response.text)

    # Test 1: Video player selectors
    print("\n[1] Looking for video player elements:")
    for selector in ["video", "iframe", "video source", ".video-container", ".player"]:
        elements = tree.css(selector)
        if elements:
            print(f"  ✓ {selector}: Found {len(elements)} elements")
            if elements and selector in ["video", "iframe"]:
                first = elements[0]
                src = first.attributes.get("src", "")
                if selector == "iframe":
                    print(f"    First: src='{src}'")
                else:
                    print(f"    First element found")

    # Test 2: Source tags in video
    print("\n[2] Looking for video sources:")
    videos = tree.css("video")
    if videos:
        for video in videos[:1]:
            sources = video.css("source")
            for source in sources:
                src = source.attributes.get("src", "")
                type_ = source.attributes.get("type", "")
                print(f"  - src='{src}', type='{type_}'")

    # Test 3: Iframe src
    print("\n[3] Looking for iframe sources:")
    iframes = tree.css("iframe")
    if iframes:
        for iframe in iframes[:3]:
            src = iframe.attributes.get("src", "")
            print(f"  - src='{src}'")

    # Test 4: Any scripts with video URLs
    print("\n[4] Looking for scripts containing video URLs:")
    scripts = tree.css("script")
    for script in scripts:
        text = script.text()
        if "http" in text and ("mp4" in text.lower() or "m3u8" in text.lower()):
            print(f"  ✓ Found script with video reference")
            # Show snippet
            lines = text.split("\n")
            for line in lines:
                if "http" in line and ("mp4" in line.lower() or "m3u8" in line.lower()):
                    print(f"    {line[:150]}...")

except Exception as e:
    print(f"Error fetching episode page: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
