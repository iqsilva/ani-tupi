"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field


# ============================================================
# Search Schemas
# ============================================================
class AnimeSource(BaseModel):
    """Single source for an anime."""

    url: str
    source: str
    params: dict = Field(default_factory=dict)


class AnimeSearchResultSchema(BaseModel):
    """Anime search result with multiple sources."""

    title: str
    normalized_title: str
    sources: list[AnimeSource]


class SearchResponse(BaseModel):
    """Response from anime search endpoint."""

    query: str
    results: list[AnimeSearchResultSchema]
    total: int


class EpisodeInfo(BaseModel):
    """Episode information."""

    number: int
    url: str
    source: str


class EpisodeListResponse(BaseModel):
    """Response from episode list endpoint."""

    anime: str
    season: int | None = None
    episodes: list[int]
    total: int
    sources: list[str]


# ============================================================
# Playback Schemas
# ============================================================
class PlaybackStartRequest(BaseModel):
    """Request to start playback."""

    anime: str
    episode: int = Field(ge=1, description="Episode number (1-indexed)")
    season: int | None = Field(default=None, description="Season number (optional)")
    source: str | None = Field(default=None, description="Preferred source")
    quality: str = Field(default="best", pattern="^(1080|720|480|360|best)$")


class PlaybackState(BaseModel):
    """Current playback state."""

    is_playing: bool = False
    anime: str | None = None
    episode: int | None = None
    total_episodes: int | None = None
    source: str | None = None
    position: float = 0.0  # Seconds
    duration: float = 0.0  # Seconds
    paused: bool = False
    autoplay: bool = False
    volume: int = 100


class PlaybackControlRequest(BaseModel):
    """Request for playback control actions."""

    action: str = Field(
        ...,
        pattern="^(pause|resume|stop|seek|volume|next|previous)$",
        description="Control action",
    )
    value: float | None = Field(
        default=None, description="Value for seek (seconds) or volume (0-100)"
    )


class PlaybackResponse(BaseModel):
    """Response from playback actions."""

    success: bool
    message: str
    state: PlaybackState | None = None


# ============================================================
# History Schemas
# ============================================================
class HistoryEntrySchema(BaseModel):
    """Watch history entry."""

    anime: str
    episode: int
    total_episodes: int | None = None
    source: str | None = None
    anilist_id: int | None = None
    timestamp: float
    urls: dict | None = None


class HistoryListResponse(BaseModel):
    """Response from history list endpoint."""

    entries: list[HistoryEntrySchema]
    total: int


# ============================================================
# Source/Config Schemas
# ============================================================
class SourceInfo(BaseModel):
    """Information about an anime source."""

    name: str
    enabled: bool
    priority: int


class SourcesResponse(BaseModel):
    """Response from sources list endpoint."""

    sources: list[SourceInfo]


class SourcePriorityRequest(BaseModel):
    """Request to update source priorities."""

    order: list[str] = Field(..., description="List of source names in priority order")


# ============================================================
# WebSocket Messages
# ============================================================
class WSMessage(BaseModel):
    """WebSocket message format."""

    type: str  # "state", "event", "error"
    data: dict
