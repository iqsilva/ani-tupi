"""Automatic source fallback logic for episode playback.

When MPV fails to play an episode from one source, this module
tries the next available source automatically until one works
or all sources are exhausted.
"""

from typing import NamedTuple
from utils.video_player import VideoPlayer, VideoPlaybackResult
from models.models import SkipTimes


# Exit code 3 indicates user abort (Ctrl+C) - stop immediately, don't fallback
MPV_USER_ABORT_CODE = 3


class PlaybackFallbackResult(NamedTuple):
    """Result from fallback-aware episode playback.

    Attributes:
        playback_result: The VideoPlaybackResult from the successful (or last) play attempt
        source_used: Name of the source that succeeded, or None if all failed
        sources_tried: List of (source_name, exit_code) for all attempted sources
        all_failed: True if every source returned a failure exit code
    """

    playback_result: VideoPlaybackResult
    source_used: str | None
    sources_tried: list[tuple[str, int]]
    all_failed: bool


def play_episode_with_fallback(
    player: VideoPlayer,
    sources: list[tuple[str, str]],
    anime_title: str,
    episode_number: int,
    total_episodes: int,
    use_ipc: bool = True,
    debug: bool = False,
    anilist_id: int | None = None,
    anilist_episodes: int | None = None,
    skip_times: SkipTimes | None = None,
) -> PlaybackFallbackResult:
    """Play episode trying each source in order until one succeeds.

    A source is considered failed when MPV returns a non-zero exit code
    that is NOT exit code 3 (user abort). Exit code 3 means the user
    intentionally cancelled — in that case we stop immediately.

    Args:
        player: VideoPlayer instance with session state (autoplay, etc.)
        sources: List of (url, source_name) sorted by priority
        anime_title: Anime title for display and IPC context
        episode_number: Current episode number (1-indexed)
        total_episodes: Total episodes in scraper
        use_ipc: Enable IPC socket for keybinding events
        debug: Skip actual playback (testing mode)
        anilist_id: AniList ID for progress sync
        anilist_episodes: Total episodes from AniList
        skip_times: Pre-fetched skip times for intro/outro

    Returns:
        PlaybackFallbackResult with outcome details
    """
    if not sources:
        error_result = VideoPlaybackResult(exit_code=2, action="quit", data=None)
        return PlaybackFallbackResult(
            playback_result=error_result,
            source_used=None,
            sources_tried=[],
            all_failed=True,
        )

    sources_tried: list[tuple[str, int]] = []

    for url, source in sources:
        # Show progress if multiple sources
        if len(sources) > 1:
            attempt_num = len(sources_tried) + 1
            print(f"   🎬 Tentando fonte {attempt_num}/{len(sources)}: {source}")

        result = player.play_episode(
            url=url,
            anime_title=anime_title,
            episode_number=episode_number,
            total_episodes=total_episodes,
            source=source,
            use_ipc=use_ipc,
            debug=debug,
            anilist_id=anilist_id,
            anilist_episodes=anilist_episodes,
            skip_times=skip_times,
        )

        sources_tried.append((source, result.exit_code))

        # User intentionally aborted — respect their intent, stop immediately
        if result.exit_code == MPV_USER_ABORT_CODE:
            return PlaybackFallbackResult(
                playback_result=result,
                source_used=source,
                sources_tried=sources_tried,
                all_failed=False,
            )

        # Successful playback (exit_code == 0) OR user action (next, previous, etc.)
        if result.exit_code == 0:
            return PlaybackFallbackResult(
                playback_result=result,
                source_used=source,
                sources_tried=sources_tried,
                all_failed=False,
            )

        # Failure — log and try next source
        failed_sources_count = len(sources_tried)
        remaining = len(sources) - failed_sources_count

        print(f"   ❌ Fonte '{source}' falhou (código: {result.exit_code})")

        if remaining > 0:
            print(f"   🔄 Tentando próxima fonte ({remaining} restante(s))...")

    # All sources exhausted
    tried_names = [s for s, _ in sources_tried]
    print(f"\n❌ Nenhuma fonte funcionou para o episódio {episode_number}.")
    print(f"   Fontes tentadas: {', '.join(tried_names)}")
    print("   💡 Tente trocar de fonte manualmente ou verifique sua conexão.")

    last_result = VideoPlaybackResult(exit_code=2, action="quit", data=None)
    return PlaybackFallbackResult(
        playback_result=last_result,
        source_used=None,
        sources_tried=sources_tried,
        all_failed=True,
    )
