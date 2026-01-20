# Change: Set Mugiwaras as default manga source with MangaDex fallback

## Why
Users want Brazilian Portuguese manga content by default since the app is focused on the Brazilian market. Currently, the source selection logic is inconsistent and may default to MangaDex instead of the preferred Mugiwaras source.

## What Changes
- Modify UnifiedMangaService to prioritize MugiwarasOficial as default source
- Use MangaDex as fallback when Mugiwaras is not available or fails
- Update source selection logic to be more deterministic

## Impact
- Affected specs: manga-service (source selection behavior)
- Affected code: services/unified_manga_service.py (source selection logic)