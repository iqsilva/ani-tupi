# ani-tupi

Brazilian Portuguese CLI for anime and manga with multi-source support, AniList integration, and external player support.

## Core Value

Users can discover and watch anime from multiple sources without leaving the terminal, with seamless AniList sync and flexible offline capabilities.

## Current State

- ✅ Multi-source scraping (AnimesDigital, AnimeFire, AnimesonlineCC, etc.)
- ✅ AniList integration with headless OAuth
- ✅ Anime download and local library
- ✅ Manga search and reading with PDF support
- ✅ Download queue with parallel execution
- ✅ Codebase uses mix of `print()` statements and stdlib `logging`
- ❌ Debug logging not wired or structured
- ❌ No visibility into app execution for AI agents

## Architecture

- **Commands** — CLI entry points (anime.py, manga.py, anilist.py)
- **Services** — Business logic (anime/, manga/, anilist integration)
- **Plugins** — Scrapers loaded dynamically from `scrapers/plugins/`
- **UI** — Menu rendering and user output
- **Config** — Pydantic-based settings in `models/config.py`
- **Utils** — Helpers including cache, discovery, logging

Logging infrastructure exists in `utils/logging.py` using loguru but isn't fully integrated.

## Milestone Sequence

- [ ] **M001: Debug Logging Infrastructure** — Full execution tracing with `--debug` flag, JSON format, sensitive data masking, print() statement replacement
