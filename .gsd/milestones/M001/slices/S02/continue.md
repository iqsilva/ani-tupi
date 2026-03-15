---
milestone: M001
slice: S02
task: T01
step: 1
total_steps: 4
saved_at: 2026-03-15T14:00:00Z
---

## Completed Work

### S01: Complete ✅
- Extended utils/logging.py with JSON format, rotation, masking
- Wired --debug flag in main.py
- 19 unit tests all passing
- S01 summary written and committed

### S02/T01: In Progress
- Started systematic print() replacement
- Completed: services/anime/search.py (5 print() calls → logger.info/debug)
- Identified 495 total print() calls across 30 files
- Top 5 files by print() count:
  1. manga_tupi.py (96)
  2. services/anime/anilist_integration.py (68)
  3. commands/anime.py (57)
  4. utils/video_player.py (43)
  5. services/repository.py (24)

## Remaining Work

### T01: Replace print() in services layer
- [ ] services/anime/anilist_integration.py (68 calls)
- [ ] services/anime/playback_fallback.py (6 calls)
- [ ] services/anime/playback_service.py (4 calls)
- [ ] services/anime/random_anime_service.py (12 calls)
- [ ] services/anime/source_management.py (3 calls)
- [ ] services/anime/episode_url_pattern.py (3 calls)
- [ ] services/anime/episode_context.py (1 call)
- [ ] services/repository.py (24 calls)
- [ ] services/history_service.py (18 calls)
- [ ] services/manga_service.py (10 calls)
- [ ] services/manga/anilist_lists.py (2 calls)
- [ ] services/manga/download.py (15 calls)
- [ ] services/anilist/client.py (4 calls)

### T02: Replace print() in commands and UI
- [ ] commands/anime.py (57 calls) — preserve UI output
- [ ] commands/local_anime.py (8 calls)
- [ ] ui/components.py (2 calls) — preserve UI output
- [ ] ui/anilist_menus.py (15 calls) — preserve UI output

### T03: Replace print() in utils, scrapers, main
- [ ] utils/anilist_discovery.py (11 calls)
- [ ] utils/video_player.py (43 calls)
- [ ] utils/manga_reader.py (10 calls)
- [ ] utils/headless_detector.py (9 calls)
- [ ] main.py (8 calls)
- [ ] manga_tupi.py (96 calls)
- [ ] manga_scrapers/loader.py (1 call)
- [ ] manga_scrapers/plugins/mangalivre.py (6 calls)
- [ ] manga_scrapers/plugins/mugiwaras.py (7 calls)
- [ ] scrapers/plugins/topanimes.py (3 calls)
- [ ] plugin_manager.py (5 calls)

### T04: Verify and test
- [ ] Run grep to confirm 0 print() in business logic
- [ ] Run full test suite
- [ ] End-to-end test with --debug flag

## Decisions Made

- All print() calls become logger.info() or logger.debug()
- UI output (prompts, menus) → logger.info() (still visible, but logged)
- Internal operations (cache hits, scraper calls, API responses) → logger.debug()
- All calls to get_logger() already in place or will be added

## Context

The task is mechanical but requires care:
1. Every print() must be replaced with logger.info/debug
2. UI output should stay visible (logger.info sends to both file and console in debug mode)
3. Need to add `from utils.logging import get_logger; logger = get_logger(__name__)` to files that don't have it

## Next Action

Continue T01 systematically. Tackle services/anime/anilist_integration.py next (68 calls — largest single file). Use this pattern:
1. Read file
2. Add logger import if missing: `from utils.logging import get_logger; logger = get_logger(__name__)`
3. Find all print() calls
4. Replace with logger.info() for user-facing, logger.debug() for internal
5. Commit atomically per file or per directory
