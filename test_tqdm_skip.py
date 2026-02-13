#!/usr/bin/env python3
"""Test script to demonstrate tqdm progress bar for skip times fetching."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from services.anime.aniskip_service import AniSkipService


def test_tqdm_progress():
    """Test tqdm progress bar with skip times fetching."""
    print("\n🎬 Testando buscas de skip times com tqdm\n")

    # Test 1: Busca de 3 episódios (próximo, atual, anterior)
    print("─" * 60)
    print("Teste 1: Busca otimizada (3 episódios)")
    print("─" * 60)

    aniskip = AniSkipService()
    mal_id = 13125  # Steins;Gate (sempre tem skip times)

    # Com tqdm para 3 episódios
    with tqdm(
        total=3,
        desc="Carregando skip times",
        unit="ep",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}",
    ) as pbar:
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(aniskip.get_skip_times, mal_id, ep): ep for ep in [1, 2, 3]}

            for future in as_completed(futures):
                ep = futures[future]
                try:
                    skip_times = future.result()
                    results[ep] = skip_times is not None
                except Exception:
                    results[ep] = False
                pbar.update(1)

    print(f"✅ Resultado: {results}\n")

    # Test 2: Busca completa (24 episódios)
    print("─" * 60)
    print("Teste 2: Busca completa (24 episódios)")
    print("─" * 60)

    with tqdm(
        total=24,
        desc="Carregando skip times",
        unit="ep",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(aniskip.get_skip_times, mal_id, ep): ep for ep in range(1, 25)
            }

            for future in as_completed(futures):
                ep = futures[future]
                try:
                    skip_times = future.result()
                    results[ep] = skip_times is not None
                except Exception:
                    results[ep] = False
                pbar.update(1)

    skip_count = sum(1 for v in results.values() if v)
    print(f"✅ Resultado: {skip_count}/24 episódios com skip times\n")

    # Test 3: Busca grande (148 episódios - Hunter x Hunter)
    print("─" * 60)
    print("Teste 3: Busca grande (148 episódios)")
    print("─" * 60)

    mal_id_hxh = 11061  # Hunter x Hunter (2011)

    with tqdm(
        total=148,
        desc="Carregando skip times",
        unit="ep",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(aniskip.get_skip_times, mal_id_hxh, ep): ep for ep in range(1, 149)
            }

            for future in as_completed(futures):
                ep = futures[future]
                try:
                    skip_times = future.result()
                    results[ep] = skip_times is not None
                except Exception:
                    results[ep] = False
                pbar.update(1)

    skip_count = sum(1 for v in results.values() if v)
    print(f"✅ Resultado: {skip_count}/148 episódios com skip times\n")

    # Test 4: Comparar visual - com vs sem tqdm
    print("─" * 60)
    print("Teste 4: Menu AniList Watching com 10 animes")
    print("─" * 60)

    anime_list = [
        ("Steins;Gate", 13125),
        ("Attack on Titan", 16498),
        ("Jujutsu Kaisen", 40748),
        ("Demon Slayer", 38000),
        ("My Hero Academia", 31964),
        ("One Punch Man", 30276),
        ("Tokyo Ghoul", 20605),
        ("Death Note", 1535),
        ("Naruto", 20),
        ("Bleach", 269),
    ]

    print("\n💡 Com tqdm: Mostra quantos animes já foram processados e quanto falta\n")

    with tqdm(
        total=len(anime_list),
        desc="Carregando skip icons",
        unit="anime",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    ) as pbar:
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(aniskip.search_mal_id, title): title for title, mal_id in anime_list
            }

            for future in as_completed(futures):
                title = futures[future]
                try:
                    mal_id = future.result()
                    results[title] = "⏭️ " if mal_id else ""
                except Exception:
                    results[title] = ""
                pbar.update(1)

    print(f"\n✅ Menu pronto com {sum(1 for v in results.values() if v)} animes com skip\n")


if __name__ == "__main__":
    test_tqdm_progress()
