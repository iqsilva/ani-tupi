"""Unified manga service with multi-source support.

Orchestrates multiple manga scraper plugins and provides a clean interface
for the manga CLI. Replaces the old MangaDex-only service.
"""

from typing import Any

from manga_scrapers.loader import load_manga_plugins
from models.config import MangaSettings
from models.models import ChapterData, MangaMetadata, MangaStatus


class UnifiedMangaService:
    """Unified manga service supporting multiple sources."""

    def __init__(self, config: MangaSettings):
        """Initialize service with config and load plugins.

        Args:
            config: Manga configuration settings
        """
        self.config = config
        self.languages = set(config.languages)

        # Load all available manga scraper plugins
        self.plugins = load_manga_plugins(self.languages)

        if not self.plugins:
            raise RuntimeError("Nenhum plugin de mangá disponível")

        # Default source (prefer MugiwarasOficial for Portuguese, MangaDex as fallback)
        self.current_source = "mugiwaras" if "mugiwaras" in self.plugins else "mangadex"

    def get_available_sources(self) -> list[str]:
        """Get list of available manga sources.

        Returns:
            List of source names
        """
        return list(self.plugins.keys())

    def set_source(self, source: str) -> bool:
        """Set the current manga source.

        Args:
            source: Source name (e.g., "mugiwaras", "mangadex")

        Returns:
            True if source was set, False if source not found
        """
        if source in self.plugins:
            self.current_source = source
            return True
        return False

    def search_manga(self, query: str, source: str | None = None) -> list[MangaMetadata]:
        """Search for manga by title.

        Args:
            query: Search query string
            source: Optional specific source to use (default: current_source)

        Returns:
            List of MangaMetadata objects

        Raises:
            ValueError: If specified source is not available
        """
        source_name = source or self.current_source

        if source_name not in self.plugins:
            raise ValueError(f"Fonte '{source_name}' não disponível")

        plugin = self.plugins[source_name]
        raw_results = plugin.search_manga(query)

        # Convert plugin results to MangaMetadata objects
        results = []
        for item in raw_results:
            try:
                # Normalize status
                status_str = item.get("status", "ongoing").lower()
                if status_str == "ongoing":
                    status = MangaStatus.ONGOING
                elif status_str == "completed":
                    status = MangaStatus.COMPLETED
                elif status_str == "hiatus":
                    status = MangaStatus.HIATUS
                elif status_str == "cancelled":
                    status = MangaStatus.CANCELLED
                else:
                    status = MangaStatus.ONGOING  # Default

                manga = MangaMetadata(
                    id=item["id"],
                    title=item["title"],
                    description=item.get("description"),
                    status=status,
                    year=item.get("year"),
                    cover_url=item.get("cover_url"),
                    tags=item.get("tags", []),
                )
                results.append(manga)
            except (KeyError, ValueError):
                continue

        return results

    def get_chapters(
        self, manga_id: str, manga_url: str | None = None, source: str | None = None
    ) -> list[ChapterData]:
        """Fetch chapters for a manga.

        Args:
            manga_id: Manga ID
            manga_url: Optional manga URL (required for some scrapers)
            source: Optional specific source to use (default: current_source)

        Returns:
            List of ChapterData objects

        Raises:
            ValueError: If specified source is not available
        """
        source_name = source or self.current_source

        if source_name not in self.plugins:
            raise ValueError(f"Fonte '{source_name}' não disponível")

        plugin = self.plugins[source_name]

        # Some plugins need the URL, others just the ID
        if manga_url is None:
            # Try to construct URL based on source
            if source_name == "mangadex":
                manga_url = f"https://mangadex.org/title/{manga_id}"
            elif source_name == "mugiwaras":
                manga_url = f"https://mugiwarasoficial.com/manga/{manga_id}/"
            else:
                manga_url = ""

        raw_chapters = plugin.get_chapters(manga_id, manga_url)

        # Convert plugin results to ChapterData objects
        chapters = []
        for item in raw_chapters:
            try:
                chapter = ChapterData(
                    id=item["id"],
                    number=item["number"],
                    title=item.get("title"),
                    language=source_name,  # Use source as language for now
                    published_at=None,  # Not all sources provide this
                    scanlation_group=None,  # Not all sources provide this
                )
                chapters.append(chapter)
            except (KeyError, ValueError):
                continue

        return chapters

    def get_chapter_pages(
        self, chapter_id: str, chapter_url: str | None = None, source: str | None = None
    ) -> list[str]:
        """Fetch image URLs for a chapter.

        Args:
            chapter_id: Chapter ID
            chapter_url: Optional chapter URL (required for some scrapers)
            source: Optional specific source to use (default: current_source)

        Returns:
            List of image URLs

        Raises:
            ValueError: If specified source is not available
        """
        source_name = source or self.current_source

        if source_name not in self.plugins:
            raise ValueError(f"Fonte '{source_name}' não disponível")

        plugin = self.plugins[source_name]

        # Some plugins need the URL, others just the ID
        if chapter_url is None:
            if source_name == "mangadex":
                chapter_url = f"https://mangadex.org/chapter/{chapter_id}"
            else:
                chapter_url = ""

        return plugin.get_chapter_pages(chapter_id, chapter_url)


# Keep backward compatibility with old MangaDexClient class
# This allows existing code to continue working
class MangaDexClient(UnifiedMangaService):
    """Legacy MangaDex client for backward compatibility.

    Use UnifiedMangaService instead for new code.
    """

    def __init__(self, config: MangaSettings):
        """Initialize with MangaDex as default source."""
        super().__init__(config)
        # Force MangaDex as default for backward compatibility
        if "mangadex" in self.plugins:
            self.current_source = "mangadex"
