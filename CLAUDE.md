# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**ani-tupi** is a Brazilian Portuguese CLI anime viewer that streams anime directly in the terminal with support for multiple scraper sources and AniList integration. It uses MPV as the video player and provides an interactive menu system for searching, browsing, and watching anime.

## Development Commands

Use UV (Astral's fast Python package manager) for all package management and script execution. Never use pip directly.

### Setup & Installation

```bash
# Install dependencies in development
uv sync

# Install as global CLI (for testing)
python3 install-cli.py

# Or manually install as tool
uv tool install --force .

# Uninstall global CLI
uv tool uninstall ani-tupi
```

### Running the Application

```bash
# Run in development mode (without global install)
uv run ani-tupi

# Run with arguments
uv run ani-tupi --query "dandadan"
uv run ani-tupi --continue-watching
uv run ani-tupi anilist

# Run manga viewer
uv run manga_tupi

# Run with debug mode
uv run main.py --debug

# Show help
uv run ani-tupi --help
```

### Linting & Code Quality

```bash
# Run Ruff linter (check only)
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_example.py

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run single test
uv run pytest tests/test_example.py::test_function_name -v
```

### Building & Distribution

```bash
# Build standalone executable (no Python needed to run)
uv run build.py

# Output: dist/ani-tupi (Linux/macOS) or dist/ani-tupi.exe (Windows)
# Also creates plugins/ folder in dist/
```

### Dependency Management

```bash
# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update all dependencies
uv sync --upgrade

# Remove dependency
uv remove package-name
```

## Architecture Overview

The application follows the **MVCP pattern** (Model-View-Controller-Plugin):

### Core Flow
1. **main.py** → CLI entry point with argument parsing, routes to commands
2. **Commands** (commands/) → Handle user flows (anime, manga, anilist)
3. **Services** (services/) → Business logic layer
4. **Scrapers** (scrapers/) → Plugin system for different anime sources
5. **UI** (ui/) → Menu rendering using Rich + InquirerPy
6. **Models** (models/) → Pydantic data models with validation
7. **Utils** (utils/) → Helper utilities and persistence

### Key Architectural Decisions

**Plugin System** (scrapers/loader.py):
- Dynamic loading of scraper plugins from `scrapers/plugins/`
- Each plugin implements search and episode extraction
- Sources can be enabled/disabled via plugin_preferences.json

**Configuration Management** (models/config.py):
- Pydantic v2 settings with environment variable support
- Centralized settings accessible from anywhere: `from models.config import settings`
- Supports overrides via `ANI_TUPI__*` environment variables

**Data Persistence**:
- JSON-based storage in `~/.local/state/ani-tupi/` (XDG standard)
- SQLite cache via diskcache for scraper results (7-day default TTL)
- AniList OAuth token stored securely in `anilist_token.json`

**UI Framework**:
- **Rich** for progress bars, spinners, and formatting
- **InquirerPy** for interactive menus (replaces Textual for better performance)

**Service Layer** Pattern:
- `anime_service.py`: Search, selection, playback orchestration
- `anilist_service.py`: AniList API interactions
- `manga_service.py`: MangaDex scraping and caching
- `history_service.py`: Watch history persistence
- `repository.py`: Repository pattern for plugin management

### Data Flow for Watching Anime

1. User searches for anime → Repository queries scrapers in parallel
2. User selects anime → Service fetches episodes from chosen scraper
3. Service checks history and cache → Shows episode menu
4. User selects episode → MPV player launches with video URL
5. After playback → Service updates history and optionally syncs to AniList

### AniList Integration

- OAuth flow stores token in `anilist_token.json`
- Automatic sync after each episode if authenticated
- Fuzzy matching maps AniList titles to scraper titles (with caching)
- Supports all AniList list types: Watching, Planning, Completed, etc.

## Project Structure

```
ani-tupi/
├── main.py                    # CLI entry point, argument parsing
├── manga_tupi.py              # Manga CLI (separate entry point)
├── models/
│   ├── config.py              # Pydantic settings (centralized config)
│   └── models.py              # DTOs: AnimeMetadata, EpisodeData, etc
├── commands/
│   ├── anime.py               # Anime search & watch flow
│   ├── manga.py               # Manga reading flow
│   ├── anilist.py             # AniList authentication & menu
│   └── sources.py             # Source management (enable/disable plugins)
├── services/
│   ├── anime_service.py       # Business logic: search, selection, playback
│   ├── anilist_service.py     # AniList API client (GraphQL)
│   ├── manga_service.py       # MangaDex API integration
│   ├── repository.py          # Repository pattern for plugin management
│   └── history_service.py     # Watch history persistence
├── scrapers/
│   ├── loader.py              # Plugin discovery & loading system
│   └── plugins/
│       ├── animefire.py       # AnimeFire scraper plugin
│       └── animesonlinecc.py  # AnimesonlineCC scraper plugin
├── ui/
│   ├── components.py          # Reusable menu & spinner components
│   └── anilist_menus.py       # AniList-specific menu UI
├── utils/
│   ├── video_player.py        # MPV integration (IPC commands)
│   ├── cache_manager.py       # Cache operations (diskcache)
│   ├── scraper_cache.py       # Scraper result caching
│   ├── history_service.py     # Watch history management
│   ├── persistence.py         # JSON file operations
│   ├── logging.py             # Loguru configuration
│   ├── exceptions.py          # Custom exceptions
│   ├── anilist_discovery.py   # Fuzzy matching AniList IDs
│   └── title_utils.py         # Title normalization
├── pyproject.toml             # Project configuration (dependencies, scripts)
├── install-cli.py             # Global CLI installer script
└── build.py                   # PyInstaller build script
```

## Important Implementation Details

### Video Player Integration (utils/video_player.py)

- Uses MPV IPC (Inter-Process Communication) for keybinding support
- Supports custom keybindings: Shift+N (next), Shift+P (prev), Shift+M (mark & menu), etc.
- Auto-play mode toggles continuation without returning to menu
- No hardcoded keys - all configurable via MPV config

### Title Normalization (utils/title_utils.py)

- Anime titles are normalized when caching results: "Dandadan 2nd Season; Episode 3" → "Dandadan S02E03"
- Episode filtering by regex patterns prevents false matches
- Important for distinguishing seasons and specials

### Caching Strategy

**Scraper Results** (SQLite via diskcache):
- TTL: 7 days (configurable via `ANI_TUPI__CACHE__DURATION_HOURS`)
- Key pattern: `{title}:{source}` (exact match required)
- Stores: anime metadata, episodes, URLs

**Episode Lists** (Memory cache during session):
- Fetched once, reused across selections
- Cleared when user switches sources

**AniList Mappings** (JSON):
- Maps AniList ID → scraper title (for automatic continuation)
- Enables seamless "continue watching" across sessions

### Error Handling Patterns

- **Missing scrapers**: Gracefully falls back to menu, doesn't crash
- **Network errors**: Shows user message, allows retry
- **Invalid URLs**: Validated by Pydantic models before processing
- **MPV crashes**: Watched separately, user notified if playback fails

### Ruff Configuration

The project uses custom Ruff rules in `pyproject.toml` that ignore less critical linting rules (complexity, magic numbers, docstrings, etc.). This is intentional to keep the codebase focused on functionality over strict linting.

## Common Development Tasks

### Available Scraper Plugins

Current scrapers available:

1. **AnimeFirePlus** (`animefire.py`) - High quality, reliable
   - URL: https://animefire.plus
   - Episodes: Usually up-to-date
   - Player: Uses video iframes

2. **AnimesonlineCC** (`animesonlinecc.py`) - Portuguese subtitles
   - URL: https://animesonlinecc.to
   - Episodes: Multiple seasons support
   - Player: iframe player

3. **AnimesDigital** (`animesdigital.py`) - Dubbed content ⭐ NEW
   - URL: https://animesdigital.org
   - Episodes: Many dubbed anime
   - Player: Direct HLS/MP4 extraction
   - Status: ✅ Fully integrated and tested

### Adding a New Scraper Plugin

1. Create `scrapers/plugins/newsource.py` with class implementing `Scraper` protocol
2. Implement `search(query)` → returns `AnimeMetadata` list
3. Implement `get_episodes(url)` → returns `EpisodeData`
4. Plugin is auto-discovered by `scrapers/loader.py` - no registration needed
5. Run `uv run test_plugin_integration.py` to verify it's discovered

**Example**: See `animesdigital.py` for a complete implementation

### Adding a New Command

1. Create `commands/newcommand.py` with function `def newcommand(args)`
2. Import in `main.py`
3. Add to CLI parser in `cli()` function
4. Route from appropriate menu or CLI argument

### Modifying AniList Integration

1. GraphQL queries are in `services/anilist_service.py` as string constants
2. Update query, add new method, call from commands
3. Test authentication with `uv run ani-tupi anilist auth`

### Working with the Cache

```python
from utils.cache_manager import clear_cache_all, clear_cache_by_prefix

# Clear specific anime from cache
clear_cache_by_prefix(":dandadan:")

# Clear everything
clear_cache_all()

# Or via CLI
uv run ani-tupi --clear-cache
uv run ani-tupi --clear-cache "dandadan"
```

## Testing Approach

The project uses pytest. Current test coverage focuses on critical paths:
- Plugin loading
- Model validation
- Service layer logic
- Cache operations

New features should include tests for:
- Happy path (normal operation)
- Error cases (invalid input, network failures)
- Edge cases (empty results, special characters in titles)

Run tests with: `uv run pytest -v`

## Common Workarounds & Known Issues

### MPV IPC Socket Not Found

**Issue**: MPV keybindings don't work
**Cause**: IPC socket path configuration
**Workaround**: Check `~/.config/mpv/mpv.conf` has `input-ipc-server=/tmp/mpvsocket`

### Geckodriver Not Found

**Issue**: Selenium can't find Firefox driver
**Cause**: geckodriver not in PATH
**Workaround**: Install via package manager (pacman, apt, brew) or manually add to PATH

### AniList Token Expired

**Issue**: "Invalid authorization" when using AniList features
**Cause**: OAuth token expired (valid for ~6 months)
**Workaround**: Re-authenticate with `uv run ani-tupi anilist auth`

## CI/CD Pipeline

The project uses GitHub Actions (`.github/workflows/`):
- **ci.yml**: Validates syntax, imports, and checks basic functionality on every push
- **build-test.yml**: Tests building standalone executables

Key validation steps:
- Python syntax checking (`py_compile`)
- Dependency validation
- Cross-platform testing (Linux, macOS, Windows)
- Plugin discovery verification

To test locally before pushing:
```bash
uv run python -m py_compile main.py
uv run python -m py_compile manga_tupi.py
uv run python -c "from scrapers import loader; loader.load_plugins({'pt-br'})"
```

## Notes for Editing

- **Always use `uv`** for running Python commands and installing packages
- **Never modify `pyproject.toml` directly** - use `uv add` / `uv remove`
- **Config changes** should go in `models/config.py` with Pydantic validation
- **New data structures** should be Pydantic models in `models/models.py`
- **Service layer** is where business logic belongs, not in commands or UI
- **Avoid circular imports** - dependency hierarchy: commands → services → models/utils
- **Persist data** in `~/.local/state/ani-tupi/` (XDG standard, respects $XDG_STATE_HOME)

## OpenSpec Integration

The project uses OpenSpec for structured change documentation. Major features are documented in `openspec/changes/`:
- Design documents explaining architectural decisions
- Spec files for each major component
- Task tracking for implementation

When making significant changes, consider updating or creating spec documentation.

## Bug Fixes & Workarounds (2025-01-07)

### AniList Title Matching with `--query` Flag
**Issue**: When using `ani-tupi --query "dandadan"`, the scraper returns titles with Portuguese suffixes like "Dandadan (Dublado)" which don't match AniList searches, preventing automatic AniList ID discovery.

**Root Cause**: The title from scrapers includes localization suffixes that need to be stripped before AniList API lookup.

**Solution**: Added `normalize_title_for_search()` call in `commands/anime.py` before passing to AniList lookup:
- Lines 52-53: Strip Portuguese suffixes for --query path
- Lines 77-78: Strip Portuguese suffixes for menu path
- Uses regex patterns in `utils/title_utils.py` to remove: (Dublado), (Legendado), (Completo), (Dual Audio), (PT-BR)

**Status**: ✅ Fixed - AniList now successfully matches titles from any source

### MPV Keybindings Not Configured
**Issue**: MPV showed "No key binding found for key 'N'" errors - custom ani-tupi keybindings (Shift+N for next, Shift+P for prev, etc.) weren't available during playback.

**Root Cause**: The `play_video()` function didn't pass custom input.conf to MPV instance. The infrastructure existed but wasn't being used.

**Solution**: Updated `utils/video_player.py` `play_video()` function:
- Line 64: Generate custom ani-tupi input.conf file with all keybindings
- Line 83: Pass `input_conf` parameter to MPV constructor
- Lines 115-118: Clean up temporary input.conf file in finally block

**Keybindings Available**:
- Shift+N: Next episode (mark watched, move to next)
- Shift+P: Previous episode
- Shift+M: Mark & Menu (mark watched, show menu options)
- Shift+R: Reload current episode
- Shift+A: Toggle auto-play
- Shift+T: Toggle sub/dub

**Status**: ✅ Fixed - Custom keybindings now configured and available

### AnimesDigital Scraper Extra Metadata in Episode Names
**Issue**: AnimesDigital plugin returned episode titles with extra metadata: "Dandadan Episódio 12 11 meses atrás smart_display" instead of clean titles.

**Root Cause**: Used `.text()` on the episode link element which included all nested text content (date, metadata badges, etc.).

**Solution**: Updated `scrapers/plugins/animesdigital.py` `search_episodes()` function:
- Line 65: Extract title from `.title_anime` CSS class instead of link text
- This selector contains only the clean episode title without metadata
- Result: "Dandadan Episódio 12" instead of "Dandadan Episódio 12 11 meses atrás smart_display"

**Status**: ✅ Fixed - Episode lists now display clean titles

### Cache Manager `iterkeys()` Error
**Issue**: `ani-tupi --clear-cache` fails with `AssertionError: cannot access iterkeys in cache shard`

**Root Cause**: The diskcache library doesn't expose `iterkeys()` method in newer versions.

**Workaround**: Use `--clear-cache` without arguments to clear entire cache:
```bash
uv run ani-tupi --clear-cache  # Clears all cache
```

Instead of:
```bash
uv run ani-tupi --clear-cache "dandadan"  # This fails
```

**Status**: ⚠️ Known issue - Clear-by-prefix not working, but full cache clear works

**To Fix**: Update `utils/cache_manager.py` `clear_cache_by_prefix()` to use iteration method compatible with current diskcache version.

### AnimesDigital Timeout Issues
**Issue**: AnimesDigital requests timeout with `ReadTimeout: HTTPSConnectionPool(host='animesdigital.org', port=443): Read timed out. (read timeout=15)`

**Root Cause**: AnimesDigital.org can be slow to respond, especially during peak hours or when fetching episode lists.

**Solution**: Updated `REQUEST_TIMEOUT` constant in `scrapers/plugins/animesdigital.py`:
- Added module-level constant: `REQUEST_TIMEOUT = 30` (line 9)
- Used in `search_anime()`, `search_episodes()`, and `search_player_src()`
- Single place to update timeout for all AnimesDigital requests

**Status**: ✅ Fixed - More tolerant of slow network conditions

**If Still Timing Out**: Consider temporarily disabling AnimesDigital source:
```bash
# Edit to deactivate animesdigital
~/.local/state/ani-tupi/plugin_preferences.json
# Set "animesdigital": false
```

### AnimesDigital Fractional Episodes Being Included (2025-01-07)
**Issue**: AnimesDigital was returning 25 episodes for Jujutsu Kaisen Season 1 instead of 24, showing "25 eps disponíveis / 24 total" in the menu.

**Root Cause**: AnimesDigital lists special episodes with fractional numbers (e.g., "Episódio 13.5") alongside regular episodes. These OVAs/specials were being included in the episode list, causing the count to be inflated. Jujutsu Kaisen Season 1 page had both "Episódio 13" and "Episódio 13.5" listed, resulting in 25 items.

**Solution**: Added filtering in `scrapers/plugins/animesdigital.py` `search_episodes()`:
- Line 53: Added `import re` for regex pattern matching
- Lines 78-81: Added check to detect and skip fractional episode numbers (`\d+\.\d+`)
- Only main numbered episodes (1, 2, 3...24) are included, not specials

**Code**:
```python
# Filter out special episodes (fractionated like 13.5, 0.5, etc)
# These are OVAs/specials that shouldn't be counted as main episodes
if re.search(r"Episódio\s+\d+\.\d+", title):
    continue  # Skip special episodes
```

**Status**: ✅ Fixed - Jujutsu Kaisen Season 1 now correctly returns 24 episodes

**Test Results**:
- Season 1: 24 episodes (was 25) ✅
- Season 2: 23 episodes (unchanged) ✅
- No fractional episodes included ✅

### Source Priority Order Configuration (2025-01-07)
**Feature**: Configurable, agnóstic source priority order for scraper sources when searching for anime and videos.

**Implementation**: Refactored `services/repository.py` and `models/config.py`:

**Configuration** (`models/config.py`, PluginSettings):
```python
priority_order: list[str] = Field(
    default_factory=lambda: ["animesdigital", "animefire", "animesonlinecc"],
    description="Priority order for scraper sources (first = highest priority)",
)
```

**Usage** (`services/repository.py`):
- **Anime Search** (`_search_with_incremental_results()`): Lines 269-283
  - Reads priority from `settings.plugins.priority_order`
  - Sorts sources dynamically without hardcoded names
  - Respects configured order for all searches

- **Video Search** (`search_player()`): Lines 656-719
  - Organizes sources by priority order
  - Tries highest-priority source first (with 15s timeout)
  - Returns immediately when any source succeeds
  - Falls back to next priority level if current source fails

**How to Change Priority**:

**Option 1: Environment Variable**
```bash
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animefire","animesdigital","animesonlinecc"]'
uv run ani-tupi --query "dandadan"
```

**Option 2: Direct Config in models/config.py**
```python
priority_order: list[str] = Field(
    default_factory=lambda: ["animefire", "animesdigital", "animesonlinecc"],
    # ... rest of config
)
```

**Current Default Order**: `["animesdigital", "animefire", "animesonlinecc"]`

**Status**: ✅ Implemented - Agnóstic priority system that works with any scraper names

### AnimesonlineCC Player Not Starting Issue (2025-01-07)
**Issue**: When playing videos from AnimesonlineCC, the video URL would be found successfully, but MPV player wouldn't start with no visible error messages.

**Root Cause**: Two separate issues:
1. Screen was being cleared with `os.system("clear")` immediately after the player exited, erasing any error messages
2. AnimesonlineCC's iframe detection was brittle with only one XPath selector, and had no validation of extracted URLs
3. The Blogger video URLs could fail without user seeing feedback

**Solution Implemented**:
1. **Improved iframe detection** in `scrapers/plugins/animesonlinecc.py`:
   - Lines 85-116: Added 3 fallback methods to find iframe with video URL
   - Method 1: Original XPath selector (5s timeout)
   - Method 2: Generic iframe search by tag (3s timeout)
   - Method 3: CSS selector as last resort
   - Line 125: Handle relative URLs by converting to absolute

2. **Fixed error message visibility** in `commands/anime.py` and `services/anime_service.py`:
   - Lines 130-136 (commands/anime.py): Don't clear screen if `exit_code != 0`
   - Show prompt "Press Enter to continue" so user has time to read errors
   - Lines 782-788 (anime_service.py): Same fix for IPC playback path

3. **Added debug mode** in `utils/video_player.py`:
   - Lines 305-321: Added `ANI_TUPI_DEBUG_MPV=1` environment variable to show MPV output
   - Lines 657-660: Show helpful message when MPV fails with exit code 2

4. **Better error reporting** in `services/repository.py`:
   - Lines 646-650: Display extracted video URL when found (truncated for long URLs)
   - Line 657: Increased error message display length from 80 to 100 characters

**Testing**:
```bash
# Test normal playback (error messages stay visible)
uv run ani-tupi --query "dandadan"

# Test with debug output from MPV
ANI_TUPI_DEBUG_MPV=1 uv run ani-tupi --query "dandadan"

# Test scraper directly
uv run python test_animesonlinecc_debug.py  # Returns ✅ with URL on success
```

**Status**: ✅ Fixed - Video extraction is robust, error messages now visible to user

**How It Works Now**:
1. AnimesonlineCC scraper tries 3 methods to find iframe
2. If found, URL is displayed: "✅ Vídeo encontrado em: animesonlinecc" + URL preview
3. Player launches with URL
4. If player fails (exit_code != 0), error message stays visible until user presses Enter
5. If debug enabled, can see full MPV output for troubleshooting

### AnimesonlineCC Blogger Token Expiration Issue (2025-01-07)

**Issue**: AnimesonlineCC videos play but immediately fail with HTTP 400 error when launched in MPV.

**Root Cause**: AnimesonlineCC uses temporary Blogger video URLs with tokens that expire very quickly (within minutes or even seconds). The scraper successfully extracts the iframe `src`, but the token becomes invalid before MPV can access it.

**Error Message**:
```
[ffmpeg] https: HTTP error 400 Bad Request
[ytdl_hook] ERROR: [blogger.com] Unable to download webpage: HTTP Error 400: Bad Request
```

**Status**: ⚠️ Limitation of AnimesonlineCC's hosting method

**Solution**: Use alternative sources that don't have this limitation:

**Recommended Sources** (in order of reliability):
1. **AnimesDigital** - Direct video URLs, no token expiration
2. **AnimeFire** - Stable iframe-based streaming
3. **AnimesonlineCC** - ⚠️ Token expiration issues (not recommended for streaming)

**How to Configure Priority**:
```bash
# Edit models/config.py or set environment variable:
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "animefire", "animesonlinecc"]'

# Or change in code:
# models/config.py line ~89:
priority_order: list[str] = Field(
    default_factory=lambda: ["animesdigital", "animefire"],  # Skip animesonlinecc
    ...
)
```

**Current Default Order**: `["animesdigital", "animefire", "animesonlinecc"]`
- This will try AnimesDigital and AnimeFire first (which work), falling back to AnimesonlineCC if needed

**Long-term Fix**: Would require AnimesonlineCC to:
- Use permanent video URLs instead of temporary tokens
- Or implement server-side streaming without expiring tokens
- Or migrate to a different video hosting solution

### AniList Search Result Ranking Issue (2025-01-07)

**Issue**: When searching anime via AniList menu, titles like "Jujutsu Kaisen 2 Dublado" were ranking much lower than expected, even though they directly matched the search query. Instead, "Jujutsu Kaisen 2nd Season (Dublado)" appeared higher due to fuzzy matching using full AniList bilingual title.

**Root Cause**: The fuzzy matching algorithm was using the full AniList bilingual title (romaji / english format, e.g., "Jujutsu Kaisen 2nd Season / JUJUTSU KAISEN Season 2") for ranking scraper results. This full title has extra tokens and different structure than the actual search query, causing incorrect ranking.

**Example**:
- User searches AniList for: "jujutsu kaisen 2"
- AniList returns: "Jujutsu Kaisen 2nd Season / JUJUTSU KAISEN Season 2"
- Old fuzzy matching used that full title for ranking
- Result: "2nd Season" variants ranked higher than "2" variants

**Solution**: Use the normalized search query (without season/suffix info) for ranking instead of the full bilingual AniList title.

**Files Changed**:
- `services/anime_service.py` lines 311 and 464: Changed from `original_query=anime_title` to `original_query=used_query`
- This passes the actual search term to the fuzzy matching algorithm

**Before**: "Jujutsu Kaisen 2 Dublado" ranked at position 7-9
**After**: "Jujutsu Kaisen 2" ranks at position 3, "Jujutsu Kaisen 2 Dublado" at position 8 (as expected)

**Status**: ✅ Fixed (v1) - Search results now rank by relevance to actual query

### AniList Search Result Ranking - Progressive Search Follow-up (2025-01-07)

**Issue**: After the initial fix, a new issue emerged: when searching "Jujutsu Kaisen 0" and the progressive search fell back to "jujutsu kaisen" (fewer words), the ranking changed and "Jujutsu Kaisen 0" would drop from 1st to 2nd place, behind the generic "Jujutsu Kaisen".

**Root Cause**: The ranking was using `used_query` which gets progressively reduced by the search system. So when searching "jujutsu kaisen 0" found no results and fell back to "jujutsu kaisen", the ranking algorithm would use "jujutsu kaisen" (without the "0"), losing the original search intent.

**Solution**: Use the **first normalized variant** (the most specific version) for ranking across all progressive search attempts. This preserves the user's original intent.

**Files Changed**:
- `services/anime_service.py` line 279: Store `first_variant = normalize_anime_title(anime_title)[0]`
- Line 314: Changed from `original_query=used_query` to `original_query=first_variant`
- Line 468: Same change for "Continue searching" flow

**Example**:
- Search "Jujutsu Kaisen 0" → first_variant = "jujutsu kaisen 0"
- If full query returns nothing, falls back to "jujutsu kaisen"
- But ranking still uses "jujutsu kaisen 0" → "Jujutsu Kaisen 0" stays at #1

**Status**: ✅ Fixed (v2) - Search intent preserved across progressive fallbacks

### AniList Search Result Ranking - Numeric Token Prioritization (2025-01-07)

**Issue**: Even after v2 fix, when searching "Jujutsu Kaisen 0", results were still scattered:
- Jujutsu Kaisen 0 (1st) ✅
- Jujutsu Kaisen 2 (2nd) ❌ (shouldn't be here)
- Jujutsu Kaisen (3rd) ❌
- Jujutsu Kaisen 0 Movie (5th) ❌ (should be 2nd)
- Jujutsu Kaisen 0 Dublado (6th) ❌ (should be 3rd)

**Root Cause**: The `token_sort_ratio` fuzzy algorithm penalizes titles with extra tokens (like "Movie"), treating "Jujutsu Kaisen 2" as a better match than "Jujutsu Kaisen 0 Movie" for query "jujutsu kaisen 0".

**Solution**: Implement numeric-aware scoring that:
1. Extracts numeric tokens from query (e.g., "0" from "jujutsu kaisen 0")
2. Checks if title contains those same numbers
3. If yes: adds +15 bonus (ensures "0" variants on top)
4. If no matching numbers: applies -20 penalty (keeps "2" variants lower)

**Files Changed**:
- `services/repository.py` lines 398-433: Added numeric token boost/penalty logic

**Scoring Examples**:
- Query: "jujutsu kaisen 0"
  - "Jujutsu Kaisen 0" → base 100 + 15 = 100 (capped)
  - "Jujutsu Kaisen 0 Movie" → base 84 + 15 = 99 ✅
  - "Jujutsu Kaisen 0 Dublado" → base 80 + 15 = 95 ✅
  - "Jujutsu Kaisen 2" → base 94 - 20 = 74 ✅
  - "Jujutsu Kaisen" → base 93 - 20 = 73 ✅

**Result**: All "0" variants grouped at top in logical order:
1. Jujutsu Kaisen 0
2. Jujutsu Kaisen 0 Movie
3. Jujutsu Kaisen 0 Dublado
4. Jujutsu Kaisen 0 Movie (Dublado)
5. Jujutsu Kaisen 2
...

**Status**: ✅ Fixed (v3) - Numeric tokens prioritized in ranking

### Title Normalization - Preserve Season Numbers (2025-01-07)

**Issue**: When AniList title contains "2nd Season" or "Season 2", the normalization was removing the number completely, preventing proper numeric-based ranking.

**Example**:
- AniList: "Jujutsu Kaisen 2nd Season / JUJUTSU KAISEN Season 2"
- Scraper: "Jujutsu Kaisen 2 Dublado"
- Problem: Query became "jujutsu kaisen" (lost the "2"), couldn't match properly

**Solution**: Extract season numbers BEFORE removing season patterns, then re-append them:
1. Detect "2nd Season", "Season 2", "Temporada 2", etc with regex
2. Extract and store the number
3. Remove season patterns
4. Re-append the extracted number

**Files Changed**:
- `services/anime_service.py` lines 97-125: Modified `normalize_anime_title()` to preserve numbers

**Result**:
- "Jujutsu Kaisen 2nd Season" → "jujutsu kaisen 2" ✅
- "Jujutsu Kaisen Season 2" → "jujutsu kaisen 2" ✅
- "Temporada 2" → preserved as "2" ✅

Now the numeric boost/penalty in ranking can work properly even when AniList uses different season formats.

**Status**: ✅ Fixed (v4) - Season numbers preserved in normalization

### Sequel Offer After Incomplete Source (2025-01-07)

**Issue**: When watching anime from a source with fewer episodes (e.g., "Tougen Anki Dublado" with 22 episodes), finishing the last available episode would incorrectly offer the sequel, even though more episodes exist on other sources (e.g., 23+ episodes on AnimesDigital subtitled version).

**Example**:
- Tougen Anki Dublado (AnimesDigital): 22 episodes
- Tougen Anki (other sources): 23+ episodes
- User finishes episode 22 → System offers sequel (WRONG - episode 23 not watched yet)

**Root Cause**: The sequel offer logic only checked if the user reached the current scraper's episode limit (`next_episode == num_episodes`), not AniList's actual episode count.

**Solution**: Before offering sequel, fetch AniList episode count and compare:
1. If `current_episode < anilist_episodes`: Don't offer sequel, show message that more episodes are available
2. If `current_episode >= anilist_episodes`: Offer sequel (user actually finished)
3. If `anilist_episodes` is None: Fallback to old behavior (offer sequel)

**Files Changed**:
- `services/anime_service.py` line 171: Updated `offer_sequel_and_continue()` signature to accept episode counts
- Lines 194-198: Added check to prevent sequel offer when more episodes available
- Lines 693-700: Get AniList episode count before offering sequel (Shift+N path)
- Lines 756-763: Get AniList episode count before offering sequel (auto-next path)
- Lines 852-859: Get AniList episode count before offering sequel (menu path)

**How It Works**:
1. User finishes episode 22 of "Tougen Anki Dublado"
2. System gets AniList info: 23 episodes total
3. Compares: 22 < 23 → Don't offer sequel
4. Shows: "💡 Existem mais 1 episódio(s) disponível(is) em outras fontes."
5. User can switch source and watch episode 23

**Status**: ✅ Fixed (v5) - Sequel offer respects actual series episode count

### Cache Loading Type Mismatch (2025-01-07)

**Issue**: When loading cached anime data (e.g., when continuing to watch previously played anime), the application crashed with:
```
AttributeError: 'ScraperCacheData' object has no attribute 'get'
```

**Root Cause**: The `load_from_cache()` method in `services/repository.py` was calling `.get()` as if the `cache_data` parameter was a dictionary, but it was receiving a Pydantic `ScraperCacheData` model object from `get_cache()`.

**Solution**: Updated `load_from_cache()` to handle both Pydantic models and dictionaries:
1. Check if the object has an `episode_urls` attribute (Pydantic model)
2. If yes: access directly as attributes
3. If no: treat as dictionary and use `.get()`

**Files Changed**:
- `services/repository.py` lines 507-526: Added type detection and dual-mode access

**Status**: ✅ Fixed (v6) - Cache loading handles both models and dicts

### AnimesDigital Missing Episodes with ?odr=1 Parameter (2025-01-07)

**Issue**: AnimesDigital has animes in multiple versions (dublada/legendada) with different episode counts:
- Without `?odr=1`: Legendada shows 19 eps, Dublada shows 22 eps
- The system would pick Dublada because it had more episodes visible
- But with `?odr=1` parameter, both show all 24 episodes

**Root Cause**: AnimesDigital has a button "ordenar" (sort/order) that adds `?odr=1` parameter to show all episodes. Without this parameter, the HTML doesn't fully render all episode divs.

**Solution**: Automatically add `?odr=1` parameter to all anime URLs in the `search_episodes()` function:
1. If URL already has query params: add `&odr=1`
2. If URL has no params: add `?odr=1`
3. If URL already has `odr=`: don't add again

**Files Changed**:
- `scrapers/plugins/animesdigital.py` lines 58-73: Added parameter handling in `search_episodes()`
- Also prioritize subtitled versions over dubbed (lines 43-56)

**Example**:
- `https://animesdigital.org/anime/a/tougen-anki` → `https://animesdigital.org/anime/a/tougen-anki?odr=1`
- Result: 24 episodes instead of 19

**Status**: ✅ Fixed (v7) - AnimesDigital shows all episodes with ?odr=1 parameter

### Anime Marked as "Recomassistindo" Instead of "Completo" After Last Episode (2025-01-08)

**Issue**: When watching the last episode of an anime that's already marked as "COMPLETED" (Completo) on AniList, the app was changing the status to "REPEATING" (Recomassistindo) instead of leaving it as "COMPLETED".

**Root Cause**: The auto-promotion logic had three cases:
1. PLANNING → CURRENT ✓ (correct)
2. CURRENT + last episode → COMPLETED ✓ (correct)
3. COMPLETED + last episode → REPEATING ✗ (incorrect - assumed every rewatch = REPEATING status)

The issue was that the code assumed watching the last episode of a COMPLETED anime meant the user wanted to mark it as REPEATING. But users might just be rewatching their favorite anime or a specific scene, not necessarily tracking a full series rewatch.

**Solution**: Removed the auto-promotion logic for COMPLETED status. When an anime is already COMPLETED and the user watches it again:
- Status stays as COMPLETED (no automatic change)
- Progress still syncs to AniList
- User can manually change status to REPEATING if they want to track a full rewatch

**Files Changed**:
- `services/anime_service.py` lines 724-736: Removed COMPLETED → REPEATING auto-promotion (Shift+N auto-play path)
- `services/anime_service.py` lines 829-841: Removed COMPLETED → REPEATING auto-promotion (Menu playback path)

**Before**:
```
✅ Último episódio assistido!
🔄 Mudando para 'Recomassistindo'...  ← WRONG
```

**After**:
```
✅ Último episódio assistido!
🔄 Sincronizando progresso com AniList (Ep 13)...
✅ Progresso salvo no AniList!  ← Stays as COMPLETED
```

**Status**: ✅ Fixed (v8) - Completed anime stays completed even when rewatched

### Cache KeyError and Missing Sources Display (2025-01-08)

**Issue 1**: When playing cached anime from AniList, app crashed with `KeyError: 'cache'`
- User loads anime from AniList cache
- App tries to access `self.sources["cache"]` which doesn't exist
- Results in: `KeyError: 'cache' at line 707 in search_player()`

**Issue 2**: Cached anime showed title without source information
- Expected: "Dandadan [animesdigital, animesonlinecc]"
- Actual: "dandadan" (no sources shown)
- User couldn't see which sources had the anime

**Root Cause**:
1. `load_from_cache()` marks episode data with source="cache" as placeholder
2. `search_player()` tried using "cache" as a real scraper source → KeyError
3. `get_anime_titles_with_sources()` included "cache" in source list, then filtered it out leaving empty sources

**Solution**:
1. **Filter "cache" marker in search_player()** (line 622-623):
   ```python
   if source != "cache":
       selected_urls.append((urls[episode_num - 1], source))
   ```

2. **Filter "cache" from display sources** (lines 394-395):
   ```python
   sources = set(source for _url, source, _params in urls_and_sources if source != "cache")
   sources_str = ", ".join(sorted(sources)) if sources else "cached"
   ```

3. **Discover real sources after loading cache** (anime_service.py, 3 locations):
   - After `load_from_cache()`, call `rep.search_anime(variant)` to find actual sources
   - Then use `get_anime_titles_with_sources()` to format with sources
   - Applied to all 3 cache-loading paths: AniList variants, manual search, CLI search

**Files Changed**:
- `services/repository.py` lines 622-623: Skip "cache" when searching for video URLs
- `services/repository.py` lines 394-395: Filter "cache" from display, show "cached" fallback
- `services/anime_service.py` lines 311-325: AniList cache path with source discovery
- `services/anime_service.py` lines 384-397: Manual search cache path with source discovery
- `services/anime_service.py` lines 1193-1198: CLI cache path with source discovery

**Result**:
Before:
```
ℹ️  Usando cache (13 eps disponíveis)
► yamada kun to lv999 no koi wo suru
KeyError: 'cache'
```

After:
```
ℹ️  Usando cache (13 eps disponíveis)
🔄 Buscando fontes disponíveis...
► Yamada-kun to Lv999 no Koi wo Suru [animesdigital, animesonlinecc]
```

**Status**: ✅ Fixed (v9) - Cache sources properly displayed and no more KeyError

### Missing norm_titles Entry When Adding Cached Anime (2025-01-08)

**Issue**: When anime was loaded from cache, then `search_anime()` tried to find sources, app crashed:
```
KeyError: 'yamada kun to lv999 no koi wo suru' at line 335 in add_anime()
```

**Root Cause**:
1. `load_from_cache()` adds anime to `anime_to_urls` but NOT to `norm_titles`
2. Later, `search_anime()` calls `add_anime()` to add scraped sources
3. `add_anime()` tries to access `self.norm_titles[key]` for deduplication
4. Key doesn't exist because anime was only in cache, not searched via `add_anime()` before

**Solution**: Use `.get()` with fallback normalization in `add_anime()`:
```python
key_normalized = self.norm_titles.get(key, self._normalize_for_filter(key))
```

This allows `add_anime()` to handle anime titles that exist in `anime_to_urls` but not yet in `norm_titles` (from cache loading).

**Files Changed**:
- `services/repository.py` line 336: Use `.get()` with fallback for norm_titles lookup

**Status**: ✅ Fixed (v10) - Cache + search_anime flow works without KeyError

### Duplicate Sources in Logs When Returning to Menu (2025-01-08)

**Issue**: When navigating AniList menu and selecting the same anime multiple times, logs showed exponentially increasing duplicate sources:

```
First time:
  🔄 Tentando fontes: animesonlinecc, animesdigital

Second time:
  🔄 Tentando fontes: animesonlinecc, animesdigital, animesdigital, animesdigital, animesonlinecc, animesonlinecc

Third time:
  🔄 Tentando fontes: (12 sources with many duplicates)
```

**Root Cause**: Repository is a singleton that persists data between function calls. When the same anime was loaded again:
1. First load: `anime_episodes_urls[anime]` had 2 source entries
2. Second load: Same anime loaded again, old entries still there, new entries added = 4 total
3. Third load: Now 6 + new ones = more duplicates

**Solution**: Clear Repository state at the start of each main flow function that uses cached/searched data:
1. `anilist_anime_flow()` - Called when selecting anime from AniList menu (line 286)
2. `search_anime_flow()` - Called for CLI anime search (line 1185)

By calling `rep.clear_search_results()` early, we ensure a clean state for each new selection.

**Code**:
```python
# In anilist_anime_flow() after loader.load_plugins():
rep.clear_search_results()

# In search_anime_flow() at start:
rep.clear_search_results()
```

**Files Changed**:
- `services/anime_service.py` line 286: Clear state in `anilist_anime_flow()`
- `services/anime_service.py` line 1185: Clear state in `search_anime_flow()`

**Result**:
```
Every time you navigate menu and select anime:
  🔄 Tentando fontes: animesonlinecc, animesdigital (no duplicates, always clean)
```

**Status**: ✅ Fixed (v11) - No more duplicate sources in logs

### [cached] Marker Appearing in Source Lists (2025-01-08)

**Issue**: When loading anime from cache and then searching for sources, the source list showed "[cached]" marker:

```
Yamada-kun to Lv999 no Koi wo Suru [animesdigital, animesonlinecc]
yamada kun to lv999 no koi wo suru [cached]  ← WRONG, shouldn't appear
```

**Root Cause**: `load_from_cache()` added a dummy entry to `anime_to_urls` with source="cache":
```python
if anime not in self.anime_to_urls:
    self.anime_to_urls[anime].append(("cached", "cache", None))
```

This entry would appear in `get_anime_titles_with_sources()` as a source, resulting in "[cached]" in the UI.

**Solution**: Remove the dummy entry from `load_from_cache()`. The reason:
1. "cache" is not a real scraper source, just an internal marker
2. Real sources are discovered via `search_anime()` called after `load_from_cache()`
3. Episode URLs are still properly stored in `anime_episodes_urls` with "cache" marker (which is filtered out during playback)

**Files Changed**:
- `services/repository.py` lines 540-543: Removed dummy anime_to_urls entry from `load_from_cache()`
- Added comment explaining why cache shouldn't appear as a source

**Result**:
```
Before:
  yamada kun to lv999 no koi wo suru [cached]

After:
  Yamada-kun to Lv999 no Koi wo Suru [animesdigital, animesonlinecc]
  (only real sources shown, no '[cached]' marker)
```

**Status**: ✅ Fixed (v12) - No more [cached] in source lists
