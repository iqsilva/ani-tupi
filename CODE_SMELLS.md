# ani-tupi Code Smells Analysis

Violations of CLAUDE.md architectural principles, identified for systematic remediation.

---

## Priority: CRITICAL

### [C1] Duplicate Service Implementation - Manga
**Status**: Blocking, creates confusion
**Files**:
- `services/manga_service.py` (old, 600+ lines)
- `services/unified_manga_service.py` (new, 463 lines)

**Issue**: Two competing implementations of the same service. Which one is active? Tests and commands may import different one.

**Violation**: Service Layer as Coordinator principle - unclear which is the source of truth.

**Impact**:
- Bugs in one won't be fixed in the other
- New features inconsistently implemented
- 1000+ lines of dead/duplicate code

**Fix**:
1. Audit which version is active in production (check imports in commands)
2. Merge both into single `services/manga_service.py`
3. Delete `services/unified_manga_service.py`
4. Update all imports to single version
5. Run full test suite to verify

**Effort**: Medium (reconcile 1000 lines of logic)

---

### [C2] Repository God Object - 750 Lines, 5 Responsibilities
**Status**: Blocks proper plugin architecture
**File**: `services/repository.py` (750 lines)

**Issue**: Single class managing:
1. Plugin registry (register, get_active_sources)
2. Search logic (search_anime, incremental search)
3. Episode caching (add_episode_list, get_episode_list)
4. Video URL search (search_player)
5. Deduplication (add_anime, norm_titles)

**Violation**: Single Responsibility Principle + violates DRY Architecture

**Code Example** (lines 70-750 all mixed):
```python
class Repository:
    def search_anime(self):  # Plugin coordination + cache logic
        ...

    def add_episode_list(self):  # Episode caching
        ...

    def search_player(self):  # Video search
        ...

    def search_with_incremental_results(self):  # Search algorithm
        ...
```

**Fix**: Split into 4 classes:
1. **PluginRegistry** - plugin lifecycle
   - `register_plugin(name, scraper)`
   - `get_active_sources()`
   - `unregister_plugin(name)`

2. **SearchRepository** - anime search results caching
   - `cache_search_results(query, results, ttl)`
   - `get_cached_results(query)`
   - `clear_search_cache()`

3. **EpisodeRepository** - episode metadata caching
   - `cache_episodes(anime_url, episodes, ttl)`
   - `get_cached_episodes(anime_url)`

4. **PlayerRepository** - video URL resolution
   - `cache_video_urls(episode_url, urls, ttl)`
   - `get_video_urls(episode_url)`

Each class: <200 lines, single responsibility, testable in isolation.

**Effort**: High (refactor with tests, update all imports)

---

### [C3] Mutable Repository State - Incremental Search Destroys Prior Results
**Status**: Causes data loss during search
**File**: `services/repository.py` (lines 124, 239-305, 336-340)

**Issue**: Repository mutates instance variables during search:
```python
def search_anime(self, query):
    # Line 124: Clear ALL prior results
    self.anime_to_urls = defaultdict(list)
    self.anime_episodes_titles = defaultdict(list)

    # Lines 239-305: _search_with_incremental_results
    # Mutates self.anime_to_urls, self.norm_titles, self._last_search_metadata

    # Lines 336-340: Directly append/mutate
    self.anime_to_urls[title].append((url, source, params))
    self.norm_titles[title] = title_
```

**Violation**: Immutable Data Flow principle - services must return new values, not mutate state.

**Problem Scenario**:
1. User searches "danddadan"
2. Repository mutates self.anime_to_urls
3. Search algorithm finds 20 results
4. clear_search_results() called mid-iteration
5. User gets partial results

**Fix**:
1. Don't mutate self.* during search
2. Build results in local variables
3. Return `SearchResult(anime_list, metadata)` dataclass
4. Let caller decide what to do with result (cache, display, etc.)

Example refactor:
```python
def search_anime(self, query: str) -> SearchResult:
    """Returns new SearchResult, never mutates state."""
    results = []  # Local, not self.anime_to_urls
    metadata = {}  # Local, not self.norm_titles

    for source in self.get_active_sources():
        search_results = source.search(query)
        results.extend(search_results)
        metadata.update(self._build_metadata(search_results))

    return SearchResult(anime_list=results, metadata=metadata)
```

**Effort**: High (refactor with tests)

---

## Priority: HIGH

### [H1] 4 Different Cache Implementations
**Status**: Inconsistent behavior, maintenance nightmare
**Files**:
- `services/manga_service.py:50-94` - MangaCache with TTL
- `scrapers/core/cache.py` - Scraper cache
- `utils/scraper_cache.py` - Wrapper around scraper cache
- `utils/cache_manager.py` - Global cache manager

**Issue**: Same concept (cache search results with TTL) implemented 4 times with different interfaces.

**Violation**: DRY Architecture principle

**Interfaces differ**:
```python
# MangaCache
manga_cache.get(key)
manga_cache.set(key, value, ttl)

# ScraperCache
scraper_cache.get_cached(key)
scraper_cache.cache(key, value)

# CacheManager
cache_manager.get(namespace, key)
cache_manager.set(namespace, key, value, ttl)
```

**Fix**: Unified cache abstraction:
1. Create `utils/cache.py`:
```python
class Cache(Protocol):
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...
    def invalidate(self, key: str) -> None: ...
```

2. Single implementation:
```python
class RedisCache(Cache):
    def __init__(self, redis_client, ttl: int):
        self.redis = redis_client
        self.ttl = ttl
```

3. Config injection:
```python
# In models/config.py
cache_type: str = "memory" | "redis"  # From env var ANI_TUPI__CACHE_TYPE

# In services
cache = get_cache(settings.cache_type)
```

4. Replace all 4 implementations with single injection point.

**Effort**: High (refactor + migrate storage backends)

---

### [H2] Inconsistent Configuration Fields
**Status**: Confusing, breaks incremental rollout
**File**: `models/config.py`
- Lines 74-78: `CacheSettings.duration_hours`
- Lines 226-230: `MangaSettings.cache_duration_hours`

**Issue**: Cache duration defined twice with different field names.

**Violation**: Centralized Configuration principle - should be one source of truth.

**Problem**:
```python
# Which one to use?
settings.cache.duration_hours  # 24
settings.manga.cache_duration_hours  # 12

# Code uses both inconsistently:
# Some files: TTL = settings.cache.duration_hours
# Other files: TTL = settings.manga.cache_duration_hours
```

**Fix**:
1. Consolidate to single `settings.cache.default_ttl_hours`
2. Allow override per-source: `settings.cache.source_ttls: dict[str, int]`
```python
class CacheSettings(BaseSettings):
    default_ttl_hours: int = Field(default=24, env="ANI_TUPI__CACHE__DEFAULT_TTL_HOURS")
    source_ttls: dict[str, int] = Field(
        default={
            "anime": 24,
            "manga": 12,
            "episodes": 48
        },
        env="ANI_TUPI__CACHE__SOURCE_TTLS"
    )
```

3. Search & replace in all files:
   - `settings.cache.duration_hours` → `settings.cache.default_ttl_hours`
   - `settings.manga.cache_duration_hours` → `settings.cache.source_ttls["manga"]`

**Effort**: Low (consolidate fields, search/replace)

---

### [H3] Inheritance Instead of Protocol (Plugin Architecture)
**Status**: Defeats structural typing benefits
**File**: `scrapers/loader.py:57-58, plugins/animefire.py:12-13`

**Issue**: Plugins inherit from Protocol, breaking structural typing.

**Current code**:
```python
# scrapers/loader.py
PluginInterface = PluginProtocol  # Aliased

# scrapers/plugins/animefire.py
class AnimeFire(PluginInterface):  # Inherits from Protocol!
    def search(self, query: str) -> list[AnimeMetadata]:
        ...
```

**Violation**: Plugin Protocol principle - should use duck typing, not inheritance.

**Why this matters**:
- Protocol is meant for structural typing (no inheritance)
- Inheritance creates tight coupling
- Third-party plugins must inherit, can't just implement interface

**Fix**:
1. Remove `PluginInterface` alias
2. Remove `(PluginProtocol)` from all plugin class definitions
3. Keep protocol for type hints only:
```python
# scrapers/plugins/animefire.py
class AnimeFire:
    languages = ["pt-br"]

    def search(self, query: str) -> list[AnimeMetadata]:
        ...

    def get_episodes(self, url: str) -> list[EpisodeData]:
        ...

# For type hinting in loader:
def load_plugin(plugin_class: Type[PluginProtocol]) -> PluginProtocol:
    return plugin_class()
```

4. Validation via duck typing:
```python
# scrapers/loader.py
def _validate_plugin(plugin_cls: type) -> bool:
    """Validate plugin implements required interface."""
    required_methods = {"search", "get_episodes"}
    return all(hasattr(plugin_cls, method) for method in required_methods)
```

**Effort**: Medium (remove inheritance, update plugins, add validation)

---

### [H4] Commands Doing Business Logic
**Status**: Violates separation of concerns
**File**: `commands/anime.py:46-97, 37, 49-69, 54, 109-124`

**Issue**: Command handler performs:
- AniList discovery (lines 49-69)
- History loading (line 37)
- Title normalization (line 54)
- Progress calculation (lines 109-124)

**Violation**: Service Layer as Coordinator - business logic belongs in services, not commands.

**Current code**:
```python
# commands/anime.py
def anime(query, ...):
    # Business logic scattered here
    if history.contains(query):  # History lookup
        ...

    anilist_discovery()  # AniList logic

    normalized_title = normalize(query)  # Normalization

    progress = calculate_progress()  # Progress calc

    service.search(query)  # Finally calls service
```

**Fix**: Move to `services/anime_service.py`:
```python
class AnimeService:
    def __init__(self, plugins, cache, anilist_api, history):
        self.plugins = plugins
        self.cache = cache
        self.anilist = anilist_api
        self.history = history

    def search(self, query: str) -> SearchResult:
        # All business logic here
        if cached := self.cache.get(query):
            return cached

        # Try AniList discovery first
        if anilist_result := self.anilist.search(query):
            return anilist_result

        # Search plugins
        results = self._search_plugins(query)
        self.cache.set(query, results, ttl=settings.cache_ttl)
        return results
```

Command becomes thin:
```python
# commands/anime.py
def anime(query, ...):
    service = AnimeService(...)
    result = service.search(query)  # One line!
    ui.display_menu(result)
```

**Effort**: Medium (extract business logic, update tests)

---

## Priority: MEDIUM

### [M1] Video URL Caching Disabled
**Status**: Performance issue with workaround
**File**: `services/repository.py:643-645`

**Issue**:
```python
# CACHE DISABLED for video URLs - tokens expire too quickly
# Caching causes playback failures
```

**Violation**: Caching as wrapper principle - but not using it optimally.

**Problem**: Video tokens from scrapers expire in seconds/minutes. Caching would return stale tokens.

**Fix**: Implement TTL-aware caching:
```python
class VideoURLRepository:
    def cache_url(self, episode_url: str, video_url: str, ttl_seconds: int = 300) -> None:
        """Cache video URL with short TTL (5 minutes default)."""
        cache_key = f"video_url:{episode_url}"
        expires_at = time.time() + ttl_seconds
        self.cache.set(cache_key, {
            "url": video_url,
            "expires_at": expires_at
        })

    def get_url(self, episode_url: str) -> Optional[str]:
        """Get cached URL if not expired."""
        if cached := self.cache.get(f"video_url:{episode_url}"):
            if time.time() < cached["expires_at"]:
                return cached["url"]
            # Expired, remove from cache
            self.cache.invalidate(f"video_url:{episode_url}")
        return None
```

Add to config:
```python
class PerformanceSettings(BaseSettings):
    video_url_cache_ttl_seconds: int = Field(
        default=300,  # 5 minutes
        env="ANI_TUPI__PERFORMANCE__VIDEO_URL_CACHE_TTL_SECONDS"
    )
```

**Effort**: Low (add TTL tracking to cache)

---

### [M2] Global Mutable State - Video Player Autoplay
**Status**: Causes state leakage between episodes
**File**: `utils/video_player.py:27-39`

**Issue**:
```python
_autoplay_enabled = False  # Global state

def set_autoplay_state(enabled: bool) -> None:
    global _autoplay_enabled
    _autoplay_enabled = enabled  # Mutation!
```

**Violation**: Immutable Data Flow + side effects.

**Problem**: State persists across episodes. If user cancels one episode, autoplay state may carry to next.

**Fix**: Pass state through object:
```python
class VideoPlayer:
    def __init__(self, autoplay: bool = False):
        self.autoplay = autoplay  # Instance state, not global

    def set_autoplay(self, enabled: bool) -> None:
        self.autoplay = enabled  # Mutate instance, not global

    def play(self, url: str) -> None:
        # Use self.autoplay, not global
        ...

# Usage
player = VideoPlayer(autoplay=settings.playback.autoplay)
player.play(episode_url)
```

**Effort**: Low (refactor to instance variables)

---

### [M3] Unbounded Plugin Map Growth
**Status**: Memory leak in long-running sessions
**File**: `services/unified_manga_service.py:49, 73`

**Issue**:
```python
self.manga_plugin_map: dict[str, str] = {}
# ...
self.manga_plugin_map[manga_id] = plugin_name  # Grows unbounded
```

**Violation**: Immutable Data Flow (mutation) + resource management.

**Problem**: Every manga search adds to map. No cleanup. After 1000 searches, map has 1000 entries.

**Fix**: Use LRU cache instead:
```python
from functools import lru_cache

class UnifiedMangaService:
    def __init__(self, ...):
        ...
        # LRU with max 1000 entries
        self._manga_plugin_cache = {}

    def _get_plugin_for_manga(self, manga_id: str) -> str:
        """Get plugin for manga, cache result."""
        # Check if in cache
        if manga_id in self._manga_plugin_cache:
            return self._manga_plugin_cache[manga_id]

        # Not in cache, search
        plugin = self._find_plugin(manga_id)

        # Add to cache with cleanup
        if len(self._manga_plugin_cache) > settings.cache.max_entries:
            # Remove oldest entry (simple FIFO cleanup)
            oldest_key = next(iter(self._manga_plugin_cache))
            del self._manga_plugin_cache[oldest_key]

        self._manga_plugin_cache[manga_id] = plugin
        return plugin
```

Or use `functools.lru_cache`:
```python
@lru_cache(maxsize=1000)
def _get_plugin_for_manga(self, manga_id: str) -> str:
    return self._find_plugin(manga_id)
```

**Effort**: Low (add cache eviction)

---

### [M4] Hardcoded PDF Reader Priority List
**Status**: Not configurable, scattered config
**File**: `utils/manga_reader.py:121`

**Issue**:
```python
readers = ["zathura", "evince", "okular", "mupdf", "xdg-open"]  # Hardcoded
```

**Violation**: User Configuration Over Code + Centralized Configuration principles.

**Fix**:
1. Add to config:
```python
class MangaSettings(BaseSettings):
    pdf_reader_priority: list[str] = Field(
        default=["zathura", "evince", "okular", "mupdf", "xdg-open"],
        env="ANI_TUPI__MANGA__PDF_READER_PRIORITY"
    )
```

2. Use in code:
```python
# utils/manga_reader.py
from models.config import settings

def open_pdf(pdf_path: str) -> None:
    for reader in settings.manga.pdf_reader_priority:
        if shutil.which(reader):
            subprocess.run([reader, str(pdf_path)])
            return
    raise RuntimeError(f"No PDF reader found. Install one of: {settings.manga.pdf_reader_priority}")
```

**Effort**: Low (add config field, update usage)

---

### [M5] Subprocess Calls Without Error Handling
**Status**: Silent failures
**File**: `utils/manga_reader.py:164-168`

**Issue**:
```python
process = subprocess.Popen(
    [reader, str(pdf_path)],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)  # No error handling
```

**Fix**:
```python
def open_pdf(pdf_path: str) -> None:
    """Open PDF with configured reader, with error handling."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    for reader in settings.manga.pdf_reader_priority:
        if shutil.which(reader):
            try:
                process = subprocess.Popen(
                    [reader, str(pdf_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30
                )
                # Wait for process to start
                process.wait(timeout=5)

                if process.returncode != 0:
                    stderr = process.stderr.read().decode() if process.stderr else ""
                    logger.warning(f"Reader {reader} failed: {stderr}")
                    continue

                return  # Success

            except subprocess.TimeoutExpired:
                logger.warning(f"Reader {reader} timed out")
                process.kill()
                continue
            except Exception as e:
                logger.warning(f"Failed to open with {reader}: {e}")
                continue

    raise RuntimeError(f"Could not open PDF with any reader. Tried: {settings.manga.pdf_reader_priority}")
```

**Effort**: Low (add error handling)

---

### [M6] Direct Plugin Access Without Validation
**Status**: Silent skips on plugin not found
**File**: `services/repository.py:463-467`

**Issue**:
```python
for url, source, params in urls_and_scrapers:
    if source in self.sources:  # Silent skip if not found
        th = Thread(
            target=self.sources[source].search_episodes,
        )
```

**Problem**: If plugin crashes or isn't loaded, code silently continues. User gets no warning.

**Fix**:
1. Validate plugins on load:
```python
def register_plugin(self, name: str, scraper: PluginProtocol) -> None:
    """Register plugin with validation."""
    # Validate interface
    required = ["search", "get_episodes"]
    for method in required:
        if not hasattr(scraper, method):
            raise ValueError(f"Plugin {name} missing method: {method}")

    self.sources[name] = scraper
```

2. Fail explicitly:
```python
def search_episodes(self, source: str, url: str) -> list[EpisodeData]:
    if source not in self.sources:
        raise ValueError(f"Plugin not found: {source}. Available: {list(self.sources.keys())}")

    return self.sources[source].get_episodes(url)
```

**Effort**: Low (add validation)

---

### [M7] Tests Import Plugins Directly
**Status**: Violates plugin repository pattern
**Files**:
- `tests/test_mangalivre_integration.py:9`
- `tests/test_mangalivre_plugin.py:11`
- `tests/test_manga_workflow_integration.py:12, 474, 482`

**Issue**:
```python
from manga_scrapers.plugins.mangalivre import MangaLivre  # Direct import!
plugin = MangaLivre()
```

**Violation**: Repository for Plugin Access pattern.

**Fix**: Load via loader:
```python
# Before
from manga_scrapers.plugins.mangalivre import MangaLivre

# After
from services.repository import get_manga_plugins

plugins = get_manga_plugins()
mangalivre = next(p for p in plugins if p.__class__.__name__ == "MangaLivre")
```

Or mock the repository:
```python
@pytest.fixture
def manga_plugin():
    from manga_scrapers.plugins.mangalivre import MangaLivre
    return MangaLivre()

def test_mangalivre(manga_plugin):
    # Test with plugin instance
    ...
```

**Effort**: Low (update test setup)

---

## Priority: LOW

### [L1] Hardcoded Browser User-Agent
**Status**: Works but not configurable
**File**: `scrapers/core/browser_pool.py:167-180`

**Issue**:
```python
user_agent = "Mozilla/5.0 ..."  # Hardcoded
```

**Fix**: Move to config:
```python
class BrowserSettings(BaseSettings):
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        env="ANI_TUPI__BROWSER__USER_AGENT"
    )
```

**Effort**: Minimal

---

### [L2] Hardcoded HTTP Timeouts
**Status**: Works but not tunable
**Locations**:
- `scrapers/plugins/animesdigital.py:10` - `REQUEST_TIMEOUT = 30`
- Various other files

**Issue**:
```python
REQUEST_TIMEOUT = 30  # Hardcoded
```

**Fix**:
```python
class PerformanceSettings(BaseSettings):
    http_timeout_seconds: int = Field(
        default=30,
        env="ANI_TUPI__PERFORMANCE__HTTP_TIMEOUT_SECONDS"
    )

# In scrapers
from models.config import settings
requests.get(url, timeout=settings.performance.http_timeout_seconds)
```

**Effort**: Minimal

---

## Refactoring Order

**Phase 1 - Foundation** (blocking others):
1. [C3] Remove mutable state from Repository
2. [C2] Split Repository into 4 classes
3. [C1] Consolidate duplicate manga_service

**Phase 2 - Architecture**:
4. [H1] Unify cache implementations
5. [H2] Consolidate config fields
6. [H3] Remove inheritance from plugins

**Phase 3 - Logic**:
7. [H4] Move business logic from commands to services
8. [M1] Implement TTL-aware video URL caching
9. [M2] Remove global state from video player
10. [M3] Add LRU cache to plugin map

**Phase 4 - Polish**:
11. [M4] Externalize reader priority list
12. [M5] Add subprocess error handling
13. [M6] Add plugin validation
14. [M7] Update tests to use repository
15. [L1], [L2] Externalize remaining hardcoded values

---

## Dependency Graph

```
[C3] Remove mutations
  ↓
[C2] Split Repository
  ↓
[H1] Unify cache → [H4] Move commands logic
  ↓
[H2] Config fields
  ↓
[H3] Remove plugin inheritance → [M7] Fix tests
  ↓
[M1] Video cache TTL
  ↓
[M2-M6] Cleanup
```

**Start with Phase 1**, which unblocks everything else.

---

## Testing Strategy

Each refactor should:
1. Preserve test suite (all tests pass before/after)
2. Add new unit tests for split classes
3. Verify integration tests pass
4. Run E2E tests on critical paths (search → play, search → read)

```bash
# Before refactoring
uv run pytest -v --cov --cov-report=html

# After refactoring
uv run pytest -v --cov --cov-report=html  # Should match or exceed
```

---

## Notes for Next Agent

- Use git branches for each refactor phase
- Small, atomic commits within each issue
- Update CLAUDE.md after major architectural changes
- Keep test coverage above 80%
- Run `uv run ruff check . && uv run ruff format .` after each phase
