"""Anime search, selection, and playback command handler.

This module handles:
- Interactive anime search or continue watching
- Episode selection and playback loop
- History management and AniList progress sync
- Source switching and quality selection

This is a thin coordinator that delegates all business logic to services.
"""

from services import anime_service
from services.history_service import save_history
from services.anime.playback_service import (
    prepare_playback_from_search,
    prepare_playback_from_history,
    get_episode_url_and_source,
    sync_progress_to_anilist,
    navigate_episodes,
)
from ui.components import loading, menu_navigate
from utils.video_player import VideoPlayer


def anime(args) -> None:
    """Handle anime search, selection, and playback flow.

    Supports:
    - Direct search with -q flag
    - Continue watching from history
    - Episode selection and playback loop
    - AniList progress sync
    - Source switching
    """
    # Variables for AniList integration and source tracking
    source = None

    # If command-line args provided, use them; otherwise handled by main menu
    if args.query or args.continue_watching:
        if args.continue_watching:
            # Prepare playback context from history
            ctx = prepare_playback_from_history()
            if ctx is None:
                raise Exception("Problema ao conseguir informacoes do anime.")
        else:
            # Search for anime
            result = anime_service.search_anime_flow(args)
            selected_anime, episode_idx, source = result
            if not selected_anime or episode_idx is None:
                return

            # Prepare playback context from search results
            ctx = prepare_playback_from_search(selected_anime, episode_idx, source)
            if ctx is None:
                return
    else:
        # This path is used when called from main menu
        result = anime_service.search_anime_flow(args)
        selected_anime, episode_idx, source = result
        if not selected_anime or episode_idx is None:
            return

        # Prepare playback context from search results
        ctx = prepare_playback_from_search(selected_anime, episode_idx, source)
        if ctx is None:
            return

    # Display AniList discovery info if found
    if ctx.anilist_title:
        print(f"✅ Encontrado: {ctx.anilist_title}")
    else:
        print("⚠️  Não foi possível encontrar no AniList (continuando sem sincronização)")

    # Initialize video player for this session
    player = VideoPlayer()

    # Main playback loop
    while True:
        episode = ctx.episode_idx + 1  # Convert to 1-indexed

        # Get episode video URL
        with loading("Buscando vídeo..."):
            playback_result = get_episode_url_and_source(ctx.anime_title, episode)

        if not playback_result.success:
            print(f"\n❌ {playback_result.error_message}")
            print("   💡 O episódio pode estar indisponível em todas as fontes.")
            print("   💡 Tente outro episódio ou espere e tente novamente mais tarde.\n")
            continue

        # Play video
        player_url = playback_result.player_url
        source = playback_result.source

        if player_url is None:
            print("\n❌ Nenhum vídeo encontrado")
            continue

        # Format progress string
        from services.anime.progress_service import get_episode_progress_info
        from services.anime.anilist_discovery_service import AniListDiscoveryResult

        anilist_result = None
        if ctx.anilist_id:
            anilist_result = AniListDiscoveryResult(
                anilist_id=ctx.anilist_id,
                anilist_title=ctx.anilist_title,
                total_episodes=ctx.total_episodes_anilist,
                found=True,
                authenticated=True,
            )

        progress_info = get_episode_progress_info(episode, ctx.num_episodes, anilist_result)

        print(f"\n▶️  Iniciando reprodução do episódio {progress_info.progress_str}...")
        print(f"   Fonte: {source or 'unknown'}")
        print(f"   URL: {player_url[:80]}{'...' if len(player_url) > 80 else ''}\n")

        exit_code = player.play_video_raw(player_url, args.debug)

        print(f"\n📊 Reprodução encerrada - Exit code: {exit_code}")

        # Log MPV exit code if it's not a normal exit
        if exit_code not in [0, 3]:  # 0=normal, 3=user quit with 'q'
            print(f"\n⚠️  MPV exit code: {exit_code}")
            if exit_code == 2:
                print("    (Possível erro ao reproduzir ou janela fechada)")

        # Only clear terminal if playback was successful
        # If there was an error, keep messages visible for user to read
        if exit_code != 0:
            # Error occurred - give user time to see error messages
            print("\n⏳ Pressione Enter para continuar...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

        # Ask if watched until the end
        confirm_options = ["✅ Sim, assisti até o final", "❌ Não, parei antes."]
        confirm = menu_navigate(
            confirm_options, msg=f"Você assistiu o episódio {episode} até o final?"
        )

        # Only save history and sync if user watched until the end
        if confirm == "✅ Sim, assisti até o final":
            save_history(ctx.anime_title, ctx.episode_idx, ctx.anilist_id, source)

            # AniList sync
            if ctx.anilist_id:
                success = sync_progress_to_anilist(ctx.anilist_id, episode, ctx.num_episodes)
                if success:
                    print("✅ Progresso salvo no AniList!")
                else:
                    print("⚠️  Não foi possível salvar no AniList (continuando...)")

                # Check for sequels when last episode is watched
                if episode == ctx.num_episodes:
                    if anime_service.offer_sequel_and_continue(ctx.anilist_id, args):
                        return  # Sequel started, exit this flow
        else:
            # User didn't finish - go back to episode menu without saving
            continue

        # Episode navigation menu
        opts = []
        if ctx.episode_idx < ctx.num_episodes - 1:
            opts.append("▶️  Próximo")
        if ctx.episode_idx > 0:
            opts.append("◀️  Anterior")
        opts.append("🔁 Replay")
        opts.append("📋 Escolher outro episódio")
        opts.append("🔄 Trocar fonte")

        selected_opt = menu_navigate(list(opts), msg="O que quer fazer agora?")

        if not selected_opt or selected_opt == "🔙 Voltar":
            return  # Exit to main menu
        elif selected_opt == "▶️  Próximo":
            ctx = navigate_episodes(ctx, "next")
        elif selected_opt == "◀️  Anterior":
            ctx = navigate_episodes(ctx, "previous")
        elif selected_opt == "🔁 Replay":
            ctx = navigate_episodes(ctx, "replay")
        elif selected_opt == "📋 Escolher outro episódio":
            # User selects episode from menu
            selected_episode = menu_navigate(list(ctx.episode_list), msg="Escolha o episódio.")
            if not selected_episode:
                return  # User cancelled, exit function
            episode_idx = ctx.episode_list.index(selected_episode)
            ctx = navigate_episodes(ctx, "choose", episode_idx)
        elif selected_opt == "🔄 Trocar fonte":
            # Source switching
            result = anime_service.switch_anime_source(ctx.anime_title, args, ctx.anilist_id)
            new_anime, new_episode_idx = result
            if new_anime and new_episode_idx is not None:
                # Prepare new context with switched source
                new_ctx = prepare_playback_from_search(new_anime, new_episode_idx, source)
                if new_ctx:
                    ctx = new_ctx
                    # Update episode count and list
                    ctx = navigate_episodes(ctx, "choose", new_episode_idx)
