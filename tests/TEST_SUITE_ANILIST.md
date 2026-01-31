# AniList Search & Watch Flow Test Suite

## Overview

Comprehensive test suite for the AniList anime search and watch flow, covering the functionality described in the bug report: "After searching for anime via '🔍 Buscar Anime' and clicking '▶️ Assistir agora', playback should start immediately."

## Test Files

### 1. `tests/unit/ui/test_anilist_menus.py` (Unit Tests)

20 unit tests covering:

#### TestStartWatchingAnime (5 tests)
- `test_calls_anilist_anime_flow_with_correct_parameters`: Verifies `anilist_anime_flow` is called with all correct parameters
- `test_passes_zero_progress_when_no_entry`: Progress defaults to 0 when user has no AniList entry
- `test_passes_zero_progress_when_entry_has_none_progress`: Progress set to 0 when entry.progress is None
- `test_creates_argparse_namespace_with_debug_false`: Creates proper Namespace object with debug=False
- `test_fetches_progress_from_anilist_client`: Calls `get_media_list_entry` with correct anime_id

#### TestSearchAndAddAnimeLoggedIn (4 tests)
- `test_watch_now_without_adding_to_list`: "▶️ Assistir agora" option starts playback immediately
- `test_add_then_watch_after_choosing_status`: User can add anime to list then watch
- `test_add_then_go_back_without_watching`: User can add anime but choose not to watch
- `test_go_back_from_action_menu`: User can return to main menu from action menu

#### TestSearchAndAddAnimeNotLoggedIn (2 tests)
- `test_calls_start_watching_anime_directly`: Non-logged-in user goes straight to watch
- `test_no_add_to_list_option_for_non_logged_in`: Action menu not shown for non-authenticated users

#### TestCompleteSearchToPlaybackFlow (3 tests)
- `test_end_to_end_search_and_watch_logged_in`: Complete flow with AniList progress
- `test_end_to_end_search_and_watch_no_progress`: Complete flow for new anime
- `test_end_to_end_add_then_watch_flow`: Complete flow: search → add → watch

#### TestEdgeCases (5 tests)
- `test_empty_search_query`: Empty query returns to main menu
- `test_no_search_results`: No results returns to main menu
- `test_user_cancels_search_results`: ESC on search results menu
- `test_add_status_selection_cancelled`: ESC during status selection shows menu again
- `test_zero_progress_from_entry`: Progress=0 is handled correctly

#### TestStatusMapping (1 test)
- `test_all_status_options_map_correctly`: All 6 status options map to correct AniList codes (CURRENT, PLANNING, COMPLETED, PAUSED, DROPPED, REPEATING)

### 2. `tests/integration/test_anime_search_watch_flow.py` (Integration Tests)

6 integration tests covering:

#### TestCompleteSearchToWatchIntegration
- `test_search_watch_with_progress_starts_playback`: User with progress watches from that position
- `test_search_multiple_results_user_selects_second`: Correct anime selected from multiple results
- `test_add_new_anime_then_watch`: New anime added before playback starts
- `test_playback_starts_immediately_no_menu_recursion`: **Bug fix verification** - playback starts immediately without menu recursion
- `test_correct_parameters_passed_to_playback`: All parameters passed to playback function
- `test_unauthenticated_user_skips_add_option`: Non-authenticated users skip add menu

## Test Coverage

### Functions Tested
- **`_start_watching_anime(search_title, anime_id, display_title)`**: Handles playback initiation with progress tracking
- **`_search_and_add_anime(is_logged_in)`**: Complete search and add flow for both authenticated and non-authenticated users

### Scenarios Covered

#### User Authentication States
- ✅ Authenticated users (with and without anime progress)
- ✅ Non-authenticated users

#### Search Results
- ✅ Single result
- ✅ Multiple results
- ✅ No results
- ✅ User cancels search

#### AniList Integration
- ✅ User has progress on anime (uses existing progress)
- ✅ User has no progress (starts from 0)
- ✅ User has entry with progress=None (treated as 0)
- ✅ User not on list (no entry returned)

#### Action Menu Flows
- ✅ "▶️ Assistir agora" (watch now) - immediately starts playback
- ✅ "➕ Adicionar à lista" (add to list) then "▶️ Assistir agora"
- ✅ "➕ Adicionar à lista" then "🔙 Voltar ao menu" (don't watch)
- ✅ "🔙 Voltar" (back to menu)

#### Status Selection
- ✅ All 6 status options correctly map to AniList codes
- ✅ Status selection cancellation (ESC) shows menu again

## Running the Tests

### Run all AniList tests
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py tests/integration/test_anime_search_watch_flow.py -v
```

### Run with coverage
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py tests/integration/test_anime_search_watch_flow.py --cov=ui.anilist_menus --cov-report=html
```

### Run specific test class
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py::TestStartWatchingAnime -v
```

### Run specific test
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py::TestSearchAndAddAnimeLoggedIn::test_watch_now_without_adding_to_list -v
```

## Mocking Strategy

All tests use `unittest.mock` to isolate functions:

- **`anilist_client`**: Mocked to avoid API calls
- **`anilist_anime_flow`**: Mocked to avoid starting actual playback
- **`menu_navigate`**: Mocked to simulate user menu selections
- **`loading`**: Mocked context manager for loading UI
- **`anilist_main_menu`**: Mocked to prevent menu recursion
- **`builtins.input`**: Mocked to simulate user input

## Key Test Data Fixtures

- **`sample_anime`**: AniListAnime with id=123, romaji="Dandadan", 12 episodes
- **`sample_media_list_entry`**: AniListMediaListEntry with progress=5
- **`sample_viewer_info`**: AniListViewerInfo with user stats
- **`sample_search_results`**: List of 2 anime (Dandadan, Jujutsu Kaisen)

## Bug Fix Verification

The critical test that verifies the bug is fixed:

```python
def test_playback_starts_immediately_no_menu_recursion(...)
    """Bug fix verification: playback starts immediately, no menu recursion."""
```

This test ensures that:
1. User clicks "▶️ Assistir agora"
2. `anilist_anime_flow` is called to start playback
3. The function returns to main menu only once (not in a loop)
4. No additional menu navigation occurs after playback initiation

## Test Quality Metrics

- **Total Tests**: 26
- **Pass Rate**: 100%
- **Edge Cases**: 5 (empty query, no results, cancellations, zero progress)
- **Status Options Tested**: 6/6
- **User States**: 2 (authenticated, non-authenticated)
- **Progress Scenarios**: 4 (with progress, no progress, progress=None, progress=0)

## Future Extensions

To increase coverage of the entire `anilist_menus.py` file (currently 22%), consider adding tests for:

1. `anilist_main_menu()` - Main menu navigation
2. `_show_anime_list(list_type)` - Trending and user list display
3. `_show_recent_history()` - Recent watched anime
4. `_show_account_menu()` - Account management
5. `_choose_status()` - Status selection menu
6. `_choose_year()` - Year filter for trending
7. `_choose_season()` - Season filter for trending
8. `authenticate_flow()` - OAuth authentication

## Notes

- All tests follow TDD principles (tests written before implementation)
- Comprehensive mocking ensures tests don't depend on external services
- Tests are independent (no shared state between tests)
- Clear, descriptive test names and docstrings
- Edge cases explicitly tested
- Status mapping verified with parametrized test approach
