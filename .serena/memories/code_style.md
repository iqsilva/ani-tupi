# Code Style Guide for ani-tupi

## Python Version & Style
- **Target**: Python 3.12+ (PEP 8, type hints where practical)
- **Formatter**: Ruff (line length: 100)
- **Linter**: Ruff with custom ignore rules (see pyproject.toml)
- **Type Checking**: Optional (mypy/pyright configured but not enforced)

## Naming Conventions
- **Classes**: PascalCase (e.g., `AnimeService`, `EpisodeData`)
- **Functions/Methods**: snake_case (e.g., `get_episodes`, `normalize_title`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_CACHE_TTL`)
- **Private**: leading underscore (e.g., `_internal_method`)

## File Organization
- **Small > Large**: Prefer many focused files (200-400 lines) over few monolithic ones
- **By Feature/Domain**: Organize by what code does, not by type (services/ not utils/)
- **Max File Size**: 800 lines (hard limit)

## Data Structures & Types
- **Use Pydantic v2** for all data models (models/models.py)
- **Immutability**: Return new objects, NEVER mutate input
- **Protocol over ABC**: Use `typing.Protocol` for plugin contracts
- **Type Hints**: Required at function signatures (minimal, not aggressive)

## Example: Good Style
```python
from pydantic import BaseModel
from typing import Protocol

class AnimeMetadata(BaseModel):
    title: str
    url: str
    cover: str | None = None

class Scraper(Protocol):
    def search(self, query: str) -> list[AnimeMetadata]: ...
    def get_episodes(self, url: str) -> list[EpisodeData]: ...

def search_anime(query: str, scrapers: list[Scraper]) -> list[AnimeMetadata]:
    """Search all scrapers and deduplicate results."""
    results = []
    for scraper in scrapers:
        results.extend(scraper.search(query))
    return _deduplicate(results)
```

## Docstrings & Comments
- **Docstrings**: Use triple quotes for public functions/classes (brief only)
- **Comments**: Only when logic isn't self-evident (avoid over-commenting)
- **No**: Line-by-line comments, comment blocks for obvious code

## Error Handling
- **Validation**: Validate at system boundaries (user input, external APIs)
- **Trust Internal Code**: Don't over-validate internal function calls
- **Logging**: Use loguru for all logging (NOT print, NOT warnings)
- **Exceptions**: Create domain-specific exceptions when useful

## Circular Import Prevention
- **Import Order**: commands → services → models/utils (never reverse)
- **Lazy Imports**: Use conditional imports in functions if needed
- **Service Injection**: Pass dependencies to services, don't import globally

## Testing
- **Coverage Target**: 80%+ on service layer
- **Test Structure**: `tests/unit/` (fast), `tests/integration/`, `tests/e2e/`
- **Markers**: Use @pytest.mark decorators (unit, integration, e2e, slow, etc.)
- **Mocking**: Mock external dependencies (scrapers, APIs, cache)

## Configuration
- **Centralization**: All config via models/config.py (Pydantic)
- **Environment Variables**: Use ANI_TUPI__ prefix (e.g., ANI_TUPI__CACHE__DURATION_HOURS)
- **No Config Files**: Avoid .env files that require parsing
- **Validation on Boot**: Pydantic validates all env vars at startup

## Ruff Ignore Rules (for this project)
- `ANN*`: Missing type annotations (optional)
- `ARG*`: Unused function arguments (common in plugins)
- `D*`: Docstring rules (relaxed)
- `PLR*`: Too complex (allowed for business logic)
- `SLF001`: Private member access (acceptable)
- `S105/S113/S603/S607`: Security rules with exceptions (false positives)
- `FBT`: Boolean args (acceptable for CLI flags)
