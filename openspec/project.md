# Project Context

## Purpose

ani-tupi is a terminal-based anime and manga streaming application in Brazilian Portuguese. It provides a unified interface to search, browse, and play anime and manga from multiple sources (animes sites), with integration to AniList.co for progress tracking and watch list management.

**Key Goals:**
- Lightweight, keyboard-driven TUI alternative to web browsers.
- Multi-source scraping for anime content (animefire.plus, animesonlinecc.to, etc.).
- AniList synchronization for watch progress and personalized recommendations.
- Plugin-based extensibility for adding new anime/manga sources.
- Cross-platform support (Linux, macOS, Windows).

## Tech Stack

**Core:**
- **Python 3.12+**: Modern features and type safety.
- **UV**: Fast package manager, dependency resolver, and environment manager.
- **Rich**: Rich text and beautiful formatting in the terminal.
- **InquirerPy**: Interactive terminal user interfaces (replacement for legacy curses).

**Scraping & HTTP:**
- **Selenium + BeautifulSoup**: Web scraping for dynamic and static sites.
- **httpx**: Modern, async-capable HTTP client.
- **Firefox/Geckodriver**: Browser automation.

**External APIs:**
- **AniList GraphQL API**: Anime metadata, watch lists, and progress sync.
- **MangaDex API**: Primary source for manga reading.

**Video Playback:**
- **MPV**: Media player with JSON-RPC IPC integration for advanced control and episode navigation.

**Utilities:**
- **Pydantic v2**: Settings management and data validation models.
- **DiskCache**: SQLite-backed persistent caching for scraper results and episodes.
- **Loguru**: Structured and colorful logging.
- **pathlib**: Modern cross-platform path handling.

**Dev Tools:**
- **pytest**: Comprehensive testing suite (unit, integration, e2e).
- **Ruff**: Extremely fast Python linter and code formatter.

## Project Conventions

### Code Style

- **Language:** Python 3.12+ with strict type hints.
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes.
- **Formatting:** Managed by Ruff (Black-compatible).
- **Imports:** Standard lib -> External -> Local. Use absolute imports.
- **Logging:** Use `utils.logging.get_logger(__name__)`.
- **Path Handling:** Use `pathlib.Path` exclusively. Use `get_resource_path()` for bundled files.

### Architecture Patterns

**MVCP (Model-View-Controller-Plugin) Architecture:**

1. **Model** (`models/models.py`, `services/repository.py`)
   - Centralized data structures using Pydantic.
   - Singleton Repository managing global state (anime, episodes, source mappings).
   - DiscCache-backed persistence for scraper results.

2. **View** (`ui/components.py`, `ui/anilist_menus.py`)
   - Rich and InquirerPy based terminal UI.
   - Component-based approach for menus, inputs, and progress bars.

3. **Controller** (`commands/*.py`, `main.py`)
   - Route logic and application flow orchestration.
   - Separation of concerns (anime, manga, anilist commands).

4. **Plugin System** (`scrapers/loader.py`, `scrapers/plugins/`)
   - Structural typing via `PluginInterface` (Protocol).
   - Dynamic discovery and loading of scraper plugins.
   - Async racing for finding stream URLs in parallel.

### Testing Strategy

- **Test Framework:** pytest with marks for categorization.
- **Categories:**
  - `unit`: Fast tests for logic/models.
  - `integration`: Testing component interactions (e.g., repository + plugins).
  - `e2e`: Full workflow tests (search -> select -> play).
- **CI Integration:** Automated runs on push/PR via GitHub Actions.

### Git Workflow

- **Branching:** `master` for production, feature branches for development.
- **Commit Messages:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- **PRs:** Required for merging into master; must pass CI quality gates (lint, tests).

## Domain Context

### Anime/Manga Streaming Context

- **Localization:** Focused on the Brazilian Portuguese market (dubbed/subtitled content).
- **Fuzzy Matching:** Scraper titles normalized and matched against AniList titles with a threshold (default 90).
- **Source Handling:** Scrapers must handle varied HTML structures and potential rate limits.

### Video Playback Context

- **MPV IPC:** Uses sockets (Unix) or Named Pipes (Windows) for real-time control.
- **Keybindings:** Custom `Shift+N`, `Shift+P`, `Shift+M` etc., for episode navigation within MPV.
- **History:** Local watch progress persistence in `~/.local/state/ani-tupi/`.

## Important Constraints

- **Package Manager:** MUST use `uv`.
- **Environment:** Requires `mpv` and `geckodriver` in system PATH.
- **Caching:** Video stream URLs MUST NOT be cached (short-lived tokens).
- **Cross-platform:** Native path handling and IPC implementation must account for Windows vs Unix differences.

## External Dependencies

- **AniList**: GraphQL API for tracking and discovery.
- **MangaDex**: Primary manga source.
- **Scraper Targets**: Brittle dependency on external site HTML (e.g., animefire.plus).
- **MPV**: Critical for media playback.
- **Selenium**: Essential for sites requiring JS rendering.
