"""Unified manga service with multi-source support.

Orchestrates multiple manga scraper plugins and provides a clean interface
for the manga CLI. Replaces the old MangaDex-only service.
"""

import json
from pathlib import Path

from manga_scrapers.loader import load_manga_plugins
from models.config import MangaSettings, get_data_path
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

        # Default source (prioritize MugiwarasOficial for Brazilian Portuguese, MangaDex as fallback)
        self.current_source = self._determine_default_source()

        # Path to manga plugin metadata
        self.metadata_file = get_data_path() / "manga_plugin_metadata.json"
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load manga plugin metadata from file.

        Metadata maps manga_id to which plugin has it (e.g., {"manga-id": "mugiwaras"})
        This allows us to remember which plugin a manga was found in.
        """
        self.manga_plugin_map: dict[str, str] = {}
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    self.manga_plugin_map = json.load(f)
            except Exception:
                self.manga_plugin_map = {}

    def _save_metadata(self) -> None:
        """Save manga plugin metadata to file."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w") as f:
                json.dump(self.manga_plugin_map, f, indent=2)
        except Exception:
            pass  # Silently ignore save errors

    def _record_manga_in_plugin(self, manga_id: str, plugin_name: str) -> None:
        """Record which plugin a manga was found in.

        Args:
            manga_id: The manga ID
            plugin_name: The plugin name that has this manga
        """
        self.manga_plugin_map[manga_id] = plugin_name
        self._save_metadata()

    def _get_known_plugin_for_manga(self, manga_id: str) -> str | None:
        """Get the plugin where a manga was previously found.

        Args:
            manga_id: The manga ID

        Returns:
            Plugin name or None if not found in metadata
        """
        return self.manga_plugin_map.get(manga_id)

    def _determine_default_source(self) -> str:
        """Determine the default manga source based on availability and preferences.

        Uses configured preferred sources, prioritizing MugiwarasOficial for Brazilian
        Portuguese users, with MangaDex as fallback.

        Returns:
            The chosen source name
        """
        # Use configured preferred sources
        source_priority = self.config.preferred_sources

        # Try sources in priority order
        for source in source_priority:
            if source in self.plugins:
                return source

        # Fallback to any available source
        available_sources = list(self.plugins.keys())
        if available_sources:
            return available_sources[0]

        # This should not happen due to the check in __init__
        raise RuntimeError("Nenhum plugin de mangá disponível")

    def _get_fallback_source(self, failed_source: str) -> str | None:
        """Get a fallback source when the current source fails.

        Args:
            failed_source: The source that just failed

        Returns:
            Fallback source name or None if no fallback available
        """
        # Use configured preferred sources for fallback logic
        preferred_sources = self.config.preferred_sources

        # Try other preferred sources first
        for source in preferred_sources:
            if source != failed_source and source in self.plugins:
                return source

        # Try any other available source
        for source in self.plugins:
            if source != failed_source:
                return source

        return None

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
        """Search for manga by title across all available sources.

        First tries the specified source, then falls back to searching all plugins
        if the primary search returns no results and no specific source was requested.

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

        # Try primary source
        try:
            results = self._search_manga_from_source(query, source_name)
            # If we got results, return them
            if results:
                # Record found manga in metadata
                for result in results:
                    self._record_manga_in_plugin(result.id, source_name)
                return results
            # If no results and specific source requested, return empty (don't try others)
            if source is not None:
                return []
            # Otherwise, fall through to try other sources
        except Exception as e:
            # If specific source requested, don't try others
            if source is not None:
                raise ValueError(f"Falha ao buscar em {source_name}: {e}")
            # Fall through to try other sources
            print(f"⚠️  Falha na fonte {source_name}: {e}")

        # Try fallback sources if no results or error
        print("🔄 Tentando outras fontes...")

        all_sources = [s for s in self.config.preferred_sources if s in self.plugins]
        if source_name in all_sources:
            all_sources.remove(source_name)

        # Try each source in order
        for try_source in all_sources:
            try:
                print(f"  Tentando {try_source}...")
                results = self._search_manga_from_source(query, try_source)
                if results:
                    print(f"✓ Encontrados {len(results)} resultado(s) em {try_source}")
                    # Record found manga in metadata
                    for result in results:
                        self._record_manga_in_plugin(result.id, try_source)
                    return results
            except Exception:
                continue

        # If still no results, try any remaining sources not in preferred list
        for plugin_name in self.plugins:
            if plugin_name not in all_sources and plugin_name != source_name:
                try:
                    print(f"  Tentando {plugin_name}...")
                    results = self._search_manga_from_source(query, plugin_name)
                    if results:
                        print(f"✓ Encontrados {len(results)} resultado(s) em {plugin_name}")
                        # Record found manga in metadata
                        for result in results:
                            self._record_manga_in_plugin(result.id, plugin_name)
                        return results
                except Exception:
                    continue

        # No results in any source
        return []

    def _search_manga_from_source(self, query: str, source_name: str) -> list[MangaMetadata]:
        """Search for manga from a specific source.

        Args:
            query: Search query string
            source_name: Source name to search

        Returns:
            List of MangaMetadata objects
        """
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

        First tries the specified source or last-known source from metadata,
        then falls back to current_source and other sources if needed.

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

        # Try primary source
        try:
            return self._get_chapters_from_source(manga_id, manga_url, source_name)
        except Exception as e:
            # If specific source requested, don't try others
            if source is not None:
                raise ValueError(f"Falha ao buscar capítulos em {source_name}: {e}")

            # Try known plugin for this manga from metadata
            known_source = self._get_known_plugin_for_manga(manga_id)
            if known_source and known_source != source_name:
                try:
                    print(
                        f"⚠️  Falha em {source_name}, tentando fonte conhecida {known_source}..."
                    )
                    return self._get_chapters_from_source(manga_id, manga_url, known_source)
                except Exception:
                    pass

            # Try other fallback sources
            fallback_source = self._get_fallback_source(source_name)
            if fallback_source:
                print(f"⚠️  Tentando fallback {fallback_source}...")
                try:
                    return self._get_chapters_from_source(manga_id, None, fallback_source)
                except Exception as fallback_error:
                    print(f"⚠️  Falha no fallback {fallback_source}: {fallback_error}")

            # Re-raise the original error
            raise e

    def _get_chapters_from_source(
        self, manga_id: str, manga_url: str | None, source_name: str
    ) -> list[ChapterData]:
        """Get chapters from a specific source.

        Args:
            manga_id: Manga ID
            manga_url: Optional manga URL
            source_name: Source name

        Returns:
            List of ChapterData objects
        """
        plugin = self.plugins[source_name]

        # Some plugins need the URL, others just the ID
        if manga_url is None:
            # Try to construct URL based on source
            if source_name == "mangadex":
                manga_url = f"https://mangadex.org/title/{manga_id}"
            elif source_name == "mugiwaras":
                manga_url = f"https://mugiwarasoficial.com/manga/{manga_id}/"
            elif source_name == "mangalivre":
                manga_url = f"https://mangalivre.blog/manga/{manga_id}/"
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
                    url=item.get("url"),  # Store chapter URL from plugin if available
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
        if chapter_url is None or chapter_url == "":
            if source_name == "mangadex":
                chapter_url = f"https://mangadex.org/chapter/{chapter_id}"
            # For other sources like mangalivre, mugiwaras that need URL,
            # pass empty string only if URL construction isn't available
            # Let plugin handle empty URL gracefully

        return plugin.get_chapter_pages(chapter_id, chapter_url or "")

    def check_manga_available(self, manga_title: str, source: str | None = None) -> bool:
        """Quick check if a manga is available in a source.

        Tries to search for the manga and see if it exists.

        Args:
            manga_title: Manga title to search
            source: Source to check (default: current_source)

        Returns:
            True if manga found, False otherwise
        """
        source_name = source or self.current_source

        if source_name not in self.plugins:
            return False

        try:
            results = self._search_manga_from_source(manga_title, source_name)
            return len(results) > 0
        except Exception:
            return False

    def get_available_sources_for_manga(self, manga_title: str) -> list[str]:
        """Get list of sources that have a specific manga.

        Args:
            manga_title: Manga title to search

        Returns:
            List of source names that have this manga
        """
        available = []
        for source in self.plugins:
            if self.check_manga_available(manga_title, source):
                available.append(source)
        return available


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
