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
from services.history_service import save_history
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
_current_playback_info: dict | None = None  # Store info for autoplay


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


async def _send_mpv_command_async(command: list) -> dict | None:
    """Async wrapper for _send_mpv_command: keeps a stuck MPV socket (up to 2s
    per call) from blocking the event loop."""
    return await asyncio.to_thread(_send_mpv_command, command)


async def _broadcast_status(message: str, error: bool = False) -> None:
    """Broadcast a loading/status phase to all WebSocket clients."""
    try:
        await playback_state.broadcast(
            {"type": "status", "data": {"message": message, "error": error}}
        )
    except Exception:
        pass


async def _poll_mpv_state():
    """Continuously poll MPV for playback position/duration and broadcast updates."""
    ticks = 0
    while playback_state.is_playing:
        if playback_state.mpv_socket_path:
            pos_resp = await _send_mpv_command_async(["get_property", "time-pos"])
            if pos_resp and "data" in pos_resp and pos_resp["data"] is not None:
                playback_state.position = pos_resp["data"]

            dur_resp = await _send_mpv_command_async(["get_property", "duration"])
            if dur_resp and "data" in dur_resp and dur_resp["data"] is not None:
                playback_state.duration = dur_resp["data"]

            pause_resp = await _send_mpv_command_async(["get_property", "pause"])
            if pause_resp and "data" in pause_resp:
                playback_state.paused = pause_resp["data"]

            await playback_state.broadcast_state()

            # Persist in-episode progress to history every ~30s
            ticks += 1
            if ticks % 30 == 0 and _current_playback_info and playback_state.position:
                info = _current_playback_info
                try:
                    save_history(
                        anime=info["anime"],
                        episode=info["episode"] - 1,
                        total_episodes=info["total_episodes"],
                        source=info.get("source"),
                        position=playback_state.position,
                        duration=playback_state.duration or None,
                    )
                except Exception as e:
                    logger.debug(f"Periodic history save failed: {e}")

        await asyncio.sleep(1)  # Poll every second


async def _autoplay_next_episode(info: dict) -> None:
    """Start the next episode automatically."""
    await _play_episode_offset(info, +1)


async def _play_episode_offset(info: dict, offset: int) -> None:
    """Start playback of the episode at info['episode'] + offset."""
    from api.schemas import PlaybackStartRequest

    target_episode = info["episode"] + offset
    request = PlaybackStartRequest(
        anime=info["anime"],
        episode=target_episode,
        season=info.get("season"),
        source=info.get("source"),
        quality=info.get("quality", "best"),
    )

    try:
        await start_playback(request)
    except Exception as e:
        logger.error(f"Autoplay failed: {e}")
        await playback_state.broadcast_state()


@router.get("/state", response_model=PlaybackState)
async def get_playback_state() -> PlaybackState:
    """Get current playback state."""
    # Update position/duration from MPV if playing
    if playback_state.is_playing and playback_state.mpv_socket_path:
        pos_resp = await _send_mpv_command_async(["get_property", "time-pos"])
        if pos_resp and "data" in pos_resp:
            playback_state.position = pos_resp["data"] or 0.0

        dur_resp = await _send_mpv_command_async(["get_property", "duration"])
        if dur_resp and "data" in dur_resp:
            playback_state.duration = dur_resp["data"] or 0.0

        pause_resp = await _send_mpv_command_async(["get_property", "pause"])
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
        # Ensure episodes are loaded (sync scraping → threadpool so the event
        # loop keeps serving requests and WebSocket updates)
        await _broadcast_status(f"Buscando fontes para '{request.anime}'...")
        await asyncio.to_thread(rep.search_episodes, request.anime)

        # Get episode list
        episodes = rep.get_episode_list(request.anime, season=request.season)
        if not episodes:
            await _broadcast_status("Nenhum episódio encontrado", error=True)
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

        # Reorder by preferred source if specified (preferred first, others as fallback)
        preferred_source = request.source
        if preferred_source:
            available = {src for _, src in sources_with_urls}
            if preferred_source not in available:
                logger.info(
                    f"Preferred source '{preferred_source}' unavailable for "
                    f"episode {request.episode}; falling back to priority order"
                )
                preferred_source = None

        # Get video URL via playback coordinator (use async version) with a
        # global deadline so a chain of slow sources can't hang the request
        from services.playback_coordinator import PlaybackCoordinator
        coordinator = PlaybackCoordinator(rep.sources)
        await _broadcast_status(f"Extraindo vídeo do episódio {request.episode}...")
        try:
            video_url, winning_source = await asyncio.wait_for(
                coordinator.search_player_with_source_async(
                    sources_with_urls,
                    request.anime,
                    request.episode,
                    preferred_source=preferred_source,
                ),
                timeout=60,
            )
        except (TimeoutError, asyncio.TimeoutError):
            await _broadcast_status("Tempo esgotado ao extrair vídeo", error=True)
            raise HTTPException(
                status_code=504,
                detail="Timed out extracting video URL (60s). Try again or pick another source.",
            )

        if not video_url:
            await _broadcast_status("Falha ao extrair vídeo das fontes", error=True)
            tried = ", ".join(sorted({src for _, src in sources_with_urls}))
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Nenhuma fonte conseguiu extrair o vídeo do episódio "
                    f"{request.episode} (tentadas: {tried})."
                ),
            )

        await _broadcast_status("Iniciando player...")

        # Use the source that actually produced the video URL; fall back to the
        # first candidate if unknown (e.g. legacy cache hit)
        source_name = winning_source or (
            sources_with_urls[0][1] if sources_with_urls else "unknown"
        )
        # Referrer must match the winning source's page URL (Cloudflare bypass)
        referrer = next(
            (url for url, src in sources_with_urls if src == source_name),
            sources_with_urls[0][0] if sources_with_urls else None,
        )

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

        # Store playback info for autoplay. The source preference (explicit
        # user choice, else the source that actually worked) is persisted to
        # history so the frontend can preselect it next time.
        global _current_playback_info
        _current_playback_info = {
            "anime": request.anime,
            "episode": request.episode,
            "total_episodes": len(episodes),
            "quality": request.quality,
            "season": request.season,
            "source": request.source or source_name,
        }

        # Get the current event loop to schedule callbacks from thread
        loop = asyncio.get_event_loop()

        # Start playback in background thread
        def play_in_background():
            global _mpv_process, _current_playback_info
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

            # Playback ended - save to history (with last known in-episode progress)
            info = _current_playback_info
            if info:
                try:
                    save_history(
                        anime=info["anime"],
                        episode=info["episode"] - 1,  # Convert to 0-indexed
                        total_episodes=info["total_episodes"],
                        source=info.get("source"),
                        position=playback_state.position or None,
                        duration=playback_state.duration or None,
                    )
                    logger.info(f"History saved: {info['anime']} ep {info['episode']}")
                except Exception as e:
                    logger.error(f"Failed to save history: {e}")

            # Check for autoplay
            should_autoplay = (
                playback_state.autoplay
                and info
                and info["episode"] < info["total_episodes"]
            )

            playback_state.reset()
            
            try:
                if should_autoplay:
                    # Schedule next episode
                    next_ep = info["episode"] + 1
                    logger.info(f"Autoplay: starting episode {next_ep}")
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(_autoplay_next_episode(info))
                    )
                else:
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
        await _broadcast_status("Erro ao iniciar reprodução", error=True)
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
            # Save current episode to history and start next
            if _current_playback_info:
                info = _current_playback_info
                try:
                    save_history(
                        anime=info["anime"],
                        episode=info["episode"] - 1,  # Convert to 0-indexed
                        total_episodes=info["total_episodes"],
                        source=info.get("source"),
                        position=playback_state.position or None,
                        duration=playback_state.duration or None,
                    )
                    logger.info(f"History saved: {info['anime']} ep {info['episode']}")
                except Exception as e:
                    logger.error(f"Failed to save history: {e}")
                
                # Check if there's a next episode
                if info["episode"] < info["total_episodes"]:
                    # Stop current playback and start next
                    await stop_playback_internal()
                    await _autoplay_next_episode(info)
                    return PlaybackResponse(
                        success=True,
                        message=f"Starting episode {info['episode'] + 1}",
                        state=PlaybackState(**playback_state.to_dict()),
                    )
                else:
                    msg = "No more episodes"
            else:
                msg = "No playback info available"

        elif action == "previous":
            # Start the previous episode (mirrors 'next')
            if _current_playback_info:
                info = _current_playback_info
                if info["episode"] > 1:
                    await stop_playback_internal()
                    await _play_episode_offset(info, -1)
                    return PlaybackResponse(
                        success=True,
                        message=f"Starting episode {info['episode'] - 1}",
                        state=PlaybackState(**playback_state.to_dict()),
                    )
                else:
                    msg = "Already at first episode"
            else:
                msg = "No playback info available"

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
