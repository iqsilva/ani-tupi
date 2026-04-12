#!/usr/bin/env python3
"""
Script de teste para simular busca de animes e identificar gargalos.
Mede tempo de cada scraper e identifica o que está lento.
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from os import cpu_count

from services.repository import Repository
from models.config import settings
from services.anime.title_normalization import normalize_search_cache_key

# Setup logging detalhado
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PERF_TEST")


def test_search_with_detailed_timing():
    """Testa busca de anime com timing detalhado de cada scraper."""

    logger.info("=" * 80)
    logger.info("TESTE DE PERFORMANCE DE BUSCA DE ANIME")
    logger.info("=" * 80)

    # Configurações
    test_queries = [
        "Jujutsu Kaisen",
        "Naruto",
        "Dragon Ball",
    ]

    for query in test_queries:
        logger.info(f"\n\n{'=' * 80}")
        logger.info(f"BUSCANDO: '{query}'")
        logger.info(f"{'=' * 80}")

        # Reset repository para nova busca
        repo = Repository()
        repo.clear_search_results()

        search_start = time.time()

        # Log de plugins disponíveis
        logger.info(f"\n📦 Plugins carregados: {len(repo.sources)}")
        for plugin_name, plugin in repo.sources.items():
            logger.info(f"   - {plugin_name}: {plugin.__class__.__name__}")

        # Log de settings
        logger.info("\n⚙️  SETTINGS:")
        logger.info(f"   - HTTP Timeout: {settings.performance.http_timeout}s")
        logger.info(
            f"   - Progressive Search Min Words: {settings.search.progressive_search_min_words}"
        )
        logger.info(f"   - Priority Order: {settings.plugins.priority_order}")
        logger.info(f"   - Disabled Plugins: {settings.plugins.disabled_plugins}")

        # Teste de cache
        logger.info("\n🔍 Verificando cache...")
        cache_start = time.time()
        try:
            from utils.cache_manager import get_cache

            dc = get_cache()
            cache_key = normalize_search_cache_key(query)
            cached = dc.get(cache_key)
            cache_time = int((time.time() - cache_start) * 1000)

            if cached:
                logger.info(f"   ✓ CACHE HIT em {cache_time}ms ({len(cached)} animes)")
            else:
                logger.info(f"   ✗ CACHE MISS em {cache_time}ms → Indo para scraping")
        except Exception as e:
            logger.warning(f"   ⚠️  Erro ao acessar cache: {e}")

        # Teste de scraping
        logger.info("\n🕷️  INICIANDO SCRAPING...")
        scraping_start = time.time()

        # Simular a busca com timing granular
        test_scraping_with_timing(query)

        scraping_time = int((time.time() - scraping_start) * 1000)
        total_time = int((time.time() - search_start) * 1000)

        logger.info("\n⏱️  TIMING TOTAL:")
        logger.info(f"   - Scraping: {scraping_time}ms")
        logger.info(f"   - Total: {total_time}ms")


def test_scraping_with_timing(query: str):
    """Executa scraping com timing detalhado de cada scraper."""

    repo = Repository()
    n_cpu = cpu_count() or 10

    executor = ThreadPoolExecutor(max_workers=min(len(repo.sources), n_cpu))

    try:
        logger.info(f"   ThreadPoolExecutor: {min(len(repo.sources), n_cpu)} workers")

        sources_list = list(repo.sources.items())

        # Aplicar prioridade
        priority_order = settings.plugins.priority_order
        if priority_order:
            priority_map = {name: idx for idx, name in enumerate(priority_order)}

            def sort_priority(item):
                return priority_map.get(item[0], len(priority_order))

            sources_list.sort(key=sort_priority)
        else:
            sources_list.sort(key=lambda x: x[0])

        # Log de ordem de execução
        logger.info("   Ordem de execução:")
        for idx, (source_name, _) in enumerate(sources_list):
            logger.info(f"      {idx + 1}. {source_name}")

        # Submeter tarefas
        logger.info(f"\n   Submetendo {len(sources_list)} tarefas...")
        future_to_source = {}
        submit_start = time.time()

        for source_name, plugin in sources_list:
            logger.debug(f"      → Submetendo {source_name}")
            future = executor.submit(plugin.search_anime, query)
            future_to_source[future] = (source_name, time.time())

        submit_time = int((time.time() - submit_start) * 1000)
        logger.info(f"   Todas as tarefas submetidas em {submit_time}ms")

        # Aguardar conclusão com timeout
        logger.info(
            f"\n   Aguardando resultados (timeout: {settings.performance.http_timeout * 6}s)..."
        )
        timeout = settings.performance.http_timeout * 6
        wait_start = time.time()

        done, not_done = wait(
            future_to_source.keys(),
            timeout=timeout,
            return_when=ALL_COMPLETED,
        )

        wait_time = int((time.time() - wait_start) * 1000)
        logger.info(f"   Espera concluída em {wait_time}ms")

        # Processar resultados
        logger.info(
            f"\n   Processando resultados ({len(done)} completadas, {len(not_done)} timeout)..."
        )

        scraper_times = []
        for future in done:
            source_name, submit_time_obj = future_to_source[future]
            execution_time = int((time.time() - submit_time_obj) * 1000)

            try:
                future.result()
                anime_count = len(repo.anime_to_urls)
                logger.info(
                    f"      ✓ {source_name:20} → {execution_time:5}ms ({anime_count} resultados acumulados)"
                )
                scraper_times.append((source_name, execution_time))
            except Exception as e:
                logger.error(f"      ❌ {source_name:20} → {execution_time:5}ms (ERRO: {e})")
                scraper_times.append((source_name, execution_time))

        # Timeouts
        if not_done:
            for future in not_done:
                source_name = future_to_source[future][0]
                logger.warning(f"      ⏱️  {source_name:20} → TIMEOUT")
                future.cancel()

        # Resumo
        logger.info("\n   📊 RESUMO DE SCRAPERS:")
        scraper_times.sort(key=lambda x: x[1], reverse=True)
        for source_name, exec_time in scraper_times:
            logger.info(f"      {source_name:20} {exec_time:5}ms")

        total_scraper_time = sum(t for _, t in scraper_times)
        avg_time = total_scraper_time // len(scraper_times) if scraper_times else 0
        logger.info(f"      {'Total':20} {total_scraper_time:5}ms (avg: {avg_time}ms)")

        # Identificar gargalo
        if scraper_times:
            slowest = scraper_times[0]
            logger.warning(f"\n   🚀 GARGALO IDENTIFICADO: {slowest[0]} leva {slowest[1]}ms")

    finally:
        executor.shutdown(wait=True)


def test_cache_performance():
    """Testa performance do cache."""
    logger.info("\n\n" + "=" * 80)
    logger.info("TESTE DE PERFORMANCE DO CACHE")
    logger.info("=" * 80)

    query = "Jujutsu Kaisen"

    # Primeira busca (sem cache)
    logger.info("\n1️⃣  PRIMEIRA BUSCA (sem cache):")
    repo = Repository()
    repo.clear_search_results()

    start = time.time()
    results1 = repo.search_anime(query, verbose=False)
    time1 = int((time.time() - start) * 1000)
    logger.info(f"   Tempo: {time1}ms")
    logger.info(f"   Resultados: {len(results1.results)}")

    # Segunda busca (com cache)
    logger.info("\n2️⃣  SEGUNDA BUSCA (com cache):")
    repo.clear_search_results()

    start = time.time()
    results2 = repo.search_anime(query, verbose=False)
    time2 = int((time.time() - start) * 1000)
    logger.info(f"   Tempo: {time2}ms")
    logger.info(f"   Resultados: {len(results2.results)}")

    speedup = time1 / time2 if time2 > 0 else 1
    logger.info(f"\n   ⚡ Speedup com cache: {speedup:.1f}x")


if __name__ == "__main__":
    logger.info("\n\n🎬 Iniciando testes de performance...\n")

    # Carregar plugins
    logger.info("📦 Carregando plugins...")
    from scrapers.loader import load_plugins

    load_plugins(languages={"pt-br"})

    # Teste de busca com timing detalhado
    test_search_with_detailed_timing()

    # Teste de cache
    test_cache_performance()

    logger.info("\n\n✅ Testes concluídos!")
