# Spec: AniList Manga Sync Integration

## ADDED Requirements

### Requirement: Manga Progress Confirmation
The application SHALL prompt users for chapter completion confirmation and synchronize progress with AniList when authenticated.

#### Scenario: Chapter completion prompt and sync
- **GIVEN** a user is reading manga with AniList authentication enabled
- **WHEN** they finish reading a chapter and close the PDF reader
- **THEN** the system MUST:
  1. Ask "Você leu até o final do capítulo?"
  2. If user answers "Sim", update progress in both local history and AniList
  3. If user answers "Não" or cancels, only update local history
  4. Handle any AniList sync errors gracefully

#### Scenario: Progress conflict resolution
- **GIVEN** a user has manga progress in AniList that differs from local history
- **WHEN** they start reading a manga
- **THEN** the system MUST:
  1. Use the maximum progress between local and AniList
  2. Display which source has higher progress
  3. Offer to sync the current status

### Requirement: AniList Manga List Management  
The application SHALL provide browsing and management of AniList manga lists through the same interface used for anime.

#### Scenario: Browse manga lists from AniList menu
- **GIVEN** a user is authenticated with AniList
- **WHEN** they access the AniList main menu
- **THEN** the system MUST display manga-specific options:
  1. "📚 Trending Manga"
  2. "🔍 Buscar Manga" 
  3. "📚 Reading" (manga-specific)
  4. Combined status lists showing both anime and manga counts

#### Scenario: Read manga from AniList list
- **GIVEN** a user selects a manga from their AniList list
- **WHEN** they choose to read it
- **THEN** the system MUST:
  1. Display their current reading progress
  2. Start reading from the next unread chapter
  3. Maintain synchronization with their AniList status

### Requirement: Manga Status Management
The application SHALL manage manga reading status using the same categories as anime with automatic transitions based on reading behavior.

#### Scenario: Automatic status transitions
- **GIVEN** a user adds a manga to their AniList list
- **WHEN** they read the first chapter and confirm completion
- **THEN** the system MUST:
  1. Automatically change status from "PLANNING" to "READING"
  2. Update the progress count in AniList

#### Scenario: Manga completion handling
- **GIVEN** a user reads the final chapter of a manga
- **WHEN** they confirm completion of the last chapter
- **THEN** the system MUST:
  1. Offer to change the status to "COMPLETED"
  2. Update the total chapters read in AniList
  3. Update completion date in AniList

### Requirement: Unified AniList Authentication
The application SHALL use a single AniList authentication for both anime and manga functionality without requiring separate logins.

#### Scenario: Single auth for anime and manga
- **GIVEN** a user authenticates with AniList for anime functionality
- **WHEN** they access manga features
- **THEN** the system MUST:
  1. Use the same authentication token
  2. Allow immediate access to their manga lists
  3. Enable manga progress sync without re-authentication

### Requirement: Manga Search and Discovery
The application SHALL allow users to search for manga on AniList and add them to their lists with manga-specific metadata.

#### Scenario: Search and add manga to AniList
- **GIVEN** a user wants to add a manga to their AniList list
- **WHEN** they use the manga search function
- **THEN** the system MUST:
  1. Allow search by manga title
  2. Display results with manga-specific metadata (chapters, volumes, scores)
  3. Allow adding the manga to their desired list status

#### Scenario: Immediate reading from search
- **GIVEN** a user searches for a manga
- **WHEN** they select a manga from the search results
- **THEN** the system MUST allow them to:
  1. Add it to a specific list (Reading, Planning, etc.)
  2. Start reading immediately if added to Reading list

## MODIFIED Requirements

### Requirement: Extended AniList Main Menu
The application SHALL enhance the existing AniList main menu to include manga options while maintaining all current anime functionality.

#### Scenario: Enhanced menu with manga options
- **GIVEN** a user accesses the AniList main menu
- **WHEN** they are authenticated
- **THEN** the system MUST:
  1. Display both anime and manga options organized logically
  2. Provide clear separation between anime and manga categories
  3. Maintain all existing anime functionality unchanged
  4. Show combined counts for shared status categories

### Requirement: Configuration Extension
The application SHALL extend AniList settings to include manga-specific preferences while maintaining backward compatibility.

#### Scenario: Manga-specific AniList settings
- **GIVEN** a user configures AniList settings
- **WHEN** they access manga-specific configuration options
- **THEN** the system MUST allow them to:
  1. Set preferences for manga title display (English/Romaji)
  2. Enable/disable manga auto-sync
  3. Configure manga progress confirmation behavior
  4. Maintain backward compatibility with existing anime settings