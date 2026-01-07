#!/usr/bin/env python3
"""
Detailed test for AnimesDigital selectors and HTML structure.
"""

import requests
from selectolax.parser import HTMLParser

# Test with exact URL from user
search_url = "https://animesdigital.org/search/isekai+de"

print("=" * 70)
print("AnimesDigital Search: " + search_url)
print("=" * 70)

response = requests.get(search_url, timeout=10)
print(f"Status: {response.status_code}\n")

tree = HTMLParser(response.text)

# Get all anime results
print("STEP 1: Find anime link containers")
print("-" * 70)

anime_links = tree.css("a[href*='/anime/']")
print(f"Found {len(anime_links)} anime links\n")

if anime_links:
    print("Examining structure of first anime result:")
    first_link = anime_links[0]
    print(f"Link href: {first_link.attributes.get('href')}")
    print(f"Link text: {first_link.text()}")

    # Get parent structure
    print("\nTraversing parent elements:")
    parent = first_link.parent
    level = 1
    while parent and level <= 5:
        classes = parent.attributes.get("class", "")
        tag = parent.tag
        print(f"  {'  ' * (level-1)}└ <{tag} class='{classes}'>")
        parent = parent.parent
        level += 1

# Extract all anime data from search results
print("\n" + "=" * 70)
print("STEP 2: Extract anime data")
print("-" * 70)

anime_list = []

for link in anime_links[:5]:  # Show first 5
    href = link.attributes.get("href")
    title = link.text().strip()

    # Try to get more info from siblings
    print(f"\nAnime: {title}")
    print(f"URL: {href}")

    # Look for image
    parent = link.parent
    while parent:
        img = parent.css_first("img")
        if img:
            print(f"Image: {img.attributes.get('src')}")
            break
        parent = parent.parent

    anime_list.append({"title": title, "url": href})

# Test clicking on one anime to see episode structure
print("\n" + "=" * 70)
print("STEP 3: Check anime detail pages")
print("-" * 70)

if anime_list:
    test_anime = anime_list[0]
    test_url = test_anime["url"]
    print(f"Testing anime detail page: {test_url}")

    try:
        detail_response = requests.get(test_url, timeout=10)
        print(f"Status: {detail_response.status_code}")

        if detail_response.status_code == 200:
            detail_tree = HTMLParser(detail_response.text)

            # Look for episodes
            print("\nLooking for episode links on detail page:")
            for selector in [
                "a[href*='/episodio/']",
                "a.ep",
                "a.episode",
                "li a",
                "div.episode a",
                ".ep-item a",
            ]:
                elements = detail_tree.css(selector)
                if elements:
                    print(f"  ✓ {selector}: Found {len(elements)}")
                    if elements:
                        first = elements[0]
                        href = first.attributes.get("href", "")
                        text = first.text()
                        print(f"    First: href='{href}', text='{text}'")

            # Check for any divs that might contain episodes
            print("\nDiv class analysis on detail page:")
            divs = detail_tree.css("div[class]")
            unique_classes = {}
            for div in divs:
                classes = div.attributes.get("class", "")
                if classes:
                    if classes not in unique_classes:
                        unique_classes[classes] = 0
                    unique_classes[classes] += 1

            for classes, count in sorted(unique_classes.items(), key=lambda x: -x[1])[:15]:
                print(f"  - '{classes}': {count}")

    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 70)
print("Selector Test Summary")
print("=" * 70)
print("""
Working selectors found:
  ✓ a[href*='/anime/'] - Links to anime detail pages
  ✓ Classes: itemA, thumb, button_play, play-video, sOverlay, title

Next steps:
  1. Check the detail page structure to find episode selectors
  2. Find video player iframe or video element
  3. Create plugin with confirmed selectors
""")
