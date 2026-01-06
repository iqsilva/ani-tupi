# Spec: Skip Playback Control

**Capability:** skip-playback-control
**Type:** Video Player Enhancement

---

## ADDED Requirements

### Requirement: Monitor Playback Position via MPV IPC

The system MUST monitor the current playback position to detect when the video enters a skip interval.

**Depends on:** anime-skip-api-integration (requires skip intervals)

#### Scenario: Subscribe to time-pos property changes

**Given** MPV is playing an episode with IPC socket active
**And** skip intervals are configured: [{type: "op", start: 90.0, end: 210.0}]
**When** the IPC event loop initializes
**Then** the system subscribes to MPV's "time-pos" property changes
**And** receives position updates as playback progresses

#### Scenario: Receive position updates during playback

**Given** MPV is actively playing at 95.3 seconds
**And** the system is monitoring time-pos
**When** MPV reports a property-change event: {property: "time-pos", data: 95.3}
**Then** the system records current_time = 95.3
**And** proceeds to check skip intervals

#### Scenario: Handle IPC unavailability gracefully

**Given** MPV IPC socket is unavailable (legacy playback mode)
**When** the system attempts to monitor time-pos
**Then** it falls back to legacy playback without position monitoring
**And** skip intervals are ignored
**And** playback continues normally without skipping

---

### Requirement: Trigger Skip When Entering Interval

The system MUST automatically seek past skip intervals when playback enters them.

**Depends on:** Monitor Playback Position via MPV IPC

#### Scenario: Skip intro when playback enters interval

**Given** MPV is playing with skip interval: {type: "op", start: 90.0, end: 210.0}
**And** current playback position is 95.3 seconds
**And** 90.0 <= 95.3 < 210.0 (inside interval)
**And** the interval has NOT been processed yet
**When** the system detects position within skip interval
**Then** it sends MPV command: ["seek", 210.0, "absolute"]
**And** playback jumps to 210.0 seconds (end of intro)
**And** the interval is marked as processed to prevent re-triggering

#### Scenario: Skip outro near end of episode

**Given** MPV is playing with skip interval: {type: "ed", start: 1320.0, end: 1410.0}
**And** current playback position is 1325.0 seconds
**When** the system detects position within outro interval
**Then** it sends seek command to 1410.0 seconds
**And** playback continues after credits

#### Scenario: Do not re-trigger already processed interval

**Given** an intro interval was already skipped (processed_intervals contains it)
**And** user manually seeks backward into the intro region
**When** the system detects position within the same interval again
**Then** it does NOT send another seek command
**And** allows user to watch the skipped content if they manually seeked there

---

### Requirement: Display OSD Notification During Skip

The system MUST show an on-screen notification when automatically skipping content.

**Depends on:** Trigger Skip When Entering Interval

#### Scenario: Show intro skip notification

**Given** the system triggers skip for intro interval at 95.3 seconds
**When** the seek command is sent to MPV
**Then** the system sends OSD command: ["show-text", "⏩ Pulando abertura...", "3000"]
**And** MPV displays "⏩ Pulando abertura..." in bottom-right corner
**And** the message disappears after 3 seconds

#### Scenario: Show outro skip notification

**Given** the system triggers skip for outro interval at 1325.0 seconds
**When** the seek command is sent to MPV
**Then** the system sends OSD command: ["show-text", "⏩ Pulando encerramento...", "3000"]
**And** MPV displays localized Brazilian Portuguese message

#### Scenario: No notification when skip disabled

**Given** skip is globally disabled (settings.skip.enabled = False)
**When** playback reaches an intro interval
**Then** no seek command is sent
**And** no OSD notification is shown
**And** playback continues normally through the intro

---

### Requirement: Accept Skip Intervals in play_episode()

The system MUST extend the video player interface to accept skip intervals as a parameter.

**Depends on:** anime-skip-api-integration

#### Scenario: Pass skip intervals to playback function

**Given** anime_service has fetched skip intervals: [{type: "op", start: 90.0, end: 210.0}]
**When** anime_service calls play_episode()
**Then** it passes skip_intervals parameter: play_episode(..., skip_intervals=[...])
**And** the video player receives the intervals for processing

#### Scenario: Handle None skip intervals (no skipping)

**Given** no skip intervals are available (API error or disabled)
**When** anime_service calls play_episode(..., skip_intervals=None)
**Then** the video player initializes without skip monitoring
**And** playback proceeds normally without any automatic skipping

#### Scenario: Backward compatibility with existing callers

**Given** existing code calls play_episode() without skip_intervals parameter
**When** the function is invoked with legacy signature
**Then** skip_intervals defaults to None
**And** playback works exactly as before (no breaking change)

---

### Requirement: Handle Edge Cases in Skip Logic

The system MUST correctly handle unusual scenarios during skip processing.

**Depends on:** Trigger Skip When Entering Interval

#### Scenario: Multiple consecutive intervals

**Given** skip intervals: [{type: "recap", start: 10, end: 60}, {type: "op", start: 90, end: 210}]
**And** playback reaches 15 seconds (inside recap interval)
**When** the system triggers skip to 60 seconds
**Then** the recap interval is marked as processed
**And** when playback later reaches 95 seconds (inside intro interval)
**Then** the intro skip triggers independently
**And** both skips execute without interference

#### Scenario: User seeks backward into skipped interval

**Given** intro interval {type: "op", start: 90, end: 210} was already skipped
**And** processed_intervals contains this interval
**And** playback is currently at 250 seconds
**When** user manually seeks to 100 seconds (inside intro)
**Then** the system does NOT trigger skip again (interval already processed)
**And** user can watch the intro content they manually seeked to

#### Scenario: Playback speed changes

**Given** skip interval {type: "op", start: 90, end: 210}
**And** user changes playback speed to 1.5x
**When** playback reaches 95 seconds at 1.5x speed
**Then** the system still triggers skip based on absolute time-pos (not adjusted for speed)
**And** seeks to 210 seconds regardless of speed setting

#### Scenario: Overlapping intervals (invalid data)

**Given** API returns malformed data with overlapping intervals:
  - {type: "op", start: 90, end: 210}
  - {type: "recap", start: 150, end: 180} (overlaps intro)
**When** the system validates skip intervals
**Then** it detects the overlap
**And** logs warning: "Overlapping skip intervals detected, using first occurrence only"
**And** keeps only the first interval (intro) and discards the overlapping one

---

## MODIFIED Requirements

### Requirement: play_episode() Function Signature (Updated)

The system MUST extend play_episode() to accept optional skip intervals parameter.

**Previous behavior:** `play_episode(url, anime_title, episode_number, total_episodes, source, use_ipc, debug, anilist_id)`

**New behavior:** Add optional `skip_intervals` parameter

#### Scenario: Extended signature maintains backward compatibility

**Given** existing code calls play_episode with 8 parameters (no skip_intervals)
**When** the function executes
**Then** skip_intervals defaults to None
**And** playback behavior matches previous version (no skipping)
**And** all other parameters work as before

---

## ADDED Requirements (Cross-Capability)

### Requirement: Integrate Skip Intervals into Playback Flow

The system MUST fetch skip intervals before playback and pass them to the video player.

**Depends on:** anime-skip-api-integration, skip-playback-control

#### Scenario: Full integration from search to skip

**Given** user selects episode 3 of "Dandadan" (AniList ID 171018)
**And** skip is enabled in settings
**When** anime_service orchestrates playback
**Then** it queries AnimeSkipService for timestamps (171018, episode 3)
**And** receives skip intervals: [{type: "op", start: 90.0, end: 210.0}]
**And** passes intervals to play_episode() call
**And** MPV plays the episode
**And** automatically skips the intro at 90 seconds
**And** shows OSD notification: "⏩ Pulando abertura..."
**And** playback continues after intro at 210 seconds

#### Scenario: Skip disabled in settings

**Given** user has set ANI_TUPI__SKIP__ENABLED=false
**When** anime_service checks settings before playback
**Then** it skips the API query entirely
**And** calls play_episode() with skip_intervals=None
**And** playback proceeds without any skipping

#### Scenario: No AniList ID available

**Given** user manually searched for anime (not via AniList integration)
**And** anilist_id is None for this playback
**When** anime_service attempts to fetch skip intervals
**Then** it logs info: "Skip unavailable (no AniList ID)"
**And** calls play_episode() with skip_intervals=None
**And** playback continues normally
