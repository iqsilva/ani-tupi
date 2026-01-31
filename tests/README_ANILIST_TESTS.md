# AniList Search & Watch Flow - Comprehensive Test Suite

## Quick Start

Run all tests:
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py tests/integration/test_anime_search_watch_flow.py -v
```

All tests pass: ✅ 26/26

## Files Overview

| File | Purpose | Type | Tests |
|------|---------|------|-------|
| `tests/unit/ui/test_anilist_menus.py` | Core function testing | Unit | 20 |
| `tests/integration/test_anime_search_watch_flow.py` | End-to-end flows | Integration | 6 |
| `tests/TEST_SUITE_ANILIST.md` | Detailed test reference | Documentation | - |
| `TESTING_SUMMARY.md` | Project summary | Documentation | - |

## What's Being Tested

### Bug Report Context
After searching for anime via "🔍 Buscar Anime" and clicking "▶️ Assistir agora", the playback should start immediately.

### Functions Under Test

#### 1. `_start_watching_anime(search_title, anime_id, display_title)`
Initiates anime playback with proper progress tracking from AniList.

**Behaviors tested:**
- Fetches user's progress from AniList
- Handles missing entries (no progress = 0)
- Handles progress=None (treats as 0)
- Handles progress=0 (correct value)
- Creates proper argparse.Namespace
- Calls anilist_anime_flow with all correct parameters

**Test count:** 5

#### 2. `_search_and_add_anime(is_logged_in)`
Handles the complete search, selection, and optional add-to-list flow.

**Behaviors tested:**
- Gets search query from user
- Searches anime via AniList API
- Shows search results
- For authenticated users: shows action menu
- For non-authenticated users: goes straight to watch
- Handles adding anime to list with status selection
- Initiates playback via _start_watching_anime
- Returns to main menu

**Test count:** 15

## Test Categories

### 1. Unit Tests (20 tests)

#### TestStartWatchingAnime (5 tests)
- Direct function behavior
- Progress handling
- Parameter creation

#### TestSearchAndAddAnimeLoggedIn (4 tests)
- Authenticated user flows
- Watch without adding
- Watch after adding
- Back without watching

#### TestSearchAndAddAnimeNotLoggedIn (2 tests)
- Non-authenticated user flow
- No action menu shown

#### TestCompleteSearchToPlaybackFlow (3 tests)
- End-to-end happy paths
- With and without progress
- Add then watch flow

#### TestEdgeCases (5 tests)
- Empty search query
- No search results
- User cancellations (ESC)
- Progress edge cases

#### TestStatusMapping (1 test)
- All 6 status options
- Correct mapping to AniList codes

### 2. Integration Tests (6 tests)

#### TestCompleteSearchToWatchIntegration
- Real-world user flows
- Cross-function interactions
- Bug fix verification
- Parameter passing verification

## Running Tests

### All tests
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py \
               tests/integration/test_anime_search_watch_flow.py -v
```

### Just unit tests
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py -v
```

### Just integration tests
```bash
uv run pytest tests/integration/test_anime_search_watch_flow.py -v
```

### Specific test class
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py::TestStartWatchingAnime -v
```

### Specific test
```bash
uv run pytest "tests/unit/ui/test_anilist_menus.py::TestSearchAndAddAnimeLoggedIn::test_watch_now_without_adding_to_list" -v
```

### With coverage report
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py \
               tests/integration/test_anime_search_watch_flow.py \
               --cov=ui.anilist_menus --cov-report=html
```

### Watch mode (continuous)
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py \
               tests/integration/test_anime_search_watch_flow.py \
               -v --watch
```

### Verbose output with full tracebacks
```bash
uv run pytest tests/unit/ui/test_anilist_menus.py \
               tests/integration/test_anime_search_watch_flow.py \
               -vv --tb=long
```

## Test Scenarios

### Authentication States
- ✅ Authenticated user with prior progress
- ✅ Authenticated user without progress
- ✅ Authenticated user with progress=None
- ✅ Authenticated user with progress=0
- ✅ Non-authenticated user

### User Flows
| Flow | Tested | Pass |
|------|--------|------|
| Search → Watch | ✅ | PASS |
| Search → Add → Watch | ✅ | PASS |
| Search → Add → Back | ✅ | PASS |
| Search → Back | ✅ | PASS |
| Search → Empty | ✅ | PASS |
| Empty Query | ✅ | PASS |

### Edge Cases
- ✅ ESC on search results menu
- ✅ ESC on status selection menu
- ✅ User cancellation at action menu
- ✅ None progress handling
- ✅ Zero progress handling
- ✅ Missing AniList entry

### Status Options
- ✅ 📺 Watching (CURRENT)
- ✅ 📋 Planning (PLANNING)
- ✅ ✅ Completed (COMPLETED)
- ✅ ⏸️ Paused (PAUSED)
- ✅ ❌ Dropped (DROPPED)
- ✅ 🔁 Rewatching (REPEATING)

## Test Quality

### Code Organization
- 7 test classes (by functionality)
- 26 test methods (clear naming)
- 8 pytest fixtures (reusable components)
- 100% independent tests (no shared state)

### Mocking
All external dependencies are mocked:
- `anilist_client` - AniList API operations
- `anilist_anime_flow` - Playback initiation
- `menu_navigate` - Menu system
- `loading` - Loading UI
- `anilist_main_menu` - Main menu navigation
- `builtins.input` - User input

No actual API calls or external services used in tests.

### Documentation
- Clear test names describing what is tested
- Docstrings on all test classes and methods
- Comments explaining complex assertions
- Setup/Execute/Verify structure in all tests

## Key Test Cases

### Bug Verification: Playback Starts Immediately

**Test:** `test_playback_starts_immediately_no_menu_recursion`

**What it verifies:**
1. User clicks "▶️ Assistir agora"
2. Playback function called immediately
3. No menu recursion occurs
4. Returns to main menu exactly once

**Why this matters:**
This is the core bug that was reported - ensuring playback doesn't get lost in menu navigation loops.

### Progress Handling

**Test:** `test_search_watch_with_progress_starts_playback`

**What it verifies:**
1. User has watched 5/12 episodes
2. Playback starts from episode 6
3. Correct progress value passed to playback function

**Why this matters:**
Users should resume from where they left off, not restart from beginning.

### Authentication Flow

**Test:** `test_calls_start_watching_anime_directly`

**What it verifies:**
1. Non-authenticated users skip the "add to list" menu
2. Go straight to playback
3. Still get proper progress handling

**Why this matters:**
Both authenticated and non-authenticated users should have smooth flows.

## Common Issues & Solutions

### Tests fail with "No attribute 'anilist_menus'"
**Solution:** Remove any `__init__.py` files in `tests/unit/ui/`

### Mock not being called
**Solution:** Verify the patch path matches the import in the module being tested

### Mock side_effect exhausted (StopIteration)
**Solution:** Ensure all menu_navigate() calls are mocked with enough side effects

### Import errors
**Solution:** Ensure tests are run from project root with `uv run pytest`

## Extending the Tests

### Add a new test for a new scenario
```python
def test_new_scenario(self, mock_anilist_client, mock_anilist_anime_flow, ...):
    """Describe what is being tested."""
    # Setup
    mock_anilist_client.search_anime.return_value = [sample_anime]

    # Execute
    _search_and_add_anime(is_logged_in=True)

    # Verify
    assert mock_anilist_anime_flow.called
```

### Add a new fixture for test data
```python
@pytest.fixture
def my_test_data():
    """Create test data."""
    return MyObject(...)
```

### Add a new test class
```python
class TestNewFeature:
    """Tests for new feature."""

    def test_something(self, fixtures):
        """Test description."""
        # test code
```

## References

- Pytest documentation: https://docs.pytest.org/
- unittest.mock documentation: https://docs.python.org/3/library/unittest.mock.html
- TDD approach: Write tests first, implement later

## Summary

This test suite provides comprehensive coverage of the AniList anime search and watch functionality:

- **26 tests** covering all major scenarios
- **100% pass rate** confirming correct implementation
- **5 edge cases** ensuring robustness
- **Full documentation** for maintenance and extension
- **All mocked** so tests run fast and independently
- **Bug verification** for the reported playback issue

The tests confirm that the implementation correctly handles the user flow from search to playback without menu recursion or unexpected navigation.
