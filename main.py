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


def show_main_menu():
    """Display main menu with options."""
    options = [
        "🔍 Buscar Anime",
        "▶️  Continuar Assistindo",
        "📺 AniList",
        "📚 Mangá",
        "⚙️  Gerenciar Fontes",
    ]
    return menu(options, msg="Ani-Tupi - Menu Principal")


def main_menu_flow(args) -> None:
    """Show main menu and route to appropriate command handler."""
    choice = show_main_menu()

    if choice == "🔍 Buscar Anime":
        anime_cmd(args)
    elif choice == "▶️  Continuar Assistindo":
        # Set continue_watching flag and let anime handler take it
        args.continue_watching = True
        anime_cmd(args)
    elif choice == "📺 AniList":
        anilist_menu_cmd(args)
    elif choice == "📚 Mangá":
        manga_cmd(args)
    elif choice == "⚙️  Gerenciar Fontes":
        manage_sources_cmd(args)


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

    # Test Skip API command
    test_skip_parser = subparsers.add_parser(
        "test-skip", help="Testar conectividade com Anime Skip API"
    )
    test_skip_parser.add_argument(
        "--show-id", help="UUID do show no Anime Skip para testar timestamps"
    )
    test_skip_parser.add_argument(
        "--episode", type=int, default=1, help="Número do episódio para testar (padrão: 1)"
    )
    test_skip_parser.add_argument(
        "--anilist-id", type=int, help="AniList ID para testar mapeamento de show"
    )
    test_skip_parser.add_argument(
        "--anime-title", help="Título do anime para busca (ex: 'Dandadan')"
    )

    # Main anime command arguments (default)
    parser.add_argument(
        "--query",
        "-q",
    )
    parser.add_argument("--debug", "-d", action="store_true")
    parser.add_argument("--continue-watching", "-c", action="store_true", dest="continue_watching")
    parser.add_argument("--manga", "-m", action="store_true")
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Listar todas as fontes de anime disponíveis",
    )
    parser.add_argument(
        "--clear-cache",
        nargs="?",
        const=True,
        metavar="[anime_name]",
        help="Limpar cache (sem argumentos limpa tudo, ou especifique anime para limpar apenas um)",
    )

    args = parser.parse_args()

    # Load plugins once at startup
    loader.load_plugins({"pt-br"})  # type: ignore

    # Show active sources
    active_sources = rep.get_active_sources()
    if active_sources:
        print(f"ℹ️  Fontes ativas: {', '.join(active_sources)}")

    # Handle --list-sources before other commands
    if args.list_sources:
        sources = rep.get_active_sources()
        if sources:
            print("\n🔌 Fontes de anime disponíveis:")
            for i, source in enumerate(sources, 1):
                print(f"   {i}. {source}")
        else:
            print("\n❌ Nenhuma fonte de anime encontrada!")
        sys.exit(0)

    # Handle --clear-cache before other commands
    if args.clear_cache:
        from utils.cache_manager import clear_cache_all, clear_cache_by_prefix
        from utils.anilist_discovery import auto_discover_anilist_id

        if args.clear_cache is True:
            # Clear all cache
            clear_cache_all()
            print("✅ Cache completamente limpo!")
        else:
            # Try to discover AniList ID for more precise clearing
            anilist_id = auto_discover_anilist_id(args.clear_cache)
            if anilist_id:
                clear_cache_by_prefix(f":{anilist_id}:")
                print(f"✅ Cache de '{args.clear_cache}' (AniList ID {anilist_id}) foi limpo!")
            else:
                # Fallback: clear by title prefix
                clear_cache_by_prefix(f":{args.clear_cache}:")
                print(f"✅ Cache de '{args.clear_cache}' foi limpo!")
        sys.exit(0)

    # Handle commands
    if args.command == "anilist":
        if args.action == "auth":
            anilist_auth_cmd(args)
            sys.exit(0)
        else:  # menu
            anilist_menu_cmd(args)
    elif args.command == "test-skip":
        from services.anime_skip_service import anime_skip_service
        from models.config import settings

        print("🧪 Testando conectividade com Anime Skip API...")
        print(f"📡 API URL: {settings.skip.api_url}")
        print(f"🔑 Client ID: {settings.skip.api_client_id[:8]}...")
        print()

        # Test API reachability
        if args.anime_title:
            print(f"🔍 Buscando show: {args.anime_title}")
            shows = anime_skip_service.search_show(args.anime_title)
            if shows:
                print(f"✅ Encontrados {len(shows)} resultados:")
                for i, show in enumerate(shows[:5], 1):
                    show_name = show.get("name", "Unknown")
                    show_id = show.get("id", "N/A")
                    show_original = show.get("originalName", "")
                    print(f"   {i}. {show_name}")
                    if show_original and show_original != show_name:
                        print(f"      Original: {show_original}")
                    print(f"      UUID: {show_id}")
            else:
                print("❌ Nenhum resultado encontrado ou erro na API")
            print()

        # Test AniList ID mapping
        if args.anilist_id:
            print(f"🔗 Mapeando AniList ID {args.anilist_id}...")
            show_id = anime_skip_service.map_anilist_to_show(
                anilist_id=args.anilist_id, anime_title=args.anime_title
            )
            if show_id:
                print(f"✅ Mapeado para Anime Skip show ID: {show_id}")
            else:
                print("❌ Mapeamento falhou ou show não encontrado")
            print()

        # Test timestamp fetching
        if args.show_id or (args.anilist_id and args.anime_title):
            episode_num = args.episode
            if args.anilist_id and args.anime_title:
                print(
                    f"⏱️  Buscando timestamps para AniList {args.anilist_id}, episódio {episode_num}..."
                )
                intervals = anime_skip_service.fetch_timestamps(
                    anilist_id=args.anilist_id,
                    episode_number=episode_num,
                    anime_title=args.anime_title,
                )
            else:
                # Direct show ID query (advanced usage)
                print(f"⏱️  Buscando timestamps para show {args.show_id}, episódio {episode_num}...")
                # This requires implementing direct show query, skip for now
                print("⚠️  Query direto por show ID não implementado ainda")
                print("   Use --anilist-id e --anime-title para buscar timestamps")
                intervals = []

            if intervals:
                print(f"✅ Encontrados {len(intervals)} intervalos de skip:")
                for interval in intervals:
                    start_min = int(interval.start // 60)
                    start_sec = int(interval.start % 60)
                    end_min = int(interval.end // 60)
                    end_sec = int(interval.end % 60)
                    duration = interval.end - interval.start
                    print(
                        f"   {interval.type_label.upper()}: "
                        f"{start_min}:{start_sec:02d} → {end_min}:{end_sec:02d} "
                        f"({duration:.0f}s)"
                    )
            else:
                print("❌ Nenhum intervalo de skip encontrado")
            print()

        # Test cache status
        print("💾 Status do cache:")
        cache_stats = anime_skip_service.cache.volume()
        print(f"   Total de itens em cache: {cache_stats}")
        print(f"   TTL configurado: {settings.skip.cache_duration_days} dias")
        print()

        print("✅ Teste concluído!")
        sys.exit(0)
    elif args.query or args.continue_watching or args.manga:
        # Command-line arguments provided, route to appropriate handler
        if args.manga:
            manga_cmd(args)
        else:
            # Query or continue_watching - use anime command
            anime_cmd(args)
    else:
        # No arguments - show main menu and route
        main_menu_flow(args)


if __name__ == "__main__":
    cli()
