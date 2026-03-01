# CLAUDE.md

Guidance for developing ani-tupi: a Brazilian Portuguese CLI for anime and manga with multi-source support, AniList integration, and external player support.

---

## Workflow Orchestration

**Everything starts with execution discipline.** These principles prevent mistakes, reduce rework, and ensure high-quality contributions.

### 1. Plan Mode Default

- **Enter plan mode for ANY non-trivial task** (3+ steps or architectural decisions)
- If something goes sideways, **STOP and re-plan immediately** — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop

- After ANY correction from the user, update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done

- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)

- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing what I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing

- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

### Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

### Core Execution Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Core Values

**Simplicity First**: Every feature should feel effortless to the user. Complex logic (incremental search, fuzzy matching, automatic syncing) runs invisibly.

**DRY Architecture**: Code is organized by *what it does*, not *where it lives*. If multiple scrapers implement `search()` → they're one pattern (plugin protocol). If multiple services fetch from APIs → they share a base class. If code repeats → extract it.

**Immutable Data Flow**: Data flows forward only. Services don't modify input; they return transformed copies. This makes debugging trivial: follow the data, not the mutations.

**Plugin Everything**: Scrapers, PDF readers, storage backends—all pluggable. New source? Create one file. Done.

**User Configuration Over Code**: Settings live in environment variables (via Pydantic config), not config files that break. Users can tune everything without touching code.

---

## Architecture Principles

### The Three-Tier System

1. **Commands** (CLI entry points) - Parse user intent
2. **Services** (business logic) - Coordinate plugins, cache, APIs, and persistence
3. **Plugins** (implementations) - Scrapers, readers, storage backends

Services orchestrate. They decide: "Should I search cache first?" "Should I sync to AniList?" "Which plugin should I use?"

Commands ask services questions. Services ask plugins for data. Plugins never ask anything—they're pure adapters.

**To extend**: Add a new feature? Build a service. Add a new data source? Build a plugin. Add a new command? Wire up a service call.

### Pattern: Centralized Configuration

All settings flow through `models/config.py` (Pydantic v2):

```python
from models.config import settings
cache_ttl = settings.cache_duration_hours
reader = settings.manga.pdf_reader
```

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
from services.repository import get_scrapers

for scraper in get_scrapers():
    results.extend(scraper.search(query))
```

Why? Scrapers are loaded dynamically. The repository tracks which ones exist, which ones are enabled.

### Pattern: Multi-Source Title Normalization

The repository automatically deduplicates anime results from multiple sources using intelligent title normalization. This means:

**Same anime, different title formats are merged:**
```
AnimesDigital: "Anime A: Revolucao Dublado"
AnimeOnlineCC: "Anime A - Revolucao Dublado"
AnimeFireTV:   "Anime A | Revolucao Dublado"

Result: Single entry "Anime A: Revolucao Dublado [animesdigital, animesonlinecc, animefiretv]"
```

**How it works:**
- `normalize_title_for_dedup()` strips away separators (`:`, `-`, `|`, `/`), language markers (`Dublado`, `Legendado`), and season indicators
- When `add_anime()` is called, new titles are matched against existing normalized titles
- If normalized forms match, the source is appended to the existing entry
- If no match, a new entry is created

**Examples of merged titles:**
```
"Jujutsu Kaisen Season 2 Dublado" + "Jujutsu Kaisen 2nd Season"
→ "Jujutsu Kaisen 2 [both sources]"

"Hell's Paradise: Jigokuraku" + "Hell's Paradise - Jigokuraku"
→ "Hell's Paradise: Jigokuraku [both sources]"
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

MPV, PDF readers, MangaDex API—all external. Wrap them:

```python
class VideoPlayer:
    def play(self, url: str, episode_number: int) -> None:
        # IPC to MPV

class MangaReader:
    def open(self, pdf_path: str) -> None:
        # Detect installed readers, execute in priority order
```

Why? Replacing MPV = swap one class. Testing doesn't require external tools (mock them).

---

## Data Structures

All data validated with Pydantic (`models/models.py`):

```python
class AnimeMetadata(BaseModel):
    title: str
    url: str
    cover: str | None = None

class EpisodeData(BaseModel):
    number: int
    title: str
    video_url: str
    aired: date | None = None
```

Why Pydantic? Validation on entry (fail fast if scraper returns garbage), type hints everywhere, serialization to JSON for cache/history.

---

## Configuration

All settings are environment variables. Use Pydantic as the source of truth:

```bash
ANI_TUPI__CACHE__DURATION_HOURS=48
ANI_TUPI__MANGA__PDF_READER=zathura
ANI_TUPI__LOG_LEVEL=debug
```

### Source Priority Configuration

**Standard Priority** (used for all anime):
```bash
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "goyabu", "animefire", "animesonlinecc"]'
```

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

2. In the command layer (`commands/anime.py`), instantiate and use:
```python
service = TrendingService(get_scrapers(), cache, api_client)
trending = service.get_trending("pt-br")
```

Services own the business logic. Commands own the CLI flow.

### Add a New Command

1. Create `commands/newcommand.py`:
```python
def handle_new_command(args):
    service = SomeService()
    result = service.do_something()
    render_menu(result)
```

2. Wire it in `main.py` argument parser, route to the function.

### Modify AniList Integration

AniList touches three places (because AniList is stateful—token, rate limits, cached queries):

1. **API client**: `services/anilist_service.py`
   - All GraphQL queries/mutations live here
   - Handles rate limiting, token refresh

2. **Discovery** (title mapping): `utils/anilist_discovery.py`
   - Fuzzy-matches scraper titles to AniList IDs
   - Caches winning matches in JSON

3. **Commands**: `commands/anilist.py`
   - User-facing flow: auth, list browsing, sync triggers

To add a feature: modify 1 (add the API method), then 2–3 if title mapping is needed.

---

## Features

### Anime Download

Download episodes for offline viewing. Episodes stored in `~/.local/share/ani-tupi/anime/` organized by title.

**How to Download**:
1. While watching, select "📥 Baixar para assistir depois"
2. Enter episode range: `5`, `1-12`, `5-`, `-12`, or `5-15`
3. Episodes download in parallel (respects `max_parallel_downloads` config, default: 2)
4. Already-downloaded episodes are skipped automatically

**Configuration**:
```bash
export ANI_TUPI__ANIME__MAX_PARALLEL_DOWNLOADS=4
export ANI_TUPI__ANIME__DOWNLOAD_DIRECTORY="~/Videos/Anime"
export ANI_TUPI__ANIME__VIDEO_FORMAT="mp4"
```

**Architecture**:
- `AnimeDownloadService`: Orchestrates downloads with parallel queue and retry logic
- `LocalAnimeService`: Scans and manages local library
- Episodes stored in: `~/.local/share/ani-tupi/anime/{anime_title}/{episode_number}.mkv`
- Metadata stored in: `~/.local/state/ani-tupi/anime_downloads.json`

### Airing Episodes

The "🎬 Novos Episódios" tab displays anime from your AniList watching list that have new episodes currently airing.

**How to Access**:
1. Open the AniList menu: `uv run ani-tupi`
2. Select "🎬 Novos Episódios" (appears at top of authenticated menu)
3. Browse anime sorted by urgency (most episodes behind first)
4. Select an anime to start playback

**Display Format**:
```
Jujutsu Kaisen - Ep 25 aired, você viu 22 (3 atrasado) ⭐82%
Dandadan - Ep 18 aired, você viu 15 (3 atrasado) ⭐79%
Blue Lock - Ep 11 aired, você viu 11 (0 atrasado) ⭐75%
```

**Architecture**:
- `services/anime/airing_episodes_service.py`: Business logic (filtering, sorting, gap calculation)
- `services/anilist/anime_operations.py`: GraphQL query `get_airing_episodes_for_watching()`
- `models/models.py`: `AiringAnimeEntry` Pydantic model for display data

**Testing**:
```bash
uv run pytest tests/test_airing_episodes_service.py tests/test_anilist_airing_query.py -v
```

---

## Development Workflow

**Setup**:
```bash
uv sync
```

**Run**:
```bash
uv run ani-tupi                          # Anime CLI
uv run manga_tupi                        # Manga CLI
uv run main.py --debug                   # Enable debug logging
```

**Quality**:
```bash
uv run ruff check .                      # Lint
uv run ruff format .                     # Format
uv run pytest                            # Test
uv run pytest -v --cov=. --cov-report=html  # Coverage
```

**Manage**:
```bash
uv add package-name                      # Add dependency
uv remove package-name                   # Remove dependency
uv sync --upgrade                        # Update all
```

---

## Known Issues & Solutions

### Scraper Results Not Cached

**Root Cause**: Service not calling `cache.set()` after fetch.

**Solution**: Check `services/anime_service.py` where results are returned. If cache miss, add:
```python
self.cache.set(cache_key, results, ttl=settings.cache_duration_hours)
```

### New PDF Reader Not Detected

**Root Cause**: `utils/manga_reader.py` detection loop doesn't check for your reader.

**Solution**: Add executable name to priority list:
```python
PRIORITY = ["zathura", "evince", "your-reader-name", "xdg-open"]
```

### AniList Sync Fails

**Root Causes**:
1. Token expired (valid ~6 months)
2. Network error (retry on next episode)
3. Title mismatch (create mapping manually)

**Debugging**:
```bash
export ANI_TUPI__LOG_LEVEL=debug
uv run ani-tupi --query "anime name"
```

Logs show GraphQL requests/responses.

### AnimesonlineCC Videos Fail

**Root Cause**: Videos use temporary Blogger URLs with short expiry.

**Solution**: Use AnimesDigital or AnimeFire as primary sources:
```bash
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "animefire"]'
```

### Incremental Search Gives Wrong Results

**Root Cause**: Words not split correctly or thresholds miscalibrated.

**Solution**: Check `services/anime_service.py` incremental search algorithm:
- Split query by space
- Start with first 3 words
- Add one word per iteration
- Stop when results ≤ 5 or all words used

---

## Design Trade-Offs

**Protocol over Inheritance**: Less boilerplate, but requires discipline (protocols aren't enforced at runtime—duck typing catches mistakes late).

**Centralized Config**: Simpler, but environment variables are less discoverable than a config file.

**External Tools as Adapters**: Maximum flexibility, but means testing requires mocks (no integration tests with real MPV).

**DRY Documentation**: This guide repeats no code flows. But it's denser to read. Always refer to actual services for truth.

---

## Testing Strategy

- **Unit tests** for services (mock scrapers, cache, API clients)
- **Integration tests** for plugin loading (verify scrapers are discoverable)
- **E2E tests** for critical flows (search → select → play/read)

Goal: 80%+ coverage on service layer (business logic). CLI layer and utilities need less coverage (tested manually).

---

## Notes for Contributors

1. **Always use `uv`**.
2. **Config in `models/config.py`**—not scattered imports.
3. **Business logic in services**—not commands or UI.
4. **Don't import plugins directly**—use the repository.
5. **Immutable data**—return new objects, never mutate input.
6. **Avoid circular imports**: commands → services → models/utils.
7. **Persist data** in `~/.local/state/ani-tupi/` (XDG standard).
8. **No hardcoded values**—use config or Pydantic models.

---

## When to Refactor

**Red flag**: Code is repeated in two places → extract a function.

**Red flag**: A function has more than 3 parameters → create a type (dataclass, Pydantic model, or class) to hold them.

**Red flag**: Two functions have identical parameters and both modify state → make them methods of a class.

**Red flag**: A service has 3+ dependencies → consider dependency injection pattern.

**Red flag**: A plugin doesn't implement the protocol → it's probably a command or service, not a plugin.
