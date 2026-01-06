# Spec: Skip Configuration Management

**Capability:** configuration-management
**Type:** Settings & User Controls

---

## ADDED Requirements

### Requirement: Skip Feature Settings

The system MUST provide configuration options to control automatic skip behavior.

**Depends on:** None (configuration foundation)

#### Scenario: Default settings enable intro/outro skip

**Given** ani-tupi is freshly installed with no custom configuration
**When** the system loads default settings
**Then** settings.skip.enabled is True (global enable)
**And** settings.skip.skip_intros is True (skip openings)
**And** settings.skip.skip_outros is True (skip endings)
**And** settings.skip.skip_recaps is False (disabled by default)
**And** settings.skip.skip_previews is False (disabled by default)

#### Scenario: Global disable via environment variable

**Given** user sets environment variable: ANI_TUPI__SKIP__ENABLED=false
**When** the system loads settings
**Then** settings.skip.enabled is False
**And** all skip functionality is disabled regardless of other settings
**And** no API queries are made
**And** playback proceeds without skipping

#### Scenario: Selective skip type control

**Given** user sets:
  - ANI_TUPI__SKIP__SKIP_INTROS=true
  - ANI_TUPI__SKIP__SKIP_OUTROS=false
**When** the system fetches skip intervals
**Then** intro intervals (type "op") are included
**But** outro intervals (type "ed") are filtered out
**And** only intros are skipped during playback

---

### Requirement: API Client Configuration

The system MUST allow configuration of Anime Skip API connection parameters.

**Depends on:** None (configuration foundation)

#### Scenario: Default API client ID

**Given** ani-tupi is installed with default configuration
**When** the system initializes AnimeSkipService
**Then** it uses default client ID: "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
**And** includes this ID in X-Client-ID header for all API requests

#### Scenario: Custom API client ID for production

**Given** user registers custom client ID on anime-skip.com
**And** sets ANI_TUPI__SKIP__API_CLIENT_ID=custom-production-id
**When** the system initializes AnimeSkipService
**Then** it uses "custom-production-id" for X-Client-ID header
**And** avoids rate limits of shared development key

#### Scenario: API endpoint configuration (future-proofing)

**Given** Anime Skip API changes endpoint URLs
**And** user needs to override default endpoint
**When** user sets ANI_TUPI__SKIP__API_URL=https://new-api.anime-skip.com/graphql
**Then** the system uses the custom endpoint
**And** all GraphQL queries go to the new URL

---

### Requirement: Cache Duration Configuration

The system MUST allow users to configure how long timestamp data is cached.

**Depends on:** anime-skip-api-integration (caching)

#### Scenario: Default 30-day cache TTL

**Given** ani-tupi is installed with default configuration
**When** the system caches skip intervals
**Then** the TTL is 30 days (settings.skip.cache_duration_days = 30)
**And** cached data expires after 30 days
**And** triggers API re-fetch on next playback

#### Scenario: Custom cache duration

**Given** user sets ANI_TUPI__SKIP__CACHE_DURATION_DAYS=7
**When** the system caches skip intervals
**Then** the TTL is 7 days
**And** cache entries expire after 1 week
**And** user gets more frequent updates from API

#### Scenario: Cache duration validation

**Given** user sets ANI_TUPI__SKIP__CACHE_DURATION_DAYS=100 (exceeds maximum)
**When** the system loads settings
**Then** Pydantic validation raises error
**And** error message indicates valid range: 1-90 days
**And** application fails to start (fail fast on invalid config)

---

### Requirement: Settings Validation

The system MUST validate all skip-related settings at startup to catch configuration errors early.

**Depends on:** Skip Feature Settings, API Client Configuration

#### Scenario: Validate boolean settings

**Given** user sets ANI_TUPI__SKIP__ENABLED=yes (not a valid boolean)
**When** the system loads settings
**Then** Pydantic raises ValidationError
**And** error message indicates expected type: bool
**And** suggests valid values: true/false, 1/0

#### Scenario: Validate integer ranges

**Given** user sets ANI_TUPI__SKIP__CACHE_DURATION_DAYS=0 (below minimum)
**When** the system loads settings
**Then** Pydantic raises ValidationError
**And** error message indicates constraint: ge=1 (greater than or equal to 1)

#### Scenario: Validate string formats

**Given** user sets ANI_TUPI__SKIP__API_CLIENT_ID="" (empty string)
**When** the system loads settings
**Then** validation passes (empty string is technically valid)
**But** API requests will fail with authentication error
**And** system logs error with configuration hint

---

## MODIFIED Requirements

### Requirement: AppSettings Configuration Class (Updated)

The system MUST extend AppSettings to include skip configuration section.

**Previous behavior:** AppSettings contains anilist, cache, search, plugins, manga settings

**New behavior:** AppSettings includes skip settings section

#### Scenario: Skip settings integrated into AppSettings

**Given** the system loads configuration
**When** AppSettings is initialized
**Then** it includes settings.skip attribute
**And** settings.skip is of type SkipSettings
**And** all skip configuration is accessible via settings.skip.*

---

## ADDED Requirements (Data Models)

### Requirement: SkipSettings Pydantic Model

The system MUST define a validated configuration model for skip settings.

**Depends on:** None (data model)

#### Scenario: SkipSettings model with default values

**Given** SkipSettings is defined as Pydantic model
**When** an instance is created with no parameters
**Then** it has the following defaults:
  - enabled: True
  - skip_intros: True
  - skip_outros: True
  - skip_recaps: False
  - skip_previews: False
  - api_client_id: "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
  - cache_duration_days: 30

#### Scenario: SkipSettings field validation

**Given** SkipSettings model definition
**When** creating instance with cache_duration_days=150
**Then** Pydantic raises ValidationError
**And** validation constraint enforced: ge=1, le=90

---

### Requirement: SkipInterval Pydantic Model

The system MUST define a validated data model for skip intervals.

**Depends on:** None (data model)

#### Scenario: SkipInterval model with validation

**Given** SkipInterval is defined with fields: type, start, end
**When** creating instance: SkipInterval(type="op", start=90.0, end=210.0)
**Then** validation passes
**And** instance is created successfully

#### Scenario: Reject invalid interval (end before start)

**Given** SkipInterval validation requires start < end
**When** creating instance: SkipInterval(type="op", start=210.0, end=90.0)
**Then** Pydantic raises ValidationError
**And** error message: "end must be greater than start"

#### Scenario: Reject negative timestamps

**Given** SkipInterval validation requires start >= 0
**When** creating instance: SkipInterval(type="op", start=-10.0, end=90.0)
**Then** Pydantic raises ValidationError
**And** error message indicates constraint: ge=0

#### Scenario: Type label property for localization

**Given** SkipInterval instance: {type: "op", start: 90.0, end: 210.0}
**When** accessing interval.type_label
**Then** it returns Brazilian Portuguese label: "abertura"
**And** for type "ed", returns "encerramento"

---

## ADDED Requirements (CLI Commands)

### Requirement: Test Skip Connectivity Command

The system MUST provide a CLI command to test Anime Skip API connectivity and configuration.

**Depends on:** API Client Configuration

#### Scenario: Test API connectivity successfully

**Given** Anime Skip API is reachable
**And** client ID is configured correctly
**When** user runs: `ani-tupi test-skip`
**Then** the system queries API health endpoint
**And** displays: "✓ Anime Skip API reachable"
**And** displays: "✓ Using client ID: ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
**And** displays cache statistics: X entries, Y MB total size

#### Scenario: Test API connectivity failure

**Given** Anime Skip API is unreachable (network error)
**When** user runs: `ani-tupi test-skip`
**Then** the system attempts connection
**And** displays: "✗ Anime Skip API unreachable: connection timeout"
**And** suggests troubleshooting: check internet connection, try again later

#### Scenario: Test with specific anime query

**Given** user runs: `ani-tupi test-skip --anilist-id 171018 --episode 3`
**When** the system executes test query
**Then** it fetches timestamps for the specified anime/episode
**And** displays result:
  - "✓ Found 1 skip interval:"
  - "  - Intro: 90.0s → 210.0s (120.0s duration)"
**Or** if not found:
  - "✗ No skip data found for AniList ID 171018, Episode 3"

---

### Requirement: Debug Output for Skip Status

The system MUST include skip-related information in debug mode output.

**Depends on:** Skip Feature Settings

#### Scenario: Debug output shows skip configuration

**Given** user runs ani-tupi with --debug flag
**When** playback starts
**Then** debug output includes:
  - "Skip enabled: True"
  - "Skip types: intros=True, outros=True, recaps=False, previews=False"
  - "API client ID: ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
  - "Cache duration: 30 days"

#### Scenario: Debug output shows skip intervals fetched

**Given** skip intervals are fetched for an episode
**When** playback begins
**Then** debug output includes:
  - "Skip intervals fetched: 2"
  - "  - [op] 90.0s → 210.0s"
  - "  - [ed] 1320.0s → 1410.0s"

#### Scenario: Debug output shows cache hit/miss

**Given** system checks cache for skip intervals
**When** cache lookup occurs
**Then** debug output includes:
  - "Cache lookup: skip:171018:3"
  - "Cache result: HIT (loaded in 8ms)" OR "Cache result: MISS (querying API)"
