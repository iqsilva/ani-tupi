# Proposal: Shift+N Command for Next Episode Navigation

**Change ID:** `add-next-episode-command`
**Status:** Implemented
**Priority:** High
**Date:** 2026-01-04

---

## Why

**Problem:** While the current MPV IPC infrastructure supports basic navigation, the `Shift+N` command needs to be fully integrated with the watch history and AniList progress syncing. Users expect that skipping to the next episode automatically marks the current one as completed.

**Impact:** Improved binge-watching experience and automated progress tracking.

**Opportunity:** Leverage the existing IPC socket implementation in `utils/video_player.py` to trigger history updates and fetch the next episode's stream URL without returning to the main menu.

---

## Executive Summary

Implement the logic for the `Shift+N` keybinding to:
1. Mark the current episode as watched in local history and AniList.
2. Fetch the next episode's URL from the repository.
3. Command MPV to load the new URL using `loadfile`.
4. Provide visual feedback via OSD.

---

## Proposed Solution

### Architecture Overview

The `Shift+N` command flow:
1. **MPV**: User presses `Shift+N`.
2. **ani-tupi (IPC loop)**: Receives `mark-next` event.
3. **History Service**: `save_history_from_event` is called to mark current episode as watched.
4. **Repository**: `get_episode_url` fetches the next episode's stream URL.
5. **IPC Socket**: Sends `loadfile` command to MPV with the new URL.
6. **MPV**: Loads and plays the next episode.

### Key Components

- **`utils/video_player.py`**: Update `_ipc_event_loop` to handle the `mark-next` (Shift+N) action by integrating with `HistoryService` and `Repository`.
- **`services/history_service.py`**: Ensure `save_history_from_event` correctly handles AniList syncing if enabled.
- **`services/repository.py`**: Provide a reliable way to get the next episode's URL based on current context.

---

## Technical Details

### IPC Event Handling

```python
if action == "mark-next":
    # 1. Save progress
    save_history_from_event(anime_title, current_ep_idx, "watched", source, anilist_id)
    
    # 2. Get next URL
    next_url = rep.get_episode_url(anime_title, current_ep_idx + 1)
    
    # 3. Tell MPV to play
    if next_url:
        _send_mpv_command(sock, "loadfile", [next_url, "replace"])
        _send_mpv_command(sock, "show-text", [f"Loading Episode {next_ep_number}..."])
    else:
        _send_mpv_command(sock, "show-text", ["No more episodes available"])
```

---

## Testing Strategy

- **Integration Test**: Mock the MPV IPC socket and send a `mark-next` event, then verify that `save_history_from_event` was called and a `loadfile` command was sent back.
- **E2E Test**: Verify the full flow from playing an episode to pressing `Shift+N` and seeing the next episode start.

---

## Success Criteria

- [ ] `Shift+N` marks current episode as watched in local history.
- [ ] `Shift+N` marks current episode as watched in AniList (if authenticated).
- [ ] `Shift+N` loads the next episode in the same MPV window.
- [ ] OSD feedback is shown to the user.
