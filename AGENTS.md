# AGENTS.md

This guide provides essential information for AI agents working on the **ani-tupi** codebase.

## Project Overview

**ani-tupi** is a CLI-based anime viewer for Brazilian Portuguese users. It streams content from various scrapers (AnimeFire, AnimesDigital, etc.) using MPV as the video player and integrates with AniList for tracking.

- **Stack**: Python 3.12+, `uv` for package management.
- **Key Libraries**: `pydantic` (models/settings), `requests`/`selectolax` (scraping), `rich`/`inquirerpy` (UI), `diskcache` (caching), `python-mpv` (video player).
- **Architecture**: MVCP (Model-View-Controller-Plugin).

## Essential Commands

Always use `uv` for execution and package management.

```bash
# Development & Execution
uv sync                         # Install dependencies
uv run ani-tupi                 # Run the main application
uv run main.py --debug          # Run with debug logs
uv run manga_tupi               # Run the manga viewer

# Testing & Quality
uv run pytest                   # Run all tests
uv run ruff check .             # Linting (use --fix to auto-fix)
uv run ruff format .            # Formatting

# Build
uv run build.py                 # Build standalone executable with PyInstaller
```

## Code Organization

- `main.py`: Entry point and CLI argument parsing.
- `commands/`: Higher-level user flows (anime, manga, anilist).
- `services/`: Core business logic (search, playback orchestration, repository).
- `scrapers/plugins/`: Individual scraper implementations.
- `models/`: Pydantic models for data (`models.py`) and configuration (`config.py`).
- `utils/`: Low-level helpers (video player IPC, cache, persistence).
- `ui/`: Rich/InquirerPy components.

## Development Patterns & Conventions

### 1. Repository Pattern (`services/repository.py`)
The `Repository` is a singleton that manages search results and episode lists across all scrapers.
- Scrapers MUST register themselves with `rep.register(PluginClass)`.
- Scrapers call `rep.add_anime()` and `rep.add_episode_list()`.

### 2. Plugin System (`scrapers/loader.py`)
Scrapers follow a specific protocol defined in `scrapers/loader.py`:
- `search_anime(query)`: Finds anime and adds to repository.
- `search_episodes(anime, url, params)`: Finds episodes and adds to repository.
- `search_player_src(url, container, event)`: Extracts video URL.

### 3. Pydantic for Everything
- All data structures must be defined in `models/models.py`.
- Global configuration is in `models/config.py` using `Pydantic Settings`.
- Access settings via: `from models.config import settings`.

### 4. Video Player & IPC (`utils/video_player.py`)
- Uses MPV with IPC for controls.
- Custom keybindings (Shift+N, Shift+P, etc.) are generated into a temporary `input.conf`.

## Important Gotchas

- **Whitespace Matters**: When editing scrapers or UI, preserve exact formatting for terminal rendering.
- **Cache**: Scraper results are cached for 7 days. Use `--clear-cache` to reset.
- **Video URLs**: DO NOT cache video stream URLs (especially from AnimesonlineCC) as they often contain expiring tokens (Blogger).
- **Portuguese Suffixes**: Scrapers often return titles with "(Dublado)" or "(Legendado)". Use `utils.title_utils.normalize_title_for_search()` before matching with external APIs like AniList.
- **Priority Order**: Source priority is configurable via `settings.plugins.priority_order`.

## Testing Approach

- Use `pytest` for all tests.
- Mocking network requests is preferred, but many integration tests (prefixed with `test_plugin_`) run against live sites.
- New scrapers should include an integration test.

## AniList Integration

- Token is stored in `~/.local/state/ani-tupi/anilist_token.json`.
- Uses GraphQL via `services/anilist_service.py`.
- Fuzzy matching is used to map local titles to AniList IDs.
