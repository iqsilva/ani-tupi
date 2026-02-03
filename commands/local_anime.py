"""Local anime library browsing and playback.

Handles offline viewing of downloaded anime episodes with:
- Episode selection and playback
- Post-playback navigation (Next, Previous, Replay, Back)
- AniList sync with offline queue for failures
- Automatic file cleanup after successful sync
"""

from services.local_anime_service import LocalAnimeService
from utils.anilist_discovery import get_anilist_id_from_title
from commands.anime import handle_post_playback_confirmation
from ui.components import menu_navigate
from utils.video_player import VideoPlayer


def handle_local_library_playback(args) -> None:
    """Handle local anime library browsing and playback.

    Allows users to:
    1. Select downloaded anime from library
    2. Select episode to play
    3. Play episode offline
    4. Navigate to next/previous episodes or replay
    5. Sync progress to AniList with offline queue fallback
    """
    service = LocalAnimeService()

    # Get list of downloaded anime
    anime_list = service.get_downloaded_anime_list()

    if not anime_list:
        print("\n📂 Biblioteca Local")
        print("❌ Nenhum anime baixado ainda")
        print("   💡 Use '📥 Baixar para assistir depois' no menu de reprodução")
        return

    # Let user select anime
    anime_list_with_counts = []
    for title in anime_list:
        info = service.get_anime_info(title)
        count = info["total_episodes"]
        anime_list_with_counts.append(f"{title} ({count} eps)")

    selected = menu_navigate(anime_list_with_counts, msg="📂 Biblioteca Local - Selecione um anime")

    if not selected:
        return

    # Extract title (remove episode count)
    selected_title = selected.split(" (")[0]

    # Initialize selected_ep_str - will be set by menu or navigation
    selected_ep_str = None

    # Playback loop for this anime
    while True:
        # Get episodes
        try:
            episodes = service.get_downloaded_episodes(selected_title)
        except FileNotFoundError:
            print(f"❌ Anime não encontrado: {selected_title}")
            return

        if not episodes:
            print(f"❌ Nenhum episódio encontrado para {selected_title}")
            return

        # Show episodes for selection only if not already selected by navigation
        if selected_ep_str is None:
            episode_options = [f"Episódio {ep_num}" for ep_num, _ in episodes]
            selected_ep_str = menu_navigate(
                episode_options,
                msg=f"📂 {selected_title} - Selecione um episódio",
            )

            if not selected_ep_str:
                return  # User cancelled, back to library

        # Extract episode number
        selected_ep_num = int(selected_ep_str.split()[1])

        # Find the file path
        ep_path = None
        for ep_num, file_path in episodes:
            if ep_num == selected_ep_num:
                ep_path = file_path
                break

        if not ep_path:
            print("❌ Episódio não encontrado")
            selected_ep_str = None  # Reset so menu shows again on next iteration
            continue

        # Play the episode
        player = VideoPlayer()
        file_url = f"file://{ep_path.resolve()}"

        print(f"\n▶️  Reproduzindo: {selected_title} - Episódio {selected_ep_num}")
        print(f"   Arquivo: {ep_path}")

        player.play_episode(
            url=file_url,
            anime_title=selected_title,
            episode_number=selected_ep_num,
            total_episodes=len(episodes),
            source="local",
            use_ipc=True,
        )

        # Post-playback confirmation and navigation
        anilist_id = get_anilist_id_from_title(selected_title)

        handle_post_playback_confirmation(
            anime_title=selected_title,
            episode_number=selected_ep_num,
            num_episodes=len(episodes),
            anilist_id=anilist_id,
            source="local",
            is_local=True,
            file_path=ep_path,
        )

        # Navigation menu after playback
        opts = []

        # Find current episode index
        current_idx = None
        for i, (ep_num, _) in enumerate(episodes):
            if ep_num == selected_ep_num:
                current_idx = i
                break

        if current_idx is not None:
            if current_idx < len(episodes) - 1:
                opts.append("▶️  Próximo")
            if current_idx > 0:
                opts.append("◀️  Anterior")

        opts.append("🔁 Replay")
        opts.append("📂 Voltar à Biblioteca")

        selected_opt = menu_navigate(opts, msg="O que quer fazer agora?")

        if not selected_opt or selected_opt == "📂 Voltar à Biblioteca":
            return  # Back to library selection

        # Handle navigation
        if selected_opt == "▶️  Próximo":
            if current_idx is not None and current_idx < len(episodes) - 1:
                # Loop will reload episodes and select next episode
                selected_ep_num = episodes[current_idx + 1][0]
                # Re-create selected_ep_str to trigger next playback
                selected_ep_str = f"Episódio {selected_ep_num}"
                # Continue loop to play next episode
                continue

        elif selected_opt == "◀️  Anterior":
            if current_idx is not None and current_idx > 0:
                # Loop will reload episodes and select previous episode
                selected_ep_num = episodes[current_idx - 1][0]
                selected_ep_str = f"Episódio {selected_ep_num}"
                # Continue loop to play previous episode
                continue

        elif selected_opt == "🔁 Replay":
            # Keep same episode_num, loop will replay
            continue
