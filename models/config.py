"""Application configuration using Pydantic v2.

Centralized settings for ani-tupi including:
- API endpoints and credentials
- Cache settings
- Search configuration
- OS-specific data paths

Configuration can be overridden via environment variables:
    ANI_TUPI__ANILIST__CLIENT_ID=12345
    ANI_TUPI__CACHE__DURATION_HOURS=12
    ANI_TUPI__SEARCH__PROGRESSIVE_SEARCH_MIN_WORDS=2
"""

import os
import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_data_path() -> Path:
    """Get OS-specific data directory for ani-tupi.

    Returns:
        Path: ~/.local/state/ani-tupi (Linux/macOS) or C:\\Program Files\\ani-tupi (Windows)
    """
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ani-tupi"
    return Path.home() / ".local" / "state" / "ani-tupi"


def get_user_config_path() -> Path:
    """Get OS-specific user configuration directory for ani-tupi."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "ani-tupi"
        return Path.home() / "AppData" / "Roaming" / "ani-tupi"
    return Path.home() / ".config" / "ani-tupi"


def get_user_settings_file() -> Path:
    """Get file path for persisted user settings overrides."""
    return get_user_config_path() / "settings.json"


def load_user_settings_overrides() -> dict:
    """Load user settings overrides from JSON file."""
    settings_file = get_user_settings_file()
    if not settings_file.exists():
        return {}
    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_user_settings_overrides(overrides: dict) -> None:
    """Persist user settings overrides atomically."""
    settings_file = get_user_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = settings_file.with_suffix(".json.tmp")
    temp_file.write_text(json.dumps(overrides, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_file.replace(settings_file)


class CacheSettings(BaseModel):
    """Unified cache configuration with TTL and refresh options."""

    cache_dir: Path = Field(
        default_factory=lambda: get_data_path() / "cache",
        description="Path to cache directory (unified backends)",
    )
    anilist_auto_discover: bool = Field(
        True,
        description="Deprecated (AniList integration removed)",
    )
    anilist_fuzzy_threshold: int = Field(
        90,
        ge=70,
        le=100,
        description="Deprecated (AniList integration removed)",
    )
    episodes_cache_enabled: bool = Field(
        False,
        description="Enable episodes cache (disabled by default due to new episode needed to be fetched)",
    )
    # TTL Configuration
    search_cache_ttl_seconds: int = Field(
        3600,
        ge=60,
        description="Time-to-live for search results cache in seconds (default: 1 hour)",
    )
    episodes_cache_ttl_seconds: int = Field(
        1800,
        ge=60,
        description="Time-to-live for episode lists cache in seconds (default: 30 minutes)",
    )
    video_url_cache_ttl_seconds: int = Field(
        7200,
        ge=60,
        description="Time-to-live for video URLs cache in seconds (default: 2 hours)",
    )
    cache_max_size_bytes: int = Field(
        50 * 1024 * 1024,  # 50 MB
        ge=1_000_000,
        description="Maximum cache size in bytes before LRU eviction (default: 50 MB)",
    )
    # Background refresh configuration
    background_refresh_enabled: bool = Field(
        False,
        description="Enable background refresh of stale cache entries (default: disabled for conservative behavior)",
    )
    background_refresh_threshold_seconds: int = Field(
        2700,  # 45 minutes
        ge=60,
        description="Threshold for background refresh: refresh cache older than this (seconds)",
    )
    background_refresh_max_workers: int = Field(
        2,
        ge=1,
        le=16,
        description="Maximum parallel background refresh workers",
    )


class SearchSettings(BaseModel):
    """Anime search configuration."""

    progressive_search_min_words: int = Field(
        1,  # Changed from 2 to support single-word anime like "Dandadan"
        ge=1,
        description="Minimum words to use in progressive search",
    )
    top_results_limit: int = Field(
        10,
        ge=5,
        le=50,
        description="Maximum results to show initially (before 'Show all' button)",
    )
    preferred_audio: str = Field(
        "dublado",
        pattern="^(dublado|legendado)$",
        description="Preferred audio type for AnimesDigital: 'dublado' or 'legendado'",
    )
    enable_title_resolution: bool = Field(
        True,
        description="Retry manual anime searches with externally resolved titles when direct search fails",
    )
    title_resolution_timeout_seconds: float = Field(
        8.0,
        gt=0,
        le=30,
        description="Timeout for each external title resolution provider",
    )
    title_resolution_cache_ttl_seconds: int = Field(
        7 * 24 * 3600,
        ge=60,
        description="TTL for cached resolved anime titles in seconds",
    )
    title_resolution_min_confidence: int = Field(
        75,
        ge=0,
        le=100,
        description="Minimum confidence required before retrying search with an externally resolved title",
    )


class PluginSettings(BaseModel):
    """Plugin/scraper management settings."""

    disabled_plugins: list[str] = Field(
        default_factory=list,
        description="List of disabled plugin names (e.g., ['sushianimes'])",
    )
    priority_order: list[str] = Field(
        default_factory=lambda: [
            "dattebayo",
            "sushianimes",
            "anitube",
            "animesdigital",
            "animefire",
            "goyabu",
            "animesonlinecc",
        ],
        description="Priority order for scraper sources (first = highest priority)",
    )

    @field_validator("priority_order")
    @classmethod
    def append_missing_plugins(cls, v: list[str]) -> list[str]:
        """Append any installed plugins not yet in the saved priority list."""
        plugins_dir = Path(__file__).parent.parent / "scrapers" / "plugins"
        skip = {"__init__.py", "utils.py"}
        installed = {f.stem for f in plugins_dir.glob("*.py") if f.name not in skip}
        missing = [p for p in installed if p not in v]
        return v + sorted(missing)


class PerformanceSettings(BaseModel):
    """Performance optimization settings for scrapers."""

    # HTTP Client Settings
    http_timeout: int = Field(
        15,
        ge=5,
        le=60,
        description="Default timeout for HTTP requests (seconds)",
    )
    http_pool_connections: int = Field(
        10,
        ge=5,
        le=50,
        description="Number of connection pools to cache",
    )
    http_pool_maxsize: int = Field(
        20,
        ge=10,
        le=100,
        description="Maximum connections per pool",
    )
    http_retry_attempts: int = Field(
        3,
        ge=1,
        le=5,
        description="Number of retry attempts for failed HTTP requests",
    )

    # Cache Settings (additional to existing cache settings)
    search_cache_ttl: int = Field(
        300,
        ge=60,
        le=1800,
        description="TTL for search results cache (seconds, 5 minutes default)",
    )
    episodes_cache_ttl: int = Field(
        1800,
        ge=300,
        le=3600,
        description="TTL for episode list cache (seconds, 30 minutes default)",
    )
    video_url_cache_ttl_seconds: int = Field(
        3600,
        ge=300,
        le=86400,
        description="TTL for video URL cache (seconds, 1 hour default)",
    )
    smart_cache_max_size_mb: int = Field(
        100,
        ge=50,
        le=500,
        description="Maximum size of smart cache (MB)",
    )

    # Unified Cache Settings
    cache_type: str = Field(
        "disk",
        description="Cache backend: memory, disk, or hybrid",
    )

    # Consolidated Cache TTL Settings (replaces duplicate duration_hours fields)
    default_ttl_hours: int = Field(
        168,
        ge=1,
        le=720,
        description="Default cache TTL in hours (7 days, max 30 days)",
    )
    source_ttls: dict[str, int] = Field(
        default_factory=lambda: {
            "search": 5,  # 5 minutes for search results
            "episodes": 30,  # 30 minutes for episode lists
            "video": 15,  # 15 minutes for video URLs (expire quickly)
            "anilist_meta": 720,  # 30 days for AniList metadata
        },
        description="Source-specific TTL in hours",
    )


class AnimeDownloadSettings(BaseModel):
    """Anime download and local library settings."""

    download_directory: Path = Field(
        default_factory=lambda: Path.home() / ".local" / "share" / "ani-tupi" / "anime",
        description="Where to save downloaded anime episodes",
    )
    max_parallel_downloads: int = Field(
        3,
        ge=1,
        le=16,
        description="Maximum parallel episode downloads (1 = sequential, 16 = max)",
    )
    video_format: str = Field(
        "mkv",
        description="Default video format for downloads (mkv, mp4, etc)",
    )
    skip_already_downloaded: bool = Field(
        True,
        description="Skip already-downloaded episodes in batch operations",
    )


class UpdateCheckSettings(BaseModel):
    """Configuration for startup update checks."""

    enabled: bool = Field(
        True,
        description="Enable automatic update checks on startup",
    )
    interval_hours: int = Field(
        24,
        ge=1,
        le=720,
        description="Minimum hours between successful remote update checks",
    )
    request_timeout_seconds: float = Field(
        2.0,
        gt=0,
        le=30,
        description="HTTP timeout for update-check requests",
    )
    release_source_url: str = Field(
        "https://api.github.com/repos/levyvix/ani-tupi/releases/latest",
        description="Canonical endpoint used to fetch latest release version",
    )
    update_command: str = Field(
        "curl -sSL https://raw.githubusercontent.com/levyvix/ani-tupi/master/install.sh | bash",
        description="Command shown to users when an update is available",
    )


class PlaybackSettings(BaseModel):
    """MPV playback and buffering configuration.

    Defaults are tuned for low-power devices (e.g. Raspberry Pi 3):
    hardware decoding via v4l2m2m-copy and conservative buffer sizes
    to avoid memory pressure on 1 GB RAM systems.
    """

    hwdec: str = Field(
        "auto-safe",
        description="Hardware decoding mode for MPV: 'auto-safe' (recommended), 'v4l2m2m-copy' (Raspberry Pi), 'auto', 'no', 'vaapi', 'nvdec', etc.",
    )
    demuxer_max_bytes: str = Field(
        "100M",
        description="Maximum forward demuxer cache size (e.g. '100M'; keep low on devices with little RAM)",
    )
    demuxer_max_back_bytes: str = Field(
        "25M",
        description="Maximum backward demuxer cache size (e.g. '25M')",
    )
    demuxer_readahead_secs: int = Field(
        60,
        ge=1,
        le=3600,
        description="Seconds of stream to read ahead into the demuxer cache",
    )
    stream_buffer_size: str = Field(
        "4M",
        description="Network stream read buffer size (e.g. '2M', '4M')",
    )
    cache_secs: int = Field(
        60,
        ge=1,
        le=3600,
        description="Seconds of audio/video to cache when the demuxer cache is enabled",
    )
    vd_lavc_threads: int = Field(
        0,
        ge=0,
        le=64,
        description="Video decoder threads (0 = auto-detect CPU cores)",
    )
    concurrent_fragments: int = Field(
        5,
        ge=1,
        le=16,
        description="Parallel fragment downloads for yt-dlp based streams",
    )
    default_quality: str = Field(
        "480",
        pattern="^(1080|720|480|360|best)$",
        description="Default video quality preset when none is specified",
    )


class ApiSettings(BaseModel):
    """Remote control API server settings."""

    enabled: bool = Field(
        False,
        description="Enable remote control API server",
    )
    host: str = Field(
        "0.0.0.0",
        description="Host address to bind the API server",
    )
    port: int = Field(
        8765,
        ge=1024,
        le=65535,
        description="Port for the API server",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins for the API",
    )
    auth_token: str | None = Field(
        None,
        description="Optional auth token for API requests (None = no auth)",
    )


class AppSettings(BaseSettings):
    """Root application settings with environment variable support.

    Environment variables use the prefix ANI_TUPI__ with nested delimiters:
    - ANI_TUPI__ANILIST__CLIENT_ID=12345
    - ANI_TUPI__CACHE__DURATION_HOURS=12
    - ANI_TUPI__SEARCH__PROGRESSIVE_SEARCH_MIN_WORDS=2

    Can also be configured via .env file in project root.
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",  # ANI_TUPI__ANILIST__CLIENT_ID
        env_prefix="ANI_TUPI__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Apply source precedence: init > env/.env > persisted overrides > defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            load_user_settings_overrides,
            file_secret_settings,
        )

    cache: CacheSettings = CacheSettings()  # type: ignore[call-arg]
    search: SearchSettings = SearchSettings()  # type: ignore[call-arg]
    plugins: PluginSettings = PluginSettings()  # type: ignore[call-arg]
    anime_download: AnimeDownloadSettings = AnimeDownloadSettings()  # type: ignore[call-arg]
    performance: PerformanceSettings = PerformanceSettings()  # type: ignore[call-arg]
    updates: UpdateCheckSettings = UpdateCheckSettings()  # type: ignore[call-arg]
    api: ApiSettings = ApiSettings()  # type: ignore[call-arg]
    playback: PlaybackSettings = PlaybackSettings()  # type: ignore[call-arg]


# Singleton instance - import and use throughout the app
settings = AppSettings()
