# AniList Manga Sync Integration Design

## Architecture Overview

This design extends the existing AniList integration to support manga, maintaining consistency with the current anime implementation while adding manga-specific functionality.

## System Components

### 1. Extended AniListService
```
services/anilist_service.py
├── Existing anime methods (unchanged)
└── New manga methods:
    ├── get_manga_by_id(manga_id: int) -> AniListManga
    ├── get_manga_list_entry(manga_id: int) -> AniListMediaListEntry
    ├── update_manga_progress(manga_id: int, chapter: int) -> bool
    ├── add_manga_to_list(manga_id: int, status: str) -> bool
    ├── change_manga_status(manga_id: int, status: str) -> bool
    ├── get_user_manga_list(status: str, per_page: int = 50) -> List[AniListMediaListEntry]
    └── search_manga(query: str) -> List[AniListManga]
```

### 2. Extended Data Models
```
models/models.py (additions)
├── AniListManga (extends base AniListMedia)
│   ├── chapters: Optional[int]
│   ├── volumes: Optional[int]
│   └── manga_specific_fields...
└── MangaHistory extensions
    ├── anilist_id: int | None
    ├── last_chapter_read: int
    └── manga_status: str | None
```

### 3. Enhanced Manga Workflow
```
manga_tupi.py (modified flow)
1. Search manga → Select manga → Get chapters
2. Read chapter → Close PDF reader
3. NEW: Ask "Você leu até o final do capítulo?"
   ├─ Yes → Update local history + Sync to AniList
   └─ No/Cancel → Only update local history
4. Continue to next chapter or exit
```

### 4. Unified AniList Menu
```
ui/anilist_menus.py (extended)
AniList Main Menu:
├── 📈 Trending Anime
├── 📚 Trending Manga (NEW)
├── 📅 Recentes (Local)
├── 🔍 Buscar Anime
├── 🔍 Buscar Manga (NEW)
├── ───────────────────
├── 👤 Username
├── 📺 Watching (Anime)
├── 📚 Reading (Manga) (NEW)
├── 📋 Planning (Both)
├── ✅ Completed (Both)
├── ⏸️ Paused (Both)
├── ❌ Dropped (Both)
└── 🔁 Rewatching/Rereading (Both)
```

## Key Technical Decisions

### 1. Reuse Existing Infrastructure
- **Authentication**: Single login works for both anime and manga
- **AniListService**: Extend existing class rather than create new one
- **Configuration**: Add manga-specific options to existing AniListSettings
- **UI Patterns**: Follow same menu structure and interaction patterns

### 2. Progress Synchronization Strategy
- **Source of Truth**: AniList is primary source for manga progress
- **Local Fallback**: Maintain local history for offline use
- **Conflict Resolution**: Use max(local_progress, anilist_progress)
- **Batch Updates**: Sync multiple chapters if user reads several

### 3. Status Management
- **Unified Status Types**: Use same status enums for anime and manga
- **Auto-Status Changes**: PLANNING → READING when first chapter read
- **Completion Detection**: When last chapter read → COMPLETED
- **User Control**: Allow manual status changes through menus

### 4. Error Handling & Resilience
- **Network Failures**: Graceful degradation to local-only mode
- **Authentication**: Prompt re-authentication if token expires
- **API Limits**: Respect AniList rate limiting (90/minute)
- **Data Validation**: Validate manga IDs and chapter numbers

## Integration Points

### 1. CLI Interface Extension
```bash
# New manga commands under existing anilist namespace
ani-tupi anilist manga          # Manga main menu
ani-tupi anilist manga search   # Search manga
ani-tupi anilist manga reading  # Browse reading list
```

### 2. Configuration Additions
```python
# models/config.py
class AniListSettings:
    # ... existing fields ...
    manga_prefer_english_title: bool = Field(...)
    manga_auto_sync: bool = Field(...)
    manga_progress_confirmation: bool = Field(...)
```

### 3. History Service Extension
```python
# services/history_service.py (extended)
def save_manga_history(
    manga_title: str,
    chapter_number: int,
    anilist_id: int | None = None,
    source: str = "local",
    total_chapters: int | None = None,
) -> None:
    # Extended to handle manga-specific metadata
```

## Migration Strategy

### Phase 1: Foundation (No Breaking Changes)
- Extend AniListService with manga methods
- Add manga data models
- Create configuration options

### Phase 2: Integration (Optional Feature)
- Modify manga_tupi.py to check for AniList auth
- Add progress confirmation dialog
- Integrate with existing manga workflow

### Phase 3: UI Enhancement (Optional)
- Extend AniList menus to include manga
- Add manga browsing and management
- Maintain full backward compatibility

## Testing Strategy

### 1. Unit Tests
- Test new AniListService manga methods
- Test progress confirmation logic
- Test status management

### 2. Integration Tests
- Test complete manga reading workflow
- Test AniList synchronization
- Test error handling scenarios

### 3. E2E Tests
- Test manga search → read → sync workflow
- Test menu navigation for manga lists
- Test authentication and token refresh

## Performance Considerations

- **API Calls**: Minimize unnecessary AniList API calls
- **Caching**: Cache manga metadata to reduce API usage
- **Background Sync**: Optional background synchronization
- **Bulk Operations**: Batch multiple chapter updates when possible