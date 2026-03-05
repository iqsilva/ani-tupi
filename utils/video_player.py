from typing import NamedTuple, Optional

import os
import platform
import socket
import subprocess
import tempfile
import uuid
import json
import time
from pathlib import Path

from models.models import SkipTimes


class VideoPlaybackResult(NamedTuple):
    """Result of video playback with optional navigation data.

    Attributes:
        exit_code: MPV exit code (0=normal, 2=error, 3=abort)
        action: Action triggered by keybinding ("quit", "next", "previous", "mark-menu", "reload", "toggle-autoplay", "toggle-sub-dub")
        data: Optional metadata about the action (e.g., next episode URL, episode number)
    """

    exit_code: int
    action: str = "quit"
    data: dict | None = None


class VideoPlayer:
    """Manager for video playback using MPV with IPC support."""

    def __init__(self, autoplay: bool = False):
        """Initialize VideoPlayer with session state.

        Args:
            autoplay: Whether to automatically play the next episode when current finishes
        """
        self.autoplay = autoplay

    def get_autoplay_state(self) -> bool:
        """Get current auto-play state."""
        return self.autoplay

    def set_autoplay_state(self, enabled: bool) -> None:
        """Set auto-play state."""
        self.autoplay = enabled

    def play_episode(
        self,
        url: str,
        anime_title: str,
        episode_number: int,
        total_episodes: int,
        source: str,
        use_ipc: bool = True,
        debug: bool = False,
        anilist_id: int | None = None,
        anilist_episodes: int | None = None,
        mal_id: int | None = None,
        skip_times: Optional[SkipTimes] = None,
    ) -> VideoPlaybackResult:
        """Play a single episode with optional IPC support for episode navigation.

        Args:
            url: Video URL to play
            anime_title: Name of anime being watched
            episode_number: Current episode number (1-indexed)
            total_episodes: Total episodes available in scraper
            source: Name of scraper source (e.g., "animefire")
            use_ipc: Enable IPC socket for keybinding events (default True)
            debug: Skip playback and return simulated result
            anilist_id: AniList ID for syncing progress (optional)
            anilist_episodes: Total episodes from AniList (optional, for display)
            mal_id: MyAnimeList ID for AniSkip integration (optional)

        Returns:
            VideoPlaybackResult with exit code, action, and optional data
        """
        # Check if IPC should be disabled globally
        if os.environ.get("ANI_TUPI_DISABLE_IPC") == "1":
            use_ipc = False

        if debug:
            print("DEBUG MODE: Skipping video playback")
            return VideoPlaybackResult(exit_code=0, action="quit", data=None)

        if not use_ipc:
            # Use legacy blocking playback
            return self._play_video_legacy(url, debug=False)

        # Try IPC-based playback with fallback
        input_conf_path = None
        socket_path = None
        mpv_process = None

        # Episode context passed to IPC handlers
        episode_context = {
            "anime_title": anime_title,
            "episode_number": episode_number,
            "total_episodes": total_episodes,
            "anilist_episodes": anilist_episodes,
            "source": source,
            "url": url,
            "anilist_id": anilist_id,
            "mal_id": mal_id,
            "skip_cache": {},
            "skip_lua_path": str(self._get_skip_lua_path()),
        }

        try:
            # Generate socket path and input.conf
            socket_path = self._create_ipc_socket_path()
            input_conf_path, _ = self._generate_input_conf()

            # Launch MPV with IPC
            mpv_process = self._launch_mpv_with_ipc(
                url,
                socket_path,
                input_conf_path,
                skip_times,
                anime_title=anime_title,
                episode_number=episode_number,
            )

            # Start monitoring events
            result = self._ipc_event_loop(mpv_process, socket_path, episode_context)

            # Wait for process to finish if still running
            if mpv_process.poll() is None:
                try:
                    mpv_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    mpv_process.terminate()

            return result

        except (FileNotFoundError, OSError, Exception) as e:
            # IPC launch failed, fallback to legacy
            print(f"⚠️  IPC playback unavailable: {e}. Using legacy mode.")

            # Clean up any dangling process
            if mpv_process and mpv_process.poll() is None:
                try:
                    mpv_process.terminate()
                    mpv_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    mpv_process.kill()

            return self._play_video_legacy(url, debug=False)

        finally:
            # Clean up temporary files
            if input_conf_path:
                try:
                    Path(input_conf_path).unlink()
                except OSError:
                    pass

            if socket_path:
                self._cleanup_ipc_socket(socket_path)

    def _play_video_legacy(self, url: str, debug: bool = False) -> VideoPlaybackResult:
        """Play video using legacy python-mpv blocking mode (fallback)."""
        if debug:
            print("DEBUG MODE: Skipping video playback")
            return VideoPlaybackResult(exit_code=0, action="quit", data=None)

        try:
            exit_code = self.play_video_raw(url, debug=False)
            return VideoPlaybackResult(exit_code=exit_code, action="quit", data=None)
        except Exception as e:
            print(f"⚠️  Playback error: {e}")
            return VideoPlaybackResult(exit_code=2, action="quit", data=None)

    def play_video_raw(self, url: str, debug=False, ytdl_format: str | None = None) -> int:
        """Play video using python-mpv and return exit code."""
        if debug:
            print("DEBUG MODE: Skipping video playback")
            return 0

        import mpv

        # Generate custom ani-tupi keybindings
        input_conf_path, _ = self._generate_input_conf()

        player = None
        try:
            # Create MPV instance with current settings
            player = mpv.MPV(
                fullscreen=True,
                cursor_autohide_fs_only=True,
                log_handler=print,
                ytdl=True,
                ytdl_format=ytdl_format or "bestvideo[height<=1080]+bestaudio/best",
                ytdl_raw_options="concurrent-fragments=5",
                cache=True,
                demuxer_max_bytes="400M",
                demuxer_max_back_bytes="100M",
                demuxer_readahead_secs=40,
                stream_buffer_size="2M",
                speed=1.8,  # Default playback speed
                input_default_bindings=True,  # Enable default key bindings
                input_vo_keyboard=True,  # Handle keyboard input on video output
                input_conf=input_conf_path,  # Use custom ani-tupi keybindings
                osc=True,  # On-screen controller for mouse interaction
            )

            # Start playback (blocking)
            player.play(url)
            player.wait_for_playback()

            return 0  # Normal playback completion

        except mpv.ShutdownError:
            # User aborted (Ctrl+C or window close)
            return 3
        except FileNotFoundError as e:
            msg = "Error: 'mpv' is not installed or not found in the system PATH."
            raise OSError(msg) from e
        except Exception as e:
            # Playback error
            print(f"⚠️  MPV error: {e}")
            return 2
        finally:
            # Clean up player instance
            try:
                if player is not None:
                    player.terminate()
            except OSError:
                pass

            # Clean up temporary input.conf file
            if input_conf_path:
                try:
                    Path(input_conf_path).unlink()
                except OSError:
                    pass

    def _create_ipc_socket_path(self) -> str:
        """Generate platform-specific IPC socket path for MPV communication."""
        unique_id = str(uuid.uuid4())[:8]
        system = platform.system()

        if system == "Windows":
            return f"\\\\.\\pipe\\ani-tupi-mpv-{unique_id}"
        else:
            temp_dir = tempfile.gettempdir()
            return str(Path(temp_dir) / f"ani-tupi-mpv-{unique_id}.sock")

    def _get_skip_lua_path(self) -> Path:
        """Get path to bundled skip.lua script.

        Returns:
            Path to skip.lua in utils/mpv_scripts/
        """
        # Get path relative to this file
        current_file = Path(__file__)
        return current_file.parent / "mpv_scripts" / "skip.lua"

    def _create_chapters_file(self, skip_times: "SkipTimes") -> str | None:
        """Create temporary chapters file for MPV timeline markers.

        Args:
            skip_times: Skip times for intro/outro

        Returns:
            Path to temporary chapters file, or None if creation fails
        """
        try:
            # Create chapters in MPV format
            chapters = []

            if skip_times.op_start is not None and skip_times.op_end is not None:
                # Add OP markers
                chapters.append(f"CHAPTER01={self._format_time(skip_times.op_start)}")
                chapters.append("CHAPTER01NAME=Opening Start")
                chapters.append(f"CHAPTER02={self._format_time(skip_times.op_end)}")
                chapters.append("CHAPTER02NAME=Opening End")

            if skip_times.ed_start is not None and skip_times.ed_end is not None:
                # Add ED markers (chapter numbers continue)
                chapter_num = 3 if chapters else 1
                chapters.append(
                    f"CHAPTER{chapter_num:02d}={self._format_time(skip_times.ed_start)}"
                )
                chapters.append(f"CHAPTER{chapter_num:02d}NAME=Ending Start")
                chapters.append(
                    f"CHAPTER{chapter_num + 1:02d}={self._format_time(skip_times.ed_end)}"
                )
                chapters.append(f"CHAPTER{chapter_num + 1:02d}NAME=Ending End")

            if not chapters:
                return None

            # Write to temporary file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="ani-tupi-chapters-",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write("\n".join(chapters))
                return f.name

        except Exception:
            return None

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MPV chapter time format (HH:MM:SS.mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def _cleanup_ipc_socket(self, path: str) -> None:
        """Clean up IPC socket file/pipe without errors."""
        if not path:
            return

        try:
            socket_path = Path(path)
            if socket_path.exists():
                socket_path.unlink()
        except (OSError, FileNotFoundError):
            pass

    def _generate_input_conf(self) -> tuple[str, str]:
        """Generate temporary MPV input.conf with custom IPC keybindings."""
        input_conf_content = """# ani-tupi IPC Keybindings Configuration
# Auto-generated for episode navigation

# Next Episode (mark watched, move to next)
shift+n script-message mark-next

# Previous Episode (go to previous, resume from saved position)
shift+p script-message previous

# Mark & Menu (mark watched, show menu: next/continue/quit)
shift+m script-message mark-menu

# Reload Current Episode (retry same episode)
shift+r script-message reload-episode

# Toggle Auto-play (skip episode selection for next episode)
shift+a script-message toggle-autoplay

# Toggle Subtitle/Dub (switch if available)
shift+t script-message toggle-sub-dub
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".conf",
            prefix="ani-tupi-input-",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(input_conf_content)
            temp_path = f.name

        return temp_path, input_conf_content

    def _handle_keybinding_action(
        self,
        action: str,
        context: dict,
    ) -> VideoPlaybackResult | None:
        """Handle keybinding action from MPV and return navigation result."""
        match action:
            case "mark-next":
                return VideoPlaybackResult(
                    exit_code=0,
                    action="next",
                    data={"episode": context.get("episode_number", 0) + 1},
                )
            case "previous":
                return VideoPlaybackResult(
                    exit_code=0,
                    action="previous",
                    data={"episode": max(1, context.get("episode_number", 1) - 1)},
                )
            case "mark-menu":
                return VideoPlaybackResult(
                    exit_code=0,
                    action="mark-menu",
                    data={"episode": context.get("episode_number", 0)},
                )
            case "reload-episode":
                return VideoPlaybackResult(
                    exit_code=0,
                    action="reload",
                    data={"episode": context.get("episode_number", 0)},
                )
            case "toggle-autoplay":
                self.autoplay = not self.autoplay
                return VideoPlaybackResult(
                    exit_code=0,
                    action="toggle-autoplay",
                    data={"enabled": self.autoplay},
                )
            case "toggle-sub-dub":
                return VideoPlaybackResult(
                    exit_code=0,
                    action="toggle-sub-dub",
                    data={"message": "Sub/Dub toggle (if available)"},
                )
            case _:
                return None

    def _launch_mpv_with_ipc(
        self,
        url: str,
        socket_path: str,
        input_conf: str,
        skip_times: Optional[SkipTimes] = None,
        anime_title: str | None = None,
        episode_number: int | None = None,
    ) -> subprocess.Popen:
        """Launch MPV process with IPC socket support.

        Args:
            url: Video URL to play
            socket_path: Path to IPC socket
            input_conf: Path to input.conf file
            skip_times: Optional skip times for intro/outro skipping
            anime_title: Anime title for window title
            episode_number: Episode number for window title
            source: Source name for window title

        Returns:
            MPV subprocess handle
        """
        mpv_args = [
            "mpv",
            f"--input-ipc-server={socket_path}",
            f"--input-conf={input_conf}",
            "--fullscreen=yes",
            "--osc=yes",
            "--cache=yes",
            "--demuxer-max-bytes=400M",
            "--demuxer-max-back-bytes=100M",
            "--demuxer-readahead-secs=40",
            "--stream-buffer-size=2M",
            "--speed=1.8",
            "--ytdl=yes",
            "--ytdl-format=bestvideo[height<=1080]+bestaudio/best",
        ]

        if anime_title and episode_number:
            media_title = f"{anime_title} Episode {episode_number}"
            mpv_args.append(f"--force-media-title={media_title}")

        # Add skip.lua script if skip times are available
        if skip_times:
            skip_lua_path = self._get_skip_lua_path()

            if skip_lua_path.exists():
                print(f"   📝 Carregando script de skip: {skip_lua_path.name}")
                mpv_args.append(f"--script={skip_lua_path}")

                # Build script-opts string
                script_opts = []
                if skip_times.op_start is not None and skip_times.op_end is not None:
                    script_opts.append(f"skip-op_start={skip_times.op_start}")
                    script_opts.append(f"skip-op_end={skip_times.op_end}")
                if skip_times.ed_start is not None and skip_times.ed_end is not None:
                    script_opts.append(f"skip-ed_start={skip_times.ed_start}")
                    script_opts.append(f"skip-ed_end={skip_times.ed_end}")

                if script_opts:
                    script_opts_str = ",".join(script_opts)
                    mpv_args.append(f"--script-opts={script_opts_str}")
                    print("   🎬 Script configurado com os tempos de skip")

                # Create chapters file for visual markers
                chapters_file = self._create_chapters_file(skip_times)
                if chapters_file:
                    mpv_args.append(f"--chapters-file={chapters_file}")
                    print("   📌 Marcadores de tempo adicionados à timeline")
            else:
                print(f"   ⚠️  Script de skip não encontrado em {skip_lua_path}")

        mpv_args.append(url)

        try:
            debug_mode = os.environ.get("ANI_TUPI_DEBUG_MPV") == "1"
            if debug_mode:
                return subprocess.Popen(
                    mpv_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            else:
                return subprocess.Popen(
                    mpv_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
        except FileNotFoundError as e:
            raise FileNotFoundError("MPV not found in PATH. Please install mpv.") from e
        except Exception as e:
            raise OSError(f"Failed to launch MPV: {e}") from e

    def _fetch_skip_times_for_episode(
        self,
        mal_id: int | None,
        episode_number: int,
        skip_cache: dict,
    ) -> Optional["SkipTimes"]:
        """Fetch skip times for a specific episode dynamically.

        This method is called when the user navigates to a new episode during
        playback. It fetches skip times asynchronously without blocking the player.

        Args:
            mal_id: MyAnimeList ID for the anime
            episode_number: Episode number to fetch skip times for (1-indexed)
            skip_cache: Cache dict mapping episode_number → SkipTimes

        Returns:
            SkipTimes object if available, None otherwise
        """
        if not mal_id:
            return None

        # Check cache first
        if episode_number in skip_cache:
            return skip_cache[episode_number]

        try:
            from services.anime.aniskip_service import AniSkipService

            aniskip = AniSkipService()
            skip_times = aniskip.get_skip_times(mal_id, episode_number)

            # Cache the result (even if None)
            skip_cache[episode_number] = skip_times

            if skip_times:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(
                    f"Fetched skip times for episode {episode_number}: "
                    f"OP={skip_times.op_start}-{skip_times.op_end}, "
                    f"ED={skip_times.ed_start}-{skip_times.ed_end}"
                )

            return skip_times

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to fetch skip times for episode {episode_number}: {e}")
            return None

    def _ipc_event_loop(
        self,
        mpv_process: subprocess.Popen,
        socket_path: str,
        episode_context: dict,
        timeout: float = 1.0,
    ) -> VideoPlaybackResult:
        """Monitor IPC socket for keybinding events from MPV."""
        # Wait for socket to be ready
        max_wait = 5.0
        start_time = time.time()
        sock = None

        while time.time() - start_time < max_wait:
            try:
                if platform.system() == "Windows":
                    # Fallback to legacy on Windows for now
                    return self._play_video_legacy("", debug=False)

                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect(socket_path)
                break
            except (FileNotFoundError, ConnectionRefusedError, OSError):
                time.sleep(0.1)
                continue

        if not sock:
            return self._play_video_legacy("", debug=False)

        try:
            buffer = ""
            while mpv_process.poll() is None:
                try:
                    chunk = sock.recv(1024).decode("utf-8", errors="ignore")
                    if not chunk:
                        break
                    buffer += chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if not line.strip():
                            continue

                        try:
                            msg = json.loads(line)
                            if msg.get("event") == "client-message":
                                args = msg.get("args", [])
                                if args:
                                    action = args[0]
                                    if action == "mark-next":
                                        from services.history_service import (
                                            save_history_from_event,
                                        )
                                        from services.repository import rep

                                        anime_title = episode_context.get("anime_title")
                                        episode_number = episode_context.get("episode_number", 1)
                                        source = episode_context.get("source")
                                        anilist_id = episode_context.get("anilist_id")

                                        if not anime_title:
                                            continue

                                        episode_idx = episode_number - 1
                                        save_history_from_event(
                                            anime_title=anime_title,
                                            episode_idx=episode_idx,
                                            action="watched",
                                            source=source,
                                            anilist_id=anilist_id,
                                        )

                                        next_episode_number = episode_number + 1
                                        scraper_total = episode_context.get("total_episodes")
                                        anilist_total = episode_context.get("anilist_episodes")
                                        progress_str = _format_episode_progress(
                                            next_episode_number,
                                            scraper_total,
                                            anilist_total,
                                        )
                                        self._send_mpv_command(
                                            sock,
                                            "show-text",
                                            [f"Buscando Episódio {progress_str}..."],
                                        )
                                        next_url = rep.search_player(
                                            anime_title, next_episode_number
                                        )

                                        if next_url:
                                            self._send_mpv_command(
                                                sock, "loadfile", [next_url, "replace"]
                                            )
                                            self._send_mpv_command(
                                                sock,
                                                "show-text",
                                                [f"▶️ Reproduzindo Episódio {progress_str}"],
                                            )
                                            # Update MPV title to show new episode number
                                            new_title = (
                                                f"{anime_title} Episode {next_episode_number}"
                                            )
                                            self._send_mpv_command(
                                                sock,
                                                "set_property",
                                                ["force-media-title", new_title],
                                            )
                                            episode_context["episode_number"] = next_episode_number
                                            episode_context["url"] = next_url
                                            print(f"▶️  Reproduzindo Episódio {progress_str}")

                                            # Fetch skip times dynamically for next episode
                                            mal_id = episode_context.get("mal_id")
                                            skip_cache = episode_context.get("skip_cache", {})
                                            skip_lua_path = episode_context.get("skip_lua_path")

                                            # If mal_id is None, try to discover it
                                            if not mal_id and anime_title:
                                                from services.anime.anilist_discovery_service import (
                                                    discover_anilist_info,
                                                )

                                                try:
                                                    result = discover_anilist_info(anime_title)
                                                    if result.found:
                                                        mal_id = result.mal_id
                                                        episode_context["mal_id"] = mal_id
                                                except Exception:
                                                    pass

                                            if mal_id:
                                                print(
                                                    f"Fetching skip times for ep {next_episode_number}: mal_id={mal_id}, cache={skip_cache}"
                                                )
                                                skip_times = self._fetch_skip_times_for_episode(
                                                    mal_id, next_episode_number, skip_cache
                                                )
                                                if skip_times and skip_lua_path:
                                                    if self._update_skip_lua_with_times(
                                                        skip_lua_path, skip_times
                                                    ):
                                                        self._send_mpv_command(
                                                            sock,
                                                            "show-text",
                                                            ["⏭️ Skip times carregados", "3000"],
                                                        )

                                            continue
                                        else:
                                            self._send_mpv_command(
                                                sock,
                                                "show-text",
                                                [
                                                    "Não há mais episódios disponíveis ou erro ao buscar"
                                                ],
                                            )
                                            print(
                                                f"❌ Falha ao carregar Episódio {next_episode_number}"
                                            )

                                    elif action == "previous":
                                        from services.repository import rep

                                        anime_title = episode_context.get("anime_title")
                                        episode_number = episode_context.get("episode_number", 1)

                                        if not anime_title:
                                            continue

                                        prev_episode_number = max(1, episode_number - 1)
                                        if prev_episode_number < episode_number:
                                            scraper_total = episode_context.get("total_episodes")
                                            anilist_total = episode_context.get("anilist_episodes")
                                            progress_str = _format_episode_progress(
                                                prev_episode_number,
                                                scraper_total,
                                                anilist_total,
                                            )
                                            self._send_mpv_command(
                                                sock,
                                                "show-text",
                                                [f"Buscando Episódio {progress_str}..."],
                                            )
                                            prev_url = rep.search_player(
                                                anime_title, prev_episode_number
                                            )

                                            if prev_url:
                                                self._send_mpv_command(
                                                    sock,
                                                    "loadfile",
                                                    [prev_url, "replace"],
                                                )
                                                self._send_mpv_command(
                                                    sock,
                                                    "show-text",
                                                    [f"⏪ Voltando para Episódio {progress_str}"],
                                                )
                                                # Update MPV title to show new episode number
                                                new_title = (
                                                    f"{anime_title} Episode {prev_episode_number}"
                                                )
                                                self._send_mpv_command(
                                                    sock,
                                                    "set_property",
                                                    ["force-media-title", new_title],
                                                )
                                                episode_context["episode_number"] = (
                                                    prev_episode_number
                                                )
                                                episode_context["url"] = prev_url
                                                print(f"⏪ Voltando para Episódio {progress_str}")

                                                # Fetch skip times dynamically for previous episode
                                                mal_id = episode_context.get("mal_id")
                                                skip_cache = episode_context.get("skip_cache", {})
                                                skip_lua_path = episode_context.get("skip_lua_path")

                                                # If mal_id is None, try to discover it
                                                if not mal_id and anime_title:
                                                    from services.anime.anilist_discovery_service import (
                                                        discover_anilist_info,
                                                    )

                                                    try:
                                                        result = discover_anilist_info(anime_title)
                                                        if result.found:
                                                            mal_id = result.mal_id
                                                            episode_context["mal_id"] = mal_id
                                                    except Exception:
                                                        pass

                                                if mal_id:
                                                    print(
                                                        f"Fetching skip times for ep {prev_episode_number}: mal_id={mal_id}, cache={skip_cache}"
                                                    )
                                                    skip_times = self._fetch_skip_times_for_episode(
                                                        mal_id, prev_episode_number, skip_cache
                                                    )
                                                    if skip_times and skip_lua_path:
                                                        if self._update_skip_lua_with_times(
                                                            skip_lua_path, skip_times
                                                        ):
                                                            self._send_mpv_command(
                                                                sock,
                                                                "show-text",
                                                                ["⏭️ Skip times carregados", "3000"],
                                                            )

                                                continue
                                            else:
                                                self._send_mpv_command(
                                                    sock,
                                                    "show-text",
                                                    [
                                                        "Episódio anterior não disponível ou erro ao buscar"
                                                    ],
                                                )
                                                print(
                                                    f"❌ Falha ao carregar Episódio {prev_episode_number}"
                                                )
                                        else:
                                            self._send_mpv_command(
                                                sock,
                                                "show-text",
                                                ["Não há episódios anteriores"],
                                            )

                                    elif action == "reload-episode":
                                        current_url = episode_context.get("url")
                                        if current_url:
                                            self._send_mpv_command(
                                                sock,
                                                "loadfile",
                                                [current_url, "replace"],
                                            )
                                            self._send_mpv_command(
                                                sock,
                                                "show-text",
                                                ["Reloading episode..."],
                                            )
                                            continue

                                    elif action == "toggle-autoplay":
                                        self.autoplay = not self.autoplay
                                        status = "ATIVADO" if self.autoplay else "DESATIVADO"
                                        message = f"Auto-play {status} (válido para toda a sessão)"
                                        self._send_mpv_command(sock, "show-text", [message, "3000"])
                                        print(f"{message}")
                                        continue

                                    result = self._handle_keybinding_action(action, episode_context)
                                    if result:
                                        return result
                        except json.JSONDecodeError:
                            continue
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"IPC error: {e}")
                    break

            exit_code = mpv_process.returncode or 0
            stderr_output = ""
            if hasattr(mpv_process, "stderr") and mpv_process.stderr:
                try:
                    stderr_output = mpv_process.stderr.read()
                except (OSError, ValueError):
                    pass

            if exit_code != 0 or "error" in stderr_output.lower():
                print(f"⚠️  MPV exited with code {exit_code}")
                if "error" in stderr_output.lower():
                    error_lines = [
                        line for line in stderr_output.split("\n") if "error" in line.lower()
                    ]
                    for error_line in error_lines[:3]:
                        if error_line.strip():
                            print(f"   ❌ {error_line.strip()[:100]}")
                    if "400" in stderr_output:
                        print("\n   ℹ️  AnimesonlineCC: Token expirado (URLs temporárias)")
                print("   Tente ativar debug: ANI_TUPI_DEBUG_MPV=1 uv run ani-tupi")

            if self.autoplay and exit_code == 0:
                from services.history_service import save_history_from_event

                anime_title = episode_context.get("anime_title")
                episode_number = episode_context.get("episode_number", 1)
                source = episode_context.get("source")
                anilist_id = episode_context.get("anilist_id")

                if anime_title:
                    episode_idx = episode_number - 1
                    save_history_from_event(
                        anime_title=anime_title,
                        episode_idx=episode_idx,
                        action="watched",
                        source=source,
                        anilist_id=anilist_id,
                    )
                print(f"▶️  Auto-play ativo: marcando Episódio {episode_number} como assistido")
                return VideoPlaybackResult(
                    exit_code=exit_code,
                    action="auto-next",
                    data={"episode": episode_number},
                )

            final_episode = episode_context.get("episode_number", 1)
            return VideoPlaybackResult(
                exit_code=exit_code, action="quit", data={"episode": final_episode}
            )
        finally:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass

    def _update_skip_lua_with_times(
        self,
        skip_lua_path: str,
        skip_times: "SkipTimes",
    ) -> bool:
        """Update skip.lua file with new skip times.

        The skip.lua script reads skip times from the file to apply them during
        playback. This method updates the file atomically so MPV can reload it.

        Args:
            skip_lua_path: Path to skip.lua file
            skip_times: SkipTimes object with op_start, op_end, ed_start, ed_end

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            from pathlib import Path
            import tempfile

            skip_lua_file = Path(skip_lua_path)

            # Format skip times as Lua table
            lua_times = {}
            if skip_times.op_start is not None and skip_times.op_end is not None:
                lua_times["op_start"] = float(skip_times.op_start)
                lua_times["op_end"] = float(skip_times.op_end)
            if skip_times.ed_start is not None and skip_times.ed_end is not None:
                lua_times["ed_start"] = float(skip_times.ed_start)
                lua_times["ed_end"] = float(skip_times.ed_end)

            if not lua_times:
                return False

            # Generate Lua table format
            lua_lines = ["-- Skip times"]
            lua_lines.append("return {")
            for key, value in lua_times.items():
                lua_lines.append(f"    {key} = {value},")
            lua_lines.append("}")

            new_content = "\n".join(lua_lines) + "\n"

            # Atomic write: write to temp file, then rename
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".lua",
                dir=skip_lua_file.parent,
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(new_content)
                tmp_path = tmp.name

            # Atomic rename
            import os

            os.replace(tmp_path, skip_lua_path)

            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Updated skip.lua with times: {lua_times}")

            return True

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update skip.lua: {e}")
            return False

    def _send_mpv_command(self, sock: socket.socket, command: str, args: list) -> None:
        """Send JSON-RPC command to MPV via IPC socket."""
        request = {"command": [command] + args}
        try:
            message = json.dumps(request) + "\n"
            sock.sendall(message.encode("utf-8"))
        except Exception as e:
            print(f"Failed to send MPV command: {e}")


def _format_episode_progress(
    episode_num: int,
    scraper_total: int | None | str = None,
    anilist_total: int | None = None,
) -> str:
    """Format episode progress with scraper and AniList episode counts."""
    if scraper_total is None:
        scraper_total = "?"
    result = f"{episode_num} / {scraper_total}"
    if anilist_total and anilist_total != scraper_total:
        result += f" (total: {anilist_total})"
    return result


# Global functions for backward compatibility (will use a default instance)
_default_player = VideoPlayer()


def get_autoplay_state() -> bool:
    """Get current auto-play state."""
    return _default_player.get_autoplay_state()


def set_autoplay_state(enabled: bool) -> None:
    """Set auto-play state."""
    _default_player.set_autoplay_state(enabled)


def play_video(url: str, debug=False, ytdl_format: str | None = None) -> int:
    """Play video using python-mpv and return exit code."""
    return _default_player.play_video_raw(url, debug=debug, ytdl_format=ytdl_format)


def play_episode(
    url: str,
    anime_title: str,
    episode_number: int,
    total_episodes: int,
    source: str,
    use_ipc: bool = True,
    debug: bool = False,
    anilist_id: int | None = None,
    anilist_episodes: int | None = None,
) -> VideoPlaybackResult:
    """Play a single episode with optional IPC support."""
    return _default_player.play_episode(
        url=url,
        anime_title=anime_title,
        episode_number=episode_number,
        total_episodes=total_episodes,
        source=source,
        use_ipc=use_ipc,
        debug=debug,
        anilist_id=anilist_id,
        anilist_episodes=anilist_episodes,
    )
