# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**ani-tupi** é um aplicativo CLI em português brasileiro para assistir anime e ler mangá direto no terminal. Suporta múltiplas fontes de scraping com integração AniList, usa MPV como player de vídeo e oferece um sistema de menus interativo para buscar, navegar e assistir anime. Inclui leitor PDF integrado para mangá com download automático de capítulos e detecção de leitores de PDF.

## Development Commands

Use UV (Astral's fast Python package manager) for all package management and script execution. Never use pip directly.

### Setup & Installation

```bash
# Install dependencies in development
uv sync

# Install as global CLI (for testing)
python3 install-cli.py

# Or manually install as tool
uv tool install --force .

# Uninstall global CLI
uv tool uninstall ani-tupi
```

### Running the Application

```bash
# Run in development mode (without global install)
uv run ani-tupi

# Run with arguments
uv run ani-tupi --query "dandadan"
uv run ani-tupi --continue-watching
uv run ani-tupi anilist

# Run manga viewer
uv run manga_tupi

# Run with debug mode
uv run main.py --debug

# Show help
uv run ani-tupi --help
```

### Linting & Code Quality

```bash
# Run Ruff linter (check only)
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_example.py

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run single test
uv run pytest tests/test_example.py::test_function_name -v
```

### Building & Distribution

```bash
# Build standalone executable (no Python needed to run)
uv run build.py

# Output: dist/ani-tupi (Linux/macOS) or dist/ani-tupi.exe (Windows)
# Also creates plugins/ folder in dist/
```

### Dependency Management

```bash
# Add new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update all dependencies
uv sync --upgrade

# Remove dependency
uv remove package-name
```

## Architecture Overview

The application follows the **MVCP pattern** (Model-View-Controller-Plugin):

### Core Flow
1. **main.py** → CLI entry point with argument parsing, routes to commands
2. **Commands** (commands/) → Handle user flows (anime, manga, anilist)
3. **Services** (services/) → Business logic layer
4. **Scrapers** (scrapers/) → Plugin system for different anime sources
5. **UI** (ui/) → Menu rendering using Rich + InquirerPy
6. **Models** (models/) → Pydantic data models with validation
7. **Utils** (utils/) → Helper utilities and persistence

### Key Architectural Decisions

**Plugin System** (scrapers/loader.py):
- Dynamic loading of scraper plugins from `scrapers/plugins/`
- Each plugin implements search and episode extraction
- Sources can be enabled/disabled via plugin_preferences.json

**Configuration Management** (models/config.py):
- Pydantic v2 settings with environment variable support
- Centralized settings accessible from anywhere: `from models.config import settings`
- Supports overrides via `ANI_TUPI__*` environment variables

**Data Persistence**:
- JSON-based storage in `~/.local/state/ani-tupi/` (XDG standard)
- SQLite cache via diskcache for scraper results (7-day default TTL)
- AniList OAuth token stored securely in `anilist_token.json`

**UI Framework**:
- **Rich** for progress bars, spinners, and formatting
- **InquirerPy** for interactive menus (replaces Textual for better performance)

**Service Layer** Pattern:
- `anime_service.py`: Search, selection, playback orchestration
- `anilist_service.py`: AniList API interactions
- `manga_service.py`: MangaDex scraping and caching
- `history_service.py`: Watch history persistence
- `repository.py`: Repository pattern for plugin management

### Data Flow for Watching Anime

1. User searches for anime → Incremental search starts with 3 words
2. System adds words progressively until results ≤ 5 or all words used
3. User can navigate backward/forward between result sets if multiple iterations exist
4. User selects anime → Service fetches episodes from chosen scraper
5. Service checks history and cache → Shows episode menu
6. User selects episode → MPV player launches with video URL
7. After playback → Service updates history and optionally syncs to AniList

### Incremental Anime Search (Busca Incremental)

**Algorithm Overview:**
- Starts with first 3 words of search query (or all if fewer)
- Adds one word at a time until results ≤ 5 (optimal choice size)
- If adding a word results in 0 results, falls back to previous result set
- User can navigate backward to see more results from previous iterations

**Example Search Flow:**
```
User input: "Boku no Hero Academia 5"
└─ Words: ["Boku", "no", "Hero", "Academia", "5"]
   ├─ Iteration 1: "Boku no Hero" → 8 results (>5, continue)
   ├─ Iteration 2: "Boku no Hero Academia" → 6 results (>5, continue)
   └─ Iteration 3: "Boku no Hero Academia 5" → 2 results (≤5, STOP)

Menu shows:
  ○ Boku no Hero Academia Movie 5
  ○ Boku no Hero Academia Season 5
  ◀ Resultados Anteriores (4 palavras: 6 resultados)
  ← Voltar
  Sair
```

**Menu Navigation:**
- User can click "◀ Resultados Anteriores" to see previous search results
- User can click "▶ Próximos Resultados" to navigate forward again
- Each navigation shows the word count and result count for that iteration

**Benefits:**
- Reduces decision fatigue: shows 2-5 results instead of 50+
- Smart fallback: if exact query returns 0, shows previous (broader) results
- Explores search space: user can try different specificity levels
- Session-only history: no persistent storage, memory-efficient

### AniList Integration (Detalhes Técnicos)

**OAuth Flow:**
- User runs: `ani-tupi anilist auth`
- System opens browser to AniList OAuth endpoint
- User authorizes ani-tupi application
- AniList returns authorization token
- Token stored securely in: `~/.local/state/ani-tupi/anilist_token.json`
- Token valid for ~6 months before re-auth needed

**GraphQL API Communication:**
- Uses AniList GraphQL endpoint: `https://graphql.anilist.co`
- Queries fetch: user lists, trending anime/manga, specific titles
- Updates sent via mutations: user progress, list status
- Handles rate limiting gracefully (500 requests/minute limit)

**Automatic Synchronization:**
- After episode/chapter completes, system shows confirmation: "✅ Assistiu até o final?"
- On confirmation, GraphQL mutation sent to AniList
- Updates fields: `progress`, `updatedAt`, `status`
- Retroactive sync on next episode if network failed

**Intelligent Title Mapping:**
- Problem: AniList title ≠ Scraper title (e.g., "My Hero Academia" vs "Boku no Hero")
- Solution: Fuzzy matching (Levenshtein distance) finds closest scraper match
- Once matched, saves mapping in: `~/.local/state/ani-tupi/anilist_mappings.json`
- Next time: Uses saved mapping, zero search delay
- Format: `{"anilist_id": "scraper_title"}`

**Search Strategy:**
1. Try exact romaji match first (via GraphQL query)
2. Try exact English title match
3. Apply fuzzy matching across all scraper results
4. If multiple matches within threshold, show user to choose
5. Cache winning match for future sessions

**List Types Supported:**
- WATCHING - Current anime/manga
- PLANNING - Want to start
- COMPLETED - Finished
- PAUSED - On hold
- DROPPED - Abandoned
- REPEATING - Re-watching/re-reading

**Score/Rating Sync:**
- Can update score/rating when syncing (optional)
- Uses `score` field in GraphQL mutation
- User can edit in AniList UI later
- Currently only auto-syncs progress, not scores

### Manga PDF Reader Workflow

**Pattern**: Similar to anime (external player + cache)

1. User selects manga and chapter
2. System checks if PDF already exists in chapter directory
3. If not: Downloads images from MangaDex → Converts to PDF (Pillow)
4. Opens PDF with Zathura (or auto-detected reader: evince, okular, mupdf)
5. Saves reading progress to history

**Reader Detection** (utils/manga_reader.py):
- Priority: User config → Zathura → Evince → Okular → MuPDF → xdg-open
- Configurable via `ANI_TUPI__MANGA__PDF_READER=reader_name`
- Graceful fallback if no reader found

**PDF Conversion** (utils/pdf_converter.py):
- Converts PNG images to single multi-page PDF
- Configurable JPEG quality (default 85) via `ANI_TUPI__MANGA__PDF_QUALITY`
- Optional PNG deletion after PDF creation via `ANI_TUPI__MANGA__DELETE_IMAGES_AFTER_PDF`

## Project Structure

```
ani-tupi/
├── main.py                    # CLI entry point, argument parsing
├── manga_tupi.py              # Manga CLI (separate entry point)
├── models/
│   ├── config.py              # Pydantic settings (centralized config)
│   └── models.py              # DTOs: AnimeMetadata, EpisodeData, etc
├── commands/
│   ├── anime.py               # Anime search & watch flow
│   ├── manga.py               # Manga reading flow
│   ├── anilist.py             # AniList authentication & menu
│   └── sources.py             # Source management (enable/disable plugins)
├── services/
│   ├── anime_service.py       # Business logic: search, selection, playback
│   ├── anilist_service.py     # AniList API client (GraphQL)
│   ├── manga_service.py       # MangaDex API integration
│   ├── repository.py          # Repository pattern for plugin management
│   └── history_service.py     # Watch history persistence
├── scrapers/
│   ├── loader.py              # Plugin discovery & loading system
│   └── plugins/
│       ├── animefire.py       # AnimeFire scraper plugin
│       └── animesonlinecc.py  # AnimesonlineCC scraper plugin
├── ui/
│   ├── components.py          # Reusable menu & spinner components
│   └── anilist_menus.py       # AniList-specific menu UI
├── utils/
│   ├── video_player.py        # MPV integration (IPC commands)
│   ├── manga_reader.py        # PDF reader launcher (Zathura, auto-detect)
│   ├── pdf_converter.py       # PNG to PDF conversion (Pillow)
│   ├── cache_manager.py       # Cache operations (diskcache)
│   ├── scraper_cache.py       # Scraper result caching
│   ├── history_service.py     # Watch history management
│   ├── persistence.py         # JSON file operations
│   ├── logging.py             # Loguru configuration
│   ├── exceptions.py          # Custom exceptions
│   ├── anilist_discovery.py   # Fuzzy matching AniList IDs
│   └── title_utils.py         # Title normalization
├── pyproject.toml             # Project configuration (dependencies, scripts)
├── install-cli.py             # Global CLI installer script
└── build.py                   # PyInstaller build script
```

## Important Implementation Details

### Video Player Integration (utils/video_player.py)

- Uses MPV IPC (Inter-Process Communication) for keybinding support
- Supports custom keybindings: Shift+N (next), Shift+P (prev), Shift+M (mark & menu), etc.
- Auto-play mode toggles continuation without returning to menu
- No hardcoded keys - all configurable via MPV config

### Title Normalization (utils/title_utils.py)

- Anime titles are normalized when caching results: "Dandadan 2nd Season; Episode 3" → "Dandadan S02E03"
- Episode filtering by regex patterns prevents false matches
- Important for distinguishing seasons and specials

### Caching Strategy

**Scraper Results** (SQLite via diskcache):
- TTL: 7 days (configurable via `ANI_TUPI__CACHE__DURATION_HOURS`)
- Key pattern: `{title}:{source}` (exact match required)
- Stores: anime metadata, episodes, URLs

**Episode Lists** (Memory cache during session):
- Fetched once, reused across selections
- Cleared when user switches sources

**AniList Mappings** (JSON):
- Maps AniList ID → scraper title (for automatic continuation)
- Enables seamless "continue watching" across sessions

### Error Handling Patterns

- **Missing scrapers**: Gracefully falls back to menu, doesn't crash
- **Network errors**: Shows user message, allows retry
- **Invalid URLs**: Validated by Pydantic models before processing
- **MPV crashes**: Watched separately, user notified if playback fails

### Ruff Configuration

The project uses custom Ruff rules in `pyproject.toml` that ignore less critical linting rules (complexity, magic numbers, docstrings, etc.). This is intentional to keep the codebase focused on functionality over strict linting.

## Common Development Tasks

### Available Scraper Plugins

Current scrapers available:

1. **AnimeFirePlus** (`animefire.py`) - High quality, reliable
   - URL: https://animefire.plus
   - Episodes: Usually up-to-date
   - Player: Uses video iframes

2. **AnimesonlineCC** (`animesonlinecc.py`) - Portuguese subtitles
   - URL: https://animesonlinecc.to
   - Episodes: Multiple seasons support
   - Player: iframe player

3. **AnimesDigital** (`animesdigital.py`) - Dubbed content ⭐ NEW
   - URL: https://animesdigital.org
   - Episodes: Many dubbed anime
   - Player: Direct HLS/MP4 extraction
   - Status: ✅ Fully integrated and tested

### Adding a New Scraper Plugin

1. Create `scrapers/plugins/newsource.py` with class implementing `Scraper` protocol
2. Implement `search(query)` → returns `AnimeMetadata` list
3. Implement `get_episodes(url)` → returns `EpisodeData`
4. Plugin is auto-discovered by `scrapers/loader.py` - no registration needed
5. Run `uv run test_plugin_integration.py` to verify it's discovered

**Example**: See `animesdigital.py` for a complete implementation

### Adding a New Command

1. Create `commands/newcommand.py` with function `def newcommand(args)`
2. Import in `main.py`
3. Add to CLI parser in `cli()` function
4. Route from appropriate menu or CLI argument

### Modificando Integração AniList

**Arquivos principais:**
- `services/anilist_service.py` - Classe AniListService com métodos GraphQL
- `commands/anilist.py` - CLI commands e menu handling
- `ui/anilist_menus.py` - Interface/menus específicos do AniList
- `utils/anilist_discovery.py` - Fuzzy matching e busca de títulos

**Adicionar nova query GraphQL:**

```python
# Em services/anilist_service.py

def get_user_favorites(self):
    """Fetch user's favorite anime/manga"""
    query = """
    query {
      Viewer {
        favourites {
          anime {
            nodes {
              id
              title { romaji english }
            }
          }
        }
      }
    }
    """
    return self._request(query)
```

**Adicionar comando CLI:**

1. Criar função em `commands/anilist.py`:
```python
def favorites_command(args):
    service = AniListService(settings.anilist_token)
    favorites = service.get_user_favorites()
    # Display/process
```

2. Registrar em `main.py`:
```python
elif args.command == "anilist" and args.subcommand == "favorites":
    from commands.anilist import favorites_command
    favorites_command(args)
```

**Testar autenticação:**
```bash
uv run ani-tupi anilist auth        # Fazer login
uv run ani-tupi anilist account     # Verificar se funciona
uv run main.py --debug              # Ver logs detalhados
```

**Debugging de sincronização:**
```bash
# Ver logs completos
export ANI_TUPI__LOG_LEVEL=DEBUG
uv run ani-tupi

# Resetar token se expirou
rm ~/.local/state/ani-tupi/anilist_token.json
uv run ani-tupi anilist auth
```

### Fluxo Completo de Leitura de Mangá

O ani-tupi oferece um fluxo integrado de leitura de mangá do MangaDex com suporte a PDF e sincronização AniList.

**Entrada Principal:**
```bash
# Iniciar leitor de mangá
uv run manga_tupi
# ou (após instalar globalmente):
manga-tupi
```

**Fluxo de Leitura Passo a Passo:**

1. **Busca Interativa**
   - Sistema mostra prompt de busca
   - Digite nome do manga para filtrar resultados em tempo real
   - Resultados buscados no MangaDex API
   - Navegue com setas (↑/↓) e pressione Enter para selecionar

2. **Seleção de Manga**
   - Mostra título em romaji + inglês se disponível
   - Exibe status (ongoing, completed, etc)
   - Mostra último capítulo disponível
   - Histórico local destacado com "⮕ Retomar"

3. **Seleção de Capítulo**
   - Lista todos os capítulos disponíveis em ordem (mais recente primeiro)
   - Sistema detecta último capítulo lido
   - Hint visual mostra onde você parou
   - Pode pular para qualquer capítulo

4. **Download e Processamento Automático**
   - Sistema baixa imagens em alta qualidade do MangaDex
   - Converte automaticamente para PDF multi-página
   - Otimiza qualidade baseado em `PDF_QUALITY` env var
   - Cache garante PDFs já criados abrem instantaneamente
   - Spinner mostra progresso durante download

5. **Abertura no Leitor**
   - Detecta leitor PDF instalado automaticamente
   - Zathura: auto-configura zoom fit-width
   - Evince/Okular: abre com defaults
   - MuPDF: minimalista, apenas renderiza
   - Fallback: xdg-open sistema padrão

6. **Navegação no Leitor**
   - Zathura: setas + Page Up/Down, zoom com +/-, q para sair
   - Cada leitor tem seus próprios keybindings
   - Progresso salvo quando você sai (EOF ou q)

7. **Sincronização Automática**
   - Sistema detecta se você leu até o final
   - Se autenticado AniList: sincroniza automaticamente
   - Atualiza capítulo/episódio na lista "Reading"
   - Salva timestamp de leitura em histórico local

**Configuração Avançada:**

```bash
# Especificar leitor de PDF (detecta automaticamente se não configurado)
export ANI_TUPI__MANGA__PDF_READER="zathura"

# Deletar imagens PNG após criação PDF (economiza ~60% espaço)
export ANI_TUPI__MANGA__DELETE_IMAGES_AFTER_PDF=true

# Ajustar qualidade JPEG do PDF (1-100, padrão 85)
export ANI_TUPI__MANGA__PDF_QUALITY=75

# Duração do cache em horas (padrão 24)
export ANI_TUPI__MANGA__CACHE_DURATION_HOURS=48

# Idiomas preferidos (padrão: pt-br,en,ja)
export ANI_TUPI__MANGA__LANGUAGES=pt-br,en

# Pasta de download (padrão ~/Downloads)
export ANI_TUPI__MANGA__OUTPUT_DIRECTORY=$HOME/Mangas

# Auto-configurar Zathura com zoom fit-width (padrão true)
export ANI_TUPI__MANGA__ZATHURA_AUTO_CONFIG=true
```

**Leitores de PDF Suportados (Auto-detectados):**

A detecção ocorre nesta ordem de prioridade:

1. **Zathura** (recomendado) ⭐
   - Leve e keyboard-driven
   - Auto-configurado com zoom fit-width
   - Perfeito para leitura de mangá
   - Disponível: `pacman -S zathura` (Arch), `apt install zathura` (Ubuntu)

2. **Evince** (GNOME padrão)
   - Mais pesado mas com mais features
   - Interface GUI completa
   - Disponível: `pacman -S evince` (Arch), incluído GNOME (Ubuntu)

3. **Okular** (KDE padrão)
   - Interface completa para KDE
   - Gerenciamento de anotações
   - Disponível: `pacman -S okular` (Arch), `apt install okular` (Ubuntu)

4. **MuPDF** (Minimalista)
   - Extremamente leve e rápido
   - Apenas renderização básica
   - Disponível: `pacman -S mupdf` (Arch), `apt install mupdf` (Ubuntu)

5. **xdg-open** (Fallback)
   - Usa associação padrão do sistema
   - Pode abrir em navegador ou outro app
   - Sempre disponível no Linux

**Histórico de Leitura:**

O ani-tupi mantém histórico em `~/.local/state/ani-tupi/manga_history.json`:

```json
{
  "mangá_id": {
    "title": "Manga Title",
    "last_chapter": 42,
    "last_read_timestamp": "2025-12-30T15:30:00",
    "url": "https://mangadex.org/title/..."
  }
}
```

Ao iniciar `manga-tupi`, sistema mostra qual foi o último manga lido com hint "⮕ Retomar".

**Integração AniList:**

Se você autenticou com `ani-tupi anilist auth`:

```bash
# Seu progresso sincroniza automaticamente para:
1. Manga "Reading" → Atualiza capítulo atual
2. Score e status (se configurado)
3. Data de última leitura

# Como funciona:
1. Você abre um manga da lista AniList
2. Lê até o final (ani-tupi detecta automaticamente)
3. Sistema sincroniza: "Manga Reading → Capítulo X"
4. Seu progresso fica visível em AniList.co
```

### Working with the Cache

```python
from utils.cache_manager import clear_cache_all, clear_cache_by_prefix

# Clear specific anime from cache
clear_cache_by_prefix(":dandadan:")

# Clear everything
clear_cache_all()

# Or via CLI
uv run ani-tupi --clear-cache
uv run ani-tupi --clear-cache "dandadan"
```

## Testing Approach

The project uses pytest. Current test coverage focuses on critical paths:
- Plugin loading
- Model validation
- Service layer logic
- Cache operations

New features should include tests for:
- Happy path (normal operation)
- Error cases (invalid input, network failures)
- Edge cases (empty results, special characters in titles)

Run tests with: `uv run pytest -v`

## Common Workarounds & Known Issues

### MPV IPC Socket Not Found

**Issue**: MPV keybindings don't work
**Cause**: IPC socket path configuration
**Workaround**: Check `~/.config/mpv/mpv.conf` has `input-ipc-server=/tmp/mpvsocket`

### Geckodriver Not Found

**Issue**: Selenium can't find Firefox driver
**Cause**: geckodriver not in PATH
**Workaround**: Install via package manager (pacman, apt, brew) or manually add to PATH

### AniList Token Expired

**Issue**: "Invalid authorization" when using AniList features
**Cause**: OAuth token expired (valid for ~6 months)
**Workaround**: Re-authenticate with `uv run ani-tupi anilist auth`

## CI/CD Pipeline

The project uses GitHub Actions (`.github/workflows/`):
- **ci.yml**: Validates syntax, imports, and checks basic functionality on every push
- **build-test.yml**: Tests building standalone executables

Key validation steps:
- Python syntax checking (`py_compile`)
- Dependency validation
- Cross-platform testing (Linux, macOS, Windows)
- Plugin discovery verification

To test locally before pushing:
```bash
uv run python -m py_compile main.py
uv run python -m py_compile manga_tupi.py
uv run python -c "from scrapers import loader; loader.load_plugins({'pt-br'})"
```

## Notes for Editing

- **Always use `uv`** for running Python commands and installing packages
- **Never modify `pyproject.toml` directly** - use `uv add` / `uv remove`
- **Config changes** should go in `models/config.py` with Pydantic validation
- **New data structures** should be Pydantic models in `models/models.py`
- **Service layer** is where business logic belongs, not in commands or UI
- **Avoid circular imports** - dependency hierarchy: commands → services → models/utils
- **Persist data** in `~/.local/state/ani-tupi/` (XDG standard, respects $XDG_STATE_HOME)

## Known Limitations & Workarounds

### MPV IPC Socket Not Found

**Issue**: MPV keybindings don't work
**Cause**: IPC socket path configuration
**Workaround**: Check `~/.config/mpv/mpv.conf` has `input-ipc-server=/tmp/mpvsocket`

### AniList Token Expired

**Issue**: "Invalid authorization" when using AniList features
**Cause**: OAuth token expired (valid for ~6 months)
**Workaround**: Re-authenticate with `uv run ani-tupi anilist auth`

### Cache Manager `iterkeys()` Error

**Issue**: `ani-tupi --clear-cache "name"` fails with diskcache error
**Cause**: diskcache library doesn't expose prefix iteration
**Workaround**: Use `uv run ani-tupi --clear-cache` without arguments to clear entire cache

### AnimesonlineCC Video Token Expiration

**Issue**: AnimesonlineCC videos fail with HTTP 400 error in MPV
**Cause**: Videos use temporary Blogger URLs with tokens that expire within minutes
**Solution**: Use AnimesDigital or AnimeFire as primary sources

**How to Configure Priority**:
```bash
export ANI_TUPI__PLUGINS__PRIORITY_ORDER='["animesdigital", "animefire"]'
uv run ani-tupi --query "dandadan"
```

### MangaLivre Source Switching - FIXED ✓

**Issue**: "Nenhuma página disponível para este capítulo" when switching manga sources to MangaLivre
**Cause**: When changing sources, app was using manga ID from previous source. While IDs are shared between Mugiwaras and MangaLivre, selecting wrong result (e.g., "Jujutsu Kaisen Modulo" instead of "Jujutsu Kaisen") caused issues.
**Solution**: App now re-validates/re-searches manga when switching sources to ensure correct manga version is used.

**How it works**:
- When you switch to a new source, the app verifies the manga exists in that source
- If the ID works, uses it directly (IDs are shared across Mugiwaras/MangaLivre)
- If not, searches for the manga in new source and prefers: exact title match → ID match → shortest title (main series vs spin-offs)

This is automatic - no action needed from user.

## OpenSpec Integration

The project uses OpenSpec for structured change documentation. Major features are documented in `openspec/changes/`:
- Design documents explaining architectural decisions
- Spec files for each major component
- Task tracking for implementation

When making significant changes, consider updating or creating spec documentation.
