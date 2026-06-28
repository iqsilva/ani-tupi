# PRD — Refatoração v3: Qualidade e Consolidação

**Status:** Proposta · **Autor:** revisão arquitetural · **Data:** 2026-06-28
**Audiência:** agente executor (LLM) com acesso de escrita ao repositório.

---

## 0. Como usar este documento

Você é o agente que vai **implementar** as tarefas abaixo. Regras:

1. **Funcionalidade não muda.** Toda tarefa é refactor: comportamento no caminho feliz idêntico, qualidade melhor.
2. **Mudanças cirúrgicas.** Toque só o que a tarefa pede. Não "melhore" código adjacente.
3. **Leia antes de editar.** Nunca edite arquivo que não leu inteiro. Os `file:line` aqui são de 2026-06-28; **reconfirme** antes de aplicar — podem ter movido.
4. **Verifique cada tarefa** com o comando de aceite antes de seguir. `uv run ruff check .` e `uv run pytest` devem passar.
5. **Use `uv`** para tudo. **Use `rtk`** como prefixo em git/gh/grep.
6. **Um commit por tarefa**, conventional commits (`refactor:`, `perf:`, `fix:`). Não use `--no-verify`.
7. Ordem importa: tarefas estão ordenadas por valor/risco crescente. Faça P0→P1→P2. Pare e reporte se um teste quebrar e a causa não for óbvia.

Convenção de prioridade: **P0** = alto valor, baixo risco. **P1** = alto valor, médio risco. **P2** = limpeza incremental.

---

## 1. Contexto da arquitetura

Three-tier (ver `CLAUDE.md`):

```
main.py  → commands/  → services/  → scrapers/plugins/* + manga_scrapers/*
                                    → utils/cache.py, utils/video_player.py (MPV IPC)
models/  (config.py Pydantic, models.py)
```

Fluxo: query → `SearchRepository` (ThreadPool por scraper, dedup título) → `EpisodeRepository` (prioridade fonte) → `PlaybackCoordinator` (extrai URL vídeo + cache) → `HistoryService` (JSON + sync AniList) → MPV.

Núcleo sólido (plugin protocol, repository pattern). Os problemas: vazamento de camada e **dois monolitos legados** que sobreviveram ao refactor v2.

---

## 2. Tarefas

### T1 — [P0] Migrar plugins anime para `PooledHTTPClient`

**Problema.** `scrapers/core/http_client.py:89` expõe `http_client` (singleton, pooling, retry com backoff, timeout 15s, `follow_redirects`). **Zero** plugins usam — todos os 7 chamam `httpx.get/post()` cru. Sem connection reuse: novo TCP+TLS por request. Docstring promete 50-70% de ganho.

**Arquivos** (todos em `scrapers/plugins/`):
`animefire.py`, `animesdigital.py`, `animesonlinecc.py`, `anitube.py`, `anroll.py`, `sushianimes.py`, `goyabu.py`.

**Ação.** Em cada plugin:
- `from scrapers.core.http_client import http_client`.
- Trocar `httpx.get(url, headers=H, timeout=T, follow_redirects=True)` → `http_client.get(url, headers=H)`. O client já define timeout/redirect/retry.
- Idem `httpx.post` → `http_client.post`.
- Remover `import httpx` se não restar uso (manter `except httpx.HTTPError` exige o import — ver T5; se fizer T5 junto, troca para `except Exception`).
- Remover constantes `REQUEST_TIMEOUT` locais agora redundantes (deixe se ainda referenciadas em outro ponto).

**Não fazer.** Não mexer na lógica de parsing, selectors, regex de cada plugin.

**Aceite.**
- `rtk grep -rl "httpx\.\(get\|post\)" scrapers/plugins/` retorna vazio.
- `uv run pytest tests/ -k scraper` passa.
- `uv run ruff check .` limpo (sem import não usado).

---

### T2 — [P0] Centralizar HEADERS, timeout e regex dos plugins

**Problema.** Headers Firefox idênticos redefinidos em ≥5 plugins (`sushianimes.py:14-24`, `animesonlinecc.py:16-19`, `anitube.py:13-15`, `anroll.py:12-15`, `goyabu.py:14-17`). Regex recompilado por chamada em vez de module-level (`sushianimes.py:51-73`, `goyabu.py:87`, `anroll.py:57,80-82`).

**Ação.**
- Em `scrapers/plugins/utils.py` (ou `scrapers/core/`), adicionar `DEFAULT_HEADERS` compartilhado.
- Cada plugin: `from ... import DEFAULT_HEADERS`; remover o dict local. Se um plugin precisa header extra, fazer `{**DEFAULT_HEADERS, "X": "..."}`.
- Mover todo `re.compile`/padrão usado em loop para constante module-level (`_NOME_RE = re.compile(...)`).

**Aceite.**
- Nenhum plugin define `HEADERS = {"User-Agent": "Mozilla/5.0 ...Firefox..."}` localmente (exceto override justificado).
- `rtk grep -rn "re.search\|re.findall" scrapers/plugins/` — chamadas usam constantes compiladas, não literais inline em funções quentes.
- `uv run pytest` passa.

---

### T3 — [P1] Eliminar duplicação de download no `manga_tupi.py`

**Problema.** `services/manga/download.py` foi extraído no refactor v2 mas **nunca importado**. `manga_tupi.py` (1695 linhas) mantém implementações paralelas que divergiram:

| Conceito | Legado (ativo) | Serviço (órfão) |
|----------|----------------|-----------------|
| download capítulo único | `manga_tupi.py:768-948` | `services/manga/download.py:18-137` |
| prompt range | `manga_tupi.py:680-738` | `services/manga/download.py:191-243` |
| loop download imagens | `manga_tupi.py:1185-1218` | `services/manga/download.py:291-356` |

Versão legada **não valida content-type nem tamanho** e não rastreia páginas falhas; a do serviço valida.

**Ação (faseada — commit por fase).**
1. **Confirmar paridade**: ler ambas as implementações. Listar diferenças de comportamento ANTES de tocar. Se a versão de serviço difere em UX (ex.: range por menu fixo vs. texto livre `"3-10"`), **portar a UX do legado para o serviço primeiro**, não o contrário — não regredir UX.
2. Em `manga_tupi.py`, importar e chamar `download_chapter`, `prompt_download_range`, `_download_images` de `services/manga/download.py` nos call sites (`_download_single_chapter` chamado em 1057/1099; `_prompt_download_range` em 1003; loop inline em 1190).
3. Deletar as funções legadas órfãs após a troca: `_download_single_chapter`, `_prompt_download_range`, loop inline.

**Risco.** Médio. `manga_tupi.py` é entry point ativo (`commands/manga.py:16`). Teste manual de um download real é recomendável — reporte ao usuário se não houver teste automatizado cobrindo.

**Aceite.**
- `rtk grep -n "_download_single_chapter\|_prompt_download_range" manga_tupi.py` retorna só definições removidas/ausentes.
- `services/manga/download.py` aparece nos imports de `manga_tupi.py`.
- Redução de linhas em `manga_tupi.py` (~150-200).
- `uv run pytest tests/ -k manga` passa.

---

### T4 — [P1] Quebrar `HistoryService.load_history()`

**Problema.** `services/history_service.py:31-417` — função de 387 linhas, 11 chamadas recursivas `return load_history()` (linhas 234,293,305,317,328,349,352,390,396,408,415), complexidade ciclomática >25. Mistura: load JSON, navegação de menu, busca, load episódios, sync AniList, validação de fonte, prompts. Importa UI direto (`history_service.py:15-16`).

**Ação.**
- Extrair helpers puros: `_validate_anime_sources(anime_titles, rep)` (de 191-241), `_resolve_anilist_id(...)`, `_load_persisted_history()`.
- Substituir recursão por loop com estado explícito (a recursão é retry de menu — vira `while` com `continue`).
- Acoplamento UI: receber callbacks de menu por parâmetro em vez de importar `menu_navigate` no módulo. Caller (command) injeta.
- Substituir índices mágicos `info[1..5]` (`history_service.py:50-70`) por NamedTuple/dataclass do schema history (ver T7 — pode fazer junto).

**Risco.** Alto — sem cobertura de teste atual nesta função. **Antes de refatorar, escreva um teste de caracterização** (input history JSON conhecido → output esperado), depois refatore mantendo o teste verde.

**Aceite.**
- `load_history()` < 80 linhas; helpers extraídos < 50 cada.
- Sem `return load_history(` recursivo.
- `history_service.py` não tem `import` de `ui.components` no topo do módulo.
- Teste de caracterização passa antes e depois.

---

### T5 — [P1] Erro silencioso nos plugins

**Problema.** `except httpx.HTTPError: pass` engole falhas sem log em quase todo plugin: `goyabu.py:43,76`, `sushianimes.py:170,211,248`, `anitube.py:75`, `anroll.py:42,69`. Debug de fonte quebrada fica cego.

**Ação.** Trocar `pass` por `logger.debug("<plugin> <metodo> falhou: %s", e)` usando o logger do projeto (confirmar import correto — provável `from utils.logger import logger`). Manter retorno vazio/`None` como hoje (não mudar fluxo). Pode unir com T1 (`except Exception` após remover dependência de `httpx`).

**Aceite.**
- `rtk grep -rn "except httpx.HTTPError:\s*$" scrapers/plugins/` seguido de `pass` retorna vazio.
- Falha de rede emite log debug, não silêncio.
- `uv run pytest` passa.

---

### T6 — [P1] Índice O(1) na deduplicação de título

**Problema.** `search_repository.py:334-360` — `add_anime()` itera TODOS os títulos existentes (`for existing_title in list(self.anime_to_urls)`) e re-normaliza cada um a cada inserção. O(n) por add → O(n²) por busca.

**Ação.** Manter dict auxiliar `{normalized_key: display_title}` atualizado em `add_anime` e limpo em `clear_search_results`. Lookup vira O(1). Normalizar a chave uma vez por inserção, não por comparação.

**Aceite.**
- Sem loop linear sobre `self.anime_to_urls` dentro de `add_anime`.
- `uv run pytest tests/ -k "search or dedup or repository"` passa (dedup multi-fonte continua mesclando — comportamento idêntico).

---

### T7 — [P2] Schema de history tipado

**Problema.** `history_service.py:50-70` usa tupla com índices mágicos (`info[1]`=episódio, `info[2]`=anilist_id, `info[3]`=fonte, `info[4]`=total, `info[5]`=urls), com guardas `len(info) > 4`. Frágil a mudança de schema (comentado como v6).

**Ação.** Definir `dataclass`/`NamedTuple` `HistoryEntry` em `models/models.py` (ou módulo dedicado). Migrar leitura/escrita. Manter compat de leitura do JSON antigo (campos faltantes → default).

**Aceite.** Sem `info[N]` numérico no `history_service.py`. Round-trip de history antigo carrega sem erro. `uv run pytest -k history` passa.

---

### T8 — [P2] Reuso de sessão Selenium nos scrapers manga

**Problema.** `mangalivre.py:60,180,281` e `mugiwaras.py:41,117,217` criam **3 instâncias de browser por fluxo** (search/chapters/pages), ~2-5s cada = 6-15s overhead.

**Ação.** Reusar um driver por fluxo (passar instância ou usar context manager no nível do fluxo). Não mudar lógica de parsing.

**Risco.** Médio — Selenium tem estado. Garantir cleanup (`finally driver.quit()`).

**Aceite.** Cada método não instancia `SeleniumWebDriver()` independente quando chamado em sequência no mesmo fluxo. Teste manual de um capítulo manga funciona.

---

### T9 — [P2] Consolidar loop de playback duplicado

**Problema.** `commands/anime.py:487-531` ≈ `commands/local_anime.py:240-282` — menu pós-playback (next/prev/replay/menu) quase idêntico, duplicado.

**Ação.** Extrair helper compartilhado (em `services/` ou `commands/_shared.py`) que recebe contexto e callbacks de navegação. Ambos os commands chamam.

**Aceite.** Lógica de menu pós-playback existe num só lugar. `uv run pytest -k playback` passa.

---

## 3. Fora de escopo (não fazer sem nova aprovação)

- Reescrever `services/anime/search.py` (1197) ou `anilist_integration.py` (1155) — fatiamento grande, alto risco; PRD próprio.
- Remover `manga_tupi.py` inteiro — ainda é entry point; só consolidar (T3).
- Trocar config Pydantic / introduzir DI para os 81 imports de `settings`.
- Mudar MPV IPC em `utils/video_player.py`.

## 4. Critérios de aceite globais

Antes de cada commit:
- [ ] `uv run ruff check .` limpo
- [ ] `uv run ruff format .` aplicado
- [ ] `uv run pytest` verde
- [ ] Diff rastreia 1:1 à tarefa (sem mudança colateral)
- [ ] Conventional commit, sem `--no-verify`

## 5. Apêndice — comandos úteis

```bash
uv run pytest tests/ -v -k <padrão>      # teste focado
rtk grep -rn "<padrão>" scrapers/plugins/  # localizar
uv run ruff check . && uv run pytest       # gate pré-commit
graphify query "<pergunta>"                # navegar arquitetura
```
