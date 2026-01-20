# Spec: Manga Chapter Action Menu

**Capability**: Allow users to choose between reading a chapter immediately or downloading for later.

**Status**: Proposal

**Related Capabilities**:
- `manga-batch-download` (the download path)
- Uses existing: `read-now` flow (existing behavior)

## ADDED Requirements

### Requirement: Chapter Action Selection Menu

The system SHALL present a menu after chapter selection that allows the user to choose between reading immediately or downloading for later.

#### Scenario: User selects "Read Now"
- **Given**: User has selected a chapter from available chapters
- **When**: Chapter action menu is displayed
- **Then**:
  - Menu shows options: "📖 Ler Agora" (Read Now), "⬇️ Baixar para Depois" (Download), "↩️ Voltar" (Back)
  - User selects "📖 Ler Agora"
  - **Expected**: PDF creation and reader opening follows (existing behavior)
  - **Expected**: After reader closes, history is updated with last_chapter
  - **Expected**: User returns to menu (or previous menu)

#### Scenario: User selects "Download for Later"
- **Given**: User has selected a chapter from available chapters
- **When**: Chapter action menu is displayed
- **Then**:
  - Menu shows options: "📖 Ler Agora", "⬇️ Baixar para Depois", "↩️ Voltar"
  - User selects "⬇️ Baixar para Depois"
  - **Expected**: Flow proceeds to range selection dialog (see `manga-batch-download` spec)

#### Scenario: User selects "Back"
- **Given**: Chapter action menu is displayed
- **When**: User selects "↩️ Voltar"
- **Then**:
  - **Expected**: Returns to chapter selection menu (no action taken)

### Requirement: Menu Display Using InquirerPy

The action menu SHALL be displayed using the existing InquirerPy infrastructure with proper formatting and Unicode icons.

#### Scenario: Menu appears with proper formatting
- **Given**: A chapter has been selected and action menu should display
- **When**: The action menu component is rendered
- **Then**:
  - **Expected**: Menu uses InquirerPy `inquirer.select()`
  - **Expected**: Menu title shows manga title and chapter number
  - **Expected**: Menu options are properly formatted with Unicode icons
  - **Expected**: Navigation uses arrow keys (InquirerPy default)

#### Scenario: Invalid selection handling
- **Given**: Menu is displayed with 3 options
- **When**: User attempts invalid selection
- **Then**:
  - **Expected**: InquirerPy prevents invalid selection (built-in validation)

### Requirement: Integrated into Chapter Selection Flow

The action menu SHALL be integrated into the chapter selection flow, appearing after the user selects a chapter and before any file operations occur.

#### Scenario: Flow after chapter selection
- **Given**: User has navigated to chapters list and selected one
- **When**: Chapter is selected
- **Then**:
  - **Expected**: Instead of immediately opening reader, action menu appears
  - **Expected**: User chooses action before any file operations occur
  - **Expected**: Previous behavior (immediate read) still works when user selects "Read Now"

#### Scenario: No reader opened for download selection
- **Given**: User selects "Download for Later"
- **When**: Range is being selected
- **Then**:
  - **Expected**: No PDF reader process is started
  - **Expected**: No temporary files are left behind if user cancels

## Implementation Notes

### Code Location
- Add function `_show_chapter_action_menu()` in `manga_tupi.py`
- Call from `_handle_chapter_selection()` after chapter is selected
- Router function routes to either read or download path

### Configuration
- No configuration needed for menu display (uses defaults from InquirerPy)
- Menu text strings should be defined as constants for i18n-readiness

### Error Handling
- Menu selection is guaranteed valid by InquirerPy
- Back option always available
- No external calls needed for menu display

### Testing
- Unit test: Verify action router selects correct path
- Integration test: Verify read path still works (existing behavior)
- Integration test: Verify download path is called (mocked to avoid network)
- Manual test: Menu appears with correct formatting

## Dependencies

- `InquirerPy`: Already in project
- `ui.components.menu_navigate()`: Existing helper (reuse or adapt)
- Existing chapter selection and reader opening logic

## Success Criteria

1. After chapter selection, user sees action menu (no automatic reader open)
2. "Read Now" option behaves exactly like old behavior (backward compatible)
3. "Download for Later" transitions to range selection (no file operations yet)
4. "Back" option returns to chapter list without changes
5. Menu uses proper formatting and icons
6. No new dependencies added
