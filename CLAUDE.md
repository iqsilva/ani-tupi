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

### Manga PDF Reader Workflow

**Pattern**: Similar to anime (external player + cache)

1. User selects manga and chapter
2. System checks if PDF already exists in chapter directory
3. If not: Downloads images from MangaDex → Converts to PDF (Pillow)
4. Opens PDF with Zathura (or auto-detected reader: evince, okular, mupdf)
5. Saves reading progress to history

**Reader Detection** (utils/manga_reader.py):
- Priority: User config → Zathura → Evince → Okular → MuPDF → xdg-open
- Configurable via `ANI_TUPI__MANGA__PDF_READER=reader_name`
- Graceful fallback if no reader found

**PDF Conversion** (utils/pdf_converter.py):
- Converts PNG images to single multi-page PDF
- Configurable JPEG quality (default 85) via `ANI_TUPI__MANGA__PDF_QUALITY`
- Optional PNG deletion after PDF creation via `ANI_TUPI__MANGA__DELETE_IMAGES_AFTER_PDF`

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
│   ├── manga_reader.py        # PDF reader launcher (Zathura, auto-detect)
│   ├── pdf_converter.py       # PNG to PDF conversion (Pillow)
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

### Using the Manga PDF Reader

**Reading Manga**:
```bash
uv run manga_tupi
```

Workflow:
1. Search for manga title
2. Select manga from results
3. Browse available chapters
4. Select chapter → System downloads images → Creates PDF → Opens Zathura
5. Read PDF in Zathura (navigate with arrow keys, q to quit)
6. System saves reading progress automatically

**Configuration**:
```bash
# Use specific PDF reader
export ANI_TUPI__MANGA__PDF_READER="zathura"

# Delete PNG files after PDF creation (saves space)
export ANI_TUPI__MANGA__DELETE_IMAGES_AFTER_PDF=true

# Adjust PDF quality (lower = smaller file, 1-100)
export ANI_TUPI__MANGA__PDF_QUALITY=80

# Disable auto PDF creation (download images only)
export ANI_TUPI__MANGA__AUTO_CREATE_PDF=false
```

**Supported PDF Readers** (auto-detected in order):
- Zathura (recommended, keyboard-driven)
- Evince (GNOME default)
- Okular (KDE default)
- MuPDF (minimal, fast)
- xdg-open (system default)

If no reader found, images are saved and you can open them manually.

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

## Known Limitations & Workarounds

### MPV IPC Socket Not Found

**Issue**: MPV keybindings don't work
**Cause**: IPC socket path configuration
**Workaround**: Check `~/.config/mpv/mpv.conf` has `input-ipc-server=/tmp/mpvsocket`

### AniList Token Expired

**Issue**: "Invalid authorization" when using AniList features
**Cause**: OAuth token expired (valid for ~6 months)
**Workaround**: Re-authenticate with `uv run ani-tupi anilist auth`

### Cache Manager `iterkeys()` Error

**Issue**: `ani-tupi --clear-cache "name"` fails with diskcache error
**Cause**: diskcache library doesn't expose prefix iteration
**Workaround**: Use `uv run ani-tupi --clear-cache` without arguments to clear entire cache

### AnimesonlineCC Video Token Expiration

**Issue**: AnimesonlineCC videos fail with HTTP 400 error in MPV
**Cause**: Videos use temporary Blogger URLs with tokens that expire within minutes
**Solution**: Use AnimesDigital or AnimeFire as primary sources

**How to Configure Priority**:
```bash
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "animefire"]'
uv run ani-tupi --query "dandadan"
```

## OpenSpec Integration

The project uses OpenSpec for structured change documentation. Major features are documented in `openspec/changes/`:
- Design documents explaining architectural decisions
- Spec files for each major component
- Task tracking for implementation

When making significant changes, consider updating or creating spec documentation.
