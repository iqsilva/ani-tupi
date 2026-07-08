"""FastAPI server for ani-tupi remote control.

Provides REST and WebSocket API for controlling anime playback from mobile devices.
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models.config import settings
from utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("🚀 Starting ani-tupi API server...")

    # Load scraper plugins
    from scrapers import loader

    loader.load_plugins()

    from services.repository import rep

    active_sources = rep.get_active_sources()
    logger.info(f"ℹ️  Fontes ativas: {', '.join(active_sources)}")

    yield

    # Shutdown
    logger.info("👋 Shutting down ani-tupi API server...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Ani-Tupi Remote Control",
        description="Control anime playback from your mobile device",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from api.routes import search_router, playback_router, history_router, sources_router

    app.include_router(search_router, prefix="/api")
    app.include_router(playback_router, prefix="/api")
    app.include_router(history_router, prefix="/api")
    app.include_router(sources_router, prefix="/api")

    # Serve static frontend files
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/")
        async def serve_frontend():
            """Serve the PWA frontend."""
            return FileResponse(frontend_dir / "index.html")

        @app.get("/manifest.json")
        async def serve_manifest():
            """Serve PWA manifest."""
            return FileResponse(frontend_dir / "manifest.json")

        @app.get("/sw.js")
        async def serve_service_worker():
            """Serve service worker."""
            return FileResponse(frontend_dir / "sw.js", media_type="application/javascript")

    # Health check endpoint
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        from services.repository import rep

        return {
            "status": "ok",
            "sources": rep.get_active_sources(),
            "version": "1.0.0",
        }

    return app


def start_server(host: str | None = None, port: int | None = None) -> None:
    """Start the API server.

    Args:
        host: Host address (default from settings)
        port: Port number (default from settings)
    """
    import uvicorn

    host = host or settings.api.host
    port = port or settings.api.port

    logger.info(f"🌐 Starting server at http://{host}:{port}")
    logger.info(f"📱 API docs: http://{host}:{port}/api/docs")

    uvicorn.run(
        "api.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )
