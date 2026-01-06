# Tasks: Automatic Intro/Outro Skip Integration

**Change ID:** `add-intro-outro-skip`

---

## Task Breakdown

### Phase 1: Configuration & Models (Foundation)

- [ ] **1.1** Add `SkipSettings` class to `models/config.py`
  - Fields: enabled, skip_intros, skip_outros, skip_recaps, skip_previews, api_client_id, cache_duration_days
  - Environment variable support: `ANI_TUPI__SKIP__*`
  - Default values: enabled=True, skip_intros=True, skip_outros=True, others=False
  - Validation: cache_duration_days between 1-90
  - **Depends on:** None
  - **Tests:** Unit test for settings loading, env var overrides

- [ ] **1.2** Create `SkipInterval` Pydantic model in `models/models.py`
  - Fields: type (str), start (float), end (float)
  - Type values: "op", "ed", "recap", "preview"
  - Validation: start < end, both >= 0
  - Add `type_label` property for Brazilian Portuguese labels
  - **Depends on:** None
  - **Tests:** Unit test for validation, label generation

- [ ] **1.3** Integrate `SkipSettings` into `AppSettings`
  - Add `skip: SkipSettings` field to AppSettings
  - Update settings singleton initialization
  - **Depends on:** 1.1
  - **Tests:** Integration test with full settings loading

### Phase 2: Anime Skip API Client (Service Layer)

- [ ] **2.1** Create `services/anime_skip_service.py` skeleton
  - Class `AnimeSkipService` with httpx client
  - Initialize with API endpoint and client ID from settings
  - Add base GraphQL request method
  - **Depends on:** 1.1
  - **Tests:** Unit test for initialization

- [ ] **2.2** Implement `search_show()` method
  - GraphQL query: `searchShows(search: str, limit: int)`
  - Parse response: extract show ID, name, externalIds
  - Return list of show candidates
  - Error handling: network errors, API errors, empty results
  - **Depends on:** 2.1
  - **Tests:** Unit test with mocked API, integration test with real API

- [ ] **2.3** Implement `map_anilist_to_show()` method
  - Use AniList ID or anime title to find Anime Skip show ID
  - Try exact externalId match first (source: "anilist")
  - Fallback to fuzzy title match (similar to anilist_discovery.py)
  - Cache mapping: `show_map:{anilist_id}` → show_id (90-day TTL)
  - **Depends on:** 2.2
  - **Tests:** Unit test for mapping logic, integration test with known anime

- [ ] **2.4** Implement `fetch_timestamps()` method
  - GraphQL query: `show(id: UUID) { episodes(episodeNumber: int) { timestamps } }`
  - Parse timestamps: group by typeId, pair consecutive timestamps
  - Convert to `SkipInterval` objects
  - Filter by enabled types (intros, outros based on settings)
  - **Depends on:** 1.2, 2.3
  - **Tests:** Unit test with mock response, test timestamp pairing logic

- [ ] **2.5** Implement caching layer for timestamps
  - Cache key: `skip:{anilist_id}:{episode_number}`
  - Use DiskCache with configurable TTL (default 30 days)
  - Cache show mapping separately (longer TTL)
  - **Depends on:** 2.4
  - **Tests:** Unit test for cache hit/miss, TTL expiration

- [ ] **2.6** Add error handling and logging
  - Log API requests (debug level)
  - Log API errors (warn level, don't crash)
  - Handle rate limiting (429 status code)
  - Handle missing data (show not found, no timestamps)
  - Return empty list on any error (graceful degradation)
  - **Depends on:** 2.4
  - **Tests:** Unit test for each error scenario

### Phase 3: MPV IPC Enhancement (Playback Integration)

- [ ] **3.1** Extend `play_episode()` signature in `utils/video_player.py`
  - Add optional parameter: `skip_intervals: list[SkipInterval] | None = None`
  - Update docstring
  - **Depends on:** 1.2
  - **Tests:** Unit test for signature compatibility

- [ ] **3.2** Implement playback position monitoring
  - Subscribe to `time-pos` property changes via MPV IPC
  - Add to `_ipc_event_loop()`: handle property-change events
  - Track current playback position (seconds)
  - **Depends on:** 3.1, existing MPV IPC infrastructure
  - **Tests:** Integration test with mock MPV socket

- [ ] **3.3** Implement skip trigger logic
  - Check if current_time within any skip interval
  - Track processed intervals (set) to avoid re-triggering
  - Send seek command when entering unprocessed interval: `["seek", interval.end, "absolute"]`
  - Mark interval as processed
  - **Depends on:** 3.2
  - **Tests:** Unit test for trigger logic, mock seek command verification

- [ ] **3.4** Add OSD notifications during skip
  - Send show-text command when skipping: `["show-text", "⏩ Pulando abertura...", "3000"]`
  - Use interval type_label for localized messages
  - Test on-screen display timing
  - **Depends on:** 3.3
  - **Tests:** Integration test verifying OSD command sent

- [ ] **3.5** Handle edge cases in skip logic
  - User manual seek during skip interval (don't re-trigger)
  - Playback speed changes (adjust position monitoring)
  - Seek backward into already-skipped interval (allow re-skip)
  - Multiple consecutive intervals (skip each once)
  - **Depends on:** 3.3
  - **Tests:** Unit tests for each edge case scenario

### Phase 4: Service Integration (Orchestration)

- [ ] **4.1** Integrate skip service into `anime_service.py`
  - Import `AnimeSkipService` and `SkipInterval`
  - Check if skip enabled before playback
  - Fetch skip intervals if anilist_id available
  - Pass intervals to `play_episode()` call
  - **Depends on:** 2.6, 3.1
  - **Tests:** Integration test for full flow

- [ ] **4.2** Add logging for skip operations
  - Log when fetching timestamps (debug)
  - Log skip intervals found (info)
  - Log skip triggers during playback (debug)
  - Log API errors (warn)
  - **Depends on:** 4.1
  - **Tests:** Verify logs in integration tests

- [ ] **4.3** Handle missing AniList ID scenario
  - If anilist_id is None, skip timestamp fetching
  - Log info message: "Skip unavailable (no AniList ID)"
  - Continue playback normally
  - **Depends on:** 4.1
  - **Tests:** Unit test for no-anilist-id path

### Phase 5: CLI & User Controls

- [ ] **5.1** Add CLI command to test API connectivity
  - New command: `ani-tupi test-skip [--show-id UUID] [--episode N]`
  - Test API reachability
  - Show example timestamp query results
  - Display cache status
  - **Depends on:** 2.6
  - **Tests:** E2E test for CLI command

- [ ] **5.2** Add skip status to debug output
  - Include skip settings in `--debug` mode output
  - Show skip intervals fetched before playback
  - Display cache hit/miss statistics
  - **Depends on:** 4.2
  - **Tests:** Manual verification with --debug flag

### Phase 6: Testing & Documentation

- [ ] **6.1** Write unit tests for all new models
  - SkipSettings validation
  - SkipInterval validation and labels
  - Test environment variable overrides
  - **Depends on:** 1.1, 1.2
  - **Coverage target:** 100%

- [ ] **6.2** Write unit tests for AnimeSkipService
  - Mock API responses for all methods
  - Test error handling paths
  - Test cache behavior
  - Test timestamp parsing logic
  - **Depends on:** 2.6
  - **Coverage target:** 90%

- [ ] **6.3** Write integration tests for skip flow
  - Real API calls (with mock fallback for CI)
  - Test known anime (Dandadan, etc.)
  - Verify cache persistence
  - Test playback with skip intervals
  - **Depends on:** 4.1, 3.4
  - **Coverage target:** 80%

- [ ] **6.4** Write E2E tests for user scenarios
  - Happy path: play episode with intro skip
  - No API data: play without timestamps
  - Disabled setting: verify no skipping
  - Network failure: graceful degradation
  - **Depends on:** All previous tasks
  - **Coverage target:** Key user paths covered

- [ ] **6.5** Update README.md with skip feature
  - Document skip functionality
  - Explain how to disable (env var)
  - List supported segment types
  - Credit Anime Skip API
  - **Depends on:** All implementation tasks
  - **Tests:** Manual review

- [ ] **6.6** Update CLAUDE.md with implementation notes
  - Document Anime Skip API integration
  - Explain skip interval caching strategy
  - Note dependencies on MPV IPC
  - Add troubleshooting section
  - **Depends on:** All implementation tasks
  - **Tests:** Manual review

### Phase 7: Polish & Validation

- [ ] **7.1** Performance optimization
  - Ensure API queries don't block playback start
  - Add timeout to API requests (5 seconds)
  - Verify cache queries are fast (<10ms)
  - **Depends on:** 4.1
  - **Tests:** Performance benchmarks

- [ ] **7.2** Cross-platform testing
  - Test on Linux (primary platform)
  - Test on macOS (if available)
  - Test on Windows (via CI or contributor)
  - Verify IPC socket compatibility
  - **Depends on:** All implementation tasks
  - **Tests:** Manual testing on each platform

- [ ] **7.3** Validate with OpenSpec
  - Run `openspec validate add-intro-outro-skip --strict`
  - Resolve any validation errors
  - Ensure all requirements have scenarios
  - **Depends on:** All spec files created
  - **Tests:** Validation command passes

---

## Task Dependencies Graph

```
1.1 ─┬─> 1.3 ───> 2.1 ───> 2.2 ───> 2.3 ───> 2.4 ───┬─> 2.5 ───> 2.6 ───┐
     │                                                │                    │
1.2 ─┴────────────────────────────────────────────> 3.1 ───> 3.2 ─┐       │
                                                                    │       │
                                                              3.3 <─┘       │
                                                                │           │
                                                              3.4           │
                                                                │           │
                                                              3.5           │
                                                                │           │
                                                              4.1 <─────────┘
                                                                │
                                                          ┌─────┴─────┐
                                                          │           │
                                                        4.2         4.3
                                                          │           │
                                                          └─────┬─────┘
                                                                │
                                                          ┌─────┴─────┐
                                                          │           │
                                                        5.1         5.2
                                                          │           │
                                                          └─────┬─────┘
                                                                │
                                                        ┌───────┼───────┐
                                                        │       │       │
                                                      6.1     6.2     6.3
                                                        │       │       │
                                                        └───┬───┴───┬───┘
                                                            │       │
                                                          6.4     6.5
                                                            │       │
                                                            └───┬───┘
                                                                │
                                                              6.6
                                                                │
                                                          ┌─────┴─────┐
                                                          │           │
                                                        7.1         7.2
                                                          │           │
                                                          └─────┬─────┘
                                                                │
                                                              7.3
```

---

## Parallelizable Tasks

The following tasks can be worked on in parallel after their dependencies are met:

**After Phase 1 complete:**
- 2.1 (API client skeleton) + 3.1 (play_episode signature)

**After Phase 2.6 complete:**
- 3.2-3.5 (MPV integration) in parallel with 5.1 (CLI command)

**After Phase 4 complete:**
- 6.1, 6.2, 6.3 (different test suites)

**After implementation complete:**
- 6.5 (README) + 6.6 (CLAUDE.md) + 7.1 (performance)

---

## Estimated Effort

- **Phase 1:** 2-3 hours (simple config and models)
- **Phase 2:** 6-8 hours (API integration, caching, error handling)
- **Phase 3:** 4-5 hours (MPV IPC enhancement, skip logic)
- **Phase 4:** 2-3 hours (service orchestration)
- **Phase 5:** 1-2 hours (CLI commands)
- **Phase 6:** 6-8 hours (comprehensive testing)
- **Phase 7:** 2-3 hours (polish and validation)

**Total:** ~23-32 hours of development work

---

## Critical Path

1.1 → 1.2 → 2.1 → 2.2 → 2.3 → 2.4 → 2.6 → 4.1 → 6.3 → 7.3

This is the minimum sequence to achieve a working skip feature with integration tests.

---

## Validation Checkpoints

- **After Phase 1:** Settings can be loaded, models validate correctly
- **After Phase 2:** API client can fetch timestamps for known anime
- **After Phase 3:** Mock MPV integration can trigger skip logic
- **After Phase 4:** Full playback with skip works end-to-end
- **After Phase 6:** All tests pass, coverage targets met
- **After Phase 7:** OpenSpec validation passes, ready for approval
