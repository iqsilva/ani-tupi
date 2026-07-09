"""Playback control API routes with WebSocket support."""

import asyncio
import json
import socket
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.schemas import (
    PlaybackControlRequest,
    PlaybackResponse,
    PlaybackStartRequest,
    PlaybackState,
)
from api.state import playback_state
from services.repository import rep
from utils.logging import get_logger
from utils.video_player import VideoPlayer

logger = get_logger(__name__)

router = APIRouter(prefix="/playback", tags=["playback"])

# Global video player instance
_player: VideoPlayer | None = None
_playback_thread: threading.Thread | None = None
_mpv_process: subprocess.Popen | None = None
_state_polling_task: asyncio.Task | None = None


def _get_player() -> VideoPlayer:
    """Get or create video player instance."""
    global _player
    if _player is None:
        _player = VideoPlayer(autoplay=playback_state.autoplay)
    return _player


def _send_mpv_command(command: list) -> dict | None:
    """Send command to MPV via IPC socket.

    Args:
        command: MPV IPC command as list (e.g., ["get_property", "time-pos"])

    Returns:
        Response dict or None if failed
    """
    socket_path = playback_state.mpv_socket_path
    if not socket_path:
        return None

    try:
        # Unix socket for Linux/macOS
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(socket_path)

        # Send command as JSON
        msg = json.dumps({"command": command}) + "\n"
        sock.sendall(msg.encode())

        # Read response
        response = sock.recv(4096).decode()
        sock.close()

        return json.loads(response)

    except Exception as e:
        logger.debug(f"MPV IPC error: {e}")
        return None


async def _poll_mpv_state():
    """Continuously poll MPV for playback position/duration and broadcast updates."""
    while playback_state.is_playing:
        if playback_state.mpv_socket_path:
            pos_resp = _send_mpv_command(["get_property", "time-pos"])
            if pos_resp and "data" in pos_resp and pos_resp["data"] is not None:
                playback_state.position = pos_resp["data"]

            dur_resp = _send_mpv_command(["get_property", "duration"])
            if dur_resp and "data" in dur_resp and dur_resp["data"] is not None:
                playback_state.duration = dur_resp["data"]

            pause_resp = _send_mpv_command(["get_property", "pause"])
            if pause_resp and "data" in pause_resp:
                playback_state.paused = pause_resp["data"]

            await playback_state.broadcast_state()

        await asyncio.sleep(1)  # Poll every second


@router.get("/state", response_model=PlaybackState)
async def get_playback_state() -> PlaybackState:
    """Get current playback state."""
    # Update position/duration from MPV if playing
    if playback_state.is_playing and playback_state.mpv_socket_path:
        pos_resp = _send_mpv_command(["get_property", "time-pos"])
        if pos_resp and "data" in pos_resp:
            playback_state.position = pos_resp["data"] or 0.0

        dur_resp = _send_mpv_command(["get_property", "duration"])
        if dur_resp and "data" in dur_resp:
            playback_state.duration = dur_resp["data"] or 0.0

        pause_resp = _send_mpv_command(["get_property", "pause"])
        if pause_resp and "data" in pause_resp:
            playback_state.paused = pause_resp["data"]

    return PlaybackState(**playback_state.to_dict())


@router.post("/start", response_model=PlaybackResponse)
async def start_playback(request: PlaybackStartRequest) -> PlaybackResponse:
    """Start playing an episode.

    This will:
    1. Search for episodes if not loaded
    2. Get video URL from the scraper
    3. Launch MPV with IPC support
    4. Update playback state
    """
    global _playback_thread, _mpv_process

    # Stop any existing playback
    if playback_state.is_playing:
        await stop_playback_internal()

    try:
        # Ensure episodes are loaded
        rep.search_episodes(request.anime)

        # Get episode list
        episodes = rep.get_episode_list(request.anime, season=request.season)
        if not episodes:
            raise HTTPException(
                status_code=404,
                detail=f"No episodes found for '{request.anime}'",
            )

        if request.episode > len(episodes):
            raise HTTPException(
                status_code=400,
                detail=f"Episode {request.episode} not available. Max: {len(episodes)}",
            )

        # Get all available sources for this episode
        sources_with_urls = rep.get_all_episode_sources(request.anime, request.episode)

        if not sources_with_urls:
            raise HTTPException(
                status_code=404,
                detail=f"No sources available for episode {request.episode}",
            )

        # Filter by preferred source if specified
        if request.source:
            sources_with_urls = [
                (url, src) for url, src in sources_with_urls if src == request.source
            ]
            if not sources_with_urls:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source '{request.source}' not available for this episode",
                )

        # Get video URL via playback coordinator (use async version)
        from services.playback_coordinator import PlaybackCoordinator
        coordinator = PlaybackCoordinator(rep.sources)
        video_url = await coordinator.search_player_async(
            sources_with_urls, request.anime, request.episode
        )

        if not video_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to extract video URL from sources",
            )

        # Get referrer from the source URL (needed to bypass Cloudflare)
        source_name = sources_with_urls[0][1] if sources_with_urls else "unknown"
        referrer = sources_with_urls[0][0] if sources_with_urls else None

        # Update state before starting playback
        playback_state.update(
            is_playing=True,
            anime=request.anime,
            episode=request.episode,
            total_episodes=len(episodes),
            source=source_name,
            quality=request.quality,
            paused=False,
            position=0.0,
        )

        # Create a predictable socket path for IPC control
        import tempfile
        socket_path = str(Path(tempfile.gettempdir()) / "ani-tupi-api-mpv.sock")
        playback_state.mpv_socket_path = socket_path

        # Get the current event loop to schedule callbacks from thread
        loop = asyncio.get_event_loop()

        # Start playback in background thread
        def play_in_background():
            global _mpv_process
            player = _get_player()
            player.set_autoplay_state(playback_state.autoplay)

            # Use our fixed socket path
            player._api_socket_path = socket_path

            result = player.play_episode(
                url=video_url,
                anime_title=request.anime,
                episode_number=request.episode,
                total_episodes=len(episodes),
                source=source_name,
                use_ipc=True,
                max_quality=request.quality,
                referrer=referrer,
            )

            # Playback ended - schedule broadcast on main event loop
            playback_state.reset()
            try:
                loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(playback_state.broadcast_state())
                )
            except RuntimeError:
                # Event loop closed, ignore
                pass

        _playback_thread = threading.Thread(target=play_in_background, daemon=True)
        _playback_thread.start()

        # Wait a moment for MPV to start
        await asyncio.sleep(0.5)

        # Start state polling task
        global _state_polling_task
        if _state_polling_task:
            _state_polling_task.cancel()
        _state_polling_task = asyncio.create_task(_poll_mpv_state())

        # Broadcast state update
        await playback_state.broadcast_state()

        return PlaybackResponse(
            success=True,
            message=f"Playing {request.anime} - Episode {request.episode}",
            state=PlaybackState(**playback_state.to_dict()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start playback: {e}")
        playback_state.reset()
        raise HTTPException(status_code=500, detail=str(e))


async def stop_playback_internal() -> None:
    """Internal function to stop playback."""
    global _state_polling_task

    # Stop polling task
    if _state_polling_task:
        _state_polling_task.cancel()
        _state_polling_task = None

    if playback_state.mpv_socket_path:
        _send_mpv_command(["quit"])
        await asyncio.sleep(0.3)

    playback_state.reset()
    await playback_state.broadcast_state()


@router.post("/control", response_model=PlaybackResponse)
async def control_playback(request: PlaybackControlRequest) -> PlaybackResponse:
    """Control playback (pause, resume, seek, volume, next, previous)."""
    if not playback_state.is_playing:
        return PlaybackResponse(
            success=False,
            message="Nothing is playing",
            state=PlaybackState(**playback_state.to_dict()),
        )

    action = request.action
    value = request.value

    try:
        if action == "pause":
            _send_mpv_command(["set_property", "pause", True])
            playback_state.paused = True
            msg = "Paused"

        elif action == "resume":
            _send_mpv_command(["set_property", "pause", False])
            playback_state.paused = False
            msg = "Resumed"

        elif action == "stop":
            await stop_playback_internal()
            return PlaybackResponse(
                success=True,
                message="Playback stopped",
                state=PlaybackState(**playback_state.to_dict()),
            )

        elif action == "seek":
            if value is None:
                raise HTTPException(status_code=400, detail="Seek requires value (seconds)")
            _send_mpv_command(["seek", value, "absolute"])
            playback_state.position = value
            msg = f"Seeked to {value:.1f}s"

        elif action == "volume":
            if value is None:
                raise HTTPException(status_code=400, detail="Volume requires value (0-100)")
            _send_mpv_command(["set_property", "volume", value])
            playback_state.volume = int(value)
            msg = f"Volume set to {int(value)}%"

        elif action == "next":
            # Trigger next episode via MPV IPC
            _send_mpv_command(["script-message", "mark-next"])
            msg = "Next episode"

        elif action == "previous":
            # Trigger previous episode via MPV IPC
            _send_mpv_command(["script-message", "previous"])
            msg = "Previous episode"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        await playback_state.broadcast_state()

        return PlaybackResponse(
            success=True,
            message=msg,
            state=PlaybackState(**playback_state.to_dict()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Control failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autoplay", response_model=PlaybackResponse)
async def toggle_autoplay(enabled: bool | None = None) -> PlaybackResponse:
    """Toggle or set autoplay state."""
    if enabled is not None:
        playback_state.autoplay = enabled
    else:
        playback_state.autoplay = not playback_state.autoplay

    # Update player if exists
    if _player:
        _player.set_autoplay_state(playback_state.autoplay)

    await playback_state.broadcast_state()

    return PlaybackResponse(
        success=True,
        message=f"Autoplay {'enabled' if playback_state.autoplay else 'disabled'}",
        state=PlaybackState(**playback_state.to_dict()),
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time playback state updates.

    Clients receive state updates whenever playback state changes.
    """
    await websocket.accept()
    await playback_state.add_connection(websocket)

    try:
        # Send initial state
        await websocket.send_text(
            json.dumps({"type": "state", "data": playback_state.to_dict()})
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)

                # Handle ping/pong for keepalive
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(
                    json.dumps({"type": "state", "data": playback_state.to_dict()})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        await playback_state.remove_connection(websocket)
