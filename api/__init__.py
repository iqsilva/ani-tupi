"""Remote control API for ani-tupi.

Provides REST and WebSocket endpoints for controlling playback from mobile devices.
"""

from api.server import create_app, start_server

__all__ = ["create_app", "start_server"]
