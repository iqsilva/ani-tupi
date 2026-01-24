"""Image viewer detection and launching.

Finds and launches image viewers for manga chapter browsing.
Supports various Linux, macOS, and cross-platform viewers.
"""

import os
import shutil
import subprocess
from pathlib import Path


def find_image_viewer() -> str | None:
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


def open_image_viewer(dir_path: str) -> None:
    """Open image viewer for downloaded chapter.

    Args:
        dir_path: Path to chapter directory containing PNG images
    """
    viewer = find_image_viewer()
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
