#!/usr/bin/env python3
"""
Test AnimesDigital episode extraction from detail page.
"""

import requests
from selectolax.parser import HTMLParser

# Test with a real anime detail page
anime_url = "https://animesdigital.org/anime/a/sentai-red-isekai-de-boukensha-ni-naru"

print("=" * 70)
print("AnimesDigital Anime Detail: " + anime_url)
print("=" * 70)

response = requests.get(anime_url, timeout=10)
print(f"Status: {response.status_code}\n")

tree = HTMLParser(response.text)

# Find the anime title
print("STEP 1: Find anime title")
print("-" * 70)
title_elem = tree.css_first("h1")
if title_elem:
    print(f"Title: {title_elem.text()}")
else:
    print("No h1 found, trying other selectors...")
    for selector in ["h2", ".title_anime", "[class*='title']"]:
        elems = tree.css(selector)
        if elems:
            print(f"  {selector}: {elems[0].text()}")

# Find episode container
print("\n" + "=" * 70)
print("STEP 2: Find episode list")
print("-" * 70)

# Look for the pattern we found: "item_ep b_flex"
item_eps = tree.css("div.item_ep")
print(f"Found {len(item_eps)} episodes using 'div.item_ep'\n")

if item_eps:
    print("Examining first 3 episodes:")
    for i, item_ep in enumerate(item_eps[:3]):
        print(f"\n  Episode {i+1}:")
        print(f"    Full element: {str(item_ep)[:200]}...")

        # Look for link inside
        link = item_ep.css_first("a")
        if link:
            href = link.attributes.get("href", "")
            text = link.text()
            print(f"    Link href: {href}")
            print(f"    Link text: {text}")

        # Look for title
        title_elem = item_ep.css_first(".title_anime")
        if title_elem:
            print(f"    Title: {title_elem.text()}")

        # Look for date
        date_elem = item_ep.css_first(".date")
        if date_elem:
            print(f"    Date: {date_elem.text()}")

# Alternative: Look for all links that might be episodes
print("\n" + "=" * 70)
print("STEP 3: Find episode links alternative method")
print("-" * 70)

# Look at the structure - maybe links are in a specific area
all_a_tags = tree.css("a")
episode_links = []

for a in all_a_tags:
    href = a.attributes.get("href", "")
    if "/episodio/" in href or "/ep" in href:
        text = a.text().strip()
        if text:
            episode_links.append({"href": href, "text": text})
            print(f"Found episode link: {text}")
            print(f"  URL: {href}\n")

if not episode_links:
    print("No links with '/episodio/' found. Checking other patterns...")
    # Check for links within item_ep divs
    for item_ep in item_eps[:3]:
        links = item_ep.css("a")
        for link in links:
            href = link.attributes.get("href", "")
            text = link.text()
            print(f"Link in item_ep: {text} -> {href}")

# Test clicking one episode to see player
print("\n" + "=" * 70)
print("STEP 4: Test episode player page")
print("-" * 70)

if episode_links:
    test_ep = episode_links[0]
    ep_url = test_ep["href"]
    print(f"Testing episode: {test_ep['text']}")
    print(f"URL: {ep_url}\n")

    try:
        ep_response = requests.get(ep_url, timeout=10)
        print(f"Status: {ep_response.status_code}")

        if ep_response.status_code == 200:
            ep_tree = HTMLParser(ep_response.text)

            # Look for video player
            print("\nLooking for video player:")

            # Check for iframe
            iframes = ep_tree.css("iframe")
            print(f"Iframes found: {len(iframes)}")
            for i, iframe in enumerate(iframes[:3]):
                src = iframe.attributes.get("src", "")
                print(f"  [{i}] {src[:100]}...")

            # Check for video tags
            videos = ep_tree.css("video")
            print(f"Video tags found: {len(videos)}")
            for i, video in enumerate(videos[:3]):
                sources = video.css("source")
                for source in sources:
                    src = source.attributes.get("src", "")
                    type_ = source.attributes.get("type", "")
                    print(f"  [{i}] {src[:100]}... (type: {type_})")

            # Look for any data-src attributes
            data_src = ep_tree.css("[data-src]")
            print(f"Elements with data-src: {len(data_src)}")
            for elem in data_src[:3]:
                src = elem.attributes.get("data-src", "")
                print(f"  {elem.tag}: {src[:100]}...")

    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 70)
print("Summary")
print("=" * 70)
print("""
Working selectors for AnimesDigital:

SEARCH PAGE:
  ✓ a[href*='/anime/'] - Links to anime pages
  ✓ Text inside link is the anime title

ANIME DETAIL PAGE:
  ✓ div.item_ep - Episode containers
  ✓ a inside div.item_ep - Episode links
  ✓ .title_anime - Episode number/title
  ✓ .date - Episode air date

EPISODE PLAYER:
  - Need to check for iframe or video element
  - May need Selenium for JavaScript-rendered content
""")
