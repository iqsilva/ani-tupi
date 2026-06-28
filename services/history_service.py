"""History management service."""

import time

from models.config import get_data_path
from services.repository import rep
from utils.persistence import JSONStore
from utils.title_utils import clean_title_for_display
from utils.exceptions import PersistenceError
from utils.logging import get_logger
from utils.anilist_discovery import get_anilist_id_with_interactive_fallback
from models.models import Status
from services.anime.mappings import load_anilist_urls

logger = get_logger(__name__)

HISTORY_PATH = get_data_path()
_history_store = JSONStore(HISTORY_PATH / "history.json")

_RETRY = object()


def _load_persisted_history():
    """Load history JSON, build menu, return parsed selection or None if cancelled."""
    from ui.components import menu_navigate

    data = _history_store.load({})
    sorted_data = sorted(data.items(), key=lambda x: x[1][0], reverse=True)

    titles = {}
    for entry, info in sorted_data:
        ep_idx = info[1]
        total = info[4] if len(info) > 4 and info[4] else None
        ep_info = f" ({ep_idx + 1}/{total})" if total else f" (Ep {ep_idx + 1})"
        titles[entry + ep_info] = len(ep_info)

    selected = menu_navigate(list(titles.keys()), msg="Continue assistindo.")
    if not selected:
        return None

    anime = selected[: -titles[selected]]
    d = data[anime]
    return (
        data,
        anime,
        d[1],
        d[2] if len(d) > 2 else None,
        d[3] if len(d) > 3 else None,
        d[5] if len(d) > 5 else None,
    )


def _resolve_anilist_progress(anilist_id, saved_source, anime):
    """Resolve AniList progress. Returns (anilist_id, anilist_title, anilist_ep_idx)."""
    from ui.components import loading

    anilist_title = None
    anilist_ep_idx = -1

    if anilist_id:
        from services.anilist_service import anilist_client

        info = anilist_client.get_anime_by_id(anilist_id)
        if info:
            anilist_title = info.title.romaji
        entry = anilist_client.get_media_list_entry(anilist_id)
        if entry and entry.progress:
            anilist_ep_idx = entry.progress - 1
    elif saved_source == "local":
        with loading(f"Buscando '{anime}' no AniList..."):
            anilist_id = get_anilist_id_with_interactive_fallback(anime, strict_threshold=95)
        if anilist_id:
            from services.anilist_service import anilist_client

            info = anilist_client.get_anime_by_id(anilist_id)
            if info:
                anilist_title = info.title.romaji
            entry = anilist_client.get_media_list_entry(anilist_id)
            if entry and entry.progress:
                anilist_ep_idx = entry.progress - 1

    return anilist_id, anilist_title, anilist_ep_idx


def _validate_anime_sources(search_results):
    """Validate which scraper sources have episodes. Returns (title, episode_list) or (_RETRY, None)."""
    from ui.components import loading, menu_navigate

    logger.info("ℹ️  Validando fontes disponíveis...")
    valid = {}
    for aw in search_results.get_anime_titles_with_sources():
        title = aw.rsplit(" [", 1)[0] if " [" in aw else aw
        with loading(f"Verificando '{title}'..."):
            rep.search_episodes(title)
        eps = rep.get_episode_list(title)
        if eps:
            valid[aw] = len(eps)

    if not valid:
        return None, []
    if len(valid) == 1:
        aw = list(valid.keys())[0]
        t = aw.rsplit(" [", 1)[0]
        return t, rep.get_episode_list(t)

    valid_list = [f"{s} ({valid[s]} eps)" for s in valid]
    selected = menu_navigate(valid_list, msg="Múltiplas fontes com episódios. Escolha uma:")
    if not selected:
        return _RETRY, None
    idx = valid_list.index(selected)
    aw = list(valid.keys())[idx]
    return aw.rsplit(" [", 1)[0], rep.get_episode_list(aw.rsplit(" [", 1)[0])


def _find_episodes(anime, anilist_id, anilist_title, saved_source, saved_urls):
    """Load episodes from saved URLs, AniList cache, or scraper search.

    Returns (anime, episode_list, searched_scrapers, was_found).
    episode_list=None means user cancelled (retry).
    """
    from ui.components import loading

    if saved_urls and saved_source:
        rep.clear_search_results()
        if isinstance(saved_urls, dict):
            for src, url in saved_urls.items():
                rep.add_anime(anime, url, src)
        else:
            rep.add_anime(anime, saved_urls, saved_source)
        with loading(f"Carregando episódios de {saved_source}..."):
            rep.search_episodes(anime)
        ep_list = rep.get_episode_list(anime)
        if ep_list:
            return anime, ep_list, False, True

    if anilist_id:
        cached = load_anilist_urls(anilist_id)
        if cached:
            rep.clear_search_results()
            for src, url in cached.items():
                rep.add_anime(anime, url, src)
            with loading(f"Carregando episódios de {anime}..."):
                rep.search_episodes(anime, source_filter=saved_source)
            ep_list = rep.get_episode_list(anime)
            if ep_list:
                return anime, ep_list, False, True

    if saved_source == "local":
        return anilist_title or anime, [], False, False

    search_title = clean_title_for_display(anime)
    rep.clear_search_results()
    with loading(f"Buscando '{search_title}'..."):
        search_results = rep.search_anime(search_title)

    anime_titles = search_results.get_anime_titles()
    if not anime_titles:
        return anime, [], True, False

    if len(anime_titles) == 1:
        t = anime_titles[0]
        if saved_source:
            with loading(f"Carregando episódios de {saved_source}..."):
                rep.search_episodes(t, source_filter=saved_source)
        else:
            with loading("Carregando episódios..."):
                rep.search_episodes(t)
        return t, rep.get_episode_list(t) or [], True, True

    t, ep_list = _validate_anime_sources(search_results)
    if t is _RETRY:
        return anime, None, True, True
    return t or anime, ep_list or [], True, bool(ep_list)


def _pick_episode(anime, episode_list, last_ep_idx, progress_source):
    """Show episode picker. Returns episode_idx or None to retry."""
    from ui.components import menu_navigate, menu_navigate_episodes

    last_ep_num = last_ep_idx + 1
    options = []
    option_to_idx = {}

    if last_ep_idx < len(episode_list) - 1:
        opt = f"⏭️  Episódio {last_ep_num + 1} (próximo)"
        option_to_idx[opt] = last_ep_idx + 1
    else:
        opt = f"⏭️  Episódio {last_ep_num + 1} (aguardando)"
        option_to_idx[opt] = None
    options.append(opt)

    cur = f"▶️  Episódio {last_ep_num} ({progress_source})"
    options.append(cur)
    option_to_idx[cur] = last_ep_idx

    if last_ep_idx > 0:
        prev = f"◀️  Episódio {last_ep_num - 1} (anterior)"
        options.append(prev)
        option_to_idx[prev] = last_ep_idx - 1

    options.append("📋 Escolher outro episódio")
    options.append("🔄 Começar do zero")

    choice = menu_navigate(options, msg=f"{anime} - De onde quer continuar?")
    if not choice:
        return None

    if choice == "📋 Escolher outro episódio":
        return menu_navigate_episodes(episode_list)

    if choice == "🔄 Começar do zero":
        confirm = menu_navigate(
            ["✅ Sim, resetar", "❌ Cancelar"],
            msg="Tem certeza? Seu progresso será perdido.",
        )
        if confirm == "✅ Sim, resetar":
            reset_history(anime)
            logger.info("✅ Histórico resetado! Começando do episódio 1...")
            return 0
        return None

    ep_idx = option_to_idx[choice]
    if ep_idx is None:
        logger.info(f"\n⏳ Episódio {last_ep_num + 1} ainda não disponível nos scrapers.")
        input("\nPressione Enter para voltar...")
        return None
    return ep_idx


def load_history() -> tuple[str, int, int | None, str | None] | None:
    """Load watch history and let user choose episode.

    Format:
        - v6: {"anime_name": [timestamp, episode_idx, anilist_id, source, total_episodes, anime_urls], ...}

    Returns: (anime_name, episode_idx, anilist_id, anilist_title)
    """
    from ui.components import menu_navigate

    for _ in range(6):
        try:
            entry = _load_persisted_history()
        except (FileNotFoundError, PersistenceError) as e:
            logger.warning("Error loading history: %s", e)
            return None

        if entry is None:
            return None

        _, anime, local_ep_idx, anilist_id, saved_source, saved_urls = entry
        original_anime_name = anime

        anilist_id, anilist_title, anilist_ep_idx = _resolve_anilist_progress(
            anilist_id, saved_source, anime
        )
        last_ep_idx = max(local_ep_idx, anilist_ep_idx)
        progress_source = "AniList" if anilist_ep_idx > local_ep_idx else "Local"

        anime, episode_list, searched, was_found = _find_episodes(
            anime, anilist_id, anilist_title, saved_source, saved_urls
        )
        if episode_list is None:
            continue

        if not episode_list and searched:
            if was_found:
                logger.info(
                    f"\n⚠️  '{anime}' foi encontrado mas nenhuma fonte tem episódios disponíveis."
                )
                logger.info("\nPossíveis motivos:")
                logger.info("  • O anime foi removido temporariamente")
                logger.info("  • Os episódios ainda não foram adicionados")
                logger.info("  • A fonte original mudou de nome/formato")
            else:
                logger.info(f"\n⚠️  '{anime}' não foi encontrado nos scrapers disponíveis.")
                logger.info("\nPossíveis motivos:")
                logger.info("  • O nome mudou no site")
                logger.info("  • O anime foi removido")
                logger.info("  • O scraper está temporariamente offline")

            retry_choice = menu_navigate(
                [
                    "🔍 Buscar manualmente (digite outro nome)",
                    "🗑️  Remover do histórico",
                    "← Voltar ao menu de histórico",
                ],
                msg="O que deseja fazer?",
            )

            if retry_choice == "🔍 Buscar manualmente (digite outro nome)":
                manual_query = input("\n🔍 Digite o nome para buscar: ").strip()
                if not manual_query:
                    continue

                from ui.components import loading

                rep.clear_search_results()
                with loading(f"Buscando '{manual_query}'..."):
                    search_results = rep.search_anime(manual_query)

                anime_titles = search_results.get_anime_titles()
                if not anime_titles:
                    logger.info(f"\n❌ Nenhum resultado encontrado para '{manual_query}'")
                    input("\nPressione Enter para continuar...")
                    continue

                anime_with_sources = search_results.get_anime_titles_with_sources()
                if len(anime_with_sources) == 1:
                    selected_title = anime_titles[0]
                else:
                    selected = menu_navigate(
                        anime_with_sources,
                        msg=f"Resultados para '{manual_query}'. Escolha:",
                    )
                    if not selected:
                        continue
                    selected_title = selected.rsplit(" [", 1)[0]

                with loading("Carregando episódios..."):
                    rep.search_episodes(selected_title)
                episode_list = rep.get_episode_list(selected_title)

                if not episode_list:
                    logger.info(f"\n❌ '{selected_title}' não tem episódios disponíveis")
                    input("\nPressione Enter para continuar...")
                    continue

                anime = selected_title
                replace = menu_navigate(
                    ["✅ Sim, substituir", "❌ Não, manter ambos"],
                    msg=f"Deseja substituir '{original_anime_name}' por '{anime}' no histórico?",
                )
                if replace == "✅ Sim, substituir":
                    reset_history(original_anime_name)
                    save_history(anime, last_ep_idx, anilist_id, saved_source)
                    logger.info("✅ Histórico atualizado!")

            elif retry_choice == "🗑️  Remover do histórico":
                reset_history(original_anime_name)
                logger.info(f"✅ '{original_anime_name}' removido do histórico.")
                input("\nPressione Enter para continuar...")
                continue
            else:
                continue

        if not episode_list:
            # No scraper search was done (local+anilist path); proceed with empty list
            pass

        episode_idx = _pick_episode(anime, episode_list, last_ep_idx, progress_source)
        if episode_idx is None:
            continue

        return anime, episode_idx, anilist_id, anilist_title

    logger.warning("Muitas tentativas de busca. Encerrando.")
    return None


def save_history(
    anime: str,
    episode: int,
    anilist_id: int | None = None,
    source: str | None = None,
    total_episodes: int | None = None,
    anime_urls: dict[str, str] | None = None,
) -> None:
    """Save watch history with timestamp, optional AniList ID, source, and total episodes.

    Format: {"anime_name": [timestamp, episode_idx, anilist_id, source, total_episodes, anime_urls], ...}
    - anilist_id can be None for anime not from AniList
    - source is the scraper name (e.g., "animefire", "sushianimes")
    - total_episodes is the known total count of episodes (auto-detected if not provided)
    """
    if total_episodes is None:
        episode_list = rep.get_episode_list(anime)
        if episode_list:
            total_episodes = len(episode_list)

    if anime_urls is None:
        anime_urls = {}
        for url, url_source, _ in rep.anime_to_urls.get(anime, []):
            anime_urls[url_source] = url

        if not anime_urls and source:
            anime_list = rep.anime_to_urls.get(anime, [])
            for url, url_source, _ in anime_list:
                if url_source == source:
                    anime_urls[url_source] = url
                    break

    try:
        _history_store.set(
            anime,
            [int(time.time()), episode, anilist_id, source, total_episodes, anime_urls],
        )
    except PersistenceError as e:
        logger.error(f"Failed to save history: {e}")


def save_history_from_event(
    anime_title: str,
    episode_idx: int,
    action: str = "watched",
    source: str | None = None,
    anilist_id: int | None = None,
) -> None:
    """Save watch history from IPC keybinding event and sync with AniList.

    This function is called when the user triggers episode navigation via
    keybindings (Shift+N, Shift+M, etc.) during MPV playback.

    Args:
        anime_title: Anime name
        episode_idx: 0-based episode index
        action: Action type - "watched" (marked as watched), "started" (began watching),
                "skipped" (skipped episode)
        source: Scraper source name (e.g., "animefire")
        anilist_id: AniList ID for syncing (optional, will try to get from repository if not provided)
    """
    total_episodes = None
    episode_list = rep.get_episode_list(anime_title)
    if episode_list:
        total_episodes = len(episode_list)

    if anilist_id is None:
        anilist_id = rep.anime_to_anilist_id.get(anime_title)
        if anilist_id is None:
            try:
                history_data = _history_store.load({})
                if anime_title in history_data:
                    history_entry = history_data[anime_title]
                    if len(history_entry) > 2:
                        anilist_id = history_entry[2]
            except Exception:
                pass

    save_history(anime_title, episode_idx, anilist_id, source, total_episodes)
    logger.info(f"Saved history for '{anime_title}' Ep {episode_idx + 1} (action: {action})")

    if anilist_id and action == "watched":
        from services.anilist_service import anilist_client

        if anilist_client.is_authenticated():
            try:
                entry = anilist_client.get_media_list_entry(anilist_id)

                if not entry:
                    logger.info(f"Adding '{anime_title}' to AniList CURRENT list")
                    anilist_client.add_to_list(anilist_id, "CURRENT")
                else:
                    if entry.status == "PLANNING":
                        logger.info(f"Moving '{anime_title}' from PLANNING to CURRENT")
                        anilist_client.add_to_list(anilist_id, "CURRENT")
                    elif entry.status == "COMPLETED":
                        logger.info(f"Changing '{anime_title}' to REPEATING")
                        status_changed = anilist_client.change_status(anilist_id, Status.REPEATING)
                        if not status_changed:
                            logger.warning(
                                f"Failed to change '{anime_title}' to REPEATING; skipping progress update"
                            )
                            return

                episode_number = episode_idx + 1
                success = anilist_client.update_progress(anilist_id, episode_number)

                if success:
                    logger.info(f"Synced progress to AniList: Ep {episode_number}")
                else:
                    logger.warning(f"Failed to sync progress to AniList for Ep {episode_number}")
            except Exception as e:
                logger.error(f"Error syncing with AniList: {e}")


def reset_history(anime: str) -> None:
    """Remove anime from watch history (reset to episode 0).

    Args:
        anime: Anime title to reset
    """
    try:
        _history_store.delete(anime)
        logger.info(f"Reset history for '{anime}'")
    except PersistenceError as e:
        logger.error(f"Failed to reset history for '{anime}': {e}")
