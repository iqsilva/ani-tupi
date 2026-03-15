# S02: Print Statement Replacement

**Goal:** Systematically replace all 2400+ print() statements with loguru logger calls across 449 files, while preserving UI output (prompts, menus, results) as intentional stdout/stderr.

**Demo:** Grep confirms zero print() calls in business logic (services, commands, utils); UI still renders normally; running with --debug shows full execution trace in debug.log.

## Must-Haves

### Truths

- No remaining print() calls in business logic (verified by grep for "print(" in src files returning 0 results)
- All internal operations (API calls, scraper decisions, cache checks, file I/O) log via loguru
- User-facing output (prompts, menus, results) still uses print() unchanged
- Running `ani-tupi --debug --query test` produces complete log entries for search, scraper calls, caching, results
- Existing tests still pass (no behavior changes, only logging changes)

### Artifacts

- Replaced print() calls across all 449 affected files (estimated 2400+ replacements)
  - Services: `services/anime/*.py`, `services/manga/*.py`, `services/anilist/*.py`
  - Commands: `commands/*.py`
  - Utils: `utils/*.py`
  - UI components: `ui/*.py` (only debug info logged, not output)
  - Scrapers: `scrapers/plugins/*.py`
  - Main entry: `main.py`
- Verification script or grep commands showing no remaining print() in business logic
- All tests pass: `uv run pytest` returns 0 failures

### Key Links

- All files → `utils/logging.py` via `from loguru import logger`
- `main.py` → logging config already wired (from S01)

## Tasks

- [ ] **T01: Replace print() in services layer**
  Systematically replace all print() calls in `services/` directory with logger calls.

- [ ] **T02: Replace print() in commands and UI**
  Replace print() in `commands/` and `ui/` directories, preserving user-facing output as intentional.

- [ ] **T03: Replace print() in utils, scrapers, and main**
  Replace remaining print() calls in `utils/`, `scrapers/`, and `main.py`.

- [ ] **T04: Verify and test**
  Run grep to confirm no remaining print() in business logic; run full test suite to ensure no regressions.

## Files Likely Touched

- All files in `services/`, `commands/`, `ui/`, `utils/`, `scrapers/plugins/`, `main.py`
- Test files may need updates if they mock print() behavior
- No new files created (replacements only)
