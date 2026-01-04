<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

## Development Environment & Commands

All development tasks MUST use **UV** as the package manager.

### Core Commands
- **Run App:** `uv run ani-tupi` (Interactive) or `uv run ani-tupi -q "search"` (Direct)
- **Run Tests:** `uv run pytest` (Run `pytest.ini` defines categories like `unit`, `integration`, `e2e`)
- **Lint/Format:** `uvx ruff check .` and `uvx ruff format .`
- **Dependencies:** `uv add package-name` or `uv add --dev package-name`
- **Build:** `uv run build.py` (Generates executable in `dist/`)

## Architecture & Design Patterns

### MVCP (Model-View-Controller-Plugin)
- **Model:** `services/repository.py` (Singleton `rep`) - Central state for anime, episodes, and source mappings.
- **View:** `ui/components.py` and `ui/anilist_menus.py` - Rich and InquirerPy based terminal UI.
- **Controller:** `commands/*.py` and `main.py` - Route logic and application flow.
- **Plugins:** `scrapers/plugins/` - Individual scrapers implementing `PluginInterface` (structural typing via `Protocol`).

### Key Services
- **`anime_service.py`**: Business logic for search, caching, and playback.
- **`anilist_service.py`**: GraphQL client for AniList API (OAuth, progress sync).
- **`history_service.py`**: Local watch progress persistence (`~/.local/state/ani-tupi/`).
- **`manga_service.py`**: MangaDex API client.

### Patterns
- **Structural Protocol:** Scrapers must implement `PluginInterface` in `scrapers/loader.py`.
- **Async Racing:** Multiple plugins race to find working stream URLs in `Repository.search_player`.
- **Singleton Repository:** Use `from services.repository import rep` to access/modify global state.
- **Pydantic Validation:** Models in `models/models.py` and settings in `models/config.py`.

## Code Conventions

- **Language:** Python 3.12+ with type hints.
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes.
- **Imports:** Standard lib -> External -> Local. Use absolute imports.
- **Path Handling:** Use `pathlib.Path` exclusively. Use `get_resource_path()` in `loader.py` for bundled files.
- **Logging:** Use `utils.logging.get_logger(__name__)` (loguru-backed).

## Important Gotchas

- **Video URLs:** DO NOT cache video stream URLs (e.g., Blogger/Google Video) as they contain short-lived tokens.
- **Scraper Brittleness:** CSS selectors change frequently; always verify selectors with current site HTML if scraping fails.
- **MPV IPC:** Playback uses IPC sockets (Unix) or Named Pipes (Windows) for episode navigation during playback.
- **Fuzzy Matching:** Scraper titles are normalized and matched against AniList titles with a threshold (default 90).

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up.
2. **Run quality gates** - `uv run pytest` and `uvx ruff check .`.
3. **Update issue status** - Close finished work.
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Verify** - All changes committed AND pushed.

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds.
- NEVER say "ready to push when you are" - YOU must push.
- If push fails, resolve and retry until it succeeds.
