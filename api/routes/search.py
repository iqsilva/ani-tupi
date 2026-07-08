"""Search API routes for anime discovery."""

from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    AnimeSearchResultSchema,
    AnimeSource,
    EpisodeListResponse,
    SearchResponse,
)
from services.repository import rep
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search_anime(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
) -> SearchResponse:
    """Search for anime across all registered sources.

    Returns a list of anime with their available sources.
    """
    try:
        # Clear previous results
        rep.clear_search_results()

        # Search across all sources
        search_results = rep.search_anime(q, verbose=False)

        # Build response
        results = []
        for anime in search_results.results[:limit]:
            sources = [
                AnimeSource(url=url, source=source, params=params or {})
                for url, source, params in anime.sources
            ]
            results.append(
                AnimeSearchResultSchema(
                    title=anime.title,
                    normalized_title=anime.normalized_title,
                    sources=sources,
                )
            )

        return SearchResponse(
            query=q,
            results=results,
            total=len(results),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episodes", response_model=EpisodeListResponse)
async def get_episodes(
    anime: str = Query(..., description="Anime title (exact match from search)"),
    season: int | None = Query(None, ge=1, description="Season number (optional)"),
) -> EpisodeListResponse:
    """Get episode list for an anime.

    First fetches episodes from sources if not already loaded.
    """
    try:
        # Load episodes from sources
        rep.search_episodes(anime)

        # Get episode list
        episodes = rep.get_episode_list(anime, season=season)

        if not episodes:
            raise HTTPException(
                status_code=404,
                detail=f"No episodes found for '{anime}'",
            )

        # Get available sources for this anime
        sources = []
        for urls, source in rep.anime_episodes_urls.get(anime, []):
            if source not in sources:
                sources.append(source)

        return EpisodeListResponse(
            anime=anime,
            season=season,
            episodes=episodes,
            total=len(episodes),
            sources=sources,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seasons")
async def get_seasons(
    anime: str = Query(..., description="Anime title"),
) -> dict:
    """Get available seasons for an anime."""
    try:
        # Load episodes first
        rep.search_episodes(anime)

        # Get seasons
        seasons = rep.get_available_seasons(anime)

        return {
            "anime": anime,
            "seasons": seasons,
            "total": len(seasons),
        }

    except Exception as e:
        logger.error(f"Failed to get seasons: {e}")
        raise HTTPException(status_code=500, detail=str(e))
