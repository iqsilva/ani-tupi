# PROJECT STATE: ani-tupi Integration Test Suite

## Project Reference

See: `.planning/PROJECT.md` (updated 2025-01-24)

**Core value:** Detect real-world workflow bugs (search fails, episodes don't parse, video URLs break, AniList sync fails) BEFORE users encounter them in production.

**Current focus:** Phase 1 — Scraper Real-API Testing

## Current Status

**Phase 1:** Not started
**Phase 2:** Not started
**Phase 3:** Not started
**Phase 4:** Not started

## Key Context

### Why Real APIs?

Existing tests use mocks, which hide real-world bugs:
- HTML parsing breaks when scraper sites change layout
- AniList fuzzy matching fails with unexpected title variations
- Playwright timeout behavior differs from real pages
- Video URL extraction timing-sensitive (Selenium waits)

Real-API tests catch these issues BEFORE users hit them.

### The Critical Workflow

User flow that must work end-to-end:
1. Search for anime ("Dandadan")
2. Get episode list from scraper
3. Extract video source URL (Selenium + Firefox for AnimeFire)
4. Verify URL is playable (HTTP 200)

Failure at any step = user can't watch.

### Three Scrapers

| Scraper | URL | Quality | Risk |
|---------|-----|---------|------|
| AnimeFirePlus | animefire.plus | High, stable | HTML structure changes |
| AnimesDigital | animesdigital.org | Good (dubbed) | Fewer users, less stable |
| AnimesOnlineCC | animesonlinecc.to | Good (PT-BR) | Video tokens expire 10-15 min |

### Test Queries

Evergreen anime titles for reliable testing:
- "Dandadan" — Popular, multiple seasons, all scrapers have it
- "Jujutsu Kaisen" — Long-running, stable across sources
- "Blue Lock" — Newer, good for recency testing

### AniList Integration Notes

- OAuth token valid ~6 months
- Rate limit: 500 requests/minute
- Fuzzy matching uses Levenshtein distance (fuzzywuzzy library)
- Mappings cached in `~/.local/state/ani-tupi/anilist_mappings.json`
- Test account needed for Phase 2 write tests (update watch history)

### Manga (Mugiwaras) Notes

- Uses Playwright for dynamic content (JavaScript rendering)
- Age verification modal often present
- Chapter pages extracted from `data-src` attributes
- PDF quality configurable (env var `ANI_TUPI__MANGA__PDF_QUALITY`)

### Error Scenarios to Test

| Error | Impact | Recovery |
|-------|--------|----------|
| Network timeout | Can't fetch page | Retry with backoff |
| Malformed HTML | Parser crashes | Graceful fallback |
| Missing video element | No source URL | Show error, suggest scraper switch |
| Rate limit (429) | AniList unavailable | Queue sync for later |
| Firefox not installed | Can't extract video | Inform user, skip Selenium-dependent scrapers |

## Next Steps

**Immediate:** Run `/gsd:plan-phase 1` to create detailed execution plan for Phase 1 scraper testing.

**Setup before Phase 1:**
- Verify Firefox + geckodriver installed
- Test anime titles accessible on all scrapers
- Document timeouts/delays for Selenium waits

**Setup before Phase 2:**
- Obtain AniList test account (with write permissions)
- Document token storage (secure, not in repo)
- Verify rate limit behavior

---
*Last updated: 2025-01-24 after roadmap creation*
