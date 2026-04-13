import argparse
import sys

from scrapers import loader
from services.repository import rep
from ui.components import menu
from commands import anime as anime_cmd
from commands import anilist_menu as anilist_menu_cmd
from commands import anilist_auth as anilist_auth_cmd
from commands import manga as manga_cmd
from commands import manage_sources as manage_sources_cmd
from utils.logging import get_logger

logger = get_logger(__name__)


def handle_local_library(args) -> None:
    """Handle local anime library browsing and playback.

    Shows downloaded anime and allows playback of offline episodes.
    """
    from commands.local_anime import handle_local_library_playback

    handle_local_library_playback(args)


def show_main_menu() -> str | None:
    """Display main menu with options."""
    options = [
        "🔍 Buscar Anime",
        "▶️  Continuar Assistindo",
        "📂 Biblioteca Local",
        "📺 AniList",
        "📚 Mangá",
        "⚙️  Gerenciar Fontes",
    ]
    return menu(options, msg="Ani-Tupi - Menu Principal")


def main_menu_flow(args) -> None:
    """Show main menu and route to appropriate command handler."""
    # Clean up any zombie browser processes from previous runs
    cleanup_zombie_browsers()

    choice = show_main_menu()

    if choice == "🔍 Buscar Anime":
        anime_cmd(args)
    elif choice == "▶️  Continuar Assistindo":
        # Set continue_watching flag and let anime handler take it
        args.continue_watching = True
        anime_cmd(args)
    elif choice == "📂 Biblioteca Local":
        handle_local_library(args)
    elif choice == "📺 AniList":
        anilist_menu_cmd(args)
    elif choice == "📚 Mangá":
        manga_cmd(args)
    elif choice == "⚙️  Gerenciar Fontes":
        manage_sources_cmd(args)


def cleanup_zombie_browsers() -> None:
    """Clean up any zombie browser processes from previous runs."""
    try:
        import subprocess
        import logging

        logger = logging.getLogger(__name__)

        # Clean up Firefox zombies
        result = subprocess.run(["pkill", "-f", "firefox"], capture_output=True, timeout=5)
        if result.returncode == 0:
            logger.info("Cleaned up zombie Firefox processes")

        # Clean up Chrome/Chromium zombies
        for browser in ["chrome", "chromium"]:
            subprocess.run(["pkill", "-f", browser], capture_output=True, timeout=5)

    except (subprocess.TimeoutExpired, FileNotFoundError, ImportError):
        # Silently ignore cleanup failures
        pass


def cli() -> None:
    """Entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="ani-tupi",
        description="Veja anime sem sair do terminal.",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # AniList command
    anilist_parser = subparsers.add_parser("anilist", help="Integração com AniList")
    anilist_parser.add_argument(
        "action",
        nargs="?",
        default="menu",
        choices=["auth", "menu"],
        help="auth: fazer login | menu: navegar listas (padrão)",
    )

    # Main anime command arguments (default)
    parser.add_argument(
        "--query",
        "-q",
    )
    parser.add_argument(
        "-e",
        "--episode",
        type=int,
        help="Número do episódio para assistir (ex: 5)",
    )
    parser.add_argument(
        "-S",
        "--season",
        type=int,
        help="Número da estação para anime com múltiplas estações (ex: -S 2 | -S 2 -e 5 para estação 2 episódio 5)",
    )
    parser.add_argument("--debug", "-d", action="store_true")
    parser.add_argument("--continue-watching", "-c", action="store_true", dest="continue_watching")
    parser.add_argument("--manga", "-m", action="store_true")
    parser.add_argument(
        "--skip",
        "-s",
        action="store_true",
        help="Pular automaticamente intros (OP) e outros (ED) usando AniSkip API",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Listar todas as fontes de anime disponíveis",
    )
    parser.add_argument(
        "--random",
        "-r",
        action="store_true",
        help="Sortear um anime aleatório da lista do AniList e reproduzir",
    )
    parser.add_argument(
        "--clear-cache",
        nargs="?",
        const=True,
        metavar="[anime_name]",
        help="Limpar cache (sem argumentos limpa tudo, ou especifique anime para limpar apenas um)",
    )

    args = parser.parse_args()

    # Configure logging early, before any other imports or operations
    from utils.logging import configure_logging

    configure_logging(debug=args.debug)

    # Load plugins once at startup
    loader.load_plugins({"pt-br"})  # type: ignore

    # Retry offline AniList syncs on startup
    from models.config import settings

    if settings.offline_sync.enable_auto_retry:
        from services.anime.offline_sync_service import retry_offline_syncs

        result = retry_offline_syncs()
        if result["successful"] > 0 or result["failed"] > 0:
            logger.info(
                f"📡 Sincronização offline: {result['successful']} ok, "
                f"{result['failed']} falha(s) pendente(s)"
            )

    # Show active sources
    active_sources = rep.get_active_sources()
    if active_sources:
        logger.info(f"ℹ️  Fontes ativas: {', '.join(active_sources)}")

    # Handle --list-sources before other commands
    if args.list_sources:
        sources = rep.get_active_sources()
        if sources:
            logger.info("\n🔌 Fontes de anime disponíveis:")
            for i, source in enumerate(sources, 1):
                logger.info(f"   {i}. {source}")
        else:
            logger.info("\n❌ Nenhuma fonte de anime encontrada!")
        sys.exit(0)

    # Handle --clear-cache before other commands
    if args.clear_cache:
        from utils.cache_manager import clear_cache_all, clear_cache_by_prefix
        from utils.anilist_discovery import auto_discover_anilist_id

        if args.clear_cache is True:
            # Clear all cache
            clear_cache_all()
            logger.info("✅ Cache completamente limpo!")
        else:
            # Try to discover AniList ID for more precise clearing
            anilist_id = auto_discover_anilist_id(args.clear_cache)
            if anilist_id:
                clear_cache_by_prefix(f":{anilist_id}:")
                logger.info(
                    f"✅ Cache de '{args.clear_cache}' (AniList ID {anilist_id}) foi limpo!"
                )
            else:
                # Fallback: clear by title prefix
                clear_cache_by_prefix(f":{args.clear_cache}:")
                logger.info(f"✅ Cache de '{args.clear_cache}' foi limpo!")
        sys.exit(0)

    # Handle commands
    if args.command == "anilist":
        if args.action == "auth":
            anilist_auth_cmd(args)
            sys.exit(0)
        else:  # menu
            anilist_menu_cmd(args)
    elif args.query or args.continue_watching or args.manga or args.random:
        # Command-line arguments provided, route to appropriate handler
        if args.manga:
            manga_cmd(args)
        elif args.random:
            from commands.anime import handle_random_anime

            handle_random_anime(args)
        else:
            # Query or continue_watching - use anime command
            anime_cmd(args)
    else:
        # No arguments - show main menu and route
        main_menu_flow(args)


if __name__ == "__main__":
    cli()
