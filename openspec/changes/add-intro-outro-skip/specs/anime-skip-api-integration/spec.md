# Spec: Anime Skip API Integration

**Capability:** anime-skip-api-integration
**Type:** Service Layer Enhancement

---

## ADDED Requirements

### Requirement: Query Anime Skip API for Timestamp Data

The system MUST integrate with the Anime Skip API (anime-skip.com) to fetch crowdsourced intro/outro timestamps for anime episodes.

**Depends on:** None (new capability)

#### Scenario: Fetch timestamps for known anime episode

**Given** the Anime Skip API is reachable
**And** the anime "Dandadan" exists in the database with AniList ID 171018
**And** episode 3 has intro timestamps: start=90.0s, end=210.0s
**When** the system queries timestamps for AniList ID 171018, episode 3
**Then** the API returns timestamp data for intro (type "op")
**And** the system parses it into a SkipInterval object: {type: "op", start: 90.0, end: 210.0}

#### Scenario: Handle missing show in Anime Skip database

**Given** the Anime Skip API is reachable
**And** the anime "Obscure Show" with AniList ID 99999 does NOT exist in the database
**When** the system queries timestamps for AniList ID 99999, episode 1
**Then** the API returns empty results or show not found error
**And** the system returns an empty list of SkipIntervals
**And** the system logs info message: "No skip data found for anime 99999"
**And** playback continues without skipping

#### Scenario: Handle API unavailability gracefully

**Given** the Anime Skip API is unreachable (network error or API down)
**When** the system attempts to query timestamps for any anime
**Then** the system catches the network exception
**And** logs warning: "Anime Skip API unavailable, skipping disabled"
**And** returns an empty list of SkipIntervals
**And** playback continues without skipping

---

### Requirement: Map AniList ID to Anime Skip Show ID

The system MUST map ani-tupi's AniList IDs to Anime Skip's internal show UUIDs to enable timestamp queries.

**Depends on:** Query Anime Skip API for Timestamp Data

#### Scenario: Direct mapping via externalIds

**Given** the Anime Skip API is reachable
**And** the show "Dandadan" has an externalId entry: {source: "anilist", id: "171018"}
**When** the system searches for AniList ID 171018
**Then** the API returns the show with matching externalId
**And** the system extracts the show UUID
**And** caches the mapping: anilist:171018 → show-uuid (90-day TTL)

#### Scenario: Fallback to fuzzy title search

**Given** the Anime Skip API is reachable
**And** the show "Dan Da Dan" exists but has NO AniList externalId linked
**And** the anime title in ani-tupi is "Dandadan"
**When** the system cannot find direct ID mapping
**Then** the system queries searchShows with title "Dandadan"
**And** performs fuzzy matching on returned show names
**And** selects best match with similarity score >90%
**And** caches the mapping for future queries

#### Scenario: No mapping found

**Given** the Anime Skip API is reachable
**And** no show matches the AniList ID or title
**When** the system attempts to map AniList ID 99999 with title "Unknown Anime"
**Then** both direct ID and fuzzy search return no results
**And** the system returns None for the show ID
**And** logs info: "Could not map anime 'Unknown Anime' to Anime Skip database"
**And** returns empty SkipIntervals list for this anime

---

### Requirement: Parse API Timestamps into Skip Intervals

The system MUST parse Anime Skip API's timestamp format into ani-tupi's SkipInterval data model.

**Depends on:** Query Anime Skip API for Timestamp Data

#### Scenario: Parse paired timestamps (intro with start and end)

**Given** the API returns timestamps for an episode:
```json
{
  "timestamps": [
    {"typeId": "op", "at": 90.0, "episodeId": "ep-uuid"},
    {"typeId": "op", "at": 210.0, "episodeId": "ep-uuid"}
  ]
}
```
**When** the system parses these timestamps
**Then** it groups consecutive timestamps with same typeId
**And** creates SkipInterval: {type: "op", start: 90.0, end: 210.0}
**And** validates start < end (90.0 < 210.0)

#### Scenario: Parse multiple segment types

**Given** the API returns timestamps for intro and outro:
```json
{
  "timestamps": [
    {"typeId": "op", "at": 90.0},
    {"typeId": "op", "at": 210.0},
    {"typeId": "ed", "at": 1320.0},
    {"typeId": "ed", "at": 1410.0}
  ]
}
```
**When** the system parses these timestamps
**Then** it creates two SkipIntervals:
  - {type: "op", start: 90.0, end: 210.0}
  - {type: "ed", start: 1320.0, end: 1410.0}
**And** both pass validation

#### Scenario: Filter by enabled types

**Given** user settings have skip_intros=True but skip_outros=False
**And** the API returns both intro and outro timestamps
**When** the system parses timestamps
**Then** it creates SkipInterval objects for all types
**But** filters out outro ("ed") intervals before returning
**And** only returns intro ("op") intervals for playback

---

### Requirement: Cache Timestamp Data Locally

The system MUST cache fetched timestamps to reduce API load and support offline playback.

**Depends on:** Parse API Timestamps into Skip Intervals

#### Scenario: Cache timestamp data after successful API fetch

**Given** the system successfully fetches timestamps for AniList ID 171018, episode 3
**And** the result is: [{type: "op", start: 90.0, end: 210.0}]
**When** the fetch completes
**Then** the system stores this data in DiskCache with key "skip:171018:3"
**And** sets TTL to 30 days (configurable via settings.skip.cache_duration_days)
**And** future queries for same anime/episode return cached data without API call

#### Scenario: Use cached data when available

**Given** cached timestamps exist for key "skip:171018:3"
**And** the cache entry is not expired (within 30-day TTL)
**When** the system queries timestamps for AniList ID 171018, episode 3
**Then** it returns cached SkipIntervals immediately
**And** does NOT make API call
**And** logs debug: "Cache hit for skip:171018:3"

#### Scenario: Cache miss triggers API query

**Given** no cached timestamps exist for key "skip:171018:5"
**When** the system queries timestamps for AniList ID 171018, episode 5
**Then** it performs API query
**And** caches the result (if successful)
**And** logs debug: "Cache miss for skip:171018:5, querying API"

---

### Requirement: Authenticate with Anime Skip API

The system MUST authenticate API requests using the X-Client-ID header as required by Anime Skip.

**Depends on:** None (authentication requirement)

#### Scenario: Send client ID with all API requests

**Given** the system is configured with client ID "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
**When** the system makes any GraphQL query to Anime Skip API
**Then** it includes header: "X-Client-ID: ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
**And** the API accepts the request

#### Scenario: Support custom client ID via configuration

**Given** user sets environment variable: ANI_TUPI__SKIP__API_CLIENT_ID=custom-id-123
**When** the system initializes AnimeSkipService
**Then** it uses "custom-id-123" as the client ID for all API requests
**And** the custom ID overrides the default shared development key

#### Scenario: Handle missing client ID error

**Given** the system is misconfigured with no client ID
**When** the system attempts to query the API
**Then** the API returns error: "The X-Client-ID header must be passed"
**And** the system logs error with configuration hint
**And** returns empty SkipIntervals list
**And** playback continues without skipping
