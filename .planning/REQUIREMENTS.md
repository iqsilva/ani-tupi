# Requirements: ani-tupi Integration Test Suite

**Defined:** 2025-01-24
**Core Value:** Detect real-world workflow bugs (search fails, episodes don't parse, video URLs break, AniList sync fails) BEFORE users encounter them in production.

## v1 Requirements

### Scraper Workflows

- [ ] **SCRAPER-01**: Test AnimeFirePlus search → episode list → video source extraction (end-to-end with real API)
- [ ] **SCRAPER-02**: Test AnimesDigital search → episode list → video source extraction (end-to-end with real API)
- [ ] **SCRAPER-03**: Test AnimesOnlineCC search → episode list → video source extraction (end-to-end with real API)
- [ ] **SCRAPER-04**: Validate extracted video URLs return HTTP 200 status (playable)
- [ ] **SCRAPER-05**: Handle scraper errors gracefully (timeout, missing elements, malformed HTML)

### Search & Episode Parsing

- [ ] **SEARCH-01**: Search workflow completes with real scraper APIs (no timeouts)
- [ ] **SEARCH-02**: Episode list parsing extracts chapter/season information correctly
- [ ] **SEARCH-03**: Handle edge cases: dubbed/subbed variants, missing episodes, pagination
- [ ] **SEARCH-04**: Video source extraction works with Selenium + Firefox

### AniList Integration

- [ ] **ANILIST-01**: AniList title discovery via fuzzy matching (Levenshtein distance)
- [ ] **ANILIST-02**: Scraper titles map to correct AniList entries (no false matches)
- [ ] **ANILIST-03**: Watch history syncs to AniList via GraphQL (requires test account)
- [ ] **ANILIST-04**: Token refresh handles expired OAuth tokens
- [ ] **ANILIST-05**: Respect rate limits (500 requests/minute max)

### Manga Workflows

- [ ] **MANGA-01**: Mugiwaras chapter discovery with real API (pagination if needed)
- [ ] **MANGA-02**: Chapter page extraction (images convert to PDF)
- [ ] **MANGA-03**: Handle age verification modal if present
- [ ] **MANGA-04**: Playlist/Playwright timeouts handled gracefully

### Error Recovery

- [ ] **ERROR-01**: Network timeout doesn't crash (graceful fallback)
- [ ] **ERROR-02**: Malformed page structure doesn't crash parser
- [ ] **ERROR-03**: Missing video elements surfaces helpful error message
- [ ] **ERROR-04**: Rate limiting detected and reported to user

## v2 Requirements

### Performance & Optimization

- **PERF-01**: Cache scraper responses to reduce API calls during development
- **PERF-02**: Parallel test execution for faster feedback
- **PERF-03**: Test run reports with timing per scraper

### Monitoring & Observability

- **MONITOR-01**: Test results recorded to file for trending
- **MONITOR-02**: Alert on new scraper failures
- **MONITOR-03**: Track which scrapers are most stable

### Extended Coverage

- **EXTEND-01**: Test mobile-responsive pages (AnimesDigital dubbed detection)
- **EXTEND-02**: Test with various search queries (season numbers, romanized names)
- **EXTEND-03**: AniList read lists (WATCHING, PLANNING, COMPLETED)

## Out of Scope

| Requirement | Reason |
|-------------|--------|
| Mocked API responses | Whole point is to catch real API issues that mocks hide |
| CI/CD pipeline integration | Local development only; tests may fail if sites are down (acceptable) |
| Modify external data | Read-only queries only; don't corrupt AniList or scraper data |
| Performance benchmarking | Focus on correctness, not speed |
| Mobile app testing | CLI only; no mobile support |
| Streaming playback validation | Verify URL is valid, don't actually play video (resource-intensive) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCRAPER-01 | Phase 1 | Pending |
| SCRAPER-02 | Phase 1 | Pending |
| SCRAPER-03 | Phase 1 | Pending |
| SCRAPER-04 | Phase 1 | Pending |
| SCRAPER-05 | Phase 1 | Pending |
| SEARCH-01 | Phase 1 | Pending |
| SEARCH-02 | Phase 1 | Pending |
| SEARCH-03 | Phase 1 | Pending |
| SEARCH-04 | Phase 1 | Pending |
| ANILIST-01 | Phase 2 | Pending |
| ANILIST-02 | Phase 2 | Pending |
| ANILIST-03 | Phase 2 | Pending |
| ANILIST-04 | Phase 2 | Pending |
| ANILIST-05 | Phase 2 | Pending |
| MANGA-01 | Phase 3 | Pending |
| MANGA-02 | Phase 3 | Pending |
| MANGA-03 | Phase 3 | Pending |
| MANGA-04 | Phase 3 | Pending |
| ERROR-01 | Phase 4 | Pending |
| ERROR-02 | Phase 4 | Pending |
| ERROR-03 | Phase 4 | Pending |
| ERROR-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2025-01-24*
*Last updated: 2025-01-24 after initial definition*
