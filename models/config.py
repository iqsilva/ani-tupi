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
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_data_path() -> Path:
    """Get OS-specific data directory for ani-tupi.

    Returns:
        Path: ~/.local/state/ani-tupi (Linux/macOS) or C:\\Program Files\\ani-tupi (Windows)
    """
    if os.name == "nt":
        return Path("C:\\Program Files\\ani-tupi")  # type: ignore
    return Path.home() / ".local" / "state" / "ani-tupi"


class AniListSettings(BaseModel):
    """AniList API configuration."""

    api_url: str = Field(
        "https://graphql.anilist.co",
        description="AniList GraphQL API endpoint",
    )
    auth_url: str = Field(
        "https://anilist.co/api/v2/oauth/authorize",
        description="OAuth authorization URL",
    )
    client_id: int = Field(
        20148,
        gt=0,
        description="OAuth client ID (public)",
    )
    token_file: Path = Field(
        default_factory=lambda: get_data_path() / "anilist_token.json",
        description="Path to stored access token",
    )
    prefer_english_title: bool = Field(
        False,
        description="Use English title for searches (True) or Romaji (False)",
    )
    manga_prefer_english_title: bool = Field(
        False,
        description="Use English title for manga searches (True) or Romaji (False)",
    )
    manga_auto_sync: bool = Field(
        True,
        description="Automatically sync manga progress with AniList when confirmed",
    )
    manga_progress_confirmation: bool = Field(
        True,
        description="Ask for chapter completion confirmation after reading",
    )


class CacheSettings(BaseModel):
    """Scraper cache configuration (SQLite via diskcache)."""

    duration_hours: int = Field(
        168,
        ge=1,
        le=720,
        description="Cache validity duration in hours (default 7 days, max 30 days)",
    )
    cache_dir: Path = Field(
        default_factory=lambda: get_data_path() / "cache",
        description="Path to SQLite cache directory (diskcache)",
    )
    # Kept for migration compatibility
    cache_file: Path = Field(
        default_factory=lambda: get_data_path() / "scraper_cache.json",
        description="Path to legacy JSON cache file (deprecated, for migration only)",
    )
    anilist_auto_discover: bool = Field(
        True,
        description="Auto-discover AniList ID for manual searches via fuzzy matching",
    )
    anilist_fuzzy_threshold: int = Field(
        90,
        ge=70,
        le=100,
        description="Minimum fuzzy match score (0-100) for AniList ID auto-discovery",
    )


class SearchSettings(BaseModel):
    """Anime search configuration."""

    progressive_search_min_words: int = Field(
        1,  # Changed from 2 to support single-word anime like "Dandadan"
        ge=1,
        le=10,
        description="Minimum words to use in progressive search",
    )
    top_results_limit: int = Field(
        10,
        ge=5,
        le=50,
        description="Maximum results to show initially (before 'Show all' button)",
    )


class PluginSettings(BaseModel):
    """Plugin/scraper management settings."""

    preferences_file: Path = Field(
        default_factory=lambda: get_data_path() / "plugin_preferences.json",
        description="Path to plugin preferences (active/inactive sources)",
    )
    disabled_plugins: list[str] = Field(
        default_factory=list,
        description="List of disabled plugin names (e.g., ['animesonlinecc'])",
    )
    priority_order: list[str] = Field(
        default_factory=lambda: ["animesdigital", "animefire", "animesonlinecc"],
        description="Priority order for scraper sources (first = highest priority)",
    )


class MangaSettings(BaseModel):
    """Manga reader settings with multi-source support."""

    api_url: str = Field(
        "https://api.mangadex.org",
        description="MangaDex API base URL",
    )
    cache_duration_hours: int = Field(
        24,
        ge=1,
        le=72,
        description="How long to cache chapter lists (hours)",
    )
    output_directory: Path = Field(
        default_factory=lambda: Path.home() / ".manga_tupi",
        description="Where to save downloaded manga chapters",
    )
    languages: list[str] = Field(
        default_factory=lambda: ["pt-br", "en"],
        description="Preferred languages in order (pt-br, en, ja, etc)",
    )
    preferred_sources: list[str] = Field(
        default_factory=lambda: ["mugiwaras", "mangadex"],
        description="Preferred manga sources in priority order",
    )
    pdf_reader: str | None = Field(
        None,
        description="PDF reader to use (zathura, evince, okular, mupdf). None = auto-detect",
    )
    delete_images_after_pdf: bool = Field(
        True,
        description="Delete PNG images after PDF creation (keeps only PDF)",
    )
    pdf_quality: int = Field(
        85,
        ge=1,
        le=100,
        description="JPEG quality for images inside PDF (0-100, lower = smaller file)",
    )
    auto_create_pdf: bool = Field(
        True,
        description="Automatically create PDF after downloading images",
    )
    zathura_auto_config: bool = Field(
        True,
        description="Automatically configure Zathura for fit-width zoom",
    )
    # Download for later settings
    default_download_range: int = Field(
        5,
        ge=1,
        le=100,
        description="Default chapters to download when user selects 'download'",
    )
    auto_open_after_download: bool = Field(
        False,
        description="Auto-open PDF reader after downloading (False = stay in menu)",
    )
    skip_already_downloaded: bool = Field(
        True,
        description="Skip already-downloaded chapters in batch operations",
    )
    download_storage_dir: str | None = Field(
        None,
        description="Custom directory for downloaded PDFs (None = use output_directory)",
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

    anilist: AniListSettings = AniListSettings()  # type: ignore[call-arg]
    cache: CacheSettings = CacheSettings()  # type: ignore[call-arg]
    search: SearchSettings = SearchSettings()  # type: ignore[call-arg]
    plugins: PluginSettings = PluginSettings()  # type: ignore[call-arg]
    manga: MangaSettings = MangaSettings()  # type: ignore[call-arg]


# Singleton instance - import and use throughout the app
settings = AppSettings()
