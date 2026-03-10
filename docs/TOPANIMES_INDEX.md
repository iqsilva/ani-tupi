# TopAnimes.net Integration Documentation Index

## Overview

Complete documentation and working tools for extracting and playing videos from **topanimes.net**, a Brazilian Portuguese anime streaming site using the DooPlayer JavaScript-based player system.

## 📚 Documentation Files

### 1. **topanimes_scraping_analysis.md** (462 lines)
**Full Technical Analysis Document**

Comprehensive deep-dive into the website structure, tools, and implementation.

**Contents:**
- Website architecture and components
- The challenge: dynamic JavaScript content loading
- Root cause analysis
- Technology stack (requests, BeautifulSoup, Playwright, mpv)
- Three complete working scripts with explanations
- Step-by-step extraction process
- Results and video information
- Network requests analysis
- Integration guide for ani-tupi
- Lessons learned
- Technical insights and trade-offs
- Full troubleshooting guide

**Best for:** Understanding the problem in depth, learning why each approach was chosen, implementing your own solution.

**Key Sections:**
- Architecture Principles
- Challenge Analysis
- Script Implementations (3 versions)
- Results and Findings
- Integration Guide
- Lessons Learned

---

### 2. **topanimes_quick_reference.md** (314 lines)
**Quick Start and Reference Guide**

Fast-paced reference for common tasks and integration.

**Contents:**
- TL;DR summary
- Quick start commands
- Website structure reference table
- Why Playwright was necessary
- Video sources comparison table
- Script usage examples (CLI and module)
- ani-tupi integration code template
- Performance benchmarks
- Troubleshooting common issues
- Example output
- File references

**Best for:** Quick lookups, getting started fast, integration reference, troubleshooting.

**Key Sections:**
- TL;DR
- Quick Start
- Website Structure
- Video Sources
- Implementation for ani-tupi
- Troubleshooting

---

### 3. **scripts/extract_topanimes_video.py** (212 lines)
**Working Extraction Tool**

Production-ready Python script for extracting video URLs from topanimes.net episodes.

**Features:**
- `TopanimesExtractor` class for reusable extraction
- Async/await pattern for efficiency
- Network interception with Playwright
- Automatic video source detection
- Support for multiple video formats (MP4, HLS, MKV, WebM)
- Source identification (Discord, OdaCDN, etc.)
- CLI interface with formatted output
- Error handling and timeouts
- Example usage as both script and module

**Usage:**
```bash
# As standalone script
uv run --with playwright scripts/extract_topanimes_video.py \
  "https://topanimes.net/episodio/anime-name-episodio-10/"

# As Python module
from scripts.extract_topanimes_video import TopanimesExtractor
# ... see docs for examples
```

**Best for:** Direct video extraction, CLI usage, integrating into ani-tupi scraper.

---

## 🎯 Quick Navigation

### I want to...

**Understand why this was needed:**
→ Read `topanimes_scraping_analysis.md` - Architecture & Challenge sections

**Get started quickly:**
→ Read `topanimes_quick_reference.md` - Quick Start section

**Extract a video right now:**
→ Run `scripts/extract_topanimes_video.py <episode_url>`

**Integrate into ani-tupi:**
→ Read `topanimes_quick_reference.md` - Implementation for ani-tupi section
→ Use `TopanimesExtractor` class in new scraper plugin

**Understand the technology:**
→ Read `topanimes_scraping_analysis.md` - Tools & Technologies section

**Troubleshoot an issue:**
→ Read `topanimes_quick_reference.md` - Troubleshooting section

**See what was discovered:**
→ Read `topanimes_scraping_analysis.md` - Results section

**Implement your own version:**
→ Read both docs, review `scripts/extract_topanimes_video.py` source code

---

## 🚀 Quick Start (30 seconds)

```bash
# 1. Install Playwright
uv add playwright
uv run playwright install chromium

# 2. Extract video URL
uv run --with playwright scripts/extract_topanimes_video.py \
  "https://topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/"

# 3. Play with mpv
mpv "https://media.discordapp.net/attachments/.../video.mp4"
```

---

## 📊 Key Findings Summary

| Finding | Detail |
|---------|--------|
| **Website** | WordPress-based streaming platform |
| **Player** | DooPlayer (JavaScript-based) |
| **Challenge** | Videos loaded dynamically via AJAX |
| **Solution** | Playwright network interception |
| **Best Source** | Discord CDN direct MP4 links |
| **Status** | ✅ Working and tested |
| **Example Result** | 1920x1080 MP4, 23:50 duration, playable with mpv |

---

## 🔧 Technology Stack

- **Language:** Python 3.10+
- **Browser Automation:** Playwright (Chromium)
- **Video Player:** mpv
- **Async Runtime:** asyncio
- **Network Analysis:** Built-in Playwright interception

---

## 📁 File Structure

```
ani-tupi/
├── docs/
│   ├── TOPANIMES_INDEX.md                    ← You are here
│   ├── topanimes_scraping_analysis.md        (Main technical doc)
│   └── topanimes_quick_reference.md          (Quick start guide)
└── scripts/
    └── extract_topanimes_video.py            (Working tool)
```

---

## 💡 Next Steps

### For Understanding
1. Read `topanimes_quick_reference.md` (TL;DR + quick start)
2. Read `topanimes_scraping_analysis.md` (full analysis)
3. Review `extract_topanimes_video.py` source code

### For Integration
1. Create `scrapers/plugins/topanimes.py`
2. Import `TopanimesExtractor` from scripts
3. Implement search and episode extraction methods
4. Register in plugin system
5. Test with ani-tupi CLI

### For Extension
1. Add caching layer to avoid re-extraction
2. Implement retry logic with exponential backoff
3. Add rate limiting to be respectful to CDN
4. Support search functionality
5. Handle edge cases and error scenarios

---

## 🎓 What You'll Learn

Reading these documents and code will teach you:

1. **Web Scraping:** How to extract data from JavaScript-heavy sites
2. **Browser Automation:** Using Playwright for network interception
3. **Async Python:** Async/await patterns for efficient operations
4. **Network Analysis:** Understanding HTTP requests and responses
5. **Integration:** How to plug into existing Python projects
6. **CLI Tools:** Building command-line interfaces with Python

---

## ✅ Verification

All scripts have been tested and verified to:
- ✅ Successfully extract video URLs
- ✅ Handle multiple video sources
- ✅ Play with standard video players (mpv, vlc)
- ✅ Provide clear error messages
- ✅ Work with real ani-tupi episodes

**Example Test Result:**
- Episode: Osananajimi to wa Love Comedy ni Naranai - Episode 10
- URL: topanimes.net/episodio/osananajimi-to-wa-love-comedy-ni-naranai-episodio-10/
- Status: ✅ Video extracted and played successfully
- Video Details: 1920x1080 @ 23.976fps, 23:50 duration, H.264 + AAC

---

## 📝 Document Metadata

| Aspect | Detail |
|--------|--------|
| **Created** | March 9, 2026 |
| **Tested** | Yes, fully working |
| **Browser** | Chromium (via Playwright) |
| **Python** | 3.10+ |
| **Status** | Production ready |
| **Maintenance** | Community-driven |

---

## 🔗 Related Resources

- **Playwright Docs:** https://playwright.dev/python/
- **TopAnimes.net:** https://topanimes.net
- **mpv Player:** https://mpv.io
- **ani-tupi Project:** See CLAUDE.md for architecture

---

## 📧 Questions?

Refer to the appropriate document:
- "How do I..." → `topanimes_quick_reference.md`
- "Why does..." → `topanimes_scraping_analysis.md`
- "Show me code..." → `scripts/extract_topanimes_video.py`

---

**Last Updated:** March 9, 2026
**Total Documentation:** ~1000 lines
**Code Included:** ~200 lines
**Test Status:** ✅ Fully verified
