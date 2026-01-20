# Proposal: Add Read Online & Download for Later Options to Manga Flow

**Change ID**: `add-manga-read-download-options`

**Status**: Proposal

**Priority**: Medium

**Author**: Claude Code

**Created**: 2026-01-20

## Problem Statement

Currently, when users select a manga chapter in ani-tupi, they are immediately shown the chapter images. This doesn't support two common reading workflows:

1. **Read Later**: Users want to download a chapter (or range of chapters) to read offline without automatically opening the reader
2. **Smart Range Selection**: When downloading, users should be able to specify a range (default: next 5 chapters from last read, or start from 0 if no history)

## User Stories

### Story 1: Read Online vs. Download
> As a user, I want to choose between reading a chapter immediately or downloading it for later, so I can decide whether to commit time to reading right now.

**Acceptance Criteria:**
- When selecting a chapter, show option: "📖 Ler Agora" (Read Now) or "⬇️ Baixar para Depois" (Download for Later)
- "Read Now" opens the chapter immediately (current behavior)
- "Download for Later" downloads the chapter without opening reader

### Story 2: Download Range with Smart Defaults
> As a user, I want to download multiple chapters at once with a sensible default, so I don't have to manually select each one.

**Acceptance Criteria:**
- When downloading, prompt user for range: "Quantos capítulos deseja baixar?"
- **Default**: Next 5 chapters after last read chapter (or from start if no history)
- Allow custom range: e.g., "10", "5-15", "3" (from last read + 3)
- Validate input before processing
- Show download progress with chapter numbers

### Story 3: Batch Download Management
> As a user, I want to see which chapters are already downloaded, so I don't re-download them.

**Acceptance Criteria:**
- Show download status in chapter menu (✅ Downloaded, ⬇️ Available)
- Skip already-downloaded chapters in batch operations (with confirmation)
- Allow force-re-download if user explicitly requests

## Proposed Solution

### User Flow

**Current (1-step):**
```
Select chapter → [Auto-open reader]
```

**Proposed (2-3 steps):**
```
Select chapter → Choose action (Read/Download) → [If Download] Set range → Download → Return to menu
```

### Key Features

1. **Chapter Action Menu**: After chapter selection, present "Read Now" or "Download for Later"
2. **Range Input Dialog**: Validate range patterns:
   - `"5"` → Download 5 chapters from last read (or from 0)
   - `"3-10"` → Download chapters 3 through 10
   - `"all"` → Download all remaining chapters
3. **Smart Defaults**: Based on reading history and available chapters
4. **Download Status Tracking**: Store which chapters are downloaded locally
5. **Progress Feedback**: Show which chapters are downloading/completed

### Data Model Changes

**New**: `DownloadedChaptersTracker`
- Track downloaded chapters per manga per source
- Store metadata: download timestamp, file path, size
- Persist to JSON in `~/.local/state/ani-tupi/manga_downloads.json`

**Modified**: `MangaHistoryEntry`
- Add optional `downloaded_chapters` list to track downloaded ranges per manga

### Configuration

New settings in `models/config.py`:
```python
class MangaSettings:
    # ... existing fields
    default_download_range: int = 5  # Default chapters to download
    auto_open_after_download: bool = False  # Don't auto-open PDFs
    skip_already_downloaded: bool = True  # Skip downloaded chapters in batch ops
```

## Affected Components

1. **UI** (`ui/components.py`, `ui/anilist_menus.py`)
   - New action selection menu
   - Range input dialog with validation
   - Download progress display

2. **Services** (`services/manga_service.py`)
   - New `DownloadedChaptersTracker` class
   - Chapter action routing logic

3. **Commands** (`commands/manga.py`, `manga_tupi.py`)
   - Integrate action menu into chapter selection flow
   - Route to read vs. download paths

4. **Utils** (`utils/pdf_converter.py`)
   - Track downloaded PDFs
   - Return download path instead of auto-opening

5. **Models** (`models/models.py`, `models/config.py`)
   - New data models for download tracking

## Implementation Phases

### Phase 1: Foundation (MVP)
- [ ] Add action selection menu after chapter selection
- [ ] Implement "Read Now" path (refactored from current)
- [ ] Implement basic "Download for Later" (save PDF without opening)
- [ ] Add simple range validation (e.g., "5" or "1-10")

### Phase 2: Smart Defaults & History
- [ ] Implement reading history-aware range defaults
- [ ] Add range pattern parsing (handle "5", "3-10", "all")
- [ ] Track downloaded chapters locally
- [ ] Show download status in menus

### Phase 3: Polish & Optimization
- [ ] Batch download with progress per chapter
- [ ] Skip already-downloaded chapters (with user confirmation)
- [ ] Configuration for default behavior
- [ ] E2E tests for download workflows

## Open Questions / Clarifications Needed

1. **Chapter Range Syntax**: Should we support other patterns like:
   - `"+5"` (next 5 from last read)?
   - `"-5"` (previous 5)?
   - `"@50-55"` (exact chapter numbers)?
   - Or keep it simple: just integer offsets and ranges?

2. **PDF Storage**: Where should downloaded PDFs be stored?
   - Option A: `~/.local/state/ani-tupi/manga/{manga_id}/{chapter_number}.pdf`
   - Option B: `~/Downloads/ani-tupi/{manga_title}/{chapter_number}.pdf`
   - Option C: Configurable via `ANI_TUPI__MANGA__DOWNLOAD_DIR`

3. **Auto-Open Behavior**: Should "Download for Later" always suppress opening?
   - Or add setting: `ANI_TUPI__MANGA__AUTO_OPEN_AFTER_DOWNLOAD=false`?

4. **Batch Download Interruption**: If user cancels mid-batch, how to handle?
   - Resume from next chapter?
   - Delete partial downloads?
   - Keep what's done?

5. **Already Downloaded Handling**: What should default be?
   - Always skip with warning?
   - Always re-download?
   - Show interactive menu per chapter?

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Complex UI with too many options | Start MVP with simple read/download choice, iterate on range syntax |
| Download storage disk usage | Show file sizes during selection, allow cleanup command |
| Network timeouts on large batches | Implement per-chapter retry logic, save progress state |
| User confusion with range syntax | Clear help text, examples, validate input with feedback |

## Dependencies

- Existing: `models.models`, `services.manga_service`, `utils.pdf_converter`
- New: Range parsing utility function, download tracker persistence

## Success Criteria

1. User can select chapter and choose "Read Now" vs "Download for Later"
2. "Download for Later" downloads PDF without opening reader
3. User can specify number of chapters to download with sensible defaults
4. Downloaded chapters are tracked and visible in UI
5. All features covered by unit + integration tests (80%+ coverage)
6. No regression in existing "read now" functionality
