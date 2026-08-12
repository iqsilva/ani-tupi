"""Pydantic data models for structured data transfer.

Defines DTOs (Data Transfer Objects) for:
- AnimeMetadata: Anime information from scrapers
- EpisodeData: Episode lists from scrapers
- VideoUrl: Playback URLs with optional headers
- AnimeSearchResult: Immutable search result for one anime
- SearchResults: Immutable collection of search results
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnimeMetadata(BaseModel):
    """Anime metadata from scraper.

    Attributes:
        title: Anime title (non-empty)
        url: Anime URL from scraper (must be http/https)
        source: Plugin source name (non-empty)
        params: Optional extra parameters for scraper
    """

    title: str = Field(..., min_length=1, description="Anime title")
    url: str = Field(..., min_length=1, description="Anime URL from scraper")
    source: str = Field(..., min_length=1, description="Plugin source name")
    params: dict[str, Any] | None = Field(None, description="Extra params for scraper")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must be http(s), got: {v}")
        return v


class EpisodeData(BaseModel):
    """Episode list from scraper.

    Attributes:
        anime_title: Title of the anime
        episode_numbers: List of episode numbers (normalized to int)
        episode_urls: List of episode URLs (must be http/https)
        source: Plugin source name
        season: Season number (1-indexed). Optional: defaults to 1.

    Validation:
        - episode_numbers and episode_urls must have same length
        - All episode URLs must be valid http(s) URLs
        - season must be positive integer
    """

    anime_title: str = Field(..., min_length=1, description="Anime title")
    episode_numbers: list[int] = Field(..., description="Episode numbers (normalized)")
    episode_urls: list[str] = Field(..., description="Episode URLs (must be http/https)")
    source: str = Field(..., min_length=1, description="Plugin source name")
    season: int = Field(default=1, ge=1, description="Season number (1-indexed)")

    @field_validator("episode_urls", mode="before")
    @classmethod
    def validate_episode_urls(cls, v: list[str]) -> list[str]:
        """Validate all episode URLs are properly formatted."""
        for url in v:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Episode URL must be http(s), got: {url}")
        return v

    @model_validator(mode="after")
    def validate_lengths(self) -> "EpisodeData":
        """Validate episode lists have matching lengths."""
        if len(self.episode_numbers) != len(self.episode_urls):
            raise ValueError(
                f"Mismatched episodes: {len(self.episode_numbers)} numbers "
                f"vs {len(self.episode_urls)} URLs"
            )
        return self


class VideoUrl(BaseModel):
    """Video playback URL with optional headers.

    Attributes:
        url: Video URL (m3u8 HLS or direct video file)
        headers: Optional HTTP headers for playback (User-Agent, Referer, etc.)
    """

    url: str = Field(..., min_length=1, description="Video URL (m3u8 or mp4/mkv/etc)")
    headers: dict[str, str] | None = Field(None, description="HTTP headers for playback")

    @field_validator("url")
    @classmethod
    def validate_video_url(cls, v: str) -> str:
        """Validate video URL format.

        Accepts:
        - m3u8 (HLS streaming)
        - Direct video files (mp4, mkv, avi, webm)
        - Dynamic URLs (logged as warning but allowed)
        """
        import warnings

        valid_extensions = (".m3u8", ".mp4", ".mkv", ".avi", ".webm")
        if not any(v.endswith(ext) for ext in valid_extensions):
            # Some sites have dynamic URLs without file extensions
            warnings.warn(f"Video URL may be invalid: {v}", stacklevel=2)
        return v


# Episode and Search Models
class EpisodeContext(BaseModel):
    """Episode context for next episode navigation.

    Attributes:
        url: Episode URL
        title: Episode title
        episode: Episode number (1-indexed)
        total: Total episodes
    """

    url: str = Field(..., min_length=1, description="Episode URL")
    title: str = Field(..., min_length=1, description="Episode title")
    episode: int = Field(..., ge=1, description="Episode number (1-indexed)")
    total: int = Field(..., ge=1, description="Total episodes")


class SearchMetadata(BaseModel):
    """Search metadata from repository.

    Attributes:
        original_query: The full query user typed
        used_query: The actual query used (after reduction)
        used_words: Number of words used in final search
        total_words: Total number of words in original query
        min_words: Minimum word limit (from config)
        variant_tested: Title variation that was tested
        variant_index: Index of the variation tested
        total_variants: Total number of variations available
        source: Source of the search (cache, scraper, or mixed)
        cache_hit: Whether results came from cache
        cache_age_seconds: Age of cached result in seconds (None if not from cache)
        scraper_sources: List of scraper names that provided results
        cache_check_time_ms: Time taken to check cache (milliseconds)
        scraper_execution_time_ms: Time taken to execute scrapers (milliseconds)
        total_execution_time_ms: Total time for the search (milliseconds)
    """

    original_query: str | None = None
    used_query: str | None = None
    used_words: int | None = None
    total_words: int | None = None
    min_words: int | None = None
    variant_tested: str | None = None
    variant_index: int | None = None
    total_variants: int | None = None
    source: str | None = None
    cache_hit: bool | None = None
    cache_age_seconds: int | None = None
    scraper_sources: list[str] = Field(
        default_factory=list, description="List of scrapers that provided results"
    )
    cache_check_time_ms: int = Field(
        default=0, ge=0, description="Cache check time in milliseconds"
    )
    scraper_execution_time_ms: int = Field(
        default=0, ge=0, description="Scraper execution time in milliseconds"
    )
    total_execution_time_ms: int = Field(
        default=0, ge=0, description="Total execution time in milliseconds"
    )


# Cache Models
class ScraperCacheData(BaseModel):
    """Scraper cache data structure.

    Attributes:
        episode_urls: List of episode URLs
        episode_count: Number of episodes
        timestamp: Cache timestamp (legacy, not used in new system)
    """

    episode_urls: list[str] = Field(..., description="Episode URLs")
    episode_count: int = Field(..., ge=0, description="Number of episodes")
    timestamp: int = Field(default=0, description="Cache timestamp (legacy)")


class CacheStats(BaseModel):
    """Cache statistics.

    Attributes:
        size: Cache size
        total_items: Total number of items in cache
    """

    size: int = Field(..., ge=0, description="Cache size")
    total_items: int = Field(..., ge=0, description="Total items")


class Status(str, Enum):
    CURRENT = "CURRENT"
    PLANNING = "PLANNING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    DROPPED = "DROPPED"
    REPEATING = "REPEATING"


# ============================================================================
# IMMUTABLE DATA STRUCTURES (Phase 2 - C3)
# ============================================================================
# These frozen Pydantic models enforce Immutable Data Flow principle from CLAUDE.md
# Services return new immutable values, never mutate state


class AnimeSearchResult(BaseModel, frozen=True):
    """Immutable anime search result.

    Represents one anime found across one or more sources.
    Cannot be modified after creation (frozen=True Pydantic model).

    Attributes:
        title: Human-readable anime title
        normalized_title: Normalized title for deduplication
        sources: Immutable tuple of (url, source_name, params) tuples
    """

    title: str = Field(..., min_length=1, description="Human-readable anime title")
    normalized_title: str = Field(
        ..., min_length=1, description="Normalized title for deduplication"
    )
    sources: tuple[tuple[str, str, dict], ...] = Field(
        ..., description="Tuple of (url, source_name, params) tuples"
    )

    @model_validator(mode="after")
    def validate_sources(self) -> "AnimeSearchResult":
        """Validate sources is not empty."""
        if not self.sources:
            raise ValueError("sources cannot be empty")
        return self


class SearchResults(BaseModel, frozen=True):
    """Immutable collection of anime search results.

    Returned by Repository.search_anime() instead of mutating repository state.
    Contains all search results + metadata.

    Attributes:
        query: Original search query
        results: Immutable tuple of AnimeSearchResult objects
        metadata: Search metadata (dict[str, Any])
    """

    query: str = Field(..., min_length=1, description="Original search query")
    results: tuple[AnimeSearchResult, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of AnimeSearchResult objects",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")

    def get_anime_titles(self) -> list[str]:
        """Get list of anime titles from results.

        Returns:
            List of anime title strings
        """
        return [result.title for result in self.results]

    def get_anime_titles_with_sources(self) -> list[str]:
        """Get titles with source indicators.

        Returns:
            List of strings like "Anime Title [source1, source2]"
        """
        result_list = []
        for anime in self.results:
            sources = set(source for _url, source, _params in anime.sources)
            sources_str = ", ".join(sorted(sources))
            result_list.append(f"{anime.title} [{sources_str}]")
        return result_list


# ============================================================================
# ANIME DOWNLOAD MODELS (Phase 1 - Download Service)
# ============================================================================


class DownloadedEpisode(BaseModel):
    """Metadata for a downloaded episode.

    Attributes:
        episode_number: Episode number (1-indexed)
        file_path: Path to downloaded video file
        file_size_mb: File size in MB
        source: Source scraper name
        downloaded_at: ISO timestamp when downloaded
        status: Download status (success, failed, corrupted)
    """

    episode_number: int = Field(..., ge=1, description="Episode number (1-indexed)")
    file_path: Path = Field(..., description="Path to downloaded video file")
    file_size_mb: float = Field(..., ge=0.0, description="File size in MB")
    source: str = Field(..., min_length=1, description="Source scraper name")
    downloaded_at: datetime = Field(default_factory=datetime.now, description="Download timestamp")
    status: Literal["success", "failed", "corrupted"] = Field(
        "success", description="Download status (success, failed, corrupted)"
    )


class DownloadResult(BaseModel):
    """Result of a download operation.

    Attributes:
        successful: Number of successful downloads
        failed: List of failed episode numbers
        corrupted: List of corrupted episode numbers
        skipped: List of already-downloaded episode numbers
        summary: Human-readable summary
    """

    successful: int = Field(..., ge=0, description="Number of successful downloads")
    failed: list[int] = Field(default_factory=list, description="List of failed episode numbers")
    corrupted: list[int] = Field(
        default_factory=list, description="List of corrupted episode numbers"
    )
    skipped: list[int] = Field(
        default_factory=list, description="List of already-downloaded episodes"
    )
    summary: str = Field(..., min_length=1, description="Human-readable summary")


class AnimeDownloadHistory(BaseModel):
    """History of downloaded anime per title.

    Attributes:
        anime_title: Title of the anime
        episodes: Dictionary of episode_number -> DownloadedEpisode
        last_downloaded: ISO timestamp of last download
        total_size_mb: Total size of all downloaded episodes
    """

    anime_title: str = Field(..., min_length=1, description="Anime title")
    episodes: dict[int, DownloadedEpisode] = Field(
        default_factory=dict, description="Downloaded episodes by number"
    )
    last_downloaded: datetime = Field(
        default_factory=datetime.now, description="Last download timestamp"
    )
    total_size_mb: float = Field(default=0.0, ge=0.0, description="Total size of all episodes")

    def get_episode_numbers(self) -> list[int]:
        """Get sorted list of downloaded episode numbers.

        Returns:
            Sorted list of episode numbers
        """
        return sorted(self.episodes.keys())

    def has_episode(self, episode_number: int) -> bool:
        """Check if episode is downloaded.

        Args:
            episode_number: Episode number to check

        Returns:
            True if episode exists and status is 'success'
        """
        ep = self.episodes.get(episode_number)
        return ep is not None and ep.status == "success"


class AnimeDownloadDatabase(BaseModel):
    """Root model for anime download history database.

    Stores downloaded anime across the library, serialized to JSON.

    Attributes:
        version: Schema version for migrations
        anime: Dictionary of anime_title -> AnimeDownloadHistory
        last_updated: ISO timestamp of last update
    """

    version: int = Field(default=1, description="Schema version for migrations")
    anime: dict[str, AnimeDownloadHistory] = Field(
        default_factory=dict, description="Downloaded anime by title"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )


class UpdateCheckState(BaseModel):
    """Persisted update-check state for cooldown behavior."""

    last_checked_at: datetime | None = Field(
        default=None,
        description="Timestamp of the last successful remote version check",
    )
    last_latest_version: str | None = Field(
        default=None,
        description="Latest known upstream version from the last successful check",
    )
    last_update_available: bool = Field(
        default=False,
        description="Whether the last successful check reported an available update",
    )


class UpdateCheckResult(BaseModel):
    """Immutable startup update-check result."""

    model_config = ConfigDict(frozen=True)

    local_version: str = Field(..., min_length=1, description="Installed local version")
    latest_version: str | None = Field(default=None, description="Latest upstream version")
    update_available: bool = Field(
        default=False,
        description="True when a newer upstream version is available",
    )
    message: str | None = Field(
        default=None,
        description="User-facing update message when an update is available",
    )


@dataclass
class HistoryEntry:
    """Watch history entry. Serializes as list for JSON backward compat.

    JSON list format:
    [timestamp, episode_idx, _legacy, source, total_episodes, urls, position, duration]
    - index 2 is a legacy slot (always None; previously an external ID)
    - position/duration are in-episode playback progress in seconds (optional)
    """

    timestamp: int
    episode_idx: int
    source: str | None = None
    total_episodes: int | None = None
    urls: dict[str, str] = field(default_factory=dict)
    position: float | None = None
    duration: float | None = None

    @classmethod
    def from_list(cls, data: list) -> "HistoryEntry":
        return cls(
            timestamp=data[0],
            episode_idx=data[1],
            source=data[3] if len(data) > 3 else None,
            total_episodes=data[4] if len(data) > 4 and data[4] else None,
            urls=data[5] if len(data) > 5 and isinstance(data[5], dict) else {},
            position=data[6] if len(data) > 6 and data[6] else None,
            duration=data[7] if len(data) > 7 and data[7] else None,
        )

    def to_list(self) -> list:
        return [
            self.timestamp,
            self.episode_idx,
            None,  # legacy slot kept for format compatibility
            self.source,
            self.total_episodes,
            self.urls,
            self.position,
            self.duration,
        ]
