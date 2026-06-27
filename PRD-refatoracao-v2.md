# PRD: Refatoração Técnica ani-tupi v2.0

**Data:** 2026-06-26
**Status:** Proposta
**Escopo:** Qualidade arquitetural — sem features novas

---

## Resumo Executivo

Auditoria do codebase como senior Python developer. Encontradas **7 categorias de problema** que degradam testabilidade, legibilidade e manutenção. Nenhum quebra o produto hoje, mas cada um é dívida que se compõe. O PRD ordena por impacto e entrega correções cirúrgicas para cada um.

---

## Problema 1 — Scrapers acoplados ao singleton global `rep`

### Diagnóstico

O `CLAUDE.md` declara explicitamente: _"Plugins never ask anything — they're pure adapters."_

Na prática, todo scraper viola isso:

```python
# scrapers/plugins/sushianimes.py, animefire.py, animesdigital.py, etc.
from services.repository import rep   # ← plugin importando o agregador

class SushiAnimesScraper:
    def search_anime(self, query: str) -> None:
        ...
        rep.add_anime(title, url, self.name)  # ← plugin MUTANDO estado global
```

O Protocol declarado em `scrapers/loader.py` não define retorno para `search_anime`. Todos os 6 scrapers de anime usam `rep` como canal de saída em vez de retornar dados.

**Sintoma adicional:** `video_player.py:588` importa `rep` dentro de uma função — dependência oculta, praticamente circular.

### Impacto

- Testes de scrapers exigem `Repository.reset_singleton()` — infraestrutura vazando para unit tests
- Não é possível instanciar um scraper isolado
- Viola o contrato arquitetural documentado no próprio projeto

### Correção

**Passo 1:** Alterar o Protocol para ter retorno explícito:

```python
# scrapers/loader.py
from typing import Protocol
from models.models import AnimeMetadata

class AnimeScraper(Protocol):
    name: str
    languages: list[str]

    def search_anime(self, query: str) -> list[AnimeMetadata]: ...
    def get_episodes(self, url: str) -> list[str]: ...
    def get_episode_url(self, episode_url: str) -> str | None: ...
```

**Passo 2:** Reescrever cada scraper para retornar dados:

```python
# antes
def search_anime(self, query: str) -> None:
    rep.add_anime(title, url, self.name)

# depois
def search_anime(self, query: str) -> list[AnimeMetadata]:
    return [AnimeMetadata(title=title, url=url, source=self.name)]
```

**Passo 3:** Mover o `rep.add_anime()` para `SearchRepository.search_anime()`, que já coordena os scrapers.

**Arquivos afetados:** `scrapers/plugins/*.py` (6 arquivos), `services/search_repository.py`, `scrapers/loader.py`

---

## Problema 2 — Funções-deus em `anilist_integration.py`

### Diagnóstico

`services/anime/anilist_integration.py` tem **1277 linhas** com apenas **2 funções de nível superior**:

- `offer_sequel_and_continue()` — ~140 linhas
- `anilist_anime_flow()` — **~900 linhas**

`anilist_anime_flow` faz tudo: consulta cache, busca incremental, UI de seleção de idioma, busca manual com `input()`, seleção de anime, carregamento de episódios, loop de playback, pós-playback, sync AniList, detecção de sequência. Impossível testar qualquer etapa individualmente.

**Sintoma crítico:** `input()` chamado diretamente dentro de lógica de serviço:

```python
# services/anime/anilist_integration.py:403
manual_query = input("\n🔍 Digite o nome para buscar: ")
```

UI dentro de serviço é garantia de que a função nunca pode ser testada sem mockar stdin.

### Impacto

- Cobertura de testes próxima de zero para o fluxo mais importante do app
- Qualquer mudança em uma etapa exige entender 900 linhas de contexto
- `input()` no serviço acopla UI à lógica de negócio

### Correção

Quebrar `anilist_anime_flow()` em etapas com responsabilidade única:

```python
# services/anime/anilist_flow.py

def resolve_anime_title(anilist_id: int, english: str, romaji: str) -> str:
    """Retorna o título preferido do usuário (com cache de preferência)."""
    ...

def load_or_search_episodes(anime_title: str, anilist_id: int) -> list[EpisodeData]:
    """Cache-first: cache hit → retorna; miss → incremental_search."""
    ...

def run_playback_loop(episodes: list[EpisodeData], args, start_idx: int) -> int:
    """Loop de playback, retorna último episódio assistido."""
    ...
```

`anilist_anime_flow()` torna-se orquestrador fino que chama essas funções em sequência.

O `input()` deve ser movido para a camada de comando:

```python
# commands/anime.py — UI pertence aqui, não no serviço
def get_manual_query_from_user() -> str:
    return input("\n🔍 Digite o nome para buscar: ")
```

**Arquivos afetados:** `services/anime/anilist_integration.py`, `commands/anime.py`

---

## Problema 3 — Lógica de normalização duplicada

### Diagnóstico

Existem **4 implementações** de normalização de título espalhadas:

| Local | Função |
|-------|--------|
| `services/anime/title_normalization.py` | `normalize_title_for_dedup()` |
| `services/search_repository.py:222` | `SearchRepository._normalize_for_filter()` |
| `services/repository.py:319` | `Repository._normalize_for_filter()` (delega para `SearchRepository`) |
| `services/anilist/formatters.py:11` | `_normalize_title_for_compare()` |

E **2 implementações** do ranking por fuzzy score com lógica idêntica:

| Local | Função |
|-------|--------|
| `services/anime/search.py:115` | `_rank_anime_results_by_reference()` — usa `thefuzz` diretamente |
| `services/search_repository.py:147` | `SearchRepository._rank_search_results()` — implementação mais completa |

```python
# search.py:138 — duplicado de search_repository.py:125
score = max(
    fuzz.ratio(reference_normalized, normalized_title),
    fuzz.partial_ratio(reference_normalized, normalized_title),
    fuzz.token_sort_ratio(reference_normalized, normalized_title),
    fuzz.ratio(reference_compact, compact_title),
)
```

### Impacto

- Divergência de comportamento entre caminhos de código
- Bug corrigido em um lugar pode permanecer no outro
- Dificulta entender qual normalização está ativa em cada contexto

### Correção

**Passo 1:** Centralizar tudo em `services/anime/title_normalization.py` — único lugar de verdade.

**Passo 2:** `search.py:_rank_anime_results_by_reference()` delegar para `SearchRepository._rank_search_results()`.

**Passo 3:** Remover `Repository._normalize_for_filter()` (proxy inútil). Callers importam de `title_normalization.py`.

**Arquivos afetados:** `services/anime/search.py`, `services/repository.py`, `services/anilist/formatters.py`

---

## Problema 4 — `typing.Optional` e `typing.Dict/List/Tuple` legados

### Diagnóstico

Projeto usa Python 3.12 (`requires-python = ">=3.12"` em `pyproject.toml`). A sintaxe `X | None` e `list[str]` são nativas desde Python 3.10. Mesmo assim:

```python
# services/player_repository.py — forma mais arcaica
from typing import Optional, Dict, List, Tuple, Any

# services/repository.py, services/search_repository.py, etc.
from typing import Optional
```

`player_repository.py` usa `Dict`, `List`, `Tuple` capitalizados — removidos como aliases no Python 3.9+.

### Correção

Substituição mecânica em todos os arquivos do projeto (excluindo `.venv`):

```
Optional[str]  →  str | None
Optional[int]  →  int | None
Dict[K, V]     →  dict[K, V]
List[T]        →  list[T]
Tuple[A, B]    →  tuple[A, B]
```

Remover imports `from typing import Optional, Dict, List, Tuple` onde ficarem sem uso.

**Arquivos afetados:** `services/player_repository.py`, `services/repository.py`, `services/search_repository.py`, `services/anilist/client.py`, `services/anime/anilist_integration.py`, `models/manga_context.py`, `scrapers/core/selenium_driver.py`, `services/manga/download.py`, `utils/range_parser.py`

---

## Problema 5 — Import fantasma: `ProcessPoolExecutor`

### Diagnóstico

```python
# services/anime/search.py:9
from concurrent.futures import ProcessPoolExecutor
```

Nunca usado em nenhum lugar do arquivo. Sugere paralelismo que não existe ou plano abandonado.

### Correção

Remover a linha.

**Arquivo afetado:** `services/anime/search.py:9`

---

## Problema 6 — `except Exception` silenciosos

### Diagnóstico

99 ocorrências de `except Exception` nos services. Muitos swallowed silently:

```python
# services/anime/search.py:489
try:
    anilist_results = auto_discover_anilist_id(used_query)
    ...
except Exception:
    pass   # ← AniList falha? Ninguém sabe.
```

```python
# services/anime/search.py:539
except Exception as e:
    logger.warning(f"Error during incremental search at word {current_word_count}: {e}")
    # Swallows qualquer exceção — incluindo erros de programação
```

`except Exception: pass` em lógica de busca esconde bugs de integração, falhas de rede e erros de programação indistintamente.

### Correção

Classificar e tratar exceções específicas:

```python
# antes
except Exception:
    pass

# depois
from httpx import HTTPError, TimeoutException

try:
    anilist_results = auto_discover_anilist_id(used_query)
except (HTTPError, TimeoutException):
    logger.debug(f"AniList indisponível para '{used_query}', continuando sem ranking")
except Exception:
    logger.warning(f"Erro inesperado em auto_discover_anilist_id: {e!r}", exc_info=True)
    raise  # ← re-raise bugs de programação
```

**Arquivos afetados:** principalmente `services/anime/search.py`, `services/anime/anilist_integration.py`

---

## Problema 7 — `TypeError` capturado como flag de compatibilidade

### Diagnóstico

```python
# services/anime/search.py:200-214
def _get_ranked_titles_with_sources(...):
    """Call repository ranking with backwards-compatible fallback."""
    try:
        return rep.get_anime_titles_with_sources(
            filter_by_query=filter_by_query,
            original_query=original_query,
            anilist_results=anilist_results,
        )
    except TypeError:
        return rep.get_anime_titles_with_sources(   # ← chama de novo sem um argumento
            filter_by_query=filter_by_query,
            original_query=original_query,
        )
```

`TypeError` pode ser lançado por qualquer bug interno — índice errado, operação em `None`, unpacking falho. O fallback silencia bugs reais disfarçados de "incompatibilidade de assinatura".

### Correção

Declarar `anilist_results` como parâmetro opcional com default `None`. Remover o try/except:

```python
def get_anime_titles_with_sources(
    self,
    filter_by_query: str | None = None,
    original_query: str | None = None,
    anilist_results: list | None = None,  # ← já opcional, sem gambiarra
) -> list[str]: ...
```

**Arquivo afetado:** `services/anime/search.py:200-214`, `services/search_repository.py`

---

## Priorização

| # | Problema | Impacto | Esforço | Prioridade |
|---|----------|---------|---------|------------|
| 1 | Scrapers acoplados ao `rep` global | Alto — quebra isolamento do plugin contract | Alto | P1 |
| 2 | `anilist_anime_flow()` deus-função + `input()` em serviço | Alto — intratável para testes | Médio | P1 |
| 3 | Normalização duplicada | Médio — inconsistências de comportamento | Médio | P2 |
| 6 | `except Exception` silenciosos | Médio — esconde bugs | Baixo | P2 |
| 7 | `TypeError` como compat flag | Médio — mascara erros reais | Baixo | P2 |
| 4 | `typing.Optional` legado | Baixo — incorreto para Python 3.12 | Baixo | P3 |
| 5 | Import fantasma `ProcessPoolExecutor` | Baixo | Mínimo | P3 |

---

## Fora do escopo

- Reescrever scrapers de HTML (lógica de parsing estável)
- Mudar o sistema de cache (arquitetura correta)
- Alterar `models/models.py` (Pydantic bem usado)
- Adicionar features

---

## Critério de aceitação

1. `uv run pytest` passa com cobertura ≥ 80% depois de cada fase
2. Nenhum scraper importa `from services.repository import rep`
3. Nenhuma função acima de 200 linhas em `services/anime/`
4. Zero `except Exception: pass` sem log e sem re-raise
5. `from typing import Optional/Dict/List/Tuple` ausente em arquivos não-venv
6. `ProcessPoolExecutor` removido de `search.py`
