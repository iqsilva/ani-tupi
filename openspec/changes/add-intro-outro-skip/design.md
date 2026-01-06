# Design: Automatic Intro/Outro Skip Integration

**Change ID:** `add-intro-outro-skip`

---

## Design Overview

This design describes the architecture for integrating automatic intro/outro skipping into ani-tupi's video playback system. The solution leverages the existing MPV IPC infrastructure and adds a new service layer to query crowdsourced timestamp data from the Anime Skip API.

---

## Architectural Decisions

### Decision 1: Use Anime Skip API Instead of Local Detection

**Options Considered:**
1. **Audio fingerprinting** (like Netflix/Plex): Analyze audio patterns to detect recurring segments
2. **Manual timestamp configuration**: User defines timestamps per anime in config file
3. **Anime Skip API integration**: Use crowdsourced timestamp database

**Decision:** Option 3 (Anime Skip API)

**Rationale:**
- **Accuracy**: Crowdsourced data more reliable than automated detection for anime (varies widely in intro/outro structure)
- **Coverage**: Anime Skip has extensive database of popular anime with community contributions
- **Simplicity**: No need for complex audio analysis libraries or ML models
- **Maintainability**: External API maintained by community, not ani-tupi team
- **User convenience**: Works out-of-box without manual configuration

**Trade-offs:**
- ✅ Pros: Simple implementation, high accuracy, broad coverage, community-maintained
- ❌ Cons: External dependency, requires internet for first fetch, API rate limits

**Mitigation:**
- Cache timestamps locally (30-day TTL) to work offline
- Graceful fallback when API unavailable (no skipping, playback continues)
- Use shared dev API key initially, allow custom client ID for production

---

### Decision 2: Automatic Skip vs Manual Button

**Options Considered:**
1. **Silent automatic skip**: Skip without user confirmation
2. **On-screen button** (Netflix-style): Show "Skip Intro" button, user clicks to skip
3. **Keyboard shortcut only**: User presses key to manually skip when they want

**Decision:** Option 1 (Automatic skip)

**Rationale:**
- **User preference**: User explicitly requested "ativado por default" (enabled by default)
- **Binge-watching optimization**: Reduces friction for sequential episode watching
- **Consistency**: Matches behavior of modern streaming platforms with auto-skip
- **Keyboard-first UX**: ani-tupi is keyboard-driven CLI app, on-screen button breaks that paradigm

**Trade-offs:**
- ✅ Pros: Zero user interaction, optimal for binge-watching, matches user request
- ❌ Cons: Users who enjoy intros/outros must disable feature

**Mitigation:**
- Global enable/disable setting: `ANI_TUPI__SKIP__ENABLED=false`
- Per-type controls: disable only intros or only outros
- Clear OSD notification during skip so user aware of action
- Future enhancement: per-anime overrides for shows with unique intros

---

### Decision 3: IPC-Based Position Monitoring vs Property Observation

**Options Considered:**
1. **Poll `time-pos` property** periodically (every 500ms)
2. **Subscribe to `time-pos` property-change events** (event-driven)
3. **Use MPV Lua script** to monitor position internally in MPV

**Decision:** Option 2 (Property-change events)

**Rationale:**
- **Efficiency**: Event-driven model uses less CPU than polling
- **Accuracy**: Immediate notification when playback position changes
- **Existing infrastructure**: ani-tupi already uses IPC for keybindings (add-mpv-ipc-keybindings)
- **Python control**: Keep logic in Python (easier to maintain than Lua scripts)

**Trade-offs:**
- ✅ Pros: Efficient, accurate, builds on existing IPC system
- ❌ Cons: More complex than simple polling, requires IPC socket active

**Mitigation:**
- Fallback to no-skip if IPC unavailable (same as legacy playback mode)
- Reuse existing IPC event loop from keybindings change

---

### Decision 4: Skip Interval Storage Format

**Options Considered:**
1. **Store raw API response** (timestamps as list of floats)
2. **Store parsed intervals** (start/end pairs as objects)
3. **Store both** (raw + parsed for debugging)

**Decision:** Option 2 (Parsed intervals)

**Rationale:**
- **Simplicity**: Only store what's needed for playback
- **Type safety**: Pydantic models ensure valid data structure
- **Cache efficiency**: Smaller cache size (no redundant raw data)
- **Ease of use**: Direct consumption by playback logic

**Trade-offs:**
- ✅ Pros: Clean data model, type-safe, efficient cache
- ❌ Cons: Lose ability to re-parse if interval logic changes

**Mitigation:**
- Cache has TTL (30 days), stale data refreshed automatically
- Can clear cache manually if parsing logic updated: `ani-tupi --clear-cache skip`

---

### Decision 5: Timestamp Mapping Strategy (AniList ID → Anime Skip Show ID)

**Options Considered:**
1. **Direct ID mapping**: Assume AniList ID matches Anime Skip externalIds
2. **Title-based fuzzy search**: Use anime title to search Anime Skip API
3. **Hybrid approach**: Try ID mapping first, fallback to fuzzy title search

**Decision:** Option 3 (Hybrid approach)

**Rationale:**
- **Reliability**: Not all shows in Anime Skip have AniList external IDs linked
- **Coverage**: Fuzzy title matching increases chance of finding show
- **Efficiency**: ID mapping faster when available (skip search query)
- **Consistency**: Similar to ani-tupi's existing AniList discovery logic

**Trade-offs:**
- ✅ Pros: Maximum coverage, graceful degradation, fast when ID available
- ❌ Cons: More complex logic, potential false positives in fuzzy matching

**Mitigation:**
- Cache mapping result (90-day TTL) to avoid repeated searches
- Log fuzzy match scores for debugging
- Use high similarity threshold (>90%) for confidence

---

## Data Flow Diagrams

### Overall System Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  User Action: Select Episode to Play                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  anime_service.py: Orchestrate Playback                         │
│  - Check if skip enabled (settings.skip.enabled)                │
│  - Check if AniList ID available                                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
                   ▼ (if enabled)      ▼ (if disabled or no ID)
┌─────────────────────────────────┐   │
│ AnimeSkipService                │   │
│ - Map AniList ID → Show ID      │   │
│ - Fetch timestamps from API     │   │
│ - Parse into SkipIntervals      │   │
│ - Cache for 30 days             │   │
└──────────────┬──────────────────┘   │
               │                      │
               │ (intervals or [])    │
               └──────────┬───────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  video_player.py: play_episode()                                │
│  - Accept skip_intervals parameter                              │
│  - Launch MPV with IPC socket                                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  _ipc_event_loop(): Monitor Playback                            │
│  - Subscribe to time-pos property changes                       │
│  - Check if position within skip interval                       │
│  - Trigger seek to interval.end when detected                   │
│  - Show OSD notification                                        │
│  - Mark interval as processed                                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  MPV Player                                                      │
│  - Reports position changes via IPC                             │
│  - Executes seek commands from ani-tupi                         │
│  - Displays OSD messages                                        │
└──────────────────────────────────────────────────────────────────┘
```

### API Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  AnimeSkipService.fetch_timestamps(anilist_id, episode_number) │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Check DiskCache: skip:{anilist_id}:{episode_number}           │
└─────────────┬───────────────────────────────────┬───────────────┘
              │                                   │
         (cache hit)                         (cache miss)
              │                                   │
              ▼                                   ▼
    ┌──────────────────┐          ┌──────────────────────────────┐
    │ Return cached    │          │ Map AniList ID → Show ID     │
    │ skip intervals   │          │ (check cache first)          │
    └──────────────────┘          └──────────┬───────────────────┘
                                              │
                                              ▼
                                  ┌─────────────────────────────┐
                                  │ Query Anime Skip API:       │
                                  │ searchShows(search: title)  │
                                  └──────────┬──────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │ Find best match:            │
                                  │ - Check externalIds         │
                                  │ - Fuzzy match title (>90%)  │
                                  └──────────┬──────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │ Query Anime Skip API:       │
                                  │ show(id).episodes(number)   │
                                  │ .timestamps                 │
                                  └──────────┬──────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │ Parse timestamps:           │
                                  │ - Group by typeId           │
                                  │ - Pair into intervals       │
                                  │ - Filter by enabled types   │
                                  │ - Validate (start < end)    │
                                  └──────────┬──────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │ Cache intervals (30 days)   │
                                  │ Cache show mapping (90 days)│
                                  └──────────┬──────────────────┘
                                             │
                                             ▼
                                  ┌─────────────────────────────┐
                                  │ Return list[SkipInterval]   │
                                  └─────────────────────────────┘
```

### Skip Trigger Logic (During Playback)

```
┌──────────────────────────────────────────────────────────────┐
│  MPV reports time-pos property change: current_time = 95.3   │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  IPC Event Loop receives property-change event               │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Iterate skip_intervals: [{type:"op", start:90, end:210}]   │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Check: start <= current_time < end?                         │
│  90 <= 95.3 < 210  →  True (inside intro interval)          │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Check: interval in processed_intervals?                     │
│  False (first time entering this interval)                   │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Send MPV command: ["seek", 210, "absolute"]                │
│  (Jump to end of intro at 210 seconds)                       │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Send MPV command: ["show-text", "⏩ Pulando abertura...",   │
│                     "3000"]                                  │
│  (Show OSD message for 3 seconds)                            │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Add interval to processed_intervals set                     │
│  (Prevent re-triggering if position changes within interval) │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Continue monitoring for next position change                │
│  (Playback now at ~210s, past intro)                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Interfaces

### AnimeSkipService API

```python
class AnimeSkipService:
    """Client for Anime Skip API integration."""

    def __init__(self, api_url: str, client_id: str):
        """Initialize service with API endpoint and client ID."""
        ...

    async def search_shows(
        self,
        query: str,
        limit: int = 5
    ) -> list[AnimeSkipShow]:
        """Search shows by title.

        Returns:
            List of show candidates with id, name, externalIds
        """
        ...

    async def map_anilist_to_show(
        self,
        anilist_id: int,
        anime_title: str
    ) -> str | None:
        """Map AniList ID to Anime Skip show ID.

        Args:
            anilist_id: AniList anime ID
            anime_title: Anime title for fallback fuzzy search

        Returns:
            Anime Skip show UUID, or None if not found
        """
        ...

    async def fetch_timestamps(
        self,
        anilist_id: int,
        episode_number: int,
        anime_title: str | None = None
    ) -> list[SkipInterval]:
        """Fetch skip intervals for episode.

        Args:
            anilist_id: AniList anime ID
            episode_number: Episode number (1-indexed)
            anime_title: Anime title (optional, for mapping fallback)

        Returns:
            List of skip intervals, or empty list on error/not found
        """
        ...
```

### SkipInterval Data Model

```python
class SkipInterval(BaseModel):
    """Represents a time interval to skip during playback."""

    type: Literal["op", "ed", "recap", "preview"]
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., gt=0, description="End time in seconds")

    @field_validator("end")
    def end_after_start(cls, v, values):
        """Validate end > start."""
        if "start" in values and v <= values["start"]:
            raise ValueError("end must be greater than start")
        return v

    @property
    def type_label(self) -> str:
        """Human-readable label in Brazilian Portuguese."""
        labels = {
            "op": "abertura",
            "ed": "encerramento",
            "recap": "recap",
            "preview": "prévia"
        }
        return labels[self.type]
```

### VideoPlayer Interface Extension

```python
def play_episode(
    url: str,
    anime_title: str,
    episode_number: int,
    total_episodes: int,
    source: str,
    use_ipc: bool = True,
    debug: bool = False,
    anilist_id: int | None = None,
    skip_intervals: list[SkipInterval] | None = None,  # NEW
) -> VideoPlaybackResult:
    """Play episode with optional skip intervals.

    Args:
        skip_intervals: List of time intervals to automatically skip
                       (e.g., intros, outros). None to disable skipping.

    Returns:
        VideoPlaybackResult with exit code and action
    """
    ...
```

---

## Error Handling Strategy

### API Errors

**Scenario:** Anime Skip API unreachable or returns error

**Handling:**
1. Log warning (not error): "Anime Skip API unavailable, skipping disabled for this episode"
2. Return empty skip intervals list
3. Continue playback without skipping
4. Don't cache error responses

**Rationale:** Skip is enhancement, not core feature. Playback must continue.

### Missing Data

**Scenario:** Show or episode not found in Anime Skip database

**Handling:**
1. Log info: "No skip data found for [anime_title] Episode [N]"
2. Return empty skip intervals list
3. Cache negative result (shorter TTL: 7 days) to avoid repeated API calls
4. Continue playback without skipping

**Rationale:** Not all anime have crowdsourced timestamps. This is expected.

### Parsing Errors

**Scenario:** API response malformed or unexpected structure

**Handling:**
1. Log error with full response for debugging
2. Return empty skip intervals list
3. Don't cache (may be transient API issue)
4. Continue playback without skipping

**Rationale:** API schema may evolve. Graceful degradation prevents crashes.

### IPC Errors

**Scenario:** MPV IPC socket unavailable or seek command fails

**Handling:**
1. Fallback to no-skip mode (existing behavior)
2. Log debug message: "IPC unavailable, skip disabled"
3. Continue playback normally

**Rationale:** IPC already has fallback mechanism from keybindings change. Reuse it.

### Configuration Errors

**Scenario:** Invalid skip settings (e.g., cache_duration_days > 90)

**Handling:**
1. Pydantic validation raises error on app start
2. Error message shows field and constraint
3. App doesn't start (fail fast)

**Rationale:** Config errors should be caught early, not during playback.

---

## Performance Considerations

### API Latency

**Concern:** Skip timestamp query adds delay before playback starts

**Mitigation:**
- Use aggressive caching (30-day TTL)
- Set API request timeout: 5 seconds
- Run query asynchronously (non-blocking) if possible
- Show "Loading..." spinner during fetch (first time only)

**Target:** <500ms for API query, <10ms for cache hit

### Memory Usage

**Concern:** Caching timestamps for many anime/episodes

**Mitigation:**
- Skip intervals are small (3-4 objects × 3 floats each ≈ 100 bytes/episode)
- DiskCache automatically evicts old entries (LRU)
- 30-day TTL ensures stale data removed
- Estimate: 1000 episodes × 100 bytes = 100 KB total

**Target:** <1 MB total cache size under normal usage

### IPC Event Loop Overhead

**Concern:** Monitoring time-pos changes adds CPU load

**Mitigation:**
- Use event-driven model (not polling)
- Skip interval checks are O(n) but n is small (typically 1-2 intervals)
- Only active during playback (no background overhead)

**Target:** <1% CPU overhead from skip monitoring

---

## Security Considerations

### API Key Exposure

**Concern:** X-Client-ID header in source code

**Mitigation:**
- Use shared development key for initial release (publicly documented by Anime Skip)
- Allow custom client ID via environment variable for production users
- Document: users should create their own client ID for heavy usage

**Risk:** Low - shared key rate-limited by Anime Skip, users can override

### API Response Validation

**Concern:** Malicious/malformed API responses causing crashes

**Mitigation:**
- Pydantic validation on all parsed data
- Catch all exceptions in API client (return empty list on error)
- Never execute untrusted code from API response

**Risk:** Low - API is read-only, no code execution

### Cache Poisoning

**Concern:** Invalid data cached, breaking future playback

**Mitigation:**
- Validate intervals before caching (start < end, both non-negative)
- Add cache version key (invalidate if data model changes)
- User can clear cache manually: `ani-tupi --clear-cache skip`

**Risk:** Low - validation catches invalid data before caching

---

## Extensibility Points

### Future Enhancements

1. **Manual timestamp editing:**
   - Allow users to define custom skip intervals in config file
   - Override API data for specific anime
   - Contribute corrections back to Anime Skip API

2. **Per-anime overrides:**
   - Settings file: `skip_overrides: {20464: {skip_intros: false}}`
   - Disable skip for shows with unique intros (e.g., Monogatari series)

3. **Keyboard shortcuts:**
   - Add Shift+I (skip intro manually) and Shift+O (skip outro manually)
   - Show visual progress bar with skip zones marked

4. **Additional segment types:**
   - Enable recap and preview skipping (currently disabled by default)
   - Add "filler episode" detection

5. **Multi-source support:**
   - Integrate with MAL-based skip databases
   - Fallback to alternative APIs if Anime Skip unavailable

---

## Testing Strategy

### Unit Tests

**Scope:** Individual components in isolation

**Coverage:**
- Settings loading and validation
- SkipInterval model validation
- API response parsing
- Cache key generation
- Timestamp pairing logic

**Mocking:**
- Mock httpx responses for API calls
- Mock DiskCache for caching tests
- Mock MPV IPC socket for playback tests

### Integration Tests

**Scope:** Component interactions

**Coverage:**
- AnimeSkipService full flow (search + fetch)
- Cache persistence across service instances
- video_player.py with skip intervals
- anime_service.py orchestration

**Real Dependencies:**
- Real API calls (with mock fallback for CI)
- Real DiskCache (temp directory)
- Mock MPV IPC (socket simulation)

### E2E Tests

**Scope:** Full user workflows

**Coverage:**
- Happy path: play episode with intro skip
- No API data: play without timestamps
- Disabled setting: verify no skipping
- Network failure: graceful degradation
- Cache hit: verify no API call on second playback

**Real Dependencies:**
- Real API (test endpoint)
- Real cache (temp directory)
- Mock MPV playback (subprocess mock)

---

## Rollout Plan

### Phase 1: Soft Launch (Initial Implementation)

- Use test API endpoint: `http://test.api.anime-skip.com/graphql`
- Default enabled (user can disable via env var)
- Monitor logs for API errors
- Gather user feedback on accuracy

### Phase 2: Production API

- Switch to production endpoint: `https://api.anime-skip.com/graphql`
- Encourage users to create custom client IDs
- Add telemetry (optional): skip success rate, API latency

### Phase 3: Enhancements

- Add manual timestamp editing
- Implement per-anime overrides
- Add keyboard shortcuts for manual skip
- Expand to recap/preview segments

---

## Open Questions

1. **Should we support MAL ID in addition to AniList ID?**
   - **Decision pending:** Wait for user feedback. Most ani-tupi users use AniList integration.

2. **Should skip be per-type (intro/outro) or all-or-nothing?**
   - **Decision:** Per-type control (skip_intros, skip_outros independent). Already in design.

3. **Should we show visual indication of skip zones in seek bar?**
   - **Decision pending:** Out of scope for initial implementation. Future enhancement.

4. **Should we contribute timestamps back to Anime Skip API?**
   - **Decision pending:** Requires authentication flow and mutation support. Future enhancement.

---

## References

- [Anime Skip API Documentation](https://anime-skip.com/docs/api)
- [Anime Skip GraphQL Playground](http://test.api.anime-skip.com/graphiql)
- [Anime Skip TypeScript Client](https://github.com/anime-skip/api-client-ts)
- [Existing MPV IPC Change](openspec/changes/add-mpv-ipc-keybindings/)
- [ani-tupi Configuration System](models/config.py)
- [DiskCache Documentation](https://grantjenks.com/docs/diskcache/)
