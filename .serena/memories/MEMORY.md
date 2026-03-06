# ani-tupi Project Memory

## Project Overview
**ani-tupi** - Brazilian Portuguese CLI for anime and manga with multi-source support, AniList integration, and external player support.

### Tech Stack
- **Language**: Python 3.12+ (requires-python = ">=3.12")
- **Package Manager**: `uv` (NOT pip, NOT poetry)
- **Testing**: pytest (711 tests, 80%+ coverage target)
- **Config**: Pydantic v2 + environment variables
- **Web Frameworks**: Playwright, Selenium, httpx
- **UI**: Rich, InquirerPy (TUI)
- **Key Dependencies**: Scrapling, yt-dlp, python-mpv

### Architecture (3-Tier)
1. **Commands** (CLI entry points) → `commands/`, `main.py`, `manga_tupi.py`
2. **Services** (business logic) → `services/`
3. **Plugins** (implementations/scrapers) → `scrapers/plugins/`, `manga_scrapers/plugins/`

### Core Patterns
- **Plugin Protocol** (not inheritance) - structural typing with duck typing
- **Centralized Config** - All settings via Pydantic config (models/config.py)
- **Repository Pattern** - Don't import plugins directly, use repository
- **Title Normalization** - Multi-source dedup via normalize_title_for_dedup()
- **Immutable Data** - Services return transformed copies, never mutate input
- **Cache as Wrapper** - Services decide when to cache, not plugins
- **External Tools via Adapters** - MPV, PDF readers wrapped in classes

### Configuration (Environment Variables)
```bash
ANI_TUPI__CACHE__DURATION_HOURS=48
ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "goyabu", "animefire", "animesonlinecc"]'
ANI_TUPI__PLUGINS__DUBBED_PRIORITY_ORDER='["animesdigital", "animefire", "goyabu"]'
ANI_TUPI__MANGA__PDF_READER=zathura
ANI_TUPI__LOG_LEVEL=debug
```

### Known Features
- **Anime Download** - Episodes stored in ~/.local/share/ani-tupi/anime/
- **Airing Episodes** - Shows anime from AniList watching list with new episodes airing
- **Local Anime Service** - Scans and manages local library
- **AnimesonlineCC** - Issues: videos use temporary URLs, use AnimesDigital/AnimeFire instead
- **Incremental Search** - Intelligent search with word-by-word fallback

### Fixed Bugs
- **IPC Fallback URL Bug** (2026-03-05): When IPC socket connection fails in VideoPlayer, it was passing empty URL string ("") to legacy player instead of actual episode URL. This caused MPV to open but not play anything. Fixed by extracting URL from episode_context.

### AnimesDigital URL Pattern
- Correct: `/anime/a/anime-slug-todos-episodios` (works, finds all episodes)
- Incorrect: `/animes/anime-slug` (redirects to single episode, 0 episodes found)
- API returns correct format automatically

### Common Commands (see suggested_commands.md for full list)
- `uv sync` - Install/sync dependencies
- `uv run ani-tupi` - Run anime CLI
- `uv run manga_tupi` - Run manga CLI
- `uv run pytest` - Run tests (711 total)
- `uv run pytest --cov --cov-report=html` - Coverage report
- `uv run ruff check .` - Lint
- `uv run ruff format .` - Format
- `uv add package-name` - Add dependency
- `uv remove package-name` - Remove dependency
