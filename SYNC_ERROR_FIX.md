# Sync Error Diagnostic Improvements

## Problem
Users were getting cryptic sync failures:
```
Failed to update progress for anime 54321 ep 11
❌ Offline sync failed for Chainsaw Man Dublado ep 11 (retry 1/3)
```

With no clear indication of **why** the sync failed.

## Root Causes Identified

1. **Wrong AniList ID**: Discovery mapped to wrong anime
2. **Episode exceeds total**: Episode 11 > total episodes in anime
3. **Anime already COMPLETED**: Can't update completed anime
4. **Token expired**: Authentication failed
5. **Silent failures**: No logging of actual error

## Improvements Made

### 1. Enhanced Logging in `services/anilist/anime_operations.py`

Added detailed error logging to `update_progress()`:

```python
except Exception as e:
    error_msg = str(e)
    error_lower = error_msg.lower()

    if "completed" in error_lower or "finished" in error_lower:
        logger.warning(
            "Cannot update progress for anime_id=%d ep=%d: "
            "Anime is marked COMPLETED on AniList. "
            "Please change status manually.",
            anime_id, episode
        )
    elif "progress" in error_lower and "exceed" in error_lower:
        logger.warning(
            "Cannot update anime_id=%d ep=%d: "
            "Episode number exceeds total episodes. "
            "Check if anilist_id is correct.",
            anime_id, episode
        )
    else:
        logger.error(
            "Failed to update progress for anime_id=%d ep=%d: %s",
            anime_id, episode, error_msg
        )
```

### 2. AniList ID Validation in `services/anime/playback_service.py`

Added `_validate_anilist_id()` function that:
- Checks if anime exists on AniList
- Checks if episode number exceeds total episodes
- Logs specific warnings if validation fails

```python
def _validate_anilist_id(anilist_id: int, episode: int) -> bool:
    """Validate AniList ID by checking anime exists."""
    anime_info = anilist_client.get_anime_by_id(anilist_id)

    if not anime_info:
        logger.warning(
            "AniList ID %d not found. Anime may not exist or ID is incorrect.",
            anilist_id,
        )
        return False

    if anime_info.episodes and episode > anime_info.episodes:
        logger.warning(
            "Episode %d exceeds total episodes (%d) for anime_id=%d (%s). "
            "AniList ID may be incorrect.",
            episode, anime_info.episodes, anilist_id,
            anime_info.title.romaji,
        )
        return False

    return True
```

### 3. Better User Feedback

#### Interactive Discovery Shows AniList ID
```
🔍 Match parcial encontrado: Chainsaw Man (85%)
   Escolha a correspondência correta:

   1. Chainsaw Man (85%)
   2. Chainsaw Man Dublado (80%)
   3. Chainsaws (75%)
   4. ⏭️ Nenhuma das opções

✅ Mapeado: Chainsaw Man Dublado
   🆔 ID AniList: 54321
```

#### Successful Sync Shows ID
```
✅ Progresso sincronizado com AniList (ID: 54321)
```

#### Error Messages Include Context
```
❌ Offline sync failed for Chainsaw Man Dublado ep 11 anime_id=54321
(retry 1/3). Check logs above for error details.
```

### 4. Improved Offline Sync Queue Messages

Error messages now suggest common causes:
```python
entry.last_error = (
    "Sync failed (check logs for details). "
    "Common issues: wrong AniList ID, anime already COMPLETED, "
    "episode number exceeds total"
)
```

## Debugging Flow for Users

When sync fails, users should:

1. **Check the AniList ID displayed**
   ```
   🆔 ID AniList: 54321
   ```

2. **Visit AniList.co and verify**
   - Go to `https://anilist.co/anime/54321`
   - Check if it's the correct anime
   - Check the total episode count

3. **Check the log output** for specific error:
   ```
   ERROR Failed to update progress for anime_id=54321 ep=11:
   Cannot update progress for anime in COMPLETED status
   ```

4. **If wrong ID**, use interactive discovery again
   - For local library: watch the anime again (first episode)
   - Choose the correct anime from the list
   - Choice is cached for 30 days

## Environmental Logging

To see detailed logs during playback:

```bash
export ANI_TUPI__LOG_LEVEL=debug
uv run ani-tupi
```

This will show:
- Discovery process and matching scores
- AniList ID selected
- Validation checks
- Sync attempts and results

## Testing

All existing tests pass:
```bash
uv run pytest tests/test_offline_sync.py tests/test_local_anime_service.py -v
# 40 passed
```

## Example Error Scenarios

### Scenario 1: Wrong AniList ID
```
🔍 Match parcial encontrado: Chainsaw Man (85%)
✅ Mapeado: Chainsaw Man Dublado
   🆔 ID AniList: 54321

[User plays episode 11, but 54321 is actually "Chainsaw Saga"]

ERROR Failed to update progress for anime_id=54321 ep=11:
GraphQL error: ['Cannot update progress for media with 9 episodes']
```

**Fix**: Run interactive discovery again to select correct anime

### Scenario 2: Already COMPLETED
```
✅ Mapeado: Chainsaw Man Dublado
   🆔 ID AniList: 54321

ERROR Failed to update progress for anime_id=54321 ep=11:
Cannot update progress for anime in COMPLETED status
```

**Fix**: Go to AniList, change status back to "Watching", then retry

### Scenario 3: Episode Exceeds Total
```
WARNING Episode 11 exceeds total episodes (10) for anime_id=54321
(Chainsaw Man Dublado). AniList ID may be incorrect.
```

**Fix**: Check AniList to verify it's the correct anime and episode count

## Next Steps

Users can now:
1. See exactly what AniList ID is being used
2. Understand why sync failed (logged in detail)
3. Verify the ID is correct before playing
4. Take corrective action (change AniList status, re-discover, etc.)

The diagnostic information makes it much easier to troubleshoot sync failures without needing to ask for logs.
