"""Routes package for API."""

from api.routes.search import router as search_router
from api.routes.playback import router as playback_router
from api.routes.history import router as history_router
from api.routes.sources import router as sources_router
from api.routes.settings import router as settings_router

__all__ = ["search_router", "playback_router", "history_router", "sources_router", "settings_router"]
