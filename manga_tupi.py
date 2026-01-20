"""Manga CLI - read manga from MangaDex.

Command-line interface for searching and reading manga chapters.
Uses MangaDexClient service layer with Rich menus and loading spinners.
"""

import os
import shutil
import subprocess

from InquirerPy import inquirer

from models.config import settings
from services.manga_service import (
    MangaDexError,
    MangaHistory,
    MangaNotFoundError,
)
from services.unified_manga_service import UnifiedMangaService
from ui.components import loading, menu_navigate
from utils.manga_reader import open_pdf_reader
from utils.pdf_converter import create_pdf_from_images


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


def main() -> None:
    """Main manga CLI entry point."""
    # Initialize service with config
    config = settings.manga
    try:
        service = UnifiedMangaService(config)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    # Let user select source
    available_sources = service.get_available_sources()
    if len(available_sources) > 1:
        source_labels = {
            "mugiwaras": "MugiwarasOficial (PT-BR) ⭐",
            "mangadex": "MangaDex (Multi-idioma)",
        }
        source_choices = [source_labels.get(s, s) for s in available_sources]
        try:
            selected_label = menu_navigate(source_choices, "Selecione a fonte")
            # Find the actual source name from the label
            selected_source = next(
                s for s in available_sources if source_labels.get(s, s) == selected_label
            )
            service.set_source(selected_source)
        except KeyboardInterrupt:
            return
    else:
        selected_source = service.current_source

    # Get search query
    query = inquirer.text(message="Pesquise mangá").execute()  # type: ignore[attr-defined]
    if not query.strip():
        print("Pesquisa vazia")
        return

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

    selected_manga = next(m for m in results if m.title == selected_title)

    # Construct manga URL for scrapers that need it
    manga_url = None
    if selected_source == "mugiwaras":
        manga_url = f"https://mugiwarasoficial.com/manga/{selected_manga.id}/"
    elif selected_source == "mangadex":
        manga_url = f"https://mangadex.org/title/{selected_manga.id}"

    # Load chapters with loading spinner
    try:
        with loading("Carregando capítulos..."):
            chapters = service.get_chapters(
                selected_manga.id, manga_url=manga_url, source=selected_source
            )
    except MangaDexError as e:
        print(f"⚠️  {e.user_message}")
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

    # Format chapter labels for display
    chapter_labels = [ch.display_name() for ch in chapters]

    # Show resume hint if applicable
    if last_chapter:
        chapter_labels[0] = f"⮕ Retomar - {chapter_labels[0]}"

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
                continue

            # Find actual chapter (strip resume hint)
            display_label = selected_label.replace("⮕ Retomar - ", "")
            current_index = next(
                i
                for i, label in enumerate(chapter_labels)
                if label.replace("⮕ Retomar - ", "") == display_label
            )

        auto_load_next = False  # Reset flag for next iteration
        selected_chapter = chapters[current_index]

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
            continue
        except Exception as e:
            print(f"❌ Erro ao carregar páginas: {e}")
            continue

        if not pages:
            print("❌ Nenhuma página disponível para este capítulo")
            continue

        # Create output directory
        output_path = (
            config.output_directory / selected_manga.title / selected_chapter.number
        )
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
                    continue

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
                continue

        # Open PDF reader
        open_pdf_reader(pdf_path)

        # Save reading progress
        history.update(
            selected_manga.title,
            selected_chapter.number,
            chapter_id=selected_chapter.id,
            manga_id=selected_manga.id,
        )

        # Ask for next action
        try:
            action = menu_navigate(["Próximo", "Sair"], "O que deseja fazer?")
        except KeyboardInterrupt:
            return

        if action == "Sair":
            return

        if action is None:
            # User selected "← Voltar" - go back to chapter selection
            continue

        # Move to next chapter if available
        if current_index + 1 < len(chapters):
            current_index += 1
            # Remove resume hint from current chapter
            chapter_labels[current_index] = chapter_labels[current_index].replace(
                "⮕ Retomar - ", ""
            )
            # Set flag to skip chapter selection menu and auto-load next
            auto_load_next = True
        else:
            print("Você chegou ao final dos capítulos disponíveis")
            return


if __name__ == "__main__":
    main()
