# ani-tupi Integration Test Suite

## What This Is

Real API integration tests for ani-tupi that catch hidden workflow bugs by exercising actual scraper and AniList APIs. Tests verify that the complete chain from search → episode fetching → video extraction works end-to-end without mocks, catching issues that unit tests miss.

## Core Value

Detect real-world workflow bugs (search fails, episodes don't parse, video URLs break, AniList sync fails) BEFORE users encounter them in production.

## Requirements

### Validated

- ✓ Anime search workflows (test_anime_search_workflow_integration.py) — existing
- ✓ Manga reading workflows (test_manga_workflow_integration.py) — existing
- ✓ Incremental search algorithm (test_incremental_search_algorithm.py) — existing

### Active

- [ ] **Search → Episodes → Video Source** — Test complete workflow: search anime with each scraper, fetch episode list, extract playable video URL (critical path)
- [ ] **Multi-scraper source testing** — AnimeFirePlus, AnimesDigital, AnimesOnlineCC all working for different anime titles
- [ ] **AniList title discovery** — Fuzzy matching scraped titles to AniList entries, mapping validation
- [ ] **AniList watch history sync** — Verify episode progress syncs to AniList (requires test account)
- [ ] **Error recovery workflows** — Network timeouts, malformed pages, missing elements don't crash app
- [ ] **Manga chapter workflows** — Mugiwaras chapter discovery, page extraction with real API
- [ ] **Video URL validation** — Extracted URLs are parseable and return 200 status
- [ ] **Episode list parsing edge cases** — Handle dubbed/subbed variants, missing chapters, pagination

### Out of Scope

- Mocked API responses (test against real APIs only)
- CI/CD pipeline tests (local development only)
- Writing/modifying external data (read-only queries)
- Performance benchmarking (functional correctness only)
- Mobile/desktop app integration (CLI only)

## Context

**Current state:**
- 4 integration test files with mocked responses
- Critical gap: Mocks don't catch real-world parsing failures, API changes, rate limiting issues
- User pain point: Hidden bugs in workflows involving scrapers + AniList + video extraction

**Workflow chain complexity:**
1. Scraper search API returns HTML/JSON
2. Parser extracts anime titles and URLs (parsing can break if HTML changes)
3. Episode list page fetched, parsed (same risk)
4. Video player source extracted via Selenium (fragile, timing-dependent)
5. AniList fuzzy matching maps scraper results to AniList (levenshtein distance, ordering matters)
6. Watch history synced via GraphQL to AniList (token expiry, rate limiting)

**Known fragility points:**
- AnimesOnlineCC uses temporary video tokens (10-15 min expiry)
- AniList rate limit: 500 requests/minute
- Manga sites have age verification, dynamic content loading
- Different scrapers return different DOM structures

## Constraints

- **External dependency risk** — Scrapers can break if site HTML changes (sites monitored but not controlled by us)
- **Rate limiting** — AniList 500 req/min, scraper sites may rate-limit frequent requests
- **AniList token management** — OAuth tokens expire ~6 months, need test account for write tests
- **Network failures** — Tests may timeout/fail if sites down; acceptable (local-only, manual run)
- **Firefox requirement** — AnimeFirePlus uses Selenium+Firefox for player source extraction
- **Test data stability** — Anime sites constantly add/remove content; queries must be evergreen (e.g., "Dandadan", "Jujutsu Kaisen")
- **Read-only constraint** — No modifications to external APIs (verify syncs don't corrupt AniList)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Real APIs only (no mocks) | Catch parsing/integration bugs that mocks hide | — Pending |
| Local development only | Tests may fail if APIs down; unacceptable for CI | — Pending |
| Read-only queries | Avoid corrupting test data or hitting rate limits | — Pending |
| Test account for AniList writes | Verify sync flow without affecting user's actual list | — Pending |
| Separate test file per scraper | Easy to isolate failures, per-scraper debugging | — Pending |

---
*Last updated: 2025-01-24 after initialization*
