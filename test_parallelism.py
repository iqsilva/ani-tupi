#!/usr/bin/env python3
"""
Teste para verificar se os scrapers estão rodando em paralelo ou sequencial.
Mostra timestamp de quando cada scraper começa e termina.
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from os import cpu_count

from services.repository import Repository
from models.config import settings
from scrapers.loader import load_plugins

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d - %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PARALLELISM_TEST")


def test_parallelism():
    """Testa se scrapers rodam em paralelo ou sequencial."""

    logger.info("=" * 80)
    logger.info("TESTE DE PARALELISMO - Quando cada scraper começa e termina?")
    logger.info("=" * 80)

    # Carregar plugins
    load_plugins(languages={"pt-br"})

    repo = Repository()
    query = "Naruto"

    logger.info(f"\n🔍 Buscando: '{query}'")
    logger.info(f"⚙️  Scrapers: {len(repo.sources)}")
    logger.info(f"🔗 HTTP Timeout: {settings.performance.http_timeout}s")

    n_cpu = cpu_count() or 10
    executor = ThreadPoolExecutor(max_workers=min(len(repo.sources), n_cpu))

    try:
        sources_list = list(repo.sources.items())

        # Priority order
        priority_order = settings.plugins.priority_order
        if priority_order:
            priority_map = {name: idx for idx, name in enumerate(priority_order)}

            def sort_priority(item):
                return priority_map.get(item[0], len(priority_order))

            sources_list.sort(key=sort_priority)
        else:
            sources_list.sort(key=lambda x: x[0])

        logger.info("\n📋 Submeter tarefas:")
        future_to_source = {}
        start_times = {}

        global_start = time.time()

        for idx, (source_name, plugin) in enumerate(sources_list):
            start_time = time.time()
            logger.info(f"   [{time.time() - global_start:.2f}s] Submetendo {source_name}")

            # Wrappear o plugin para logar quando começa e termina
            def wrapped_search(plugin=plugin, source_name=source_name, start_time=start_time):
                elapsed_since_submit = time.time() - start_time
                logger.info(
                    f"   [{time.time() - global_start:.2f}s] ▶️  {source_name:20} COMEÇOU ({elapsed_since_submit:.2f}s após submit)"
                )

                result = plugin.search_anime(query)

                elapsed_total = time.time() - start_time
                logger.info(
                    f"   [{time.time() - global_start:.2f}s] ✓ {source_name:20} TERMINOU ({elapsed_total:.2f}s total)"
                )
                return result

            future = executor.submit(wrapped_search)
            future_to_source[future] = source_name
            start_times[source_name] = time.time()

        logger.info("\n⏳ Aguardando conclusão...")
        timeout = settings.performance.http_timeout * 6
        done, not_done = wait(
            future_to_source.keys(),
            timeout=timeout,
            return_when=ALL_COMPLETED,
        )

        logger.info("\n✅ Resultado:")
        logger.info(f"   Concluídas: {len(done)}/{len(future_to_source)}")
        logger.info(f"   Timeout: {len(not_done)}/{len(future_to_source)}")

        # Processar resultados
        for future in done:
            source = future_to_source[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"   ❌ {source}: {e}")

        for future in not_done:
            future.cancel()

        logger.info("\n📊 ANÁLISE:")
        elapsed = time.time() - global_start
        logger.info(f"   Tempo total: {elapsed:.2f}s")
        logger.info(f"   Se sequencial: ~{elapsed}s ✓ (soma de todos os tempos)")
        logger.info(f"   Se paralelo: ~{elapsed}s (tempo do mais lento)")

        # Heurística: se todos levarem o mesmo tempo, é sequencial
        logger.info("\n💡 CONCLUSÃO:")
        if elapsed > 20:
            logger.warning("   ⚠️  Parece ser SEQUENCIAL ou ThreadPoolExecutor com I/O bloqueante!")
        else:
            logger.info("   ✓ Parece estar rodando em paralelo")

    finally:
        executor.shutdown(wait=True)


if __name__ == "__main__":
    test_parallelism()
