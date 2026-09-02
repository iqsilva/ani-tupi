import re

from scrapers.core.http import FetchError, fetch, fetch_json, post  # noqa: F401 (re-export)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def append_player_source(container: list, source: str) -> bool:
    """Append a candidate playback URL, skipping duplicates."""
    if source in container:
        return False
    container.append(source)
    return True


def store_player_source(container: list, event, source: str) -> bool:
    """Append a candidate playback URL.

    ``event`` is kept for plugin API compatibility; extraction no longer
    stops after the first URL so playback can try every candidate in order.
    """
    _ = event
    return append_player_source(container, source)


def extract_anivideo_hls(html: str) -> str | None:
    """Extract the direct HLS URL from an anivideo videohls.php `d=` parameter."""
    from urllib.parse import unquote

    match = re.search(r"https://api\.anivideo\.net/videohls\.php\?d=([^\"'<>&\s]+)", html)
    if not match:
        return None
    base = unquote(match.group(1).split("&")[0])
    if base.endswith(".m3u8"):
        return base
    if base.endswith(".mp4"):
        return f"{base}/index.m3u8"
    return base


def load_plugin(plugin_cls, register) -> None:
    """Register an anime plugin."""
    register(plugin_cls())
