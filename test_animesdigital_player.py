#!/usr/bin/env python3
"""
Test AnimesDigital video player page.
"""

import requests
from selectolax.parser import HTMLParser

# Test with a real episode URL from the previous script
episode_url = "https://animesdigital.org/video/a/127924/"

print("=" * 70)
print("AnimesDigital Episode Player: " + episode_url)
print("=" * 70)

response = requests.get(episode_url, timeout=10)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    tree = HTMLParser(response.text)

    # Look for video elements
    print("STEP 1: Looking for video player")
    print("-" * 70)

    # Check for iframe
    iframes = tree.css("iframe")
    print(f"Iframes found: {len(iframes)}")
    for i, iframe in enumerate(iframes):
        src = iframe.attributes.get("src", "")
        id_ = iframe.attributes.get("id", "")
        classes = iframe.attributes.get("class", "")
        print(f"  [{i}] src='{src}'")
        print(f"      id='{id_}', class='{classes}'")

    # Check for video tags
    print(f"\nVideo tags found: {len(tree.css('video'))}")
    for i, video in enumerate(tree.css("video")):
        sources = video.css("source")
        for source in sources:
            src = source.attributes.get("src", "")
            type_ = source.attributes.get("type", "")
            print(f"  Video {i}: {src}")
            print(f"    type: {type_}")

    # Look for any player-related divs
    print("\nLooking for player containers:")
    for selector in [".player", "[id*='player']", "[class*='player']", ".video-container"]:
        elems = tree.css(selector)
        if elems:
            print(f"  ✓ {selector}: {len(elems)} elements")

    # Look at all divs and their classes
    print("\n" + "=" * 70)
    print("STEP 2: Analyzing page structure")
    print("-" * 70)

    # Get main content area
    main = tree.css_first("main")
    if main:
        print("Found <main> element")
        # Look for divs inside main
        divs = main.css("div[class]")
        print(f"Divs in main: {len(divs)}")

        # Show unique classes
        classes_map = {}
        for div in divs:
            classes = div.attributes.get("class", "")
            if classes not in classes_map:
                classes_map[classes] = 0
            classes_map[classes] += 1

        print("\nTop 15 div classes:")
        for classes, count in sorted(classes_map.items(), key=lambda x: -x[1])[:15]:
            print(f"  '{classes}': {count}")

    # Look for any script tags with video content
    print("\n" + "=" * 70)
    print("STEP 3: Looking for embedded video data in scripts")
    print("-" * 70)

    scripts = tree.css("script")
    found_video_data = False

    for script in scripts:
        text = script.text()
        # Look for common video patterns
        if any(pattern in text for pattern in ["src:", "url(", "http", "mp4", "m3u8"]):
            if len(text) > 50:  # Skip very small scripts
                print(f"\nScript with video references ({len(text)} chars):")
                lines = text.split("\n")
                for line in lines:
                    if any(p in line for p in ["http", "mp4", "m3u8", "embed", "player"]):
                        print(f"  {line[:150]}")
                        found_video_data = True

    if not found_video_data:
        print("No obvious video data in scripts")

    # Check for data attributes
    print("\n" + "=" * 70)
    print("STEP 4: Checking for data attributes")
    print("-" * 70)

    data_attrs = tree.css("[data-*]")
    print(f"Elements with data attributes: {len(data_attrs)}")

    for elem in data_attrs[:10]:
        attrs = elem.attributes
        data_attrs_dict = {k: v for k, v in attrs.items() if k.startswith("data-")}
        if data_attrs_dict:
            print(f"\n<{elem.tag} class='{attrs.get('class', '')}':")
            for key, val in data_attrs_dict.items():
                if len(str(val)) > 100:
                    print(f"  {key}: {str(val)[:100]}...")
                else:
                    print(f"  {key}: {val}")

    # Look for embed or object tags
    print("\n" + "=" * 70)
    print("STEP 5: Looking for embed/object tags")
    print("-" * 70)

    embeds = tree.css("embed")
    print(f"Embed tags: {len(embeds)}")
    for embed in embeds:
        src = embed.attributes.get("src", "")
        print(f"  src: {src}")

    objects = tree.css("object")
    print(f"Object tags: {len(objects)}")
    for obj in objects:
        data = obj.attributes.get("data", "")
        print(f"  data: {data}")

else:
    print(f"Error: Could not fetch page (status {response.status_code})")

print("\n" + "=" * 70)
print("Next Steps")
print("=" * 70)
print("""
If this is a player that needs JavaScript rendering:
1. Use Selenium with Firefox (headless)
2. Wait for iframe to load
3. Extract src from the iframe

If video is in HTML:
1. Look for iframe with src containing video URL
2. Extract the src attribute
3. Return it directly
""")
