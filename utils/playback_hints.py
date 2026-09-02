"""MPV playback hints for source-specific stream URLs."""


def resolve_mpv_stream_options(url: str, referrer: str | None) -> tuple[str | None, str | None]:
    """Return MPV ``(referrer, demuxer_lavf_o)`` tuned for the stream URL.

    Currently no active source needs special demuxer options; the hook is kept
    so future sources can inject Referer/demuxer tweaks without touching the
    player.
    """
    _ = url
    return referrer, None
