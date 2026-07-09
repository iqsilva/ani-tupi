"""Shared playback state for API.

Manages global playback state and WebSocket connections.
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from utils.logging import get_logger

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = get_logger(__name__)


@dataclass
class PlaybackStateManager:
    """Manages global playback state and WebSocket notifications."""

    # Current playback info
    is_playing: bool = False
    anime: str | None = None
    episode: int | None = None
    total_episodes: int | None = None
    source: str | None = None
    quality: str = "best"
    position: float = 0.0
    duration: float = 0.0
    paused: bool = False
    autoplay: bool = False
    volume: int = 100

    # MPV IPC socket path for control
    mpv_socket_path: str | None = None

    # WebSocket connections
    _connections: list["WebSocket"] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_dict(self) -> dict:
        """Convert state to dictionary for API responses."""
        return {
            "is_playing": self.is_playing,
            "anime": self.anime,
            "episode": self.episode,
            "total_episodes": self.total_episodes,
            "source": self.source,
            "quality": self.quality,
            "position": self.position,
            "duration": self.duration,
            "paused": self.paused,
            "autoplay": self.autoplay,
            "volume": self.volume,
        }

    async def add_connection(self, websocket: "WebSocket") -> None:
        """Add a WebSocket connection."""
        async with self._lock:
            self._connections.append(websocket)
        logger.debug(f"WebSocket connected. Total: {len(self._connections)}")

    async def remove_connection(self, websocket: "WebSocket") -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.debug(f"WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected WebSockets."""
        async with self._lock:
            dead_connections = []
            for ws in self._connections:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead_connections.append(ws)

            # Remove dead connections
            for ws in dead_connections:
                self._connections.remove(ws)

    async def broadcast_state(self) -> None:
        """Broadcast current playback state to all connections."""
        await self.broadcast({"type": "state", "data": self.to_dict()})

    def update(self, **kwargs) -> None:
        """Update state and schedule broadcast."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def reset(self) -> None:
        """Reset playback state to defaults."""
        self.is_playing = False
        self.anime = None
        self.episode = None
        self.total_episodes = None
        self.source = None
        self.quality = "best"
        self.position = 0.0
        self.duration = 0.0
        self.paused = False
        self.mpv_socket_path = None


# Global singleton
playback_state = PlaybackStateManager()
