# TopAnimes.net Video Extraction Analysis

## Overview

This document details the process, findings, and scripts used to extract and play video content from topanimes.net (a Brazilian Portuguese anime streaming site).

**Date:** March 9, 2026
**Objective:** Extract video source URL from a dynamic JavaScript-based video player and play it with mpv

---

## Website Architecture

### Site Structure
- **URL:** https://topanimes.net
- **Type:** WordPress-based anime streaming platform
- **Language:** Brazilian Portuguese
- **Video Player:** DooPlayer (custom WordPress plugin system)

### Key Components

#### 1. Page Structure
- Episodes are stored as WordPress posts
- Each episode has a unique post ID (extracted from shortlink: `?p=361463`)
- URL format: `https://topanimes.net/episodio/{anime-slug}/{episode-number}/`

#### 2. Video Player System
- **Player Framework:** DooPlayer (WordPress REST API integration)
- **API Endpoint:** `https://topanimes.net/wp-json/dooplayer/v2/`
- **Available Sources:** OdaCDN, Ruplay, AniPlay, Zuplay
- **API Response:** Returns empty JSON (requires browser context for actual video loading)

#### 3. Video Hosting
- Primary: Discord CDN (`media.discordapp.net`)
- Fallback streams: Various CDN providers (OdaCDN, etc.)
- Format: MP4 (h264 video, AAC audio)

---

## Challenge: Dynamic Content Loading

### Problem
The video player uses JavaScript to load video sources dynamically via AJAX requests. Standard HTTP requests to the DooPlayer API return HTTP 200 with empty response bodies.

### Root Cause
- DooPlayer API requires a browser context to execute JavaScript
- Video sources are loaded client-side after page render
- CORS and authentication checks prevent direct API calls

### Solution
Use **Playwright** (headless browser automation) to:
1. Load the page in a headless browser
2. Execute JavaScript and wait for AJAX requests
3. Intercept network requests for video resources
4. Extract actual video URLs from network traffic

---

## Tools & Technologies Used

### 1. requests (HTTP Client)
```bash
pip install requests
```
**Purpose:** Initial page fetching and exploratory API calls
**Limitation:** Cannot execute JavaScript

### 2. BeautifulSoup (HTML Parser)
**Purpose:** Parse static HTML structure
**Limitation:** Cannot handle dynamically-loaded content

### 3. Playwright (Browser Automation)
```bash
uv add playwright
playwright install chromium  # Download browser
```
**Purpose:** Execute JavaScript and intercept network requests
**Advantage:** Can see all network activity like a real browser

### 4. mpv (Video Player)
```bash
apt install mpv  # Debian/Ubuntu
```
**Purpose:** Play extracted video URL

---

## Scripts & Implementation

### Script 1: Initial Exploration (requests-based)

```python
import requests
import re

url = "https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/"

# Fetch the page
response = requests.get(url)
html = response.text

# Extract post ID from shortlink
post_id_match = re.search(r'\?p=(\d+)', html)
if post_id_match:
    post_id = post_id_match.group(1)
    print(f"✓ Found post ID: {post_id}")

    # Try to fetch from API
    api_url = f"https://topanimes.net/wp-json/dooplayer/v2/{post_id}/post"
    print(f"\nTrying API: {api_url}")

    # Try different sources
    for source in ['odacdn', 'ruplay', 'aniplay', 'zuplay']:
        api_response = requests.get(f"{api_url}/{source}")
        print(f"  {source}: {api_response.status_code}")
        if api_response.content:
            print(f"    {api_response.text[:200]}")
```

**Result:** Found post ID (361463), but API endpoints returned empty responses.

---

### Script 2: Playwright Network Interception (WORKING)

```python
import asyncio
from playwright.async_api import async_playwright

async def get_video_url():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Intercept network requests
        video_urls = []

        def handle_route(route):
            request = route.request
            if any(ext in request.url for ext in ['.m3u8', '.mp4', '.mkv']):
                print(f"Found video request: {request.url}")
                video_urls.append(request.url)
            return route.continue_()

        await page.route('**/*', handle_route)

        print("Loading page...")
        await page.goto(
            "https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/",
            wait_until="networkidle",
            timeout=30000
        )

        # Wait for player to load
        await page.wait_for_timeout(3000)

        # Try to find video source in page
        sources = await page.query_selector_all('source[src*=".m3u8"], source[src*=".mp4"]')
        print(f"Found {len(sources)} source elements")

        for source in sources:
            src = await source.get_attribute('src')
            print(f"Source: {src}")
            video_urls.append(src)

        await browser.close()

        return video_urls

urls = asyncio.run(get_video_url())
print(f"\nCollected URLs: {len(urls)}")
for url in urls:
    print(f"  {url}")
```

**Key Features:**
- Uses `page.route('**/*', handle_route)` to intercept all network requests
- Filters requests by file extension (.m3u8, .mp4)
- Waits for network idle state (`wait_until="networkidle"`)
- Extracts actual video URLs from network traffic

**Result:** ✅ Successfully extracted Discord CDN URL

---

### Script 3: Video Playback (mpv)

```bash
#!/bin/bash

VIDEO_URL="https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/You_Cant_Be_In_a_Rom-Com_with_Your_Childhood_Friends_-_S01E10_1080p.1080p.mp4?ex=69b049be&is=69aef83e&hm=109c924a4ee4d5630c089e010ec54805e97826573eb6e9cc10eb4658ef058454&"

echo "========================================="
echo "Video Details"
echo "========================================="
echo "Anime: Osananajimi to wa Love Comedy ni Naranai"
echo "Episode: 10"
echo "Provider: topanimes.net (Discord CDN)"
echo "Format: MP4 (1080p)"
echo ""
echo "Starting playback..."
echo "========================================="
echo ""

if command -v mpv &> /dev/null; then
    mpv "$VIDEO_URL" --force-window=immediate
else
    echo "Error: mpv not installed"
    echo "Install with: apt install mpv"
fi
```

**Result:** ✅ Video plays successfully in mpv

---

## Extraction Process (Step-by-Step)

### Phase 1: Reconnaissance
1. **Fetch HTML** → Identify WordPress structure
2. **Extract Post ID** → From shortlink `?p=361463`
3. **Identify API** → DooPlayer REST API endpoint
4. **Test API** → Confirm empty responses

### Phase 2: Browser Automation
1. **Launch Headless Browser** → Chromium via Playwright
2. **Intercept Requests** → Monitor all network traffic
3. **Wait for Load** → `networkidle` state
4. **Collect Video URLs** → Filter by .mp4, .m3u8 extensions

### Phase 3: Playback
1. **Filter URLs** → Prefer direct MP4 over redirect URLs
2. **Select Best Source** → Discord CDN (direct MP4)
3. **Play with mpv** → Stream to user

---

## Results

### Extracted Video Information

| Property | Value |
|----------|-------|
| **Title** | You Can't Be in a Rom-Com with Your Childhood Friends! (Osananajimi to wa Love Comedy ni Naranai) |
| **Episode** | 10 |
| **URL** | `https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/You_Cant_Be_In_a_Rom-Com_with_Your_Childhood_Friends_-_S01E10_1080p.1080p.mp4?...` |
| **Format** | MP4 (h264 1920x1080 @ 23.976 fps) |
| **Audio** | AAC 2ch Japanese 44100 Hz 75 kbps |
| **Duration** | 23:50 (24 min episode) |
| **Source** | Discord CDN |
| **Status** | ✅ Playable with mpv |

### Network Requests Captured

The Playwright script identified multiple video sources:

1. **HLS Stream (m3u8):**
   - URL: `https://topanimes.net/antivirus2/yes/?id=sbt/f-cdn/google/node/playready/a-2/letra/o/osananajimi-to-wa-love-comedy-ni-naranai/10/cdn_stream.m3u8`
   - Type: HLS (HTTP Live Streaming)
   - Status: Redirect page (not direct stream)

2. **Antivirus3 Proxy:**
   - URL: `https://topanimes.net/antivirus3/?id=You%20Cant%20Be%20In%20a%20Rom-Com%20with%20Your%20Childhood%20Friends!%20-%20S01E10%20[1080p].1080p.mp4`
   - Type: Proxy URL
   - Status: Intermediate redirect

3. **Discord CDN (WORKING):**
   - URL: `https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/You_Cant_Be_In_a_Rom-Com_with_Your_Childhood_Friends_-_S01E10_1080p.1080p.mp4?ex=69b049be&is=69aef83e&hm=109c924a4ee4d5630c089e010ec54805e97826573eb6e9cc10eb4658ef058454&`
   - Type: Direct MP4
   - Status: ✅ **DIRECT PLAYABLE**

---

## Technical Insights

### Why Playwright Was Necessary

| Approach | Result |
|----------|--------|
| `requests.get()` | ❌ Empty JSON responses |
| `BeautifulSoup` | ❌ No video URLs in HTML |
| `curl` | ❌ No video URLs in response |
| **Playwright** | ✅ Full network traffic visibility |

### Key Playwright Techniques

1. **Network Interception:**
   ```python
   await page.route('**/*', handle_route)
   ```
   Captures all HTTP requests/responses

2. **Wait Strategies:**
   ```python
   wait_until="networkidle"  # Wait for network to become idle
   ```
   Ensures JavaScript has fully executed

3. **DOM Queries:**
   ```python
   await page.query_selector_all('source[src*=".mp4"]')
   ```
   Searches for video elements

---

## Integration with ani-tupi

### Proposed Topanimes Scraper

```python
# scrapers/plugins/topanimes.py

from typing import Protocol
from models.models import AnimeMetadata, EpisodeData
from utils.playwright_helper import extract_video_urls_with_playwright

class TopanimesScraper:
    """Scraper for topanimes.net using Playwright for dynamic content"""

    async def search(self, query: str) -> list[AnimeMetadata]:
        # Implement search via topanimes.net search endpoint
        pass

    async def get_episodes(self, url: str) -> list[EpisodeData]:
        # Extract post ID from episode URL
        post_id = self._extract_post_id(url)

        # Use Playwright to load page and intercept video requests
        video_urls = await extract_video_urls_with_playwright(url)

        # Parse and return episodes
        episodes = []
        for video_url in video_urls:
            episodes.append(EpisodeData(
                number=self._extract_episode_number(url),
                title="",
                video_url=video_url,
                aired=None
            ))

        return episodes

    def _extract_post_id(self, url: str) -> int:
        import re
        match = re.search(r'\?p=(\d+)', url)
        return int(match.group(1)) if match else None
```

### Dependencies

Add to `pyproject.toml`:
```toml
playwright = "^1.48.0"
```

Install browsers:
```bash
uv run playwright install chromium
```

### Advantages
- ✅ Handles JavaScript-heavy sites
- ✅ Intercepts actual video sources
- ✅ Supports multiple CDN providers
- ✅ No API key required

### Disadvantages
- ⚠️ Slower than direct HTML parsing (requires browser startup)
- ⚠️ Higher resource usage (Chromium process)
- ⚠️ May be blocked by anti-bot measures if rate-limited

---

## Lessons Learned

### 1. JavaScript-Heavy Sites Require Browser Automation
- Static analysis (curl, requests) cannot extract dynamic content
- DooPlayer loads videos via AJAX after page render
- Playwright successfully captured network traffic

### 2. Network Interception is Key
- Don't parse DOM for video URLs
- Listen to network requests (`page.route()`)
- Filter requests by file extension or MIME type

### 3. Multiple Video Sources
- topanimes.net hosts videos on Discord CDN
- HLS streams may be redirects or proxies
- Direct MP4 URLs are most reliable

### 4. CDN & Hosting Strategy
- Using Discord CDN reduces infrastructure costs
- URLs include query parameters for expiration/validation
- Direct CDN links work seamlessly with standard players

---

## Commands Reference

### Install Dependencies
```bash
uv add requests
uv add playwright
uv run playwright install chromium
apt install mpv
```

### Run Extraction Script
```bash
uv run python3 << 'EOF'
# (Paste Script 2 here)
EOF
```

### Play Video
```bash
mpv "https://media.discordapp.net/attachments/..."
```

### View Network Requests (Debug)
```python
page.on("request", lambda request: print(request.url))
```

---

## Conclusion

TopAnimes.net uses a sophisticated DooPlayer system that dynamically loads videos from multiple CDN providers. While initial API approaches failed, **Playwright's network interception successfully extracted the actual video URL** from Discord's CDN, allowing seamless playback with mpv.

This approach is generalizable to other WordPress-based anime streaming sites using similar player frameworks.

---

## Appendix: Full Extraction Script

See `/tmp/play_topanimes.sh` for the complete working script used for playback.

### Usage
```bash
bash /tmp/play_topanimes.sh
```

### Output
```
=========================================
Video Details
=========================================
Anime: Osananajimi to wa Love Comedy ni Naranai
Episode: 10
Provider: topanimes.net (Discord CDN)
Format: MP4 (1080p)

Starting playback...
=========================================

[vo/gpu-next] 1920x1080 yuv420p
AV: 00:00:03 / 00:23:50 (0%)
```

Video plays successfully in mpv ✅
