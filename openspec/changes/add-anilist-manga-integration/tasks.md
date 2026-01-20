# AniList Manga Integration Tasks

## Implementation Tasks

### Phase 1: Core AniList Manga Support
1. **Extend AniListService for manga**
   - Add manga-specific GraphQL queries
   - Add methods: get_manga_by_id, get_manga_list_entry, update_manga_progress
   - Add method: add_manga_to_list, change_manga_status
   - Add method: get_user_manga_list for each status type

2. **Update manga models**
   - Add AniList manga ID to manga metadata
   - Extend MangaHistory to track AniList IDs
   - Add manga status mapping (READING, PLANNING, COMPLETED, etc.)

### Phase 2: Manga Workflow Integration
3. **Add progress confirmation to manga reading**
   - After chapter reading, ask "Você leu até o final do capítulo?"
   - If yes, update progress in AniList
   - Handle manga list status changes (PLANNING → READING, etc.)

4. **Extend AniList menus for manga**
   - Add manga options to AniList main menu
   - Add manga list browsing (Reading, Planning, Completed, etc.)
   - Add manga search and add to list functionality

### Phase 3: Unified Experience
5. **Integrate with existing manga CLI**
   - Modify manga_tupi.py to support AniList integration
   - Add optional AniList authentication check
   - Extend UnifiedMangaService to handle AniList metadata

6. **Add configuration options**
   - Extend AniListSettings to include manga preferences
   - Add option to enable/disable manga AniList integration
   - Add preference for english vs romaji manga titles

### Phase 4: Testing & Polish
7. **Test manga integration**
   - Unit tests for AniList manga methods
   - Integration tests for manga workflow
   - E2E tests for complete manga reading + AniList sync

8. **Documentation & Cleanup**
   - Update CLI help text to mention manga AniList integration
   - Add manga commands to AniList CLI interface
   - Update README with manga tracking features

## Validation Requirements

- [x] Users can authenticate once for both anime and manga
- [x] Progress confirmation dialog appears after chapter reading
- [x] Manga progress syncs correctly to AniList
- [x] Manga lists can be browsed and managed
- [x] Backward compatibility maintained for non-AniList users
- [x] All tests pass with new manga integration