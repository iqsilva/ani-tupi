## MODIFIED Requirements
### Requirement: Default Manga Source Selection
The UnifiedMangaService SHALL prioritize MugiwarasOficial as the default manga source for Brazilian Portuguese users, with MangaDex as automatic fallback.

#### Scenario: Service initialization with both plugins available
- **WHEN** UnifiedMangaService is initialized with both Mugiwaras and MangaDex plugins available
- **THEN** Mugiwaras SHALL be set as the current_source by default
- **AND** MangaDex SHALL be available as fallback option

#### Scenario: Service initialization with only MangaDex available
- **WHEN** UnifiedMangaService is initialized with only MangaDex plugin available
- **THEN** MangaDex SHALL be set as the current_source
- **AND** service SHALL continue to function normally

#### Scenario: Service initialization with only Mugiwaras available
- **WHEN** UnifiedMangaService is initialized with only Mugiwaras plugin available
- **THEN** Mugiwaras SHALL be set as the current_source
- **AND** service SHALL continue to function normally

#### Scenario: Source failure during operation
- **WHEN** the current source (Mugiwaras) fails during a search or chapter fetch operation
- **THEN** the service SHALL automatically attempt the same operation with MangaDex as fallback
- **AND** SHALL return results from the fallback source if successful
- **AND** SHALL notify the user about the source switch