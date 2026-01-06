# Proposal: Automatic Intro/Outro Skip Integration

**Change ID:** `add-intro-outro-skip`
**Status:** Proposed
**Priority:** High
**Date:** 2026-01-06

---

## Why

**Problem:** Users must manually skip intros and outros in every episode, disrupting the binge-watching experience. This is tedious for series with long openings (90+ seconds) and endings that repeat across all episodes.

**Impact:** Poor user experience during sequential episode watching. Users of streaming platforms (Netflix, Crunchyroll, Jellyfin with plugins) have come to expect automatic skip functionality for repetitive content.

**Opportunity:** Integrate with Anime Skip API (crowdsourced timestamp database) to automatically skip intros, outros, recaps, and previews. Enable by default with per-anime override capability.

---

## What Changes

- **New Service:** `services/anime_skip_service.py` - GraphQL client for Anime Skip API integration
- **New Models:** `SkipInterval` and `SkipSettings` Pydantic models in `models/models.py` and `models/config.py`
- **Modified:** `utils/video_player.py` - Add `skip_intervals` parameter to `play_episode()`, implement position monitoring and auto-seek
- **Modified:** `services/anime_service.py` - Fetch skip intervals before playback, pass to video player
- **Modified:** `models/config.py` - Add `skip` settings section with enable toggles and API configuration
- **New Cache:** Skip intervals cached in DiskCache with 30-day TTL (key: `skip:{anilist_id}:{episode_number}`)
- **New CLI:** `ani-tupi test-skip` command to test API connectivity and query timestamps
- **Enhancement:** MPV IPC event loop monitors `time-pos` property and triggers seek commands during skip zones

---

## Impact

- **Affected specs:** anime-skip-api-integration (new), skip-playback-control (new), configuration-management (modified)
- **Affected code:**
  - `utils/video_player.py` (IPC event loop extension)
  - `services/anime_service.py` (pre-playback skip fetch)
  - `models/config.py` (settings extension)
  - `models/models.py` (new data models)
- **Dependencies:** Requires existing MPV IPC infrastructure from `add-mpv-ipc-keybindings` change
- **External API:** anime-skip.com (test endpoint: http://test.api.anime-skip.com/graphql)

---

## Executive Summary

Implement automatic intro/outro skipping during MPV playback using the Anime Skip API (anime-skip.com):
- Query API for timestamp data using AniList ID + episode number
- Automatically seek past intro/outro segments during playback
- Enabled by default (user can disable globally or per-anime in settings)
- Support intro openings and outro endings initially (expand to recap/preview later)
- Cache timestamp data to reduce API calls and support offline playback
- Fallback gracefully when API data unavailable

This builds on the existing MPV IPC infrastructure from `add-mpv-ipc-keybindings` change.

---

## Problem Statement

**Current Behavior:**
- User watches anime episodes via `play_episode()` with no intro/outro awareness
- User must manually seek past intros (typically 90-120 seconds) every episode
- User must manually seek past outros (typically 90 seconds) at the end
- No integration with crowdsourced timestamp databases

**Desired Behavior:**
- System fetches intro/outro timestamps from Anime Skip API before playback
- MPV automatically seeks past intro when playback reaches the intro start time
- MPV automatically seeks past outro when playback reaches the outro start time
- User sees subtle OSD notification: "Pulando abertura..." (skipping intro)
- System respects user preference to disable auto-skip globally or per-anime
- Timestamps cached locally to work offline and reduce API load

---

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ani-tupi Application                         │
│  (commands/anime.py → anime_service.py → utils/video_player.py)│
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│       Anime Skip Service (services/anime_skip_service.py)       │
│  - Query Anime Skip API via GraphQL                             │
│  - Map AniList ID → Anime Skip show ID                          │
│  - Fetch timestamp data for episode                             │
│  - Cache timestamps in SQLite (diskcache)                       │
│  - Return skip intervals: [{type: "op", start: 90, end: 210}]   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│        VideoPlayerIPC (Enhanced utils/video_player.py)          │
│  - Receives skip intervals before playback                      │
│  - Monitors playback position via IPC                           │
│  - Triggers seek command when entering skip zone                │
│  - Shows OSD notification: "Pulando abertura..."                │
│  - Respects user skip_enabled setting                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    IPC Socket (Unix/Windows)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MPV Media Player                           │
│  - Reports playback position via property-change events         │
│  - Receives seek commands from ani-tupi                         │
│  - Displays OSD messages during skip actions                   │
│  - Continues normal playback                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **AnimeSkipService** (`services/anime_skip_service.py` - new)
   - GraphQL client for Anime Skip API (test: http://test.api.anime-skip.com/graphql)
   - Query `searchShows` to map AniList ID → Anime Skip show ID
   - Query timestamps for specific episode (show_id + episode_number)
   - Parse response into standardized skip intervals
   - Cache results in DiskCache (30-day TTL, timestamps rarely change)

2. **Skip Interval Data Model** (`models/models.py` - extend)
   - New Pydantic model: `SkipInterval(type: str, start: float, end: float)`
   - Types: "op" (opening), "ed" (ending), "recap", "preview"
   - Start/End in seconds from video start
   - Validation: start < end, both non-negative

3. **VideoPlayerIPC Enhancement** (`utils/video_player.py` - modify)
   - Accept optional `skip_intervals` parameter in `play_episode()`
   - Monitor `time-pos` property changes via IPC
   - When playback enters skip zone: send seek command to skip end
   - Show OSD: "⏩ Pulando abertura..." (3 second display)
   - Track which intervals already skipped (avoid re-triggering on seek)

4. **Configuration Settings** (`models/config.py` - extend)
   - New `SkipSettings` class:
     - `enabled: bool = True` (global enable/disable)
     - `skip_intros: bool = True` (skip openings)
     - `skip_outros: bool = True` (skip endings)
     - `skip_recaps: bool = False` (skip recaps - future)
     - `skip_previews: bool = False` (skip next episode previews - future)
     - `api_client_id: str` (Anime Skip API client ID)
     - `cache_duration_days: int = 30` (timestamp cache TTL)

5. **Integration with anime_service** (`services/anime_service.py` - modify)
   - Before calling `play_episode()`, check if skip enabled
   - If enabled and anilist_id available: fetch skip intervals
   - Pass intervals to `play_episode()` call
   - Handle API errors gracefully (log, continue without skipping)

---

## Scope & Deliverables

### Capability 1: Anime Skip API Integration
- GraphQL client for Anime Skip API
- Show search by AniList ID mapping (via external ID or title fuzzy match)
- Timestamp query by show ID + episode number
- Authentication via X-Client-ID header (use shared dev key initially)
- Error handling for API unavailability, rate limits, missing data

### Capability 2: Skip Interval Management
- Pydantic model for skip intervals with validation
- DiskCache-based timestamp persistence (SQLite)
- TTL management (30-day default, configurable)
- Cache key format: `skip:{anilist_id}:{episode_number}`

### Capability 3: Playback Position Monitoring
- Subscribe to MPV `time-pos` property changes via IPC
- Detect when playback enters skip interval
- Trigger seek command to interval end
- Track processed intervals to avoid re-triggering
- Handle edge cases (user manual seek during skip, playback speed changes)

### Capability 4: User Notifications
- OSD messages during skip actions:
  - "⏩ Pulando abertura..." (when skipping intro)
  - "⏩ Pulando encerramento..." (when skipping outro)
- Subtle styling (bottom-right, 3-second duration)
- Localized messages (Brazilian Portuguese)

### Capability 5: Configuration Management
- Global skip enable/disable setting
- Per-type controls (intro, outro, recap, preview)
- API credentials configuration
- CLI command to test API connectivity: `ani-tupi test-skip`

---

## Technical Details

### Anime Skip API Integration

**API Endpoints:**
- Test: `http://test.api.anime-skip.com/graphql`
- Production: `https://api.anime-skip.com/graphql` (use after testing)

**Authentication:**
- Header: `X-Client-ID: ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE` (shared dev key)
- Rate limits apply to shared key (production should use custom client ID)

**GraphQL Queries:**

1. **Search Shows** (map AniList ID → Anime Skip show ID):
```graphql
{
  searchShows(search: "Dandadan", limit: 5) {
    id
    name
    originalName
    externalIds {
      source
      id
    }
  }
}
```

2. **Get Timestamps** (fetch skip intervals for episode):
```graphql
{
  show(id: "show-uuid") {
    episodes(episodeNumber: 3) {
      timestamps {
        typeId
        at
        episodeId
      }
    }
  }
}
```

**Response Mapping:**
- `typeId`: "op" (opening), "ed" (ending), "recap", "preview", "mixed-ed", "mixed-op"
- `at`: timestamp in seconds (float)
- Parse pairs: consecutive timestamps with same typeId form interval (start, end)

### Skip Interval Processing

**Data Flow:**
1. Fetch timestamps from API/cache
2. Parse into `SkipInterval` objects
3. Sort by start time (ascending)
4. Validate no overlapping intervals
5. Pass to `play_episode()` as list

**Playback Monitoring:**
```python
# In IPC event loop
current_time = mpv.get_property("time-pos")  # seconds
for interval in skip_intervals:
    if interval.start <= current_time < interval.end:
        if interval not in processed_intervals:
            # Trigger skip
            mpv.command("seek", interval.end, "absolute")
            mpv.command("show-text", f"⏩ Pulando {interval.type_label}...")
            processed_intervals.add(interval)
```

### Configuration Schema

```python
class SkipSettings(BaseModel):
    """Intro/outro skip configuration."""

    enabled: bool = Field(True, description="Enable automatic skip")
    skip_intros: bool = Field(True, description="Skip opening themes")
    skip_outros: bool = Field(True, description="Skip ending themes")
    skip_recaps: bool = Field(False, description="Skip episode recaps")
    skip_previews: bool = Field(False, description="Skip next episode previews")
    api_client_id: str = Field(
        "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE",
        description="Anime Skip API client ID"
    )
    cache_duration_days: int = Field(
        30,
        ge=1,
        le=90,
        description="Timestamp cache duration (days)"
    )
```

**Environment Variables:**
- `ANI_TUPI__SKIP__ENABLED=false` (disable globally)
- `ANI_TUPI__SKIP__API_CLIENT_ID=custom-id` (production client ID)

### Cache Implementation

**Key Format:** `skip:{anilist_id}:{episode_number}`

**Example:**
```python
from utils.cache_manager import get_cache

cache = get_cache()
key = f"skip:{20464}:{3}"  # Dandadan, Episode 3
intervals = cache.get(key)
if not intervals:
    intervals = anime_skip_service.fetch_timestamps(anilist_id=20464, episode=3)
    cache.set(key, intervals, expire=30*24*3600)  # 30 days
```

---

## Dependencies

**New Python Dependencies:**
- `httpx` (already installed - use for GraphQL requests)
- No additional dependencies needed

**External Services:**
- Anime Skip API (anime-skip.com)
- Requires internet connection for initial timestamp fetch
- Graceful degradation when API unavailable

**Internal Dependencies:**
- Builds on `add-mpv-ipc-keybindings` change (IPC infrastructure required)
- Requires AniList ID available (from search or AniList integration)

---

## Breaking Changes

None. This is an additive feature with opt-out capability.

**Backward Compatibility:**
- `play_episode()` signature gains optional parameter: `skip_intervals: list[SkipInterval] | None = None`
- Defaults to `None` (no skipping) if not provided
- Existing callers continue to work without modification

---

## Testing Strategy

### Unit Tests
- Mock Anime Skip API responses (search, timestamps)
- Test skip interval parsing and validation
- Test cache key generation and TTL
- Test configuration loading and environment overrides

### Integration Tests
- Real API calls to test endpoint (with mock fallback for CI)
- Verify AniList ID → Anime Skip show ID mapping
- Test timestamp fetching for known anime (Dandadan, etc.)
- Verify cache persistence across runs

### E2E Tests
- Full playback flow with skip intervals
- Mock MPV IPC to verify seek commands sent
- Test skip triggering at correct timestamps
- Test OSD message display
- Test user disable setting (skip not triggered)

### Manual Testing Scenarios
1. **Happy path**: Play Dandadan Ep 3, verify intro skip at ~90s
2. **No API data**: Play obscure anime without Anime Skip entry
3. **Disabled setting**: Disable skip globally, verify no seeking
4. **Network failure**: Disconnect internet, verify graceful fallback
5. **Cache hit**: Play same episode twice, verify no API call on second

---

## Rollback Plan

If skip functionality causes issues:
1. Set environment variable `ANI_TUPI__SKIP__ENABLED=false`
2. Skip service returns empty interval list (no seeking)
3. No playback changes (backward compatible)
4. User can also disable via settings file

**Monitoring:**
- Log all API errors (warn level, not error)
- Track skip trigger events in debug logs
- Measure API response times and cache hit rate

---

## Success Criteria

- [ ] User watching Dandadan Episode 3 sees intro skipped automatically at ~90s
- [ ] OSD message "⏩ Pulando abertura..." displays during skip
- [ ] Timestamps cached locally after first fetch (verify via cache file)
- [ ] Playback continues normally when API unavailable (no crashes)
- [ ] User can disable skip via `ANI_TUPI__SKIP__ENABLED=false`
- [ ] Works on Linux, macOS, Windows (via MPV IPC)
- [ ] Tests pass with >80% coverage for new code
- [ ] API query time <500ms (cached response <10ms)
- [ ] No false triggers (skip only once per interval)

---

## Future Enhancements (Out of Scope)

- Manual timestamp editing (UI to add/correct timestamps)
- Contribute timestamps back to Anime Skip API (mutation support)
- Per-anime override settings (disable skip for specific shows)
- Keybinding to manually trigger skip (Shift+I/O)
- Visual progress bar showing skip zones
- Support for filler episode detection
- Integration with MAL ID (in addition to AniList ID)

---

## References

- **Anime Skip API Docs:** [https://anime-skip.com/docs/api](https://anime-skip.com/docs/api)
- **API Playground (Test):** [http://test.api.anime-skip.com/graphiql](http://test.api.anime-skip.com/graphiql)
- **TypeScript Client:** [https://github.com/anime-skip/api-client-ts](https://github.com/anime-skip/api-client-ts)
- **Related Changes:** `add-mpv-ipc-keybindings` (MPV IPC infrastructure)
- **Related Code:**
  - `utils/video_player.py` (playback implementation)
  - `services/anime_service.py` (playback orchestration)
  - `models/config.py` (settings management)
  - `utils/cache_manager.py` (caching utilities)
