# Design Document: Manga Read Online & Download Options

## Architecture Overview

### Current State

The manga reading flow is linear:
1. User searches/selects manga
2. User selects chapter
3. Automatic: PDFs created and reader opens immediately
4. After reader closes: History updated

### Proposed State

The flow becomes branching:
1. User searches/selects manga
2. User selects chapter
3. **NEW**: Prompt for action (Read Now vs Download)
4. **Branch A (Read Now)**:
   - Create PDF
   - Open reader
   - After close: Update history
5. **Branch B (Download for Later)**:
   - **NEW**: Prompt for range (with smart default)
   - **NEW**: Download multiple chapters as PDFs
   - **NEW**: Track downloads
   - Return to menu (no reader open)
   - **Optional**: Update history as "downloaded" vs "read"

### Component Interactions

```
manga_tupi.py (main entry)
    ↓
_handle_chapter_selection()
    ↓
[NEW] _handle_chapter_action()  ← User chooses Read vs Download
    ├─→ Branch A: _handle_read_now()
    │       ├→ utils.pdf_converter.create_pdf()
    │       ├→ utils.manga_reader.open_pdf_reader()
    │       └→ services.manga_service.MangaHistory.update()
    │
    └─→ Branch B: _handle_download_for_later()
            ├→ [NEW] _prompt_download_range()
            ├→ [NEW] _resolve_chapter_range()
            ├→ services.manga_service.DownloadedChaptersTracker.queue_download()
            ├→ Loop: Create PDF for each chapter
            ├→ [NEW] services.manga_service.DownloadedChaptersTracker.mark_downloaded()
            └→ Return to menu
```

## Data Model Design

### New: `DownloadedChaptersTracker`

```python
class DownloadedChapter(BaseModel):
    """Single downloaded chapter metadata."""
    chapter_id: str
    chapter_number: str
    file_path: Path
    file_size_mb: float
    downloaded_at: datetime
    source: str  # e.g., "mangadex"

class MangaDownloadState(BaseModel):
    """Download state for a single manga."""
    manga_id: str
    manga_title: str
    downloaded_chapters: list[DownloadedChapter]
    last_download_at: datetime | None

class DownloadedChaptersTracker:
    """Manages downloaded chapters across all manga."""

    _downloads_file: Path = get_data_path() / "manga_downloads.json"

    @classmethod
    def load() -> dict[str, MangaDownloadState]: ...

    @classmethod
    def save(state: dict[str, MangaDownloadState]) -> None: ...

    @classmethod
    def get_downloaded_chapters(manga_id: str) -> list[DownloadedChapter]: ...

    @classmethod
    def mark_downloaded(manga_id: str, chapter_data: DownloadedChapter) -> None: ...

    @classmethod
    def is_downloaded(manga_id: str, chapter_id: str) -> bool: ...

    @classmethod
    def get_download_path(manga_id: str, chapter_id: str) -> Path: ...

    @classmethod
    def cleanup_download(manga_id: str, chapter_id: str) -> None: ...
```

### Modified: `MangaHistoryEntry`

```python
class MangaHistoryEntry(BaseModel):
    last_chapter: str = Field(..., min_length=1)
    last_chapter_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    manga_id: str | None = None
    anilist_id: int | None = None
    manga_status: str | None = None

    # NEW: Track downloaded vs read chapters
    downloaded_chapters: list[str] = Field(default_factory=list)  # Chapter IDs
```

### Config: `MangaSettings` (extend existing)

```python
class MangaSettings(BaseModel):
    # ... existing fields

    # New settings for read/download feature
    default_download_range: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Default chapters to download when user selects 'download'"
    )
    auto_open_after_download: bool = Field(
        default=False,
        description="Auto-open PDF reader after downloading"
    )
    skip_already_downloaded: bool = Field(
        default=True,
        description="Skip already-downloaded chapters in batch operations"
    )
    download_storage_dir: str | None = Field(
        default=None,
        description="Custom directory for downloaded PDFs (default: .local/state/ani-tupi/manga/)"
    )
```

## UI/UX Design

### Action Selection Menu

After user selects a chapter:

```
╔════════════════════════════════════════╗
║  Dandadan - Capítulo 42               ║
╠════════════════════════════════════════╣
║  O que deseja fazer?                  ║
║                                        ║
║  ❯ 📖 Ler Agora                        ║
║    ⬇️  Baixar para Depois              ║
║    ↩️  Voltar ao Menu                  ║
╚════════════════════════════════════════╝
```

### Download Range Input Dialog

After user selects "Download for Later":

```
╔════════════════════════════════════════╗
║  Baixar Capítulos                      ║
╠════════════════════════════════════════╣
║                                        ║
║  Último capítulo lido: 41             ║
║  Próximos disponíveis: 42-50           ║
║                                        ║
║  Quantos capítulos deseja baixar?      ║
║  (padrão: 5, próximos após o último)   ║
║                                        ║
║  Digite número ou intervalo:           ║
║  • "5" → Capítulos 42-46               ║
║  • "3-10" → Capítulos 3-10             ║
║  • "all" → Todos disponíveis           ║
║                                        ║
║  Sua resposta: [_____]                 ║
║                                        ║
║  (Enter para padrão)                   ║
╚════════════════════════════════════════╝
```

### Download Progress

```
╔════════════════════════════════════════╗
║  Baixando: Dandadan                    ║
╠════════════════════════════════════════╣
║                                        ║
║  Capítulo 42: ████████░░ 80%           ║
║  Capítulo 43: ⏳ Aguardando...          ║
║  Capítulo 44: ⏳ Aguardando...          ║
║                                        ║
║  Total: 3 capítulos (12.5 MB)          ║
║                                        ║
║  [C]ancelar                            ║
╚════════════════════════════════════════╝
```

### Downloaded Status in Chapter Menu

```
Capítulo 42 ✅ Baixado (2.1 MB)
Capítulo 43 ⬇️  Disponível
Capítulo 44 ⬇️  Disponível
```

## Range Resolution Logic

### Input Patterns

```python
def parse_range_input(input_str: str, last_chapter: str | None, available_chapters: list[str]) -> list[str]:
    """
    Parse user range input and return list of chapter numbers to download.

    Patterns:
    - "5" → Next 5 chapters after last_chapter (or from 0 if no history)
    - "3-10" → Chapters numbered 3 through 10 (if available)
    - "all" → All available chapters
    - "" (empty) → Use default (5 chapters)

    Returns list of chapter numbers in order: ["42", "42.5", "43", ...]
    """
```

### Example Scenarios

**Scenario 1: No reading history**
- User has never read this manga
- Input: "" (press Enter for default)
- Result: First 5 chapters

**Scenario 2: User has read up to chapter 41**
- Last read: "41"
- Input: "" (press Enter)
- Result: Chapters 42-46 (next 5)

**Scenario 3: Custom range**
- Last read: "41"
- Available: 42-50
- Input: "3-10"
- Result: Chapters 3-10 (if available)

**Scenario 4: Download all**
- Input: "all"
- Result: All remaining chapters from last read onward

## File Storage

### Directory Structure

```
~/.local/state/ani-tupi/
├── manga_history.json
├── manga_downloads.json        ← NEW: Track downloaded chapters
└── manga/
    ├── {manga_id}/
    │   ├── 42.pdf              ← Downloaded PDFs
    │   ├── 42.5.pdf
    │   ├── 43.pdf
    │   └── metadata.json       ← Optional: Chapter metadata
    └── {another_manga_id}/
```

### File Naming
- Chapter PDFs: `{chapter_number}.pdf`
- Chapter numbers with decimals: `42.5.pdf` (not `42_5.pdf`)
- Case-sensitive folder names for consistency

## Error Handling

### Network Errors During Batch Download
```python
try:
    for chapter in chapters_to_download:
        try:
            create_pdf(chapter)
            tracker.mark_downloaded(chapter)
        except NetworkError:
            print(f"⚠️ Erro ao baixar capítulo {chapter.number}: rede indisponível")
            user_response = input("Continuar com próximo? [S/n]: ")
            if user_response.lower() == 'n':
                break
except Exception as e:
    print(f"❌ Erro fatal durante download: {e}")
```

### Validation Errors
```python
# Invalid range format
"abc" → Show error and re-prompt

# Range outside available chapters
"100-200" but only 50 available → Show warning and clip to available

# Empty input → Use default
```

## Testing Strategy

### Unit Tests
- Range parsing logic (various input formats)
- Chapter availability checking
- Download state persistence

### Integration Tests
- Read now flow (existing, ensure not broken)
- Download flow (happy path)
- Download skip already-downloaded chapters
- History updates after download

### E2E Tests
- Select chapter → Choose download → Specify range → Verify files exist
- Select chapter → Choose read → Verify reader opens and history updated

## Backward Compatibility

1. **Existing history format**: Add `downloaded_chapters` as optional field (default: `[]`)
2. **Existing download logic**: Keep `utils.pdf_converter` unchanged; wrap it in new tracking layer
3. **Config defaults**: New settings have sensible defaults; don't break if missing

## Performance Considerations

1. **Download tracker JSON file**: Keep reasonably sized (prune old entries after 90 days?)
2. **Batch downloads**: Sequential (not parallel) to avoid overwhelming network/disk
3. **PDF creation**: Existing logic, no changes

## Future Extensions (Not in Scope)

1. Parallel chapter downloads with worker pool
2. Selective image quality for downloads
3. Resume interrupted downloads
4. Sync downloaded chapters to cloud
5. Bookmark/note system within downloads
