# Tasks: Manga Read Online & Download Options

**Total Tasks**: 27

**Phases**: Foundation (MVP) → Smart Defaults → Polish & Testing

---

## Phase 1: Foundation (MVP) - Core read/download split

### Core Infrastructure
- [ ] **Task 1.1**: Create `utils/range_parser.py` with `parse_range_input()` function
  - Support patterns: "5", "3-10", "all", ""
  - Validate input and return list of chapter numbers
  - **Tests**: Unit tests covering all patterns and edge cases
  - **Validation**: `range_parser` exists with full coverage

- [ ] **Task 1.2**: Create `DownloadedChaptersTracker` class in `services/manga_service.py`
  - `load()`: Load download state from JSON
  - `save()`: Persist state to JSON
  - `mark_downloaded()`: Track downloaded chapter
  - `is_downloaded()`: Query if chapter is downloaded
  - `get_download_path()`: Return path for downloaded chapter
  - **Tests**: Unit tests for persistence layer
  - **Validation**: All methods work with mock JSON file

- [ ] **Task 1.3**: Extend `MangaSettings` in `models/config.py`
  - Add: `default_download_range: int = 5`
  - Add: `auto_open_after_download: bool = False`
  - Add: `skip_already_downloaded: bool = True`
  - Add: `download_storage_dir: str | None = None`
  - **Tests**: Config loads with defaults
  - **Validation**: Settings accessible via `settings.manga`

### UI/Menu Components
- [ ] **Task 1.4**: Create `_show_chapter_action_menu()` in `manga_tupi.py`
  - Use InquirerPy to display: "📖 Ler Agora", "⬇️ Baixar para Depois", "↩️ Voltar"
  - Return user selection
  - **Tests**: Mock InquirerPy, verify correct option returned
  - **Validation**: Menu appears and returns selection

- [ ] **Task 1.5**: Refactor `_handle_chapter_selection()` in `manga_tupi.py`
  - After chapter selection, call `_show_chapter_action_menu()`
  - Route to either `_handle_read_now()` or `_handle_download_for_later()`
  - **Tests**: Test both branches (read and download)
  - **Validation**: Old read behavior still works when selecting "Read Now"

### Read Now Path (Refactored)
- [ ] **Task 1.6**: Extract existing read logic into `_handle_read_now()` in `manga_tupi.py`
  - Move PDF creation, reader opening, history update from current flow
  - No functional changes (pure refactoring)
  - **Tests**: Existing tests still pass
  - **Validation**: "Read Now" option works exactly like before

### Download for Later Path (Basic)
- [ ] **Task 1.7**: Create `_prompt_download_range()` in `manga_tupi.py`
  - Show range input dialog with instructions
  - Call `parse_range_input()` with user input
  - Return list of chapters to download
  - **Tests**: Unit test with various inputs
  - **Validation**: Input parsed correctly

- [ ] **Task 1.8**: Create `_handle_download_for_later()` in `manga_tupi.py`
  - Call `_prompt_download_range()` to get user choice
  - Resolve range to actual chapter objects
  - Loop through chapters and create PDFs
  - Track downloads via `DownloadedChaptersTracker`
  - Show progress (simple: chapter number as it completes)
  - Return to menu
  - **Tests**: Mock PDF creation and tracker
  - **Validation**: Downloads complete without opening reader

### Data Model Updates
- [ ] **Task 1.9**: Update `MangaHistoryEntry` in `models/models.py`
  - Add optional `downloaded_chapters: list[str] = []`
  - Maintain backward compatibility
  - **Tests**: Existing history loads without error
  - **Validation**: Old entries work, new entries have field

- [ ] **Task 1.10**: Create download metadata JSON schema
  - File: `~/.local/state/ani-tupi/manga_downloads.json`
  - Store per-manga download state
  - **Tests**: Schema validation, load/save roundtrip
  - **Validation**: JSON persists correctly

### Integration & Testing
- [ ] **Task 1.11**: Integration test: Read now still works
  - Select chapter → Choose "Read Now" → PDF opens → History updated
  - Verify behavior unchanged from before
  - **Tests**: E2E test with mocked reader
  - **Validation**: Test passes

- [ ] **Task 1.12**: Integration test: Download creates files
  - Select chapter → Choose "Download" → Specify range → PDFs created
  - Verify files exist, tracker updated
  - **Tests**: File system checks
  - **Validation**: Test passes

- [ ] **Task 1.13**: Fix any import/dependency issues
  - Ensure new modules are importable
  - Check for circular dependencies
  - **Validation**: `uv run ani-tupi --help` works

---

## Phase 2: Smart Defaults & History Integration

### Smart Range Defaults
- [ ] **Task 2.1**: Integrate reading history into range defaults
  - Modify `_prompt_download_range()` to show last_chapter in prompt
  - If no history, show "First chapters" as default
  - **Tests**: Mock history data, verify correct defaults shown
  - **Validation**: Prompt shows correct context

- [ ] **Task 2.2**: Update `parse_range_input()` to use last_chapter for offset
  - "5" when last_chapter="41" → chapters [42-46]
  - "5" when last_chapter=None → chapters [1-5]
  - Handle floating-point chapter numbers ("42.5")
  - **Tests**: All offset scenarios
  - **Validation**: Correct chapters selected

### Download Status Display
- [ ] **Task 2.3**: Add download status to chapter menu display
  - Query `DownloadedChaptersTracker` for each chapter
  - Show "✅ Baixado (2.1 MB)" or "⬇️ Disponível" for each chapter
  - **Tests**: Mock tracker, verify display text
  - **Validation**: Correct status shown for downloaded/new chapters

- [ ] **Task 2.4**: Track chapter size when downloading
  - Get file size after PDF creation
  - Store in `DownloadedChaptersTracker`
  - Display in menu and progress reports
  - **Tests**: Verify sizes match actual files
  - **Validation**: Sizes displayed correctly

### Skip Already-Downloaded
- [ ] **Task 2.5**: Implement skip-already-downloaded logic
  - Before downloading batch, check which are already downloaded
  - If `skip_already_downloaded=True` and any are cached:
    - Show menu: "4 capítulos já baixados. Continuar apenas com novos?"
    - User can: Skip cached, or force re-download all, or custom selection
  - **Tests**: Mock tracker with cached chapters
  - **Validation**: Correctly identifies and handles cached chapters

### Configuration Testing
- [ ] **Task 2.6**: Test configuration overrides
  - `ANI_TUPI__MANGA__DEFAULT_DOWNLOAD_RANGE=10`
  - `ANI_TUPI__MANGA__SKIP_ALREADY_DOWNLOADED=false`
  - Verify settings are applied
  - **Tests**: Set env vars, verify behavior
  - **Validation**: Config applied correctly

---

## Phase 3: Progress Display & Robustness

### Enhanced Progress Display
- [ ] **Task 3.1**: Implement Rich-based progress display
  - Multi-line progress showing each chapter
  - Overall progress (3/5)
  - Total MB downloaded
  - Cancel button handling (Ctrl+C)
  - **Tests**: Display renders without errors
  - **Validation**: Progress bar displays correctly

- [ ] **Task 3.2**: Per-chapter progress during PDF creation
  - Track image download progress for each chapter
  - Show percentage complete per chapter
  - Update as images are fetched
  - **Tests**: Mock image downloads, verify updates
  - **Validation**: Progress updates shown

### Error Handling & Recovery
- [ ] **Task 3.3**: Per-chapter error handling in batch downloads
  - If one chapter fails, show error and ask "Continuar?"
  - Skip failed chapter and continue with next
  - Track which chapters failed
  - **Tests**: Mock network error for one chapter
  - **Validation**: Batch continues and completes

- [ ] **Task 3.4**: Handle user cancellation gracefully
  - Ctrl+C during batch download stops gracefully
  - Complete chapters are kept and tracked
  - Incomplete chapter's partial file is deleted
  - User can retry later
  - **Tests**: Simulate Ctrl+C mid-batch
  - **Validation**: Cleanup works, completed chapters saved

- [ ] **Task 3.5**: Validate disk space before batch download
  - Estimate size of batch (number of chapters * avg size)
  - Check available disk space in `download_storage_dir`
  - Warn if less than 50MB free, block if less than 10MB
  - **Tests**: Mock low disk space scenarios
  - **Validation**: Appropriate warnings/blocks shown

### Data Persistence & Cleanup
- [ ] **Task 3.6**: Persist incomplete downloads state
  - If user cancels or network fails, save progress
  - Allow user to resume from where they left off
  - **Tests**: Mock interruption, verify resume
  - **Validation**: Resume works correctly

- [ ] **Task 3.7**: Implement download cleanup command
  - `uv run ani-tupi --cleanup-downloads "manga_name"`
  - Option to delete old downloads (>30 days)
  - Query before deletion
  - **Tests**: Verify cleanup deletes and updates tracker
  - **Validation**: Old downloads removed

---

## Phase 4: Comprehensive Testing & Polish

### Unit Test Coverage
- [ ] **Task 4.1**: Full coverage for `range_parser.py`
  - Test all input patterns
  - Test boundary conditions
  - Test floating-point chapter numbers
  - **Target**: 100% coverage

- [ ] **Task 4.2**: Full coverage for `DownloadedChaptersTracker`
  - Test load/save
  - Test concurrent access
  - Test corrupted JSON recovery
  - **Target**: 100% coverage

- [ ] **Task 4.3**: Test all menu options and branches
  - Test action menu selection
  - Test read now path
  - Test download path
  - Test cancel/back options
  - **Target**: 95%+ coverage

### Integration Tests
- [ ] **Task 4.4**: End-to-end: Read now flow
  - Select manga → Select chapter → Choose "Read Now" → Verify reader opens
  - Verify history updated correctly
  - **Validation**: Test passes

- [ ] **Task 4.5**: End-to-end: Download flow
  - Select manga → Select chapter → Choose "Download" → Specify range → Verify files
  - Verify download tracker updated
  - Verify returns to menu
  - **Validation**: Test passes

- [ ] **Task 4.6**: End-to-end: Skip already-downloaded
  - Download 3 chapters → Try to re-download including cached ones
  - Verify skip prompt appears
  - Verify only new chapters downloaded
  - **Validation**: Test passes

### Documentation
- [ ] **Task 4.7**: Update CLAUDE.md with new feature
  - Document read vs. download flow
  - Show example commands/usage
  - Document configuration options
  - **Validation**: Documentation clear and complete

- [ ] **Task 4.8**: Add user-facing help text in menus
  - Explain range input format in dialog
  - Show examples: "5", "3-10", "all"
  - Translate/localize strings
  - **Validation**: Help text appears in UI

### Regression Testing
- [ ] **Task 4.9**: Run full test suite
  - Ensure no regressions in existing anime flow
  - Ensure no regressions in history/cache
  - Ensure no regressions in AniList integration
  - **Validation**: All tests pass

- [ ] **Task 4.10**: Manual testing on multiple platforms
  - Test on Linux (primary)
  - Test on macOS (if available)
  - Test on Windows (if available)
  - **Validation**: Feature works consistently

---

## Summary by Complexity

### Easy Tasks (4-8 hours each)
- 1.4, 1.5, 1.9, 2.1, 2.3, 2.6, 4.7, 4.8

### Medium Tasks (8-16 hours each)
- 1.1, 1.2, 1.3, 1.6, 1.7, 1.8, 1.10, 1.11, 1.12, 1.13, 2.2, 2.4, 2.5, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.9, 4.10

### Complex Tasks (16-24 hours each)
- 3.1, 3.2, 3.3, 3.6, 3.7

### Estimated Total: 80-120 hours (3-4 weeks sustained development)

---

## Dependencies & Sequencing

**Must be completed in order:**

1. Infrastructure (1.1-1.3): Done first
2. Menu refactoring (1.4-1.6): Done after infrastructure
3. Read now extraction (1.6): Separate but after 1.4
4. Download path (1.7-1.10): After menus
5. Basic integration (1.11-1.13): After both paths
6. Smart defaults (2.1-2.6): After foundation complete
7. Progress display (3.1-3.2): Can be parallel with error handling
8. Error handling (3.3-3.5): Can be parallel with progress
9. Testing & polish (4.x): Final phase

**Parallelizable:**
- Phase 1 infrastructure (1.1-1.3) can be done in parallel
- Unit tests can be written while waiting for PR review
- Documentation can be started before Phase 2 complete
