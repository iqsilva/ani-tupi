# TopAnimes.net Quick Reference

## TL;DR

**TopAnimes.net uses DooPlayer**, a JavaScript-based video player that loads videos dynamically. Standard HTTP requests don't work—you need **Playwright (browser automation) to intercept the actual video URLs**.

### What We Discovered
- ✅ Videos are hosted on Discord CDN
- ✅ Direct MP4 URLs are extracted via network interception
- ✅ Playable with mpv, vlc, ffplay

### Key Finding
```
topanimes.net webpage → JavaScript execution → AJAX requests → Video URLs from Discord CDN
```

---

## Quick Start

### 1. Extract Video URL
```bash
uv run --with playwright scripts/extract_topanimes_video.py \
  "https://topanimes.net/episodio/anime-name-episodio-10/"
```

### 2. Play with mpv
```bash
mpv "https://media.discordapp.net/attachments/.../video.mp4"
```

---

## Website Structure

| Component | Details |
|-----------|---------|
| **Platform** | WordPress-based streaming site |
| **Player** | DooPlayer (custom WordPress REST API) |
| **Post Format** | Episodes = WordPress posts |
| **URL Pattern** | `/episodio/{anime-slug}/{episode-number}/` |
| **Post ID** | Embedded in shortlink: `?p=361463` |
| **CDN** | Discord (`media.discordapp.net`) |

---

## Why Playwright?

### The Problem
```python
# ❌ This doesn't work
import requests
response = requests.get("https://topanimes.net/episodio/...")
# HTML has no video URLs—they're loaded by JavaScript!
```

### The Solution
```python
# ✅ This works
from playwright.async_api import async_playwright
page = await browser.new_page()
await page.route("**/*", handle_route)  # Intercept all requests
await page.goto(url, wait_until="networkidle")  # Execute JS
# Now we see the actual video URLs!
```

### Why It Works
1. Playwright **loads the page in a real browser (Chromium)**
2. JavaScript executes, triggering AJAX requests
3. We intercept requests with `page.route()`
4. We capture video URLs from network traffic
5. URLs are direct playable links

---

## Video Sources Found

| Source | Format | URL Pattern | Status |
|--------|--------|-------------|--------|
| **Discord CDN** | MP4 | `media.discordapp.net/attachments/...` | ✅ Direct |
| **OdaCDN** | HLS | `topanimes.net/antivirus2/...` | Redirect |
| **TopAnimes Proxy** | MP4 | `topanimes.net/antivirus3/...` | Redirect |
| **HLS Stream** | m3u8 | `topanimes.net/...cdn_stream.m3u8` | Redirect |

**Best for playback:** Discord CDN MP4 (direct, no redirects)

---

## Script Usage

### Option 1: Quick Extraction
```bash
uv run --with playwright scripts/extract_topanimes_video.py \
  "https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/"
```

**Output:**
```
Video Sources:

  1. MP4 (Discord CDN)
     URL: https://media.discordapp.net/attachments/1400089717697150988/...

Best Source for Playback:

✓ Recommended: Discord CDN (MP4)

Play with mpv:
  mpv 'https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/...'
```

### Option 2: Use as Python Module
```python
from scripts.extract_topanimes_video import TopanimesExtractor
import asyncio

async def main():
    extractor = TopanimesExtractor()
    result = await extractor.extract(
        "https://topanimes.net/episodio/anime-name-episodio-10/"
    )
    print(f"Found {result['video_count']} video sources")
    for video in result['video_urls']:
        print(f"  - {video['source']}: {video['url']}")

asyncio.run(main())
```

---

## API Endpoints (Reference)

### DooPlayer API
```
GET /wp-json/dooplayer/v2/{post_id}/post/{source}
```

**Parameters:**
- `post_id`: WordPress post ID (e.g., `361463`)
- `source`: Video provider (odacdn, ruplay, aniplay, zuplay)

**Returns:** Empty JSON in static requests (requires browser context)

### Extracting Post ID
```python
import re
html = requests.get(url).text
post_id_match = re.search(r'\?p=(\d+)', html)
post_id = post_id_match.group(1)  # e.g., "361463"
```

---

## Implementation for ani-tupi

### Create Scraper
```python
# scrapers/plugins/topanimes.py

from models.models import AnimeMetadata, EpisodeData
from scripts.extract_topanimes_video import TopanimesExtractor

class TopanimesScraper:
    async def search(self, query: str) -> list[AnimeMetadata]:
        # Search implementation
        pass

    async def get_episodes(self, url: str) -> list[EpisodeData]:
        extractor = TopanimesExtractor()
        result = await extractor.extract(url)

        episodes = []
        for video in result['video_urls']:
            episodes.append(EpisodeData(
                number=result['episode_number'],
                title=result['title'],
                video_url=video['url'],
                aired=None
            ))
        return episodes
```

### Dependencies
```bash
uv add playwright
uv run playwright install chromium
```

---

## Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| Browser startup | ~2-3s | One-time per extraction |
| Page load | ~5-10s | Depends on CDN/network |
| Video extraction | <1s | Just network interception |
| **Total** | ~8-13s | Acceptable for on-demand |

**Optimization:** Cache video URLs per episode URL to avoid re-extraction.

---

## Troubleshooting

### "Failed to execute script: No module named 'playwright'"
```bash
uv add playwright
uv run playwright install chromium
```

### "Timeout waiting for networkidle"
Increase timeout:
```python
await page.goto(url, wait_until="networkidle", timeout=60000)
```

### "Video URL not found"
Check if site structure changed:
```bash
uv run scripts/extract_topanimes_video.py <url> --debug
```

### "CORS error in browser"
Not an issue—Playwright bypasses CORS in headless mode.

### "Rate limited / blocked"
- Add delays: `await page.wait_for_timeout(2000)`
- Rotate user agents (future enhancement)
- Use different IP addresses

---

## Files Generated

| File | Purpose |
|------|---------|
| `docs/topanimes_scraping_analysis.md` | Full technical analysis |
| `docs/topanimes_quick_reference.md` | This file |
| `scripts/extract_topanimes_video.py` | Working extraction script |

---

## Example Output

```
============================================================
TopAnimes Video Extractor
============================================================

Loading page: https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/
  ✓ Found: MP4 from Discord CDN
  ✓ Found: HLS from TopAnimes
  ✓ Found: MP4 from TopAnimes

============================================================
Results
============================================================

✅ Status: Success
   Episode: 10
   Title: Osananajimi to wa Love Comedy ni Naranai – Episódio 10
   Videos Found: 3

Video Sources:

  1. MP4 (Discord CDN)
     URL: https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/...

  2. HLS (TopAnimes)
     URL: https://topanimes.net/antivirus2/yes/?id=sbt/f-cdn/...

  3. MP4 (TopAnimes)
     URL: https://topanimes.net/antivirus3/?id=You%20Cant%20Be%20In%20a%20Rom-Com...

============================================================
Best Source for Playback:
============================================================

✓ Recommended: Discord CDN (MP4)

Play with mpv:
  mpv 'https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/You_Cant_Be_In_a_Rom-Com_with_Your_Childhood_Friends_-_S01E10_1080p.1080p.mp4?ex=69b049be&is=69aef83e&hm=109c924a4ee4d5630c089e010ec54805e97826573eb6e9cc10eb4658ef058454&'

Play with vlc:
  vlc 'https://media.discordapp.net/attachments/1400089717697150988/1480606483744817253/You_Cant_Be_In_a_Rom-Com_with_Your_Childhood_Friends_-_S01E10_1080p.1080p.mp4?ex=69b049be&is=69aef83e&hm=109c924a4ee4d5630c089e010ec54805e97826573eb6e9cc10eb4658ef058454&'
```

---

## Next Steps

1. **Test the extractor:**
   ```bash
   uv run --with playwright scripts/extract_topanimes_video.py <any_topanimes_url>
   ```

2. **Integrate into ani-tupi:**
   - Create `scrapers/plugins/topanimes.py`
   - Implement search and episode extraction
   - Add to plugin registry

3. **Optimize:**
   - Cache extraction results
   - Implement retry logic
   - Add rate limiting

---

## References

- Playwright Docs: https://playwright.dev/python/
- TopAnimes.net: https://topanimes.net
- mpv player: https://mpv.io
