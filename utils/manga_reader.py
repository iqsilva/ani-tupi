"""Manga PDF reader launcher.

Integrates with external PDF readers (similar to video_player.py for MPV).
Auto-detects available readers with fallback chain: Zathura → Evince → Okular → MuPDF.
"""

import shutil
import subprocess
from pathlib import Path

from models.config import settings


def find_pdf_reader() -> str | None:
    """Find available PDF reader on system.

    Follows priority order:
    1. User configuration (ANI_TUPI__MANGA__PDF_READER env var)
    2. Zathura (lightweight, keyboard-focused, perfect for manga)
    3. Evince (GNOME default, widely available)
    4. Okular (KDE default, feature-rich)
    5. MuPDF (minimal, fast)
    6. xdg-open (generic system default)

    Returns:
        Path to PDF reader executable or None if not found
    """
    # Check user preference from config
    if settings.manga.pdf_reader:
        if shutil.which(settings.manga.pdf_reader):
            return settings.manga.pdf_reader

    # Auto-detect readers in order of preference
    readers = ["zathura", "evince", "okular", "mupdf", "xdg-open"]

    for reader in readers:
        if shutil.which(reader):
            return reader

    return None


def open_pdf_reader(pdf_path: Path) -> subprocess.Popen | None:
    """Open PDF reader for manga chapter.

    Launches reader in background without blocking the CLI.
    Falls back gracefully if no reader found.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Subprocess handle if reader launched, None if not found
    """
    reader = find_pdf_reader()

    if not reader:
        print(
            "⚠️  Nenhum leitor de PDF encontrado.\n"
            "   Instale um destes: zathura, evince, okular, ou mupdf\n"
            "   Ou configure manualmente: export ANI_TUPI__MANGA__PDF_READER=seu_leitor"
        )
        print(f"   PDF salvo em: {pdf_path}")
        return None

    try:
        # Launch reader in background (non-blocking)
        process = subprocess.Popen(
            [reader, str(pdf_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return process

    except Exception as e:
        print(f"⚠️  Erro ao abrir {reader}: {e}")
        print(f"   PDF salvo em: {pdf_path}")
        return None
