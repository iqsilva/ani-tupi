# Spec: Manga Batch Download with Smart Range Selection

**Capability**: Allow users to download multiple manga chapters with configurable range and smart defaults.

**Status**: Proposal

**Related Capabilities**:
- `manga-action-menu` (triggers this capability)
- Uses existing: `pdf creation`, `history tracking`

## ADDED Requirements

### Requirement: Range Input Dialog with Smart Defaults

The system SHALL prompt users for the number or range of chapters to download, with sensible defaults based on reading history (next 5 chapters from last read, or first 5 if no history).

#### Scenario: User accepts default (empty input)
- **Given**: User has selected "Download for Later" and has reading history (last read: chapter 41)
- **When**: Range input dialog is displayed
- **Then**:
  - **Expected**: Dialog shows "Último capítulo lido: 41"
  - **Expected**: Default suggestion: "Próximos 5 capítulos (42-46)"
  - **Expected**: Input field accepts empty input (Enter key)
  - **Expected**: Empty input → Download next 5 chapters: [42, 42.5, 43, 44, 45] (or available)

#### Scenario: User specifies number of chapters
- **Given**: Range input dialog is displayed
- **When**: User enters "3"
- **Then**:
  - **Expected**: Input is validated as integer
  - **Expected**: 3 chapters are downloaded from last read position
  - **Expected**: Downloads chapters: [42, 42.5, 43] (next 3 from 41)

#### Scenario: User specifies explicit chapter range
- **Given**: Range input dialog is displayed
- **When**: User enters "5-10"
- **Then**:
  - **Expected**: Input is validated as range pattern (chapter_start-chapter_end)
  - **Expected**: Chapters 5-10 are downloaded (if available)
  - **Expected**: If some chapters unavailable, show warning before downloading

#### Scenario: User requests all available chapters
- **Given**: Range input dialog is displayed with available chapters 42-50
- **When**: User enters "all"
- **Then**:
  - **Expected**: All available chapters from last read onward are downloaded
  - **Expected**: "all" = [42, 43, 44, 45, 46, 47, 48, 49, 50]

#### Scenario: User with no reading history
- **Given**: First time reading this manga (no last_chapter in history)
- **When**: Range input dialog is displayed
- **Then**:
  - **Expected**: Dialog shows "Nenhum capítulo lido ainda"
  - **Expected**: Default: First 5 chapters (or all if fewer than 5 available)
  - **Expected**: Empty input → Downloads first 5 available chapters

#### Scenario: Invalid input handling
- **Given**: Range input dialog is displayed
- **When**: User enters invalid input (e.g., "abc", "1.5-2", "999-1000")
- **Then**:
  - **Expected**: Input validation catches error
  - **Expected**: User sees error message and is re-prompted
  - **Expected**: Examples shown: "Digite número (ex: 5), intervalo (ex: 3-10), ou 'all'"

### Requirement: Range Validation and Resolution

The system SHALL validate user input and convert it to actual chapter numbers, handling patterns such as "5", "3-10", and "all" with appropriate error messaging.

#### Scenario: Range boundary checking
- **Given**: Available chapters are [1-20, 42-50] (gap for missing chapters)
- **When**: User enters "45-55"
- **Then**:
  - **Expected**: Range [45-50] is available
  - **Expected**: Warning: "Capítulo 55 não está disponível. Baixando 45-50 (6 capítulos)"
  - **Expected**: Proceeds with available chapters

#### Scenario: Range outside available
- **Given**: Available chapters are [1-50] but all after 40 are read
- **When**: User enters "10-20" and has read 40
- **Then**:
  - **Expected**: Chapters 10-20 are downloaded (even though before last read)
  - **Expected**: No error (explicit ranges always honored)

#### Scenario: Floating point chapter numbers
- **Given**: Available chapters include "42", "42.5", "43"
- **When**: Range input results in [42-43]
- **Then**:
  - **Expected**: All matching chapters returned: ["42", "42.5", "43"]
  - **Expected**: Chapters sorted numerically for download order

### Requirement: Downloaded Chapters Tracking

The system SHALL track which chapters are downloaded and provide options to skip or re-download already-cached chapters based on configuration.

#### Scenario: Skip already downloaded chapters
- **Given**: Chapters 42-45 are already downloaded for this manga
- **When**: User selects download range that includes 42-48
- **Then**:
  - **Expected**: If `skip_already_downloaded=True`: show "4 capítulos já baixados. Baixar apenas 46-48?"
  - **Expected**: User can confirm or force re-download
  - **Expected**: Only 46-48 are downloaded (46-48 new files created)

#### Scenario: Track download metadata
- **Given**: Chapter 42 is downloaded
- **When**: Download completes successfully
- **Then**:
  - **Expected**: Download tracker records:
    - chapter_id (MangaDex ID)
    - chapter_number ("42")
    - file_path (full path to PDF)
    - file_size_mb (actual size)
    - downloaded_at (timestamp)
    - source ("mangadex")

#### Scenario: Query download status in UI
- **Given**: Chapter selection menu with mix of read and downloaded chapters
- **When**: Menu is rendered
- **Then**:
  - **Expected**: Downloaded chapters show "✅ Baixado (2.1 MB)"
  - **Expected**: Available but not downloaded show "⬇️ Disponível"

### Requirement: Batch Download with Progress Tracking

The system SHALL download multiple chapters sequentially with per-chapter progress display, error recovery, and graceful cancellation support.

#### Scenario: Download progress display
- **Given**: User requested download of 5 chapters
- **When**: Download process starts
- **Then**:
  - **Expected**: Progress display shows:
    - Title of manga
    - List of chapters with individual progress bars
    - Overall progress (3/5 completed)
    - Cancel button available
  - **Expected**: Format:
    ```
    Capítulo 42: ████████░░ 80%
    Capítulo 43: ⏳ Aguardando...
    ```

#### Scenario: Successful download completion
- **Given**: All chapters downloaded without errors
- **When**: Last chapter finishes downloading
- **Then**:
  - **Expected**: Success message: "✅ 5 capítulos baixados em ~/Downloads/ani-tupi/..."
  - **Expected**: Show total storage used
  - **Expected**: User returns to menu

#### Scenario: Single chapter failure during batch
- **Given**: Downloading chapters 42-46, chapter 44 fails
- **When**: Network error occurs for chapter 44
- **Then**:
  - **Expected**: Error message: "⚠️ Erro ao baixar capítulo 44: rede indisponível"
  - **Expected**: User option to "Continuar com próximo?" or "Cancelar"
  - **Expected**: Already-downloaded chapters (42, 43) are kept
  - **Expected**: Continue skips 44 and tries 45-46

#### Scenario: User cancels batch download
- **Given**: Downloading 5 chapters, user cancels after 2
- **When**: User presses Ctrl+C or clicks Cancel
- **Then**:
  - **Expected**: Download stops gracefully
  - **Expected**: Completed chapters (42, 43) are kept and tracked
  - **Expected**: Incomplete chapter's partial file is deleted
  - **Expected**: User can retry later

## Implementation Notes

### Code Location
- Add `_prompt_download_range()` function in `manga_tupi.py`
- Add `parse_range_input()` utility in new file `utils/range_parser.py`
- Add `DownloadedChaptersTracker` class in `services/manga_service.py`
- Add download batch function in `services/manga_service.py` or `utils/pdf_converter.py`

### Range Input Patterns

```python
# Parse function must handle:
"5"         → Next 5 from last_chapter (or first 5 if no history)
"10"        → Next 10 from last_chapter
"3-10"      → Explicit range: chapters 3 through 10
"all"       → All available chapters
""          → Use default (from config)
```

### Configuration Used
- `settings.manga.default_download_range` (default: 5)
- `settings.manga.skip_already_downloaded` (default: True)
- `settings.manga.auto_open_after_download` (default: False)

### File Storage
- PDFs saved to: `~/.local/state/ani-tupi/manga/{manga_id}/{chapter_number}.pdf`
- Download metadata in: `~/.local/state/ani-tupi/manga_downloads.json`

### Error Handling
- Network errors: Per-chapter try-again / skip option
- Invalid input: Re-prompt with examples
- Disk space: Check before starting batch (optional)
- Canceled: Keep completed, delete partial

### Testing
- Unit: Range parsing logic (all input patterns)
- Unit: Chapter availability filtering
- Unit: Download state persistence
- Integration: Read history interaction (default range)
- Integration: Skip already-downloaded logic
- Integration: Multi-chapter download flow
- E2E: User select download → specify range → verify files

## Dependencies

- Existing: `services.manga_service` (MangaHistory)
- Existing: `utils.pdf_converter` (create_pdf_from_images)
- New: `utils.range_parser` (parse_range_input utility)
- New: `services.manga_service.DownloadedChaptersTracker` (persistence layer)
- Existing: `InquirerPy` (range input dialog)
- Existing: `Rich` (progress display)

## Success Criteria

1. User can input range as number, explicit range, or "all"
2. Input is validated with helpful error messages
3. Default based on last read chapter (or first 5 if no history)
4. Downloaded chapters are tracked and visible in UI
5. Batch downloads show progress per-chapter
6. Already-downloaded chapters can be skipped
7. Individual chapter failures don't stop entire batch
8. All file operations are resilient to network/disk errors
9. 80%+ test coverage for parsing, tracking, and download logic
10. No regression in existing read-now behavior
