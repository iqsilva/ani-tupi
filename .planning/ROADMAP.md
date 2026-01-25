# ROADMAP: ani-tupi Integration Test Suite

**4 phases** | **20 v1 requirements** | All mapped ✓

## Phase Overview

| Phase | Name | Goal | Requirements | Success Criteria |
|-------|------|------|--------------|------------------|
| 1 | Scraper Real-API Testing | Verify search→episodes→source workflow with real scrapers | SCRAPER-01..05, SEARCH-01..04 | All 3 scrapers tested, video URLs verified playable |
| 2 | AniList Integration | Fuzzy match and sync watch history to AniList | ANILIST-01..05 | Title mapping works, sync to AniList verified with test account |
| 3 | Manga Workflows | Real manga scraping with Playwright and page extraction | MANGA-01..04 | Chapter discovery, page extraction, PDF conversion verified |
| 4 | Error Handling | Graceful recovery from common failures | ERROR-01..04 | All error cases handled without crashes, helpful messages shown |

---

## Phase 1: Scraper Real-API Testing

**Duration:** Implement first
**Goal:** Verify that search→episode_list→video_source workflow succeeds end-to-end with REAL scraper APIs for all three sources.

**Requirements:**
- SCRAPER-01: AnimeFirePlus e2e test
- SCRAPER-02: AnimesDigital e2e test
- SCRAPER-03: AnimesOnlineCC e2e test
- SCRAPER-04: Video URL validation
- SCRAPER-05: Error handling in scraper layer
- SEARCH-01: Search completes without timeout
- SEARCH-02: Episode parsing extracts metadata
- SEARCH-03: Edge cases (seasons, dubbed, etc)
- SEARCH-04: Selenium + Firefox video extraction

**Success Criteria:**
1. `test_animefire_search_episodes_video_source()` — Search "Dandadan" in AnimeFirePlus, fetch episodes, extract video URL, verify HTTP 200
2. `test_animesdigital_search_episodes_video_source()` — Same for AnimesDigital (dubbed anime)
3. `test_animesonlinecc_search_episodes_video_source()` — Same for AnimesOnlineCC (PT-BR subtitles)
4. `test_video_urls_are_playable()` — All extracted URLs respond with 200 status
5. `test_scraper_handles_timeout()` — Timeout doesn't crash, returns helpful error
6. `test_episode_parsing_handles_edge_cases()` — Dubbed/subbed/missing chapters parsed correctly
7. Tests located in: `tests/test_scrapers_real_api_integration.py`
8. All tests pass with real APIs (may be flaky if sites change)

**Deliverables:**
- New file: `tests/test_scrapers_real_api_integration.py` with 9+ test classes
- Fixtures for: scraper instances, test anime queries, common error scenarios
- Documentation: README in tests/ explaining real-API test requirements (Firefox, geckodriver, etc)

---

## Phase 2: AniList Integration

**Duration:** Implement after Phase 1
**Goal:** Verify that scraped anime titles correctly map to AniList entries via fuzzy matching, and watch history syncs to AniList without data loss.

**Requirements:**
- ANILIST-01: Fuzzy title matching
- ANILIST-02: Correct AniList mapping (no false matches)
- ANILIST-03: Watch history sync via GraphQL
- ANILIST-04: Token refresh for expired OAuth
- ANILIST-05: Respect rate limits

**Success Criteria:**
1. `test_anilist_fuzzy_match_valid_title()` — "Boku no Hero Academia" fuzzy matches to AniList "My Hero Academia"
2. `test_anilist_fuzzy_match_no_false_matches()` — "Blue Lock" doesn't match "Blue Lock Navi" (false positive)
3. `test_anilist_sync_episode_progress()` — Mark episode 5 as watched, GraphQL mutation updates AniList (test account only)
4. `test_anilist_sync_respects_rate_limit()` — 500+ rapid requests don't crash, backoff applied
5. `test_anilist_token_refresh_on_expiry()` — Expired token triggers re-auth flow
6. `test_anilist_mapping_persistence()` — Previous mappings loaded from cache, no re-matching
7. Tests located in: `tests/test_anilist_real_api_integration.py`
8. Test account setup documented (credentials in secure location)

**Deliverables:**
- New file: `tests/test_anilist_real_api_integration.py` with test classes
- Test account setup guide: `.planning/ANILIST_TEST_ACCOUNT_SETUP.md`
- Fixtures for: AniListService with real token, test anime IDs, GraphQL mutations
- Rate limit monitoring: logs when approaching 500 req/min limit

---

## Phase 3: Manga Workflows

**Duration:** Implement after Phase 2
**Goal:** Verify manga chapter discovery, page extraction, and PDF conversion work end-to-end with Mugiwaras API.

**Requirements:**
- MANGA-01: Chapter discovery with real API
- MANGA-02: Page extraction to PDF
- MANGA-03: Age verification handling
- MANGA-04: Playwright timeout handling

**Success Criteria:**
1. `test_mugiwaras_search_real_api()` — Search "Dandadan" returns chapters
2. `test_mugiwaras_chapter_list_ordered()` — Chapters sorted descending (latest first)
3. `test_mugiwaras_page_extraction()` — Get chapter pages, filter noise (logos)
4. `test_mugiwaras_pdf_conversion()` — Pages converted to PDF, readable
5. `test_mugiwaras_age_verification_modal()` — Modal detected and handled
6. `test_mugiwaras_playwright_timeout()` — Timeout returns empty list, doesn't crash
7. Tests located in: `tests/test_manga_real_api_integration.py`
8. Reuse existing `test_manga_workflow_integration.py` as baseline

**Deliverables:**
- New file: `tests/test_manga_real_api_integration.py` with real API calls
- Enhanced `test_manga_workflow_integration.py` fixtures for real responses
- PDF generation testing (verify output is valid PDF)

---

## Phase 4: Error Handling & Recovery

**Duration:** Implement after Phase 3
**Goal:** Verify that common failure modes (network, parsing, missing elements) don't crash the app and show helpful errors to users.

**Requirements:**
- ERROR-01: Network timeout handling
- ERROR-02: Malformed HTML handling
- ERROR-03: Missing element handling
- ERROR-04: Rate limit detection

**Success Criteria:**
1. `test_scraper_network_timeout()` — 30s timeout returns error, doesn't block forever
2. `test_scraper_malformed_html()` — Broken HTML parsed without crash
3. `test_scraper_missing_video_element()` — Missing player returns helpful error
4. `test_anilist_rate_limit_detection()` — 429/Too Many Requests detected, user alerted
5. `test_anime_service_error_recovery()` — Service layer gracefully degrades (falls back to other scraper)
6. `test_manga_missing_chapter_pages()` — Chapter with no pages returns empty, doesn't crash
7. `test_error_messages_user_friendly()` — All error messages actionable and clear
8. Tests located in: `tests/test_error_handling_integration.py`

**Deliverables:**
- New file: `tests/test_error_handling_integration.py` with error scenario tests
- Error message audit: `.planning/ERROR_MESSAGES.md` (what users see)
- Fixture: `mock_network_errors()` for simulating failures

---

## Implementation Notes

### Test Infrastructure

**Fixtures Required:**
- Real scraper instances (AnimeFirePlus, AnimesDigital, AnimesOnlineCC)
- Test anime titles (evergreen: "Dandadan", "Jujutsu Kaisen", "Blue Lock")
- AniList test account credentials (stored securely, not in repo)
- Firefox/geckodriver setup verified
- Network error simulators (timeouts, 503s, rate limits)

**Test File Structure:**
```
tests/
  test_scrapers_real_api_integration.py      (Phase 1)
  test_anilist_real_api_integration.py       (Phase 2)
  test_manga_real_api_integration.py         (Phase 3)
  test_error_handling_integration.py         (Phase 4)
  conftest.py                                (shared fixtures)
```

**Running Real-API Tests:**
```bash
# All real-API tests (may take 5-10 minutes, may fail if APIs down)
uv run pytest tests/test_*_real_api_integration.py -v

# Single scraper
uv run pytest tests/test_scrapers_real_api_integration.py::TestAnimeFire -v

# Error handling only
uv run pytest tests/test_error_handling_integration.py -v
```

### Constraints & Risks

**Risk: External API Changes**
- AnimeFire HTML structure changes → parsing fails
- AniList rate limit behavior changes → tests timeout
- Mugiwaras age verification modal HTML changes
- Mitigation: Tests use stable, popular anime titles; error recovery tests cover degradation

**Risk: Rate Limiting**
- AniList: 500 requests/minute (Phase 2 tests may hit this)
- Mitigation: Tests batch requests, use test account with separate rate limit bucket if available

**Risk: Flakiness**
- Network timeouts, site downtime, slow parsing
- Mitigation: Tests are local-only (manual run), acceptable to fail if APIs unavailable; timeouts set conservatively (15-30s)

**Risk: Token Expiry**
- AniList OAuth tokens expire ~6 months
- Mitigation: Phase 2 setup includes token refresh test; CI/CD won't run Phase 2 (local only)

---

## Success Metrics

- [ ] Phase 1: 3 scrapers + 4 search tests pass (9+ tests)
- [ ] Phase 2: AniList fuzzy match + sync verified (6+ tests)
- [ ] Phase 3: Manga chapter discovery → PDF conversion verified (7+ tests)
- [ ] Phase 4: All error scenarios handled gracefully (7+ tests)
- [ ] Total: 29+ new integration tests using real APIs
- [ ] No mocked responses in Phase 1-4 tests
- [ ] Documentation complete: setup guides, error handling, rate limits
- [ ] All tests can run locally without CI/CD (manual trigger only)

---
*Roadmap created: 2025-01-24*
*Last updated: 2025-01-24 after initial planning*
