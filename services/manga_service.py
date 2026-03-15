"""Unified manga service with multi-source support and utilities.

Provides:
- UnifiedMangaService: Multi-source manga service with plugin support
- MangaHistory: Reading progress persistence
- DownloadedChaptersTracker: Download tracking and metadata
- MangaDexClient: Backward compatibility alias
- Custom exceptions: MangaError, MangaNotFoundError, etc.

This module consolidates both the legacy MangaDex-specific service
and the new multi-source unified service into a single source of truth.
"""

import json
from datetime import datetime
from typing import Any
from collections import OrderedDict


from manga_scrapers.loader import load_manga_plugins
from models.config import MangaSettings, get_data_path
from models.models import ChapterData, MangaHistoryEntry, MangaMetadata, MangaStatus
from utils.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================


class MangaError(Exception):
    """Base manga error with user-friendly message."""

    user_message = "Ocorreu um erro com o mangá"

    def __init__(self, message: str = "", user_message: str | None = None):
        super().__init__(message)
        if user_message:
            self.user_message = user_message


class MangaNotFoundError(MangaError):
    """Manga not found in search results."""

    user_message = "Mangá não encontrado. Tente outra pesquisa."


class MangaDexError(MangaError):
    """MangaDex API error (network, rate limit, etc)."""

    user_message = "Erro ao conectar com MangaDex. Verifique sua conexão."


class ChapterNotAvailableError(MangaError):
    """Chapter not available in selected languages."""

    user_message = "Capítulo não disponível no idioma selecionado."


# ============================================================================
# UTILITY CLASSES
# ============================================================================


class MangaHistory:
    """Reading progress tracker with JSON persistence."""

    _history_file = get_data_path() / "manga_history.json"

    @classmethod
    def _ensure_dir(cls) -> None:
        """Ensure history directory exists."""
        cls._history_file.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls) -> dict[str, MangaHistoryEntry]:
        """Load history from file.

        Returns:
            Dictionary mapping manga titles to history entries
        """
        cls._ensure_dir()

        if not cls._history_file.exists():
            return {}

        try:
            with cls._history_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return {title: MangaHistoryEntry(**entry) for title, entry in data.items()}
        except (json.JSONDecodeError, ValueError):
            return {}

    @classmethod
    def save(cls, history: dict[str, MangaHistoryEntry]) -> None:
        """Save history to file.

        Args:
            history: Dictionary mapping titles to history entries
        """
        cls._ensure_dir()

        data = {title: entry.model_dump() for title, entry in history.items()}

        try:
            with cls._history_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            raise MangaError(f"Failed to save history: {e}")

    @classmethod
    def get_last_chapter(cls, manga_title: str) -> str | None:
        """Get last read chapter for manga.

        Args:
            manga_title: Manga title to look up

        Returns:
            Chapter number string or None if not found
        """
        history = cls.load()
        entry = history.get(manga_title)
        return entry.last_chapter if entry else None

    @classmethod
    def update(
        cls,
        manga_title: str,
        chapter_number: str,
        chapter_id: str | None = None,
        manga_id: str | None = None,
        anilist_id: int | None = None,
    ) -> None:
        """Update reading progress.

        Args:
            manga_title: Manga title
            chapter_number: Chapter number read
            chapter_id: Optional MangaDex chapter ID
            manga_id: Optional MangaDex manga ID
            anilist_id: Optional AniList manga ID
        """
        history = cls.load()
        entry = history.get(manga_title)

        # Preserve existing AniList data if not provided
        if entry and not anilist_id:
            anilist_id = entry.anilist_id

        history[manga_title] = MangaHistoryEntry(
            last_chapter=chapter_number,
            last_chapter_id=chapter_id,
            manga_id=manga_id,
            anilist_id=anilist_id,
        )
        cls.save(history)


class DownloadedChaptersTracker:
    """Tracks and persists downloaded chapters across the application.

    Maintains a JSON file mapping manga IDs to their downloaded chapters
    with metadata like file size and download timestamp.
    """

    _downloads_file = get_data_path() / "manga_downloads.json"

    @classmethod
    def _ensure_dir(cls) -> None:
        """Ensure downloads directory exists."""
        cls._downloads_file.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _load_raw(cls) -> dict[str, Any]:
        """Load raw download state from JSON file.

        Returns:
            Dictionary mapping manga_id -> manga download state
        """
        cls._ensure_dir()

        if not cls._downloads_file.exists():
            return {}

        try:
            with cls._downloads_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    @classmethod
    def _save_raw(cls, data: dict[str, Any]) -> None:
        """Save raw download state to JSON file.

        Args:
            data: Download state dictionary
        """
        cls._ensure_dir()

        try:
            with cls._downloads_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            raise MangaError(f"Failed to save downloads: {e}")

    @classmethod
    def is_downloaded(cls, manga_id: str, chapter_number: str) -> bool:
        """Check if a chapter is already downloaded.

        Args:
            manga_id: Manga ID
            chapter_number: Chapter number (e.g., "42", "42.5")

        Returns:
            True if chapter is downloaded, False otherwise
        """
        data = cls._load_raw()
        manga_state = data.get(manga_id, {})
        downloaded = manga_state.get("downloaded_chapters", {})
        return chapter_number in downloaded

    @classmethod
    def mark_downloaded(
        cls,
        manga_id: str,
        manga_title: str,
        chapter_number: str,
        file_path: str,
        file_size_mb: float,
        source: str = "mangadex",
    ) -> None:
        """Mark a chapter as downloaded and persist metadata.

        Args:
            manga_id: Manga ID
            manga_title: Manga title for reference
            chapter_number: Chapter number
            file_path: Path to downloaded PDF file
            file_size_mb: File size in megabytes
            source: Source (default: "mangadex")
        """
        data = cls._load_raw()

        if manga_id not in data:
            data[manga_id] = {
                "manga_title": manga_title,
                "source": source,
                "downloaded_chapters": {},
                "last_download_at": None,
            }

        data[manga_id]["downloaded_chapters"][chapter_number] = {
            "file_path": file_path,
            "file_size_mb": file_size_mb,
            "downloaded_at": str(datetime.now()),
        }
        data[manga_id]["last_download_at"] = str(datetime.now())

        cls._save_raw(data)

    @classmethod
    def get_downloaded_chapters(cls, manga_id: str) -> dict[str, Any]:
        """Get all downloaded chapters for a manga.

        Args:
            manga_id: Manga ID

        Returns:
            Dictionary mapping chapter numbers to metadata
        """
        data = cls._load_raw()
        manga_state = data.get(manga_id, {})
        return manga_state.get("downloaded_chapters", {})

    @classmethod
    def get_download_path(cls, manga_id: str, chapter_number: str) -> str | None:
        """Get file path for a downloaded chapter.

        Args:
            manga_id: Manga ID
            chapter_number: Chapter number

        Returns:
            File path if downloaded, None otherwise
        """
        data = cls._load_raw()
        manga_state = data.get(manga_id, {})
        downloaded = manga_state.get("downloaded_chapters", {})
        chapter_data = downloaded.get(chapter_number)
        return chapter_data.get("file_path") if chapter_data else None

    @classmethod
    def cleanup_download(cls, manga_id: str, chapter_number: str) -> None:
        """Remove a chapter from the download tracker.

        Args:
            manga_id: Manga ID
            chapter_number: Chapter number
        """
        data = cls._load_raw()

        if manga_id in data:
            downloaded = data[manga_id].get("downloaded_chapters", {})
            if chapter_number in downloaded:
                del downloaded[chapter_number]
                cls._save_raw(data)


# ============================================================================
# SERVICE CLASSES
# ============================================================================


class UnifiedMangaService:
    """Unified manga service supporting multiple sources.

    Orchestrates multiple manga scraper plugins and provides a clean interface
    for the manga CLI.
    """

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

        # Track the last source where a manga was found (for search results)
        self.last_found_source: str | None = None

    def _load_metadata(self) -> None:
        """Load manga plugin metadata from file.

        Metadata maps manga_id to which plugin has it (e.g., {"manga-id": "mugiwaras"})
        This allows us to remember which plugin a manga was found in.
        Uses OrderedDict to implement LRU behavior.
        """
        self.manga_plugin_map: OrderedDict[str, str] = OrderedDict()
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    data = json.load(f)
                    # Load into OrderedDict, limiting to 1000 most recent
                    # Assuming the file stores them in some order, or just take first 1000
                    # For LRU, we want the most recent ones.
                    count = 0
                    for k, v in data.items():
                        self.manga_plugin_map[k] = v
                        count += 1
                        if count >= 1000:
                            break
            except Exception:
                self.manga_plugin_map = OrderedDict()

    def _save_metadata(self) -> None:
        """Save manga plugin metadata to file."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w") as f:
                # Save all entries from current in-memory map
                json.dump(dict(self.manga_plugin_map), f, indent=2)
        except Exception:
            pass  # Silently ignore save errors

    def _record_manga_in_plugin(self, manga_id: str, plugin_name: str) -> None:
        """Record which plugin a manga was found in with LRU eviction.

        Args:
            manga_id: The manga ID
            plugin_name: The plugin name that has this manga
        """
        if manga_id in self.manga_plugin_map:
            # Move to end (most recent)
            self.manga_plugin_map.move_to_end(manga_id)

        self.manga_plugin_map[manga_id] = plugin_name

        # Evict oldest if limit exceeded (1000 entries)
        if len(self.manga_plugin_map) > 1000:
            self.manga_plugin_map.popitem(last=False)

        self._save_metadata()

    def _get_known_plugin_for_manga(self, manga_id: str) -> str | None:
        """Get the plugin where a manga was previously found, updating LRU.

        Args:
            manga_id: The manga ID

        Returns:
            Plugin name or None if not found in metadata
        """
        if manga_id in self.manga_plugin_map:
            # Move to end (most recent)
            self.manga_plugin_map.move_to_end(manga_id)
            return self.manga_plugin_map[manga_id]
        return None

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
                # Record found manga in metadata and source
                for result in results:
                    self._record_manga_in_plugin(result.id, source_name)
                self.last_found_source = source_name
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
            logger.info(f"⚠️  Falha na fonte {source_name}: {e}")

        # Try fallback sources if no results or error
        logger.info("🔄 Tentando outras fontes...")

        all_sources = [s for s in self.config.preferred_sources if s in self.plugins]
        if source_name in all_sources:
            all_sources.remove(source_name)

        # Try each source in order
        for try_source in all_sources:
            try:
                logger.info(f"  Tentando {try_source}...")
                results = self._search_manga_from_source(query, try_source)
                if results:
                    logger.info(f"✓ Encontrados {len(results)} resultado(s) em {try_source}")
                    # Record found manga in metadata and source
                    for result in results:
                        self._record_manga_in_plugin(result.id, try_source)
                    self.last_found_source = try_source
                    return results
            except Exception:
                continue

        # If still no results, try any remaining sources not in preferred list
        for plugin_name in self.plugins:
            if plugin_name not in all_sources and plugin_name != source_name:
                try:
                    logger.info(f"  Tentando {plugin_name}...")
                    results = self._search_manga_from_source(query, plugin_name)
                    if results:
                        logger.info(f"✓ Encontrados {len(results)} resultado(s) em {plugin_name}")
                        # Record found manga in metadata and source
                        for result in results:
                            self._record_manga_in_plugin(result.id, plugin_name)
                        self.last_found_source = plugin_name
                        return results
                except Exception:
                    continue

        # No results in any source
        self.last_found_source = None
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
                    logger.info(
                        f"⚠️  Falha em {source_name}, tentando fonte conhecida {known_source}..."
                    )
                    return self._get_chapters_from_source(manga_id, manga_url, known_source)
                except Exception:
                    pass

            # Try other fallback sources
            fallback_source = self._get_fallback_source(source_name)
            if fallback_source:
                logger.info(f"⚠️  Tentando fallback {fallback_source}...")
                try:
                    return self._get_chapters_from_source(manga_id, None, fallback_source)
                except Exception as fallback_error:
                    logger.info(f"⚠️  Falha no fallback {fallback_source}: {fallback_error}")

            # Re-raise the original error
            raise e

    def _get_chapters_from_source(
        self, manga_id: str, manga_url: str | None, source_name: str
    ) -> list[ChapterData]:
        """Get chapters from a specific source.

        Calls the plugin's get_chapters() method and converts results to ChapterData objects.
        Validates that chapter URLs are populated by the plugin (no CLI-side URL construction).

        Args:
            manga_id: Manga ID
            manga_url: Optional manga URL
            source_name: Source name

        Returns:
            List of ChapterData objects with URLs populated by plugins
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
                # Validate URL is populated by plugin
                url = item.get("url")
                if not url:
                    logger.info(f"⚠️  Capítulo {item['id']} de {source_name} sem URL extraída")

                chapter = ChapterData(
                    id=item["id"],
                    number=item["number"],
                    title=item.get("title"),
                    url=url,  # Store chapter URL from plugin if available
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


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================


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
