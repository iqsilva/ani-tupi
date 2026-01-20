# AniList Manga Integration Proposal

## Summary
Add AniList integration for manga reading, similar to existing anime integration. Users will be able to track manga progress, manage reading status (Reading, Planned, Completed, etc.), and sync progress with AniList after confirming chapter completion.

## Problem Statement
Currently, ani-tupi has robust AniList integration for anime but lacks equivalent functionality for manga. Users cannot:
- Track manga reading progress in AniList
- Manage manga reading status (Reading, Planned, Completed, etc.)
- Sync chapter progress automatically after reading
- Browse and manage their manga lists through ani-tupi

## Proposed Solution
Extend the existing AniList integration to support manga with:
1. **Progress Confirmation**: Ask "Você leu até o final do capítulo?" after each chapter
2. **Status Management**: Use same menu structure as anime (Reading, Planning, Completed, Paused, Dropped, Repeating)
3. **Progress Sync**: Automatically update chapter progress in AniList when confirmed
4. **Manga Lists**: Browse and manage AniList manga lists within ani-tupi
5. **Unified Experience**: Consistent interface between anime and manga tracking

## Scope
- Add manga-specific AniList API methods
- Extend existing AniList menu to include manga options
- Add progress confirmation dialog after chapter reading
- Integrate with existing manga service (UnifiedMangaService)
- Reuse existing authentication and configuration

## Out of Scope
- Complete redesign of manga interface
- New manga sources (use existing ones)
- Mobile apps or web interfaces

## Success Criteria
1. Users can authenticate with AniList once for both anime and manga
2. After reading a chapter, users are asked if they completed it
3. Answering "yes" automatically updates progress in AniList
4. Users can browse their AniList manga lists (Reading, Planning, etc.)
5. Users can add manga to their AniList lists
6. Progress is synchronized between local reading and AniList

## Technical Considerations
- Reuse existing AniList authentication and client
- Extend AniListService to support manga operations
- Add manga-specific methods to handle manga list entries
- Integrate with existing manga workflow in manga_tupi.py
- Maintain backward compatibility with non-AniList manga reading