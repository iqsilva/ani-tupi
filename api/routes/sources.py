"""Sources API routes for scraper management."""

from fastapi import APIRouter, HTTPException

from api.schemas import SourceInfo, SourcePriorityRequest, SourcesResponse
from models.config import settings, save_user_settings_overrides, load_user_settings_overrides
from services.repository import rep
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=SourcesResponse)
async def get_sources() -> SourcesResponse:
    """Get list of all anime sources with their status."""
    try:
        active_sources = rep.get_active_sources()
        disabled = set(settings.plugins.disabled_plugins)
        priority_order = settings.plugins.priority_order

        sources = []
        for i, source in enumerate(priority_order):
            # Check if source is actually registered
            if source in active_sources or source in disabled:
                sources.append(
                    SourceInfo(
                        name=source,
                        enabled=source not in disabled,
                        priority=i + 1,
                    )
                )

        # Add any active sources not in priority order
        for source in active_sources:
            if not any(s.name == source for s in sources):
                sources.append(
                    SourceInfo(
                        name=source,
                        enabled=True,
                        priority=len(sources) + 1,
                    )
                )

        return SourcesResponse(sources=sources)

    except Exception as e:
        logger.error(f"Failed to get sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/priority")
async def update_priority(request: SourcePriorityRequest) -> dict:
    """Update source priority order."""
    try:
        # Load current overrides
        overrides = load_user_settings_overrides()

        # Update priority order
        if "plugins" not in overrides:
            overrides["plugins"] = {}
        overrides["plugins"]["priority_order"] = request.order

        # Save
        save_user_settings_overrides(overrides)

        return {
            "success": True,
            "message": "Priority order updated. Restart server to apply.",
            "order": request.order,
        }

    except Exception as e:
        logger.error(f"Failed to update priority: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source}/enable")
async def enable_source(source: str) -> dict:
    """Enable a disabled source."""
    try:
        overrides = load_user_settings_overrides()

        if "plugins" not in overrides:
            overrides["plugins"] = {}
        if "disabled_plugins" not in overrides["plugins"]:
            overrides["plugins"]["disabled_plugins"] = list(settings.plugins.disabled_plugins)

        disabled = overrides["plugins"]["disabled_plugins"]
        if source in disabled:
            disabled.remove(source)
            save_user_settings_overrides(overrides)

        return {
            "success": True,
            "message": f"Source '{source}' enabled. Restart server to apply.",
        }

    except Exception as e:
        logger.error(f"Failed to enable source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source}/disable")
async def disable_source(source: str) -> dict:
    """Disable a source."""
    try:
        overrides = load_user_settings_overrides()

        if "plugins" not in overrides:
            overrides["plugins"] = {}
        if "disabled_plugins" not in overrides["plugins"]:
            overrides["plugins"]["disabled_plugins"] = list(settings.plugins.disabled_plugins)

        disabled = overrides["plugins"]["disabled_plugins"]
        if source not in disabled:
            disabled.append(source)
            save_user_settings_overrides(overrides)

        return {
            "success": True,
            "message": f"Source '{source}' disabled. Restart server to apply.",
        }

    except Exception as e:
        logger.error(f"Failed to disable source: {e}")
        raise HTTPException(status_code=500, detail=str(e))
