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

**Status**: ✅ Fixed - Search results now rank by relevance to actual query
