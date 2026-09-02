## General Rules and Guidelines

**Best Practices for writing Python code:**

### Design Principles
- Apply the DRY principle - Don't Repeat Yourself
- Prefer composition over inheritance for more maintainable code
- Write pure functions when possible (no side effects, same output for same input)
- Follow SOLID principles for maintainable object-oriented design
- Write tests first (TDD) or alongside code development
- Use dataclasses for data containers

### Handling Complexity
- Hide implementation details behind clean interfaces
- Create abstractions that eliminate complexity for users
- Encapsulate related data and behavior in cohesive classes
- Use interfaces or abstract base classes to define contracts
- Apply dependency injection for more flexible and testable code
- Favor simple solutions over complex or clever ones
- Design for the most common use case first
- Keep component coupling loose through well-defined interfaces

---

## Core Values

**Simplicity First**: Every feature should feel effortless to the user. Complex logic (incremental search, fuzzy matching, automatic syncing) runs invisibly.

**DRY Architecture**: Code is organized by *what it does*, not *where it lives*. If multiple scrapers implement `search()` → they're one pattern (plugin protocol). If multiple services fetch from APIs → they share a base class. If code repeats → extract it.

**Immutable Data Flow**: Data flows forward only. Services don't modify input; they return transformed copies. This makes debugging trivial: follow the data, not the mutations.

**Plugin Everything**: Scrapers and storage backends—all pluggable. New source? Create one file. Done.

**User Configuration Over Code**: Settings live in environment variables (via Pydantic config), not config files that break. Users can tune everything without touching code.

---

## Usage Guide

ani-tupi is a **FastAPI server + PWA web frontend** (no CLI flags). Entry point: `api/server.py:main` (`ani-tupi` console script).

### Running

```bash
just serve            # Start the API server (uv run ani-tupi)
just test             # uv run pytest
just lint             # uv run ruff check .
just format           # uv run ruff format .
```

### Cache & State Management (justfile)

```bash
just clear-search-cache   # Query cache only (~/.local/state/ani-tupi/cache)
just clear-cache          # Search + episode caches
just clear-cache-full     # Entire cache directories
just clear-history        # Watch history (~/.local/state/ani-tupi/history.json)
just clear-all            # Everything
```

### API Surface (`api/routes/`)

- `search.py` — `GET /search`, `GET /search/episodes`, `GET /search/seasons`
- `playback.py` — `GET /playback/state`, `POST /playback/start|control|autoplay`, `WS /playback/ws` (controls MPV via IPC)
- `history.py` — `GET/DELETE /history`, `GET/DELETE /history/{anime}`
- `sources.py` — `GET /sources`, `PUT /sources/priority`, `POST /sources/{source}/enable|disable`
- `settings.py` — `GET/PUT /settings` (user preferences)

The PWA frontend lives in `api/frontend/` (index.html, manifest.json, sw.js) and is served by the FastAPI app. Shared playback state is managed by `PlaybackStateManager` in `api/state.py`; request/response schemas in `api/schemas.py`.

---

## Architecture Principles

### The Three-Tier System

1. **API Routes** (`api/routes/`) - Parse user intent (HTTP/WebSocket endpoints)
2. **Services** (`services/`) - Coordinate plugins, cache, APIs, and persistence
3. **Plugins** (`scrapers/plugins/`) - Scrapers, pure adapters

Services orchestrate. They decide: "Should I search cache first?" "Which plugin should I use?"

Routes ask services questions. Services ask plugins for data. Plugins never ask anything—they're pure adapters.

**To extend**: Add a new feature? Build a service. Add a new data source? Build a plugin. Add a new endpoint? Wire up a service call in a route.

### Services Layer (`services/`)

- `repository.py` — `Repository` singleton (`anime_repository`): multi-source search + dedup
- `search_repository.py`, `episode_repository.py`, `player_repository.py`, `history_service.py` — focused repositories
- `playback_coordinator.py` — `PlaybackCoordinator`, `safe_plugin_call` (resilient plugin invocation)
- `plugin_registry.py` — `PluginRegistry`: which plugins exist/are enabled, priority ordering (`priority_utils.py`)
- `anime/title_normalization.py` — title dedup logic

### Scrapers (`scrapers/`)

- `loader.py` — auto-discovers plugins
- `core/` — shared infra: `http.py` (Scrapling fetch shim: `fetch`/`post`/`fetch_json` + `FetchError`), `blogger_resolver.py`. Dynamic sources (anroll, animesdigital slug fallback) use Scrapling's `StealthyFetcher`/`DynamicFetcher` — run `just scrapling-install` once to download browsers
- `plugins/` — 9 sources: animefire, animesdigital, animesonlinecc, animesonlinecloud, anitube, anroll, dattebayo, goyabu, sushianimes (+ shared `utils.py`)

### Pattern: Centralized Configuration

All settings flow through `models/config.py` (Pydantic v2):

```python
from models.config import settings
cache_ttl = settings.cache.duration_hours
api_port = settings.api.port
```

Settings groups (`AppSettings`): `cache`, `search`, `plugins`, `performance`, `download`, `update_check`, `playback`, `api`.

Why? Environment variables override defaults (`ANI_TUPI__CACHE__DURATION_HOURS=48`), no scattered `.env` files, type validation on boot, configuration is self-documenting.

### Pattern: Plugin Protocol (Not Inheritance)

Each plugin implements a structural type:

```python
class Scraper(Protocol):
    def search(self, query: str) -> list[AnimeMetadata]: ...
    def get_episodes(self, url: str) -> list[EpisodeData]: ...
```

Why protocol, not ABC?
- Scrapers auto-discover with duck typing
- No base class boilerplate
- Plugin loading is one loop: find `.py` files in `scrapers/plugins/`, import them, extract classes matching the protocol

### Pattern: Repository for Plugin Access

Don't import plugins directly. Use the repository:

```python
from services.repository import anime_repository

results = anime_repository.search_anime(query)
```

Why? Scrapers are loaded dynamically. The repository tracks which ones exist, which ones are enabled.

### Pattern: Multi-Source Title Normalization

The repository automatically deduplicates anime results from multiple sources using intelligent title normalization. This means:

**Same anime, different title formats are merged:**
```
AnimesDigital: "Anime A: Revolucao Dublado"
AnimeOnlineCC: "Anime A - Revolucao Dublado"
AnimeFireTV:   "Anime A | Revolucao Dublado"

Result: Single entry "anime a revolucao dublado [animesdigital, animesonlinecc, animefiretv]"
```

**How it works:**
- `normalize_title_for_dedup()` strips away separators (`:`, `-`, `|`, `/`), language markers (`Dublado`, `Legendado`), and season indicators
- When `add_anime()` is called, new titles are matched against existing normalized titles
- If normalized forms match, the source is appended to the existing entry
- If no match, a new entry is created

**Examples of merged titles:**
```
"Jujutsu Kaisen Season 2 Dublado" + "Jujutsu Kaisen 2nd Season"
→ "jujutsu kaisen 2 [both sources]"

"Hell's Paradise: Jigokuraku" + "Hell's Paradise - Jigokuraku"
→ "hell s paradise jigokuraku [both sources]"
```

Why? Reduces cognitive load during search. Users see one entry per anime with all available sources, not 3-4 duplicate entries with slight title variations.

### Pattern: Caching as a Wrapper

Services decide *when* to cache, not the scraper:

```python
if cache_hit := self.cache.get(key):
    return cache_hit

results = scraper.search(query)
self.cache.set(key, results, ttl=settings.cache_duration_hours)
```

Scrapers stay simple. Services control cache strategy. Cache invalidation is centralized.

### Pattern: External Tools via Adapters

MPV and other external tools—wrap them:

```python
class VideoPlayer:
    def play(self, url: str, episode_number: int) -> None:
        # IPC to MPV
```

Why? Replacing MPV = swap one class. Testing doesn't require external tools (mock them).

---

## Data Structures

All data validated with Pydantic (`models/models.py`). Key models:

- **Scraping**: `AnimeMetadata`, `EpisodeData`, `VideoUrl`, `EpisodeContext`
- **Search**: `SearchMetadata`, `AnimeSearchResult` (frozen), `SearchResults` (frozen)
- **Cache**: `ScraperCacheData`, `CacheStats`
- **Downloads**: `DownloadedEpisode`, `DownloadResult`, `AnimeDownloadHistory`, `AnimeDownloadDatabase`
- **Misc**: `Status`, `UpdateCheckState`, `UpdateCheckResult`, `HistoryEntry`

API request/response schemas live separately in `api/schemas.py` (e.g., `SearchResponse`, `PlaybackState`, `HistoryEntrySchema`, `WSMessage`).

Why Pydantic? Validation on entry (fail fast if scraper returns garbage), type hints everywhere, serialization to JSON for cache/history.

---

## How to Extend

### Add a New Scraper

1. Create `scrapers/plugins/newsource.py`:
```python
class NewSourceScraper:
    def search(self, query: str) -> list[AnimeMetadata]:
        # Call API, parse HTML, return metadata
        pass

    def get_episodes(self, url: str) -> list[EpisodeData]:
        # Parse page, extract video URLs
        pass
```

2. Auto-discovered by `scrapers/loader.py` on boot. No registration needed.

3. Test: `uv run pytest tests/` includes plugin discovery checks.

### Add a New Service

Most feature work belongs here. Example: adding "trending anime" feature:

1. Create `services/trending_service.py`:
```python
class TrendingService:
    def __init__(self, scrapers: list[Scraper], cache: Cache, api_client: APIClient):
        self.scrapers = scrapers
        self.cache = cache
        self.api = api_client

    def get_trending(self, language: str) -> list[AnimeMetadata]:
        # Hit API or scrape, cache result, return
        pass
```

2. In a route (`api/routes/`), instantiate and use:
```python
service = TrendingService(...)
trending = service.get_trending("pt-br")
```

Services own the business logic. Routes own the HTTP flow.

### Add a New API Route

1. Create `api/routes/newfeature.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/newfeature", tags=["newfeature"])

@router.get("")
async def get_newfeature():
    return SomeService().do_something()
```

2. Register the router in `api/server.py` (`create_app()`). Define schemas in `api/schemas.py`.

---

## Development Workflow


**Quality**:
```bash
uv run ruff check .                      # Lint
uv run ruff format .                     # Format
uv run pytest                            # Test
uv run pytest -v --cov=. --cov-report=html  # Coverage
uv run mypy . && uv run pyright          # Type checking
uv run deptry . && uv run vulture        # Dep/dead-code checks
```

Pre-commit hooks run via **prek**.

**Manage**:
```bash
uv add package-name                      # Add dependency
uv remove package-name                   # Remove dependency
uv sync --upgrade                        # Update all
```

**Branch naming**:
- Do **not** use the `cursor/` prefix for feature branches — it interferes with version-bump commits from the release bot.
- Prefer descriptive names with conventional prefixes, e.g. `feat/history-sync`, `fix/scraper-timeout`, `chore/consolidate-pyright-config`.

**How to Use**:

Just write conventional commits and push to branch:

```bash
# Feature release (bumps minor: 0.2.2 → 0.3.0)
git commit -m "feat: add new capability"

# Patch release (bumps patch: 0.2.2 → 0.2.3)
git commit -m "fix: resolve issue"

# Major release (bumps major: 0.2.2 → 1.0.0)
git commit -m "feat: breaking change

BREAKING CHANGE: description of breaking change"

git push
# → CI runs → Release workflow triggers → v0.3.0 published!
```

**Never use `git commit --no-verify`.**
- Commits must pass local hooks before they are created
- If a hook fails, fix the root cause and rerun the commit
- If hooks conflict with unrelated local changes, isolate the relevant changes properly instead of bypassing verification

**Release Workflow**:
- Triggers automatically after CI passes on main branch
- Calculates next version from commit history since last release
- Creates git tag (e.g., `v0.2.0`) and GitHub Release
- Generates release notes from commit messages
- Updates CHANGELOG.md

**⚠️ Always `git pull --rebase` before pushing after a `feat:` or `fix:` commit.**
The release bot commits the version bump and CHANGELOG directly to remote, so the local branch will be behind. This is expected — just rebase and push.

**Configuration**:
- Release rules: `[tool.semantic_release]` in `pyproject.toml` (what triggers bumps)
- Workflow: `.github/workflows/release.yml` (GitHub Actions)
- Tool: `python-semantic-release` (not Node.js `semantic-release`)
- Always use conventional commits to get the correct version bump

**Troubleshooting Release Failures**:
- **Release workflow didn't trigger**: Check that CI workflow name is exactly "CI" (matches `workflow_run` trigger)
- **Version not bumped**: Ensure commits use correct conventional format (`feat:`, `fix:`, etc.)
- **Push permission error**: Ensure `GITHUB_TOKEN` has `contents: write` permission in workflow
- **"no release will be made"**: Normal for feature branches; release only happens on `master`/`main`
- **Version mismatch**: If `pyproject.toml` version diverges from latest git tag, manually update to match (`git tag -l | sort -V | tail -1`)

---


## Testing Strategy

**Principle: NO MOCKING BY DEFAULT. Use real implementations. Only mock external tools, APIs, and destructive operations.**

### The Rule
- **Start with real code**: Every test should exercise actual functions and services
- **Only mock externals**: HTTP calls, database connections, external APIs
- **Use temp directories instead of mocking**: Never mock file operations—use `temp_dir` fixture
- **Never mock internal services**: If you're mocking a service layer or plugin, you're not testing integration

### Test Approach
- **Integration tests** with real services, plugins, and storage (NEVER mock these)
- **Mock external APIs only**: external video providers, HTTP requests
- **Mock destructive operations**: Never delete real files—use temporary directories with auto-cleanup
- **Real plugin loading**: Load actual scrapers from `scrapers/plugins/` directory
- **Real storage**: Use temporary directories for cache/downloads (auto-cleanup via pytest fixtures)

### Test Layout & Markers

- `tests/unit/` — fast, isolated tests (scrapers, services, utils)
- `tests/integration/` — cross-layer tests, including real-HTTP scraper tests
- Root `tests/` — repository/coordinator tests, shared `conftest.py`
- Markers (`pytest.ini`): `unit`, `integration`, `e2e`, `slow`, `requires_browser`, `requires_http`


### Refactoring Pattern
Old (excessive mocks):
```python
# Mock both scraper AND repository = no real integration testing
with patch.object(scraper, 'search') as mock_search:
    mock_search.return_value = [...]
    result = repository.search_anime("query")
```

New (real integration):
```python
# Use real repository with real scrapers, mock only the HTTP transport
with patch("scrapers.plugins.<plugin>.fetch") as mock_fetch:  # External fetch mock only
    mock_fetch.return_value = Selector("<html>...</html>")  # scrapling.parser.Selector
    result = repository.search_anime("query")  # Real scrapers, real business logic
```

Goal: 80%+ coverage on service layer (business logic). CLI layer and utilities need less coverage (tested manually).

### Running Tests with Subagents

When running the full test suite (`uv run pytest`), use a **test-runner** subagent to avoid filling the main context window with large output:

```bash
# Instead of: uv run pytest -v
# Use the subagent system to run tests and report failures
```

The subagent will:
1. Execute `uv run pytest -v` in isolation
2. Parse test results and identify failures
3. Report failures with:
   - File paths and line numbers
   - Error messages and stack traces
   - Suggested fixes or patterns
4. Return a concise summary (not the raw 88KB output)

This keeps the conversation focused and prevents context bloat while maintaining full access to test diagnostics.

---

## Notes for Contributors

1. **Always use `uv`**.
2. **Config in `models/config.py`**—not scattered imports.
3. **Business logic in services**—not routes or UI.
4. **Don't import plugins directly**—use the repository.
5. **Immutable data**—return new objects, never mutate input.
6. **Avoid circular imports**: api → services → scrapers/models/utils.

### Utilities (`utils/`)

- `cache_manager.py`, `scraper_cache.py`, `cache.py` — cache layers
- `video_player.py` — MPV adapter (IPC); `mpv_scripts/skip.lua` — skip-intro script
- `playback_hints.py`, `episode_range_parser.py`, `title_utils.py`, `persistence.py`, `logging.py`, `exceptions.py`
7. **Persist data** in `~/.local/state/ani-tupi/` (XDG standard).
8. **No hardcoded values**—use config or Pydantic models.

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```


### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```


### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk diff                # Ultra-compact diffs
```


### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

<!-- /rtk-instructions -->
