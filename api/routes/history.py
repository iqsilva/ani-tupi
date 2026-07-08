"""History API routes for continue watching."""

from fastapi import APIRouter, HTTPException

from api.schemas import HistoryEntrySchema, HistoryListResponse
from models.config import get_data_path
from models.models import HistoryEntry
from utils.persistence import JSONStore
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/history", tags=["history"])

HISTORY_PATH = get_data_path()
_history_store = JSONStore(HISTORY_PATH / "history.json")


@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: int = 50,
) -> HistoryListResponse:
    """Get watch history sorted by most recent."""
    try:
        data = _history_store.load({})

        # Sort by timestamp (most recent first)
        sorted_data = sorted(data.items(), key=lambda x: x[1][0], reverse=True)

        entries = []
        for anime, raw in sorted_data[:limit]:
            he = HistoryEntry.from_list(raw)
            entries.append(
                HistoryEntrySchema(
                    anime=anime,
                    episode=he.episode_idx + 1,  # Convert to 1-indexed
                    total_episodes=he.total_episodes,
                    source=he.source,
                    anilist_id=he.anilist_id,
                    timestamp=he.timestamp,
                    urls=he.urls,
                )
            )

        return HistoryListResponse(
            entries=entries,
            total=len(entries),
        )

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{anime}", response_model=HistoryEntrySchema)
async def get_history_entry(anime: str) -> HistoryEntrySchema:
    """Get history entry for a specific anime."""
    try:
        data = _history_store.load({})

        if anime not in data:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for '{anime}'",
            )

        he = HistoryEntry.from_list(data[anime])

        return HistoryEntrySchema(
            anime=anime,
            episode=he.episode_idx + 1,
            total_episodes=he.total_episodes,
            source=he.source,
            anilist_id=he.anilist_id,
            timestamp=he.timestamp,
            urls=he.urls,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{anime}")
async def delete_history_entry(anime: str) -> dict:
    """Delete a specific history entry."""
    try:
        data = _history_store.load({})

        if anime not in data:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for '{anime}'",
            )

        del data[anime]
        _history_store.save(data)

        return {"success": True, "message": f"Deleted history for '{anime}'"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete history entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def clear_history() -> dict:
    """Clear all watch history."""
    try:
        _history_store.save({})
        return {"success": True, "message": "History cleared"}

    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
