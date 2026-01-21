"""Manga CLI - read manga from MangaDex.

Command-line interface for searching and reading manga chapters.
Uses MangaDexClient service layer with Rich menus and loading spinners.
"""

import os
import shutil
import subprocess

from InquirerPy import inquirer

from models.config import settings
from models.models import LocalChapter, Status
from services.anilist_service import anilist_client
from services.manga_service import (
    MangaDexError,
    MangaHistory,
    MangaNotFoundError,
)
from services.unified_manga_service import UnifiedMangaService
from ui.components import loading, menu_navigate
from utils.manga_reader import is_zathura_running, open_pdf_reader
from utils.pdf_converter import create_pdf_from_images
from utils.manga_source_preferences import manga_source_preferences
from utils.manga_selection_preferences import manga_selection_preferences


def _find_image_viewer() -> str | None:
    """Find an available image viewer on the system.

    Checks (in order of preference):
    - MANGA_VIEWER env var (custom preference)
    - yacreader: Dedicated manga/comic reader (BEST for manga!)
    - eog: Eye of GNOME (standard GNOME viewer)
    - nomacs: Modern cross-platform viewer
    - geeqie: Advanced viewer with many features
    - ristretto: XFCE image viewer
    - gpicview: Lightweight viewer
    - viewnior: GTK image viewer
    - display: ImageMagick (always available)
    - open: macOS Preview

    Returns:
        Path to image viewer executable or None if not found
    """
    # Check for user override
    custom_viewer = os.environ.get("MANGA_VIEWER")
    if custom_viewer and shutil.which(custom_viewer):
        return custom_viewer

    # List of viewers in order of preference
    viewers = [
        "yacreader",  # Dedicated manga/comic reader (BEST!)
        "eog",  # GNOME default
        "nomacs",  # Modern and cross-platform
        "geeqie",  # Feature-rich
        "ristretto",  # XFCE viewer
        "gpicview",  # Lightweight
        "viewnior",  # GTK viewer
        "display",  # ImageMagick fallback
        "open",  # macOS Preview
    ]

    for viewer in viewers:
        if shutil.which(viewer):
            return viewer
    return None


def open_viewer(dir_path: str) -> None:
    """Open image viewer for downloaded chapter.

    Args:
        dir_path: Path to chapter directory
    """
    viewer = _find_image_viewer()
    if not viewer:
        print(
            "⚠️  Nenhum visualizador de imagens encontrado.\n"
            "   Recomendamos: sxiv (rápido), eog (padrão GNOME), ou nomacs (moderno)\n"
            "   Ou customize com: export MANGA_VIEWER=seu_viewer"
        )
        print(f"   As imagens foram salvas em: {dir_path}")
        return

    try:
        if viewer == "open":  # macOS
            subprocess.Popen(["open", "-a", "Preview", dir_path])
        elif viewer == "sxiv":
            # Open sxiv with proper flags for manga reading
            # -a: auto-fit to window, -s: slideshow mode disabled by default
            # -i: read file list from stdin (ensures correct order)
            from pathlib import Path

            files = sorted(Path(dir_path).glob("*.png"))
            if files:
                # Start sxiv in a way that accepts keyboard input properly
                subprocess.run([viewer, "-a", str(dir_path)])
            else:
                print(f"⚠️  Nenhuma imagem encontrada em: {dir_path}")
        else:
            subprocess.Popen([viewer, dir_path])
    except Exception as e:
        print(f"⚠️  Erro ao abrir {viewer}: {e}")
        print(f"   As imagens foram salvas em: {dir_path}")
        print("   Customize com: export MANGA_VIEWER=seu_viewer")


def _show_manga_main_menu() -> str | None:
    """Show main manga menu with options.

    Returns:
        Selected menu option or None if user exits
    """
    menu_options = [
        "📖 Reading",
        "✅ Completed",
        "📋 Planning",
        "📅 Recent",
        "📈 Trending",
        "🔍 Search",
        "📂 Local Library",
    ]

    return menu_navigate(menu_options, "Manga Tupi - Menu Principal")


def _handle_reading_list(service: UnifiedMangaService) -> None:
    """Handle reading list from AniList."""
    if not anilist_client.is_authenticated():
        print("🔐 Faça login primeiro: uv run python main.py anilist auth")
        input("Pressione Enter para continuar...")
        return

    with loading("Carregando lista de leitura..."):
        manga_list = anilist_client.get_user_manga_list("CURRENT")

    if not manga_list:
        print("📂 Nenhum mangá na lista de leitura")
        input("Pressione Enter para continuar...")
        return

    # Format options
    options = []
    manga_map = {}
    for i, manga in enumerate(manga_list, 1):
        if manga.media:
            title = anilist_client.format_title(manga.media.title)
            progress = manga.progress or 0
            total_chapters = getattr(manga.media, "chapters", None) or "?"
            display = f"{i:2d}. {title} - Cap. {progress}/{total_chapters}"
            options.append(display)
            manga_map[display] = title

    selection = menu_navigate(options, "Reading - Manga")
    if selection and selection != "← Voltar":
        try:
            idx = int(selection.split(".")[0]) - 1
            if 0 <= idx < len(manga_list):
                manga_title = manga_map[selection]
                _start_manga_search(service, manga_title)
        except (ValueError, IndexError):
            pass


def _handle_completed_list(service: UnifiedMangaService) -> None:
    """Handle completed list from AniList."""
    if not anilist_client.is_authenticated():
        print("🔐 Faça login primeiro: uv run python main.py anilist auth")
        input("Pressione Enter para continuar...")
        return

    with loading("Carregando lista completos..."):
        manga_list = anilist_client.get_user_manga_list("COMPLETED")

    if not manga_list:
        print("📂 Nenhum mangá completado")
        input("Pressione Enter para continuar...")
        return

    # Format options
    options = []
    manga_map = {}
    for i, manga in enumerate(manga_list, 1):
        if manga.media:
            title = anilist_client.format_title(manga.media.title)
            chapters = getattr(manga.media, "chapters", None) or "?"
            score = getattr(manga.media, "averageScore", None) or "N/A"
            display = f"{i:2d}. {title} ({chapters} caps) ⭐{score}%"
            options.append(display)
            manga_map[display] = title

    selection = menu_navigate(options, "Completed - Manga")
    if selection and selection != "← Voltar":
        try:
            idx = int(selection.split(".")[0]) - 1
            if 0 <= idx < len(manga_list):
                manga_title = manga_map[selection]
                _start_manga_search(service, manga_title)
        except (ValueError, IndexError):
            pass


def _handle_planning_list(service: UnifiedMangaService) -> None:
    """Handle planning list from AniList."""
    if not anilist_client.is_authenticated():
        print("🔐 Faça login primeiro: uv run python main.py anilist auth")
        input("Pressione Enter para continuar...")
        return

    with loading("Carregando lista planejados..."):
        manga_list = anilist_client.get_user_manga_list("PLANNING")

    if not manga_list:
        print("📂 Nenhum mangá planejado")
        input("Pressione Enter para continuar...")
        return

    # Format options
    options = []
    manga_map = {}
    for i, manga in enumerate(manga_list, 1):
        if manga.media:
            title = anilist_client.format_title(manga.media.title)
            chapters = getattr(manga.media, "chapters", None) or "?"
            score = getattr(manga.media, "averageScore", None) or "N/A"
            display = f"{i:2d}. {title} ({chapters} caps) ⭐{score}%"
            options.append(display)
            manga_map[display] = title

    selection = menu_navigate(options, "Planning - Manga")
    if selection and selection != "← Voltar":
        try:
            idx = int(selection.split(".")[0]) - 1
            if 0 <= idx < len(manga_list):
                manga_title = manga_map[selection]
                _start_manga_search(service, manga_title)
        except (ValueError, IndexError):
            pass


def _handle_recent_history(service: UnifiedMangaService) -> None:
    """Handle recent manga reading history."""
    # Get history from the JSON file directly
    try:
        import json
        from models.config import get_data_path

        history_file = get_data_path() / "manga_history.json"

        if not history_file.exists():
            print("📂 Nenhum histórico recente")
            input("Pressione Enter para continuar...")
            return

        with history_file.open() as f:
            history_data = json.load(f)

        if not history_data:
            print("📂 Histórico vazio")
            input("Pressione Enter para continuar...")
            return

        # Get unique recent manga titles (last 10)
        recent_manga = list(history_data.items())[:10]

        # Format options
        options = []
        for i, (title, data) in enumerate(recent_manga, 1):
            # Handle different data formats
            if isinstance(data, dict) and "last_chapter" in data:
                chapter = data["last_chapter"]
            elif isinstance(data, list) and len(data) > 1:
                chapter = data[1] + 1  # Convert from 0-indexed
            else:
                chapter = "Desconhecido"

            display = f"{i:2d}. {title} - Cap. {chapter}"
            options.append(display)

        selection = menu_navigate(options, "Recent - Manga")
        if selection and selection != "← Voltar":
            try:
                idx = int(selection.split(".")[0]) - 1
                if 0 <= idx < len(recent_manga):
                    title, _ = recent_manga[idx]
                    _start_manga_search(service, title)
            except (ValueError, IndexError):
                pass

    except Exception as e:
        print(f"❌ Erro ao carregar histórico: {e}")
        input("Pressione Enter para continuar...")


def _handle_trending(service: UnifiedMangaService) -> None:
    """Handle trending manga from AniList."""
    with loading("Carregando trending manga..."):
        manga_list = anilist_client.get_trending_manga()

    if not manga_list:
        print("📂 Nenhum mangá trending encontrado")
        input("Pressione Enter para continuar...")
        return

    # Format options
    options = []
    manga_map = {}
    for i, manga in enumerate(manga_list, 1):
        title = anilist_client.format_title(manga.title)
        chapters = getattr(manga, "chapters", None) or "?"
        score = getattr(manga, "averageScore", None) or "N/A"
        display = f"{i:2d}. {title} ({chapters} caps) ⭐{score}%"
        options.append(display)
        manga_map[display] = title

    selection = menu_navigate(options, "Trending - Manga")
    if selection and selection != "← Voltar":
        try:
            idx = int(selection.split(".")[0]) - 1
            if 0 <= idx < len(manga_list):
                manga_title = manga_map[selection]
                _start_manga_search(service, manga_title)
        except (ValueError, IndexError):
            pass


def _start_manga_search(service: UnifiedMangaService, title: str) -> None:
    """Start manga search for given title."""
    # Search with loading spinner
    try:
        with loading(f"Buscando '{title}' em {service.current_source}..."):
            results = service.search_manga(title.strip())
    except MangaNotFoundError:
        print("❌ Mangá não encontrado. Tente outra pesquisa.")
        return
    except MangaDexError as e:
        print(f"⚠️  {e.user_message}")
        return
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return

    if not results:
        print("❌ Nenhum mangá encontrado. Tente outra pesquisa.")
        return

    # Check for saved manga preference
    preferred_manga_id = manga_selection_preferences.get_preferred_manga_id(title)
    selected_manga = None

    # Try to find preferred manga in results
    if preferred_manga_id:
        for manga in results:
            if manga.id == preferred_manga_id:
                selected_manga = manga
                print(f"✓ Usando manga salvo: {manga.title}")
                break

    # Select manga if not found in preferences or multiple results
    if not selected_manga:
        if len(results) > 1:
            manga_titles = []
            for manga in results:
                # Check if this is the saved preference
                if manga.id == preferred_manga_id:
                    manga_titles.append(f"⭐ {manga.title} (salvo)")
                else:
                    manga_titles.append(manga.title)

            try:
                selected_title = menu_navigate(manga_titles, "Selecione mangá")
                if selected_title is None:
                    return
                # Remove star and (salvo) indicators if present
                clean_title = selected_title.replace("⭐ ", "").replace(" (salvo)", "")
                selected_manga = next(m for m in results if m.title == clean_title)
            except KeyboardInterrupt:
                return
        else:
            selected_manga = results[0]

    # Save this manga preference
    manga_selection_preferences.set_preferred_manga_id(title, selected_manga.id)
    print(f"✓ Preferência salva: {selected_manga.title}")

    # Continue with normal manga flow
    _continue_manga_flow(service, selected_manga, allow_source_change=True)


def _continue_manga_flow(
    service: UnifiedMangaService, selected_manga, allow_source_change: bool = True
) -> None:
    """Continue with chapter selection and reading for selected manga."""
    selected_source = service.current_source

    # Allow user to change source if requested
    if allow_source_change:
        available_sources = service.get_available_sources()
        if len(available_sources) > 1:
            # Check if user has a saved preference
            saved_source = manga_source_preferences.get_preferred_source(selected_manga.title)

            # Build menu options
            menu_options = [f"📖 Ler com {service.current_source}"]
            if saved_source and saved_source != service.current_source:
                menu_options.append(f"⭐ Usar fonte salva: {saved_source}")

            for source in available_sources:
                if source != service.current_source:
                    menu_options.append(f"🔄 Trocar para: {source}")

            try:
                action = menu_navigate(
                    menu_options, f"{selected_manga.title} - Fonte: {service.current_source}"
                )
            except KeyboardInterrupt:
                return

            if action is None:
                # User selected "← Voltar"
                return
            elif action and action.startswith("⭐ Usar fonte salva:"):
                # Use saved source
                new_source = action.split(": ")[1]
                if service.set_source(new_source):
                    selected_source = new_source
                    print(f"✓ Fonte alterada para: {new_source}")
            elif action and action.startswith("🔄 Trocar para:"):
                # Change to selected source
                new_source = action.split(": ")[1]
                if service.set_source(new_source):
                    selected_source = new_source
                    # Save this preference
                    manga_source_preferences.set_preferred_source(selected_manga.title, new_source)
                    print(f"✓ Fonte alterada e salva: {new_source}")
                else:
                    print(f"❌ Falha ao alterar fonte para: {new_source}")
                    return

    # Save current source preference if not already saved
    current_saved = manga_source_preferences.get_preferred_source(selected_manga.title)
    if current_saved != selected_source:
        manga_source_preferences.set_preferred_source(selected_manga.title, selected_source)

    # Construct manga URL for scrapers that need it
    manga_url = None
    if selected_source == "mugiwaras":
        manga_url = f"https://mugiwarasoficial.com/manga/{selected_manga.id}/"
    elif selected_source == "mangadex":
        manga_url = f"https://mangadex.org/title/{selected_manga.id}"

    # Load chapters with loading spinner
    try:
        with loading(f"Carregando capítulos de {selected_source}..."):
            chapters = service.get_chapters(
                selected_manga.id, manga_url=manga_url, source=selected_source
            )
    except MangaDexError as e:
        print(f"⚠️  {e.user_message}")
        # Try other sources if this fails
        if allow_source_change:
            print("🔄 Tentando outras fontes...")
            available_sources = service.get_available_sources()
            for fallback_source in available_sources:
                if fallback_source != selected_source:
                    print(f"  Tentando {fallback_source}...")
                    try:
                        if service.set_source(fallback_source):
                            if fallback_source == "mugiwaras":
                                manga_url = (
                                    f"https://mugiwarasoficial.com/manga/{selected_manga.id}/"
                                )
                            elif fallback_source == "mangadex":
                                manga_url = f"https://mangadex.org/title/{selected_manga.id}"

                            chapters = service.get_chapters(
                                selected_manga.id, manga_url=manga_url, source=fallback_source
                            )
                            selected_source = fallback_source
                            manga_source_preferences.set_preferred_source(
                                selected_manga.title, fallback_source
                            )
                            print(f"✓ Usando fonte alternativa: {fallback_source}")
                            break
                    except Exception:
                        continue
            else:
                return
        else:
            return
    except Exception as e:
        print(f"❌ Erro ao carregar capítulos: {e}")
        return

    if not chapters:
        print("❌ Nenhum capítulo disponível")
        return

    # Sort chapters in ascending order (1 → 2 → 3 → ...)
    chapters.reverse()

    # Load reading history
    history = MangaHistory()
    last_chapter = history.get_last_chapter(selected_manga.title)

    # Check AniList progress if authenticated
    anilist_progress = None
    if anilist_client.is_authenticated():
        try:
            # Get user's manga list and search for matching title
            manga_list = anilist_client.get_user_manga_list("CURRENT")
            if manga_list:
                # Try to find exact or partial title match
                selected_title = selected_manga.title.lower()
                for entry in manga_list:
                    if entry.media:
                        entry_title = ""
                        if entry.media.title.romaji:
                            entry_title = entry.media.title.romaji.lower()
                        elif entry.media.title.english:
                            entry_title = entry.media.title.english.lower()

                        # Check for exact match or partial match
                        if (
                            selected_title == entry_title
                            or selected_title in entry_title
                            or entry_title in selected_title
                        ):
                            if entry.progress:
                                anilist_progress = entry.progress
                                break
        except Exception:
            pass  # Silently ignore AniList errors

    # Determine the recommended chapter to read
    recommended_chapter_num = None
    resume_source = ""

    if anilist_progress is not None:
        recommended_chapter_num = anilist_progress + 1
        resume_source = "AniList"
    elif last_chapter:
        # Extract chapter number from local history (format might be "1", "2", etc.)
        try:
            recommended_chapter_num = int(float(last_chapter)) + 1
            resume_source = "local"
        except (ValueError, TypeError):
            pass

    # Format chapter labels for display
    chapter_labels = [ch.display_name() for ch in chapters]

    # Show resume hint if applicable - prioritize AniList progress
    if recommended_chapter_num:
        # Find the chapter index that matches the recommended chapter
        recommended_index = None
        for i, chapter in enumerate(chapters):
            try:
                chapter_num = int(float(chapter.number))
                if chapter_num == recommended_chapter_num:
                    recommended_index = i
                    break
            except (ValueError, TypeError):
                continue

        # If found, move it to top with resume hint
        if recommended_index is not None:
            # Create resume label
            resume_label = f"⮕ Retomar ({resume_source}) - {chapter_labels[recommended_index]}"

            # Move recommended chapter to top
            recommended_chapter = chapters.pop(recommended_index)
            chapter_labels.pop(recommended_index)

            chapters.insert(0, recommended_chapter)
            chapter_labels.insert(0, resume_label)
        elif not any("Retomar" in label for label in chapter_labels):
            # Fallback to first chapter if no exact match found
            chapter_labels[0] = f"⮕ Retomar ({resume_source}) - {chapter_labels[0]}"

    # Chapter selection loop
    current_index = 0
    auto_load_next = False
    while True:
        # Only show chapter selection menu if not auto-loading next
        if not auto_load_next:
            try:
                selected_label = menu_navigate(chapter_labels, "Selecione capítulo")
            except KeyboardInterrupt:
                return

            if not selected_label:
                # User selected "← Voltar" - return to previous menu
                return

            # Find actual chapter (strip resume hint)
            display_label = selected_label.replace("⮕ Retomar - ", "")
            current_index = next(
                i
                for i, label in enumerate(chapter_labels)
                if label.replace("⮕ Retomar - ", "") == display_label
            )

        auto_load_next = False  # Reset flag for next iteration
        selected_chapter = chapters[current_index]

        # Show action menu (Read Now or Download for Later)
        action = _show_chapter_action_menu()

        if action is None:
            # User selected back - go back to chapter selection
            continue
        elif action == "read":
            # Continue with read now (existing behavior)
            _handle_read_now(
                service,
                selected_manga,
                selected_chapter,
                manga_url,
                selected_source,
                history,
                chapters,
                chapter_labels,
                current_index,
            )
        elif action == "download":
            # Handle download for later
            _handle_download_for_later(
                service,
                selected_manga,
                selected_chapter,
                manga_url,
                selected_source,
                history,
            )


def _show_chapter_action_menu() -> str | None:
    """Show action menu after chapter selection (Read Now or Download for Later).

    Returns:
        Selected action: "read", "download", or None for back
    """
    actions = [
        "📖 Ler Agora (Read Now)",
        "⬇️  Baixar para Depois (Download for Later)",
        "↩️  Voltar (Back)",
    ]

    selection = menu_navigate(actions, "O que deseja fazer?")

    if selection is None or selection == "↩️  Voltar (Back)":
        return None
    elif "📖" in selection:
        return "read"
    elif "⬇️" in selection:
        return "download"

    return None


def _prompt_download_range(
    last_chapter: str | None, available_chapters: list, default_count: int = 5
) -> list | None:
    """Prompt user for chapter range to download.

    Args:
        last_chapter: Last read chapter number
        available_chapters: List of available ChapterData objects
        default_count: Default number to download

    Returns:
        List of ChapterData objects to download, or None if cancelled
    """
    from utils.range_parser import parse_range_input

    # Get chapter numbers as strings
    chapter_numbers = [ch.number for ch in available_chapters]

    # Build prompt with context
    prompt_text = "Quantos capítulos deseja baixar?\n"
    if last_chapter:
        prompt_text += f"  (último lido: {last_chapter})\n"
    prompt_text += f"  (padrão: {default_count}, próximos após o último)\n\n"
    prompt_text += "Digite número ou intervalo:\n"
    prompt_text += '  • "5" → Próximos 5 capítulos\n'
    prompt_text += '  • "3-10" → Capítulos 3-10\n'
    prompt_text += '  • "all" → Todos disponíveis\n'
    prompt_text += "  (Enter para padrão)"

    try:
        user_input = inquirer.text(message=prompt_text).execute()  # type: ignore[attr-defined]
    except KeyboardInterrupt:
        return None

    if user_input is None:
        return None

    try:
        selected_chapters = parse_range_input(
            user_input.strip(),
            last_chapter=last_chapter,
            available_chapters=chapter_numbers,
            default_count=default_count,
        )
    except ValueError as e:
        print(f"❌ {e}")
        print("Voltando...")
        return None

    # Map chapter numbers back to ChapterData objects
    chapter_map = {ch.number: ch for ch in available_chapters}
    result = [chapter_map[num] for num in selected_chapters if num in chapter_map]

    if not result:
        print("❌ Nenhum capítulo selecionado")
        return None

    return result


def _handle_read_now(
    service,
    selected_manga,
    selected_chapter,
    manga_url,
    selected_source,
    history,
    chapters,
    chapter_labels,
    current_index,
) -> None:
    """Handle read now flow (existing behavior).

    Opens chapter immediately and updates history.
    """
    _process_chapter(
        service,
        selected_manga,
        selected_chapter,
        manga_url,
        selected_source,
        history,
        chapters,
        chapter_labels,
        current_index,
    )


def _handle_download_for_later(
    service,
    selected_manga,
    selected_chapter,
    manga_url,
    selected_source,
    history,
) -> None:
    """Handle download for later flow.

    Downloads chapter(s) without opening reader and returns to menu.
    """
    from services.manga_service import DownloadedChaptersTracker

    config = settings.manga

    # Get all chapters for this manga
    try:
        with loading(f"Carregando capítulos de {selected_source}..."):
            all_chapters = service.get_chapters(
                selected_manga.id, manga_url=manga_url, source=selected_source
            )
    except Exception as e:
        print(f"❌ Erro ao carregar capítulos: {e}")
        return

    if not all_chapters:
        print("❌ Nenhum capítulo disponível")
        return

    all_chapters.reverse()  # Sort ascending

    # Get last read chapter
    last_chapter = history.get_last_chapter(selected_manga.title)

    # Prompt for range
    chapters_to_download = _prompt_download_range(
        last_chapter,
        all_chapters,
        default_count=config.default_download_range,
    )

    if not chapters_to_download:
        return

    # Check for already downloaded chapters
    tracker = DownloadedChaptersTracker()
    already_downloaded = []
    new_chapters = []

    for chapter in chapters_to_download:
        if tracker.is_downloaded(selected_manga.id, chapter.number):
            already_downloaded.append(chapter)
        else:
            new_chapters.append(chapter)

    # Handle already-downloaded chapters if skip enabled
    if already_downloaded and config.skip_already_downloaded:
        if already_downloaded:
            skip_msg = (
                f"{len(already_downloaded)} capítulo(s) já baixado(s). Continuar apenas com novos?"
            )
            confirm_options = ["✅ Sim, continuar", "❌ Cancelar", "🔄 Re-baixar todos"]
            confirm = menu_navigate(confirm_options, skip_msg)

            if confirm == "❌ Cancelar":
                return
            elif confirm == "🔄 Re-baixar todos":
                new_chapters = chapters_to_download
            # else: continue with just new_chapters

    if not new_chapters:
        print(f"✓ Todos os {len(already_downloaded)} capítulo(s) já estão baixados")
        return

    # Download chapters
    print(f"\n📥 Baixando {len(new_chapters)} capítulo(s)...")

    import requests
    from tqdm import tqdm

    successful = 0
    failed = []

    for chapter_idx, chapter in enumerate(new_chapters, 1):
        print(f"\n[{chapter_idx}/{len(new_chapters)}] Capítulo {chapter.number}...")

        try:
            # Construct chapter URL
            chapter_url = None
            if selected_source == "mugiwaras":
                chapter_url = f"{manga_url}{chapter.id}/"
            elif selected_source == "mangadex":
                chapter_url = f"https://mangadex.org/chapter/{chapter.id}"

            # Get chapter pages
            with loading("Carregando páginas..."):
                pages = service.get_chapter_pages(
                    chapter.id, chapter_url=chapter_url, source=selected_source
                )

            if not pages:
                print(f"⚠️  Nenhuma página disponível para capítulo {chapter.number}")
                failed.append(chapter.number)
                continue

            # Create output directory
            output_path = config.output_directory / selected_manga.title / chapter.number
            output_path.mkdir(parents=True, exist_ok=True)

            # Define PDF path
            pdf_path = output_path / f"{chapter.number}.pdf"

            # Download pages
            print(f"Baixando {len(pages)} páginas...")
            valid_downloads = 0
            for i, url in enumerate(tqdm(pages, desc="Download")):
                from pathlib import Path as UrlPath

                ext = UrlPath(url.split("?")[0]).suffix or ".png"
                img_path = output_path / f"{i:03d}{ext}"
                if not img_path.exists():
                    try:
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()

                        # Validate content is actually an image
                        content_type = response.headers.get("content-type", "").lower()
                        if not content_type.startswith("image/"):
                            continue

                        img_data = response.content
                        if len(img_data) < 1024:  # Skip very small files (likely errors)
                            continue

                        img_path.write_bytes(img_data)
                        valid_downloads += 1
                    except Exception:
                        continue  # Skip failed downloads
                else:
                    valid_downloads += 1

            print(f"✓ {valid_downloads} imagens válidas baixadas")

            # Create PDF
            print("📄 Criando PDF...")
            create_pdf_from_images(
                output_path,
                pdf_path,
                quality=config.pdf_quality,
            )

            # Delete images if configured
            if config.delete_images_after_pdf:
                for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                    for img in output_path.glob(ext):
                        img.unlink()

            # Track download
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            tracker.mark_downloaded(
                selected_manga.id,
                selected_manga.title,
                chapter.number,
                str(pdf_path),
                file_size_mb,
                source=selected_source,
            )

            print(f"✓ Capítulo {chapter.number} baixado ({file_size_mb:.1f} MB)")
            successful += 1

        except Exception as e:
            print(f"❌ Erro ao baixar capítulo {chapter.number}: {e}")
            failed.append(chapter.number)
            try:
                # Ask if user wants to continue
                continue_options = ["✅ Continuar", "❌ Cancelar"]
                if menu_navigate(continue_options, "Continuar com próximo capítulo?"):
                    continue
                else:
                    break
            except Exception:
                break

    # Summary
    print(f"\n✓ Download concluído: {successful} capítulo(s) baixados")
    if failed:
        print(f"⚠️  {len(failed)} capítulo(s) falharam: {', '.join(failed)}")

    input("Pressione Enter para voltar ao menu...")


def _process_chapter(
    service,
    selected_manga,
    selected_chapter,
    manga_url,
    selected_source,
    history,
    chapters,
    chapter_labels,
    current_index,
) -> None:
    """Process individual chapter reading."""
    config = settings.manga

    # Construct chapter URL for scrapers that need it
    chapter_url = None
    if selected_source == "mugiwaras":
        # For MugiwarasOficial, reconstruct URL from manga URL and chapter ID
        chapter_url = f"{manga_url}{selected_chapter.id}/"
    elif selected_source == "mangadex":
        chapter_url = f"https://mangadex.org/chapter/{selected_chapter.id}"

    # Load chapter pages
    try:
        with loading("Carregando páginas..."):
            pages = service.get_chapter_pages(
                selected_chapter.id, chapter_url=chapter_url, source=selected_source
            )
    except MangaDexError as e:
        print(f"⚠️  {e.user_message}")
        return
    except Exception as e:
        print(f"❌ Erro ao carregar páginas: {e}")
        return

    if not pages:
        print("❌ Nenhuma página disponível para este capítulo")
        return

    # Create output directory
    output_path = config.output_directory / selected_manga.title / selected_chapter.number
    output_path.mkdir(parents=True, exist_ok=True)

    # Define PDF path
    pdf_path = output_path / f"{selected_chapter.number}.pdf"

    # Check if PDF already exists
    if pdf_path.exists():
        print("📖 Abrindo capítulo existente...")
    else:
        # Download pages
        print(f"Baixando {len(pages)} páginas...")
        try:
            import requests
            from tqdm import tqdm

            for i, url in enumerate(tqdm(pages, desc="Download")):
                # Extract file extension from URL (webp, png, jpg, etc.)
                from pathlib import Path as UrlPath

                ext = UrlPath(url.split("?")[0]).suffix or ".png"
                img_path = output_path / f"{i:03d}{ext}"
                if not img_path.exists():
                    img_data = requests.get(url, timeout=10).content
                    img_path.write_bytes(img_data)

            if not config.auto_create_pdf:
                print(f"✓ Capítulo salvo em: {output_path}")
                return

            # Create PDF from downloaded images
            print("📄 Criando PDF...")
            create_pdf_from_images(
                output_path,
                pdf_path,
                quality=config.pdf_quality,
            )

            # Optional: Delete images after PDF creation
            if config.delete_images_after_pdf:
                for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                    for img in output_path.glob(ext):
                        img.unlink()
                print("🗑️  Imagens removidas (mantendo apenas PDF)")

            print(f"✓ PDF criado: {pdf_path}")

        except Exception as e:
            print(f"❌ Erro ao processar capítulo: {e}")
            return

    # Open PDF reader
    open_pdf_reader(pdf_path)

    # Save reading progress
    history.update(
        selected_manga.title,
        selected_chapter.number,
        chapter_id=selected_chapter.id,
        manga_id=selected_manga.id,
    )

    # Check if Zathura is still running before showing action menu
    if is_zathura_running():
        print("📖 Feche o Zathura para continuar.")
        # Wait for Zathura to close
        while is_zathura_running():
            import time

            time.sleep(1)  # Check every second
        print("✓ Zathura fechado. Continuando...")

    # AniList progress confirmation (if authenticated)
    if anilist_client.is_authenticated():
        try:
            # Ask if user completed the chapter
            confirm_options = ["✅ Sim, li até o final", "❌ Não, parei antes"]
            confirm = menu_navigate(
                confirm_options, f"Você leu o capítulo {selected_chapter.number} até o final?"
            )

            if confirm == "✅ Sim, li até o final":
                # Try to find manga in AniList by title
                search_results = anilist_client.search_manga(selected_manga.title)
                if search_results:
                    # Simple title matching - could be improved with fuzzy matching
                    best_match = search_results[0]  # Take first result for now

                    # Get current list entry or create new one
                    list_entry = anilist_client.get_manga_list_entry(best_match.id)

                    # Update progress
                    chapter_num = int(float(selected_chapter.number))
                    if anilist_client.update_manga_progress(best_match.id, chapter_num):
                        print(
                            f"✓ Progresso atualizado no AniList: {selected_manga.title} - Cap. {selected_chapter.number}"
                        )

                        # Auto-change status if this is first chapter read
                        if not list_entry or list_entry.status == "PLANNING":
                            anilist_client.change_manga_status(best_match.id, Status.CURRENT)
                            print("✓ Status alterado para: Lendo")
                    else:
                        print("⚠️  Falha ao atualizar progresso no AniList")
                else:
                    print(f"⚠️  Mangá não encontrado no AniList: {selected_manga.title}")
            else:
                print("✓ Progresso não atualizado no AniList (capítulo não concluído)")
        except Exception as e:
            print(f"⚠️  Erro ao sincronizar com AniList: {e}")

    # Ask for next action
    try:
        action = menu_navigate(["Próximo", "Anterior", "Ler novamente"], "O que deseja fazer?")
    except KeyboardInterrupt:
        return

    if action == "Sair":
        return

    if action is None:
        # User selected "← Voltar" - go back to chapter selection
        return

    # Handle action
    auto_load_next = False  # Initialize flag
    if action == "Próximo":
        # Find next chapter by number instead of array position
        current_chapter_num = float(selected_chapter.number)
        next_chapter_index = None

        for i, chapter in enumerate(chapters):
            if float(chapter.number) > current_chapter_num:
                next_chapter_index = i
                break

        if next_chapter_index is not None:
            current_index = next_chapter_index
            # Remove resume hint from current chapter
            chapter_labels[current_index] = chapter_labels[current_index].replace(
                "⮕ Retomar - ", ""
            )
            # Set flag to skip chapter selection menu and auto-load next
            auto_load_next = True
        else:
            print("Você chegou ao final dos capítulos disponíveis")
            return
    elif action == "Anterior":
        # Move to previous chapter if available
        if current_index - 1 >= 0:
            current_index -= 1
            # Remove resume hint from current chapter
            chapter_labels[current_index] = chapter_labels[current_index].replace(
                "⮕ Retomar - ", ""
            )
            # Set flag to skip chapter selection menu and auto-load previous
            auto_load_next = True
        else:
            print("Você está no primeiro capítulo")
            # Re-open current chapter
            auto_load_next = True
    elif action == "Ler novamente":
        # Re-open current chapter
        auto_load_next = True

    # If auto_load_next is set, process the next/previous/current chapter
    if auto_load_next:
        # Update current chapter reference before calling recursively
        selected_chapter = chapters[current_index]

        # Update chapter URL for new chapter
        chapter_url = None
        if selected_source == "mugiwaras":
            chapter_url = f"{manga_url}{selected_chapter.id}/"
        elif selected_source == "mangadex":
            chapter_url = f"https://mangadex.org/chapter/{selected_chapter.id}"

        # Process the chapter recursively
        _process_chapter(
            service,
            selected_manga,
            selected_chapter,
            manga_url,
            selected_source,
            history,
            chapters,
            chapter_labels,
            current_index,
        )


def _handle_local_library() -> None:
    """Handle local library browsing (offline mode)."""
    from services.local_manga_service import LocalMangaService

    config = settings.manga
    local_service = LocalMangaService(config.output_directory)

    # Scan library
    with loading("Escaneando biblioteca local..."):
        manga_list = local_service.get_manga_list()

    if not manga_list:
        print("📂 Nenhum mangá baixado encontrado")
        print(f"   Diretório: {config.output_directory}")
        input("Pressione Enter para continuar...")
        return

    # Show manga selection with back button
    selection = menu_navigate(manga_list, "Local Library - Selecione Mangá")
    if selection is None:
        return

    # Extract manga title (remove " (X caps)" suffix)
    manga_title = selection.split(" (")[0]

    # Show chapters for selected manga
    _show_local_chapters(local_service, manga_title)


def _show_local_chapters(local_service: "LocalMangaService", manga_title: str) -> None:
    """Show chapters for selected manga from local library.

    Args:
        local_service: LocalMangaService instance
        manga_title: Manga title (directory name)
    """
    # Load chapters
    with loading("Carregando capítulos..."):
        chapters = local_service.get_chapters_for_manga(manga_title)

    if not chapters:
        print(f"❌ Nenhum capítulo encontrado para: {manga_title}")
        input("Pressione Enter para continuar...")
        return

    # Check reading history for resume hint
    history = MangaHistory()
    last_chapter = history.get_last_chapter(manga_title)

    # Build chapter menu
    chapter_labels = [ch.display_name() for ch in chapters]

    # Add resume hint if applicable (⮕ Retomar)
    if last_chapter:
        for i, ch in enumerate(chapters):
            if ch.chapter_number == last_chapter:
                chapter_labels[i] = f"⮕ Retomar: {chapter_labels[i]}"
                break

    # Chapter selection loop
    while True:
        selected_label = menu_navigate(chapter_labels, f"{manga_title} - Selecione capítulo")
        if not selected_label:
            return

        # Find selected chapter (handle resume prefix)
        clean_label = selected_label.replace("⮕ Retomar: ", "")
        chapter_index = [ch.display_name() for ch in chapters].index(clean_label)
        selected_chapter = chapters[chapter_index]

        # Process chapter (auto-create PDF if needed)
        _process_local_chapter(
            local_service,
            manga_title,
            selected_chapter,
            chapters,
            chapter_index,
            history,
        )


def _process_local_chapter(
    local_service: "LocalMangaService",
    manga_title: str,
    chapter: "LocalChapter",
    all_chapters: list["LocalChapter"],
    current_index: int,
    history: MangaHistory,
) -> None:
    """Process and open local chapter with AniList sync.

    Args:
        local_service: LocalMangaService instance
        manga_title: Manga title (directory name)
        chapter: LocalChapter object
        all_chapters: List of all chapters for navigation
        current_index: Current chapter index
        history: MangaHistory service
    """

    # Auto-create PDF if needed
    pdf_path = chapter.pdf_path
    if not chapter.has_pdf and chapter.has_images:
        print("📄 Criando PDF a partir das imagens...")
        pdf_path = local_service.auto_create_pdf_if_needed(
            manga_title,
            chapter.chapter_number,
        )
        if not pdf_path:
            print("❌ Erro ao criar PDF")
            input("Pressione Enter para continuar...")
            return
    elif not chapter.has_pdf:
        print("❌ Capítulo não disponível (sem PDF ou imagens)")
        input("Pressione Enter para continuar...")
        return

    # Open PDF reader and track the process
    reader_process = open_pdf_reader(pdf_path)

    # Update local history (always, even offline)
    history.update(
        manga_title,
        chapter.chapter_number,
        chapter_id=None,  # No online ID in local mode
        manga_id=None,
    )

    # Try to sync to AniList (forward-only)
    try:
        from services.anilist_service import AniListService

        anilist_service = AniListService()

        # Only sync if authenticated
        if anilist_service.is_authenticated():
            synced = local_service.sync_to_anilist_if_ahead(
                manga_title,
                chapter.chapter_number,
                anilist_service,
            )
            if synced:
                print("✅ Progresso sincronizado com AniList")
    except Exception:
        # Silent fail if offline or error
        pass

    # Wait for reader to close (track specific process, not any zathura instance)
    if reader_process:
        print("\n📖 Feche o leitor de PDF para continuar.")
        reader_process.wait()

    # Post-reading actions
    actions = [
        "Próximo capítulo",
        "Capítulo anterior",
        "Ler novamente",
    ]
    action = menu_navigate(actions, "O que deseja fazer?")

    if action == "Próximo capítulo":
        if current_index + 1 < len(all_chapters):
            next_chapter = all_chapters[current_index + 1]
            _process_local_chapter(
                local_service,
                manga_title,
                next_chapter,
                all_chapters,
                current_index + 1,
                history,
            )
        else:
            print("📚 Você chegou ao último capítulo disponível!")
            input("Pressione Enter para continuar...")

    elif action == "Capítulo anterior":
        if current_index > 0:
            prev_chapter = all_chapters[current_index - 1]
            _process_local_chapter(
                local_service,
                manga_title,
                prev_chapter,
                all_chapters,
                current_index - 1,
                history,
            )
        else:
            print("📚 Este é o primeiro capítulo!")
            input("Pressione Enter para continuar...")

    elif action == "Ler novamente":
        _process_local_chapter(
            local_service,
            manga_title,
            chapter,
            all_chapters,
            current_index,
            history,
        )


def main() -> None:
    """Main manga CLI entry point."""
    # Initialize service with config
    config = settings.manga
    try:
        service = UnifiedMangaService(config)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    # Show main menu
    while True:
        choice = _show_manga_main_menu()
        if choice is None:
            return

        if choice == "📖 Reading":
            _handle_reading_list(service)
        elif choice == "✅ Completed":
            _handle_completed_list(service)
        elif choice == "📋 Planning":
            _handle_planning_list(service)
        elif choice == "📅 Recent":
            _handle_recent_history(service)
        elif choice == "📈 Trending":
            _handle_trending(service)
        elif choice == "🔍 Search":
            # Original search flow
            _handle_search_flow(service)
        elif choice == "📂 Local Library":
            _handle_local_library()
        else:
            return


def _handle_search_flow(service: UnifiedMangaService) -> None:
    """Handle the original search flow."""
    # Get search query
    query = inquirer.text(message="Pesquise mangá").execute()  # type: ignore[attr-defined]
    if not query.strip():
        print("Pesquisa vazia")
        return

    selected_source = service.current_source

    # Search with loading spinner
    try:
        with loading(f"Buscando mangás em {selected_source}..."):
            results = service.search_manga(query.strip())
    except MangaNotFoundError:
        print("❌ Mangá não encontrado. Tente outra pesquisa.")
        return
    except MangaDexError as e:
        print(f"⚠️  {e.user_message}")
        return
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return

    if not results:
        print("❌ Nenhum mangá encontrado. Tente outra pesquisa.")
        return

    # Select manga
    manga_titles = [m.title for m in results]
    try:
        selected_title = menu_navigate(manga_titles, "Selecione mangá")
    except KeyboardInterrupt:
        return

    if selected_title is None:
        return

    selected_manga = next(m for m in results if m.title == selected_title)

    # Continue with the normal manga flow (allowing source change)
    _continue_manga_flow(service, selected_manga, allow_source_change=True)


if __name__ == "__main__":
    main()
